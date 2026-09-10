"""Tests du codegen : le code généré doit être syntaxiquement valide."""

import ast
import asyncio
import contextlib
import importlib
import io
import os
import sys
from pathlib import Path

import pytest

from nova_compiler.codegen import generate_project
from nova_compiler.parser import NovaSyntaxError, parse_file, parse_source

EXAMPLES = Path(__file__).parent.parent / "examples"


def _assert_all_python_files_parse(root: Path):
    py_files = list(root.rglob("*.py"))
    assert py_files, "aucun fichier Python généré"
    for f in py_files:
        source = f.read_text(encoding="utf-8")
        ast.parse(source, filename=str(f))  # lève SyntaxError si invalide


def test_generate_project_from_english_example(tmp_path):
    program = parse_file(EXAMPLES / "blog.en.nova")
    written = generate_project(program, tmp_path)
    assert len(written) > 10
    _assert_all_python_files_parse(tmp_path)
    assert (tmp_path / "backend/app/models.py").exists()
    assert (tmp_path / "backend/app/routers/posts.py").exists()
    assert (tmp_path / "Dockerfile.backend").exists()
    assert (tmp_path / "Dockerfile.frontend").exists()
    assert any((tmp_path / "helm").rglob("Chart.yaml"))


def test_generate_project_from_french_example(tmp_path):
    program = parse_file(EXAMPLES / "blog.fr.nova")
    generate_project(program, tmp_path)
    _assert_all_python_files_parse(tmp_path)
    # Les identifiants générés sont translittérés en ASCII même si le
    # fichier source est en français avec des accents.
    assert (tmp_path / "backend/app/routers/articles.py").exists()


def test_generate_project_from_mixed_example(tmp_path):
    program = parse_file(EXAMPLES / "mixed.nova")
    generate_project(program, tmp_path)
    _assert_all_python_files_parse(tmp_path)


def test_relation_generates_foreign_key(tmp_path):
    program = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(program, tmp_path)
    models = (tmp_path / "backend/app/models.py").read_text(encoding="utf-8")
    assert "author_id" in models
    assert 'foreign_key="authors.id"' in models


def test_relation_foreign_key_is_settable_via_create_and_update_schemas(tmp_path):
    program = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(program, tmp_path)
    models = (tmp_path / "backend/app/models.py").read_text(encoding="utf-8")
    create_block = models.split("class PostCreate(SQLModel):")[1].split("class")[0]
    update_block = models.split("class PostUpdate(SQLModel):")[1].split("class")[0]
    assert "author_id" in create_block
    assert "author_id" in update_block


def test_form_page_generates_explicit_setters_not_reflex_auto_setters(tmp_path):
    """Régression : le code généré référence `<State>.set_new_<champ>` dans
    `on_change`. Ce setter doit être défini explicitement dans la classe
    State plutôt que de dépendre du setter auto-généré par Reflex
    (`set_<var>`), car ce comportement implicite a varié selon les versions
    de Reflex et a provoqué en pratique une AttributeError à l'exécution
    (`'XxxState' has no attribute 'set_new_xxx'`) alors que le code généré
    est syntaxiquement valide."""
    program = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(program, tmp_path)
    frontend_files = list((tmp_path / "frontend").rglob("*.py"))
    main_files = [f for f in frontend_files if f.name not in ("rxconfig.py", "__init__.py", "custom.py")]
    assert main_files, "fichier frontend principal introuvable"
    source = main_files[0].read_text(encoding="utf-8")

    # La page `NewPost` (mode form) doit générer un state avec un setter
    # explicite pour chaque champ, défini dans la classe elle-même.
    state_block = source.split("class NewPostState(rx.State):")[1].split("class ")[0]
    assert "def set_new_title(self, value: str) -> None:" in state_block
    assert "self.new_title = value" in state_block

    # Et la vue doit bien référencer ce setter explicite dans on_change.
    assert "on_change=NewPostState.set_new_title" in source


def test_frontend_dockerfile_does_not_use_prod_mode_with_split_ports(tmp_path):
    """Régression : Reflex refuse de démarrer si `--env prod` est combiné à
    des `--backend-port`/`--frontend-port` différents ("In prod mode,
    frontend and backend must run on the same port"), ce qui faisait
    planter le conteneur frontend (`docker compose up`) alors que l'image
    se construisait sans erreur. Le Dockerfile généré doit donc rester en
    mode dev tant que les deux ports restent distincts."""
    program = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(program, tmp_path)
    dockerfile = (tmp_path / "Dockerfile.frontend").read_text(encoding="utf-8")
    assert '"--env", "dev"' in dockerfile
    assert '"--env", "prod"' not in dockerfile


def test_frontend_dockerfile_installs_unzip_for_bun(tmp_path):
    """Régression : `reflex run` télécharge et extrait son runtime Bun au
    premier démarrage, ce qui échoue dans l'image `python:3.11-slim` avec
    `SystemPackageMissingError: System package 'unzip' is missing` — le
    paquet n'est pas présent par défaut. Le Dockerfile généré doit
    l'installer avant de lancer Reflex."""
    program = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(program, tmp_path)
    dockerfile = (tmp_path / "Dockerfile.frontend").read_text(encoding="utf-8")
    assert "unzip" in dockerfile


def test_form_submit_redirects_to_the_matching_table_page(tmp_path):
    """Après création d'un enregistrement via un formulaire, l'utilisateur
    doit revenir sur la page qui liste cette entité (ici `Posts`, en mode
    table) plutôt que de rester sur le formulaire vide."""
    program = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(program, tmp_path)
    frontend_files = list((tmp_path / "frontend").rglob("*.py"))
    source = [f for f in frontend_files if f.name not in ("rxconfig.py", "__init__.py", "custom.py")][0].read_text(
        encoding="utf-8"
    )
    submit_block = source.split("class NewPostState(rx.State):")[1].split("class ")[0]
    assert 'return rx.redirect("/posts")' in submit_block
    # Les champs du formulaire sont réinitialisés après l'envoi.
    assert 'self.new_title = ""' in submit_block


def test_navbar_and_create_link_are_generated(tmp_path):
    """Une barre de navigation partagée (une par page définie dans le
    fichier .nova) et un bouton "+ <FormPage>" sur la page tableau
    correspondante doivent être générés, pour ne pas laisser les pages
    isolées les unes des autres."""
    program = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(program, tmp_path)
    frontend_files = list((tmp_path / "frontend").rglob("*.py"))
    source = [f for f in frontend_files if f.name not in ("rxconfig.py", "__init__.py", "custom.py")][0].read_text(
        encoding="utf-8"
    )
    assert "def nova_navbar() -> rx.Component:" in source
    assert 'rx.link("Posts", href="/posts"' in source
    assert 'rx.link("NewPost", href="/new-post"' in source
    assert 'rx.link(rx.button("+ NewPost", size="2"), href="/new-post")' in source


def test_field_pattern_generates_regex_validation(tmp_path):
    """Un champ avec `motif`/`pattern = "..."` doit produire une contrainte
    Pydantic `pattern=r"..."` sur le modèle de table ET sur les schémas
    Create/Update, pour que l'API rejette une valeur invalide (422) sans
    code de validation écrit à la main."""
    src = """
    entity Contact {
      field email: string required pattern = "^[^@]+@[^@]+$"
    }
    api Contact { list create update }
    """
    program = parse_source(src)
    generate_project(program, tmp_path)
    models = (tmp_path / "backend/app/models.py").read_text(encoding="utf-8")

    table_block = models.split("class Contact(SQLModel, table=True):")[1].split("class")[0]
    create_block = models.split("class ContactCreate(SQLModel):")[1].split("class")[0]
    update_block = models.split("class ContactUpdate(SQLModel):")[1].split("class")[0]
    for block in (table_block, create_block, update_block):
        assert 'pattern=r"^[^@]+@[^@]+$"' in block


def test_custom_backend_extension_point_is_scaffolded_and_wired(tmp_path):
    """Un dossier routers_custom/ doit être créé (une fois) pour accueillir
    du code métier hors DSL (validations avancées, requêtes complexes,
    écritures en base sur mesure), et app/main.py doit l'inclure
    automatiquement — sans quoi la seule façon d'étendre l'API générée
    serait d'éditer des fichiers regénérés à chaque compilation."""
    program = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(program, tmp_path)

    example = tmp_path / "backend/app/routers_custom/example.py"
    assert example.exists()
    assert "router = APIRouter" in example.read_text(encoding="utf-8")

    main_py = (tmp_path / "backend/app/main.py").read_text(encoding="utf-8")
    assert "from . import routers_custom" in main_py
    assert "pkgutil.iter_modules(routers_custom.__path__)" in main_py


def test_generated_backend_actually_imports_and_wires_custom_router(tmp_path):
    """Régression : la boucle de découverte des routeurs custom utilisait
    `importlib.import_module(..., package=__name__)` dans app/main.py. Or
    `__name__` y vaut `"app.main"` (un module, pas un paquet) : l'import
    relatif plantait avec `ModuleNotFoundError: 'app.main' is not a
    package`. Le code généré était syntaxiquement valide (passait
    `ast.parse` et `py_compile`) mais ne démarrait jamais — seul un import
    réel du module pouvait le détecter. Il fallait `package=__package__`."""
    program = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(program, tmp_path)
    backend_dir = str(tmp_path / "backend")
    sys.path.insert(0, backend_dir)
    for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[mod_name]
    try:
        main = importlib.import_module("app.main")
        # Une vraie requête HTTP via TestClient, plutôt qu'inspecter la
        # structure interne de `app.routes` (sa forme a changé entre
        # versions de FastAPI — les routeurs inclus n'y apparaissent plus
        # comme de simples objets Route) : c'est la façon fiable de
        # vérifier que la route est réellement câblée et répond.
        from fastapi.testclient import TestClient

        client = TestClient(main.app)
        assert client.get("/custom/ping").status_code == 200
        assert client.get("/health").status_code == 200
    finally:
        sys.path.remove(backend_dir)
        for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
            del sys.modules[mod_name]


def test_custom_extension_scaffolds_are_never_overwritten(tmp_path):
    """Recompiler le même projet ne doit jamais écraser le code métier
    écrit à la main dans routers_custom/ ou custom.py — seuls les fichiers
    strictement générés depuis l'AST sont réécrits à chaque fois."""
    program = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(program, tmp_path)

    backend_custom = tmp_path / "backend/app/routers_custom/example.py"
    frontend_custom = next((tmp_path / "frontend").rglob("custom.py"))
    backend_custom.write_text("# modifié à la main par l'utilisateur\nrouter = None\n", encoding="utf-8")
    frontend_custom.write_text("# modifié à la main par l'utilisateur\n", encoding="utf-8")

    generate_project(program, tmp_path)  # nouvelle compilation, même AST

    assert backend_custom.read_text(encoding="utf-8") == "# modifié à la main par l'utilisateur\nrouter = None\n"
    assert frontend_custom.read_text(encoding="utf-8") == "# modifié à la main par l'utilisateur\n"


def test_alembic_scaffold_generated_once_for_sql_backend(tmp_path):
    """Migrations Alembic (tâche #38, choix confirmé par Alan : « structure
    générée une fois + `nova migrate` ») : `backend/alembic.ini`,
    `backend/migrations/env.py`/`script.py.mako`/`versions/` doivent exister
    pour un backend SQL, `alembic` doit être dans `requirements.txt`, et —
    exactement comme `routers_custom/` (voir test_custom_extension_scaffolds_
    are_never_overwritten ci-dessus) — rien de tout ça ne doit être réécrit
    par une recompilation (l'historique réel des révisions appliquées à une
    base de production serait sinon détruit à chaque `nova compile`).
    L'exécution réelle d'`alembic revision --autogenerate`/`upgrade head`
    contre ce scaffold est couverte par tests/test_cli.py (processus
    `alembic` réel, pas de mock)."""
    program = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(program, tmp_path)

    alembic_ini = tmp_path / "backend/alembic.ini"
    env_py = tmp_path / "backend/migrations/env.py"
    script_mako = tmp_path / "backend/migrations/script.py.mako"
    versions_dir = tmp_path / "backend/migrations/versions"
    assert alembic_ini.exists()
    assert "script_location = migrations" in alembic_ini.read_text(encoding="utf-8")
    env_src = env_py.read_text(encoding="utf-8")
    assert "from app import models" in env_src
    assert "from app.database import DATABASE_URL, engine" in env_src
    assert "target_metadata = SQLModel.metadata" in env_src
    assert "import sqlmodel" in script_mako.read_text(encoding="utf-8")
    assert versions_dir.is_dir()

    requirements = (tmp_path / "backend/requirements.txt").read_text(encoding="utf-8")
    assert "alembic" in requirements

    alembic_ini.write_text(alembic_ini.read_text(encoding="utf-8") + "\n# modifié à la main\n", encoding="utf-8")
    (versions_dir / "0001_fake_revision.py").write_text("# révision déjà appliquée en prod\n", encoding="utf-8")

    generate_project(program, tmp_path)  # nouvelle compilation, même AST

    assert alembic_ini.read_text(encoding="utf-8").endswith("\n# modifié à la main\n")
    assert (versions_dir / "0001_fake_revision.py").read_text(encoding="utf-8") == "# révision déjà appliquée en prod\n"


def test_custom_frontend_extension_point_is_scaffolded_and_wired(tmp_path):
    program = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(program, tmp_path)

    frontend_custom = next((tmp_path / "frontend").rglob("custom.py"))
    assert "def register(app: rx.App) -> None:" in frontend_custom.read_text(encoding="utf-8")

    main_files = [
        f
        for f in (tmp_path / "frontend").rglob("*.py")
        if f.name not in ("rxconfig.py", "__init__.py", "custom.py")
    ]
    main_source = main_files[0].read_text(encoding="utf-8")
    assert "from . import custom as _custom" in main_source
    assert "_custom.register(app)" in main_source


# ---------------------------------------------------------------- style ---


def test_style_block_generates_class_name_and_inline_style_props(tmp_path):
    """Le bloc `style { couleur_fond: "#445566" classe: "carte-produit" }`
    du fichier .nova doit se retrouver dans le composant Reflex généré :
    `classe`/`class` -> `class_name=`, les autres clés connues de
    `keywords.STYLE_ALIASES` -> la vraie propriété CSS (camelCase) dans un
    dict `style={...}`."""
    program = parse_file(EXAMPLES / "full_featured.nova")
    generate_project(program, tmp_path)
    frontend_files = [
        f
        for f in (tmp_path / "frontend").rglob("*.py")
        if f.name not in ("rxconfig.py", "__init__.py", "custom.py")
    ]
    source = frontend_files[0].read_text(encoding="utf-8")
    assert 'class_name="carte-produit"' in source
    assert '"backgroundColor": "#445566"' in source


def test_external_css_file_is_copied_into_frontend_assets(tmp_path):
    """`application { css: "theme.css" }` doit copier le contenu réel du
    fichier (résolu relativement au dossier du .nova source) dans
    `frontend/<app>/assets/theme.css`, et l'app Reflex générée doit le
    référencer via `stylesheets=["/theme.css"]`."""
    program = parse_file(EXAMPLES / "full_featured.nova")
    generate_project(program, tmp_path, source_dir=EXAMPLES)

    asset_files = list((tmp_path / "frontend").rglob("theme.css"))
    assert len(asset_files) == 1
    copied = asset_files[0].read_text(encoding="utf-8")
    original = (EXAMPLES / "theme.css").read_text(encoding="utf-8")
    assert copied == original
    assert ".carte-produit" in copied  # pas un placeholder vide

    frontend_files = [
        f
        for f in (tmp_path / "frontend").rglob("*.py")
        if f.name not in ("rxconfig.py", "__init__.py", "custom.py")
    ]
    source = frontend_files[0].read_text(encoding="utf-8")
    assert 'stylesheets=["/theme.css"]' in source


def test_css_placeholder_left_when_source_dir_not_given(tmp_path):
    """Sans `source_dir` (ou si le fichier référencé n'existe pas), un
    placeholder vide est laissé à l'emplacement attendu par Reflex plutôt
    que de faire planter la génération."""
    program = parse_file(EXAMPLES / "full_featured.nova")
    generate_project(program, tmp_path)  # pas de source_dir
    asset_files = list((tmp_path / "frontend").rglob("theme.css"))
    assert len(asset_files) == 1
    placeholder = asset_files[0].read_text(encoding="utf-8")
    assert ".carte-produit" not in placeholder  # pas le vrai contenu de theme.css


# ----------------------------------------------------------------- auth ---


def test_auth_and_query_flow_end_to_end(tmp_path):
    """Vérifie le flux JWT complet ET le point de requête déclarative en
    exécutant réellement le backend généré (pas seulement une validation
    de syntaxe) : inscription, connexion, accès refusé sans jeton, refusé
    avec le mauvais rôle, autorisé pour un admin (bloc `auth { roles:
    admin, user }` + `api Produit { ... proteger: admin }`), puis que
    `requete ProduitsChers sur Produit { filtre: prix > 100 ... }` filtre/
    trie/limite les données réelles.

    Les deux vérifications sont regroupées dans un seul test (plutôt que
    deux tests qui importeraient chacun `app.main`) car le module `auth.py`
    généré définit une table SQLModel `nova_users` sur le registre global
    partagé de SQLAlchemy : un second `importlib.import_module("app.main")`
    dans le même process, même après avoir vidé `sys.modules`, redéfinit la
    même classe de table et lève `InvalidRequestError: Table 'nova_users'
    is already defined for this MetaData instance`."""
    program = parse_file(EXAMPLES / "full_featured.nova")
    generate_project(program, tmp_path, source_dir=EXAMPLES)

    requirements = (tmp_path / "backend/requirements.txt").read_text(encoding="utf-8")
    assert "bcrypt" in requirements
    assert "python-jose" in requirements
    assert "python-multipart" in requirements

    router_src = (tmp_path / "backend/app/routers/_requetes.py").read_text(encoding="utf-8")
    assert "models.Produit.prix > 100" in router_src
    assert "order_by(models.Produit.prix.desc())" in router_src
    assert ".limit(10)" in router_src
    # `requete ProduitsAlerte` : filtre ET de premier niveau + bloc `ou: {
    # ... }` -> un `.where()` ET-é (comportement historique) suivi d'un seul
    # `.where(or_(...))` pour le groupe OU-é (voir _generate_query_router).
    assert "from sqlalchemy import or_" in router_src
    assert "query = query.where(models.Produit.stock < 10)" in router_src
    assert "query.where(or_(models.Produit.prix < 10, models.Produit.prix > 1000))" in router_src
    # `requete AccessoiresAvecProduit` : jointure explicite -> `select()` sur
    # les deux entités + `.join(...)`, filtre sur le champ qualifié de
    # l'entité jointe, réponse = liste de dicts (pas de response_model
    # unique) avec l'entité jointe nichée sous une clé nommée d'après elle.
    assert "query = select(models.Accessoire, models.Produit)" in router_src
    assert "query = query.join(models.Produit, models.Accessoire.produit_id == models.Produit.id)" in router_src
    assert "query = query.where(models.Produit.prix > 100)" in router_src
    assert 'item["produit"] = row[1].model_dump()' in router_src

    backend_dir = str(tmp_path / "backend")
    sys.path.insert(0, backend_dir)
    db_url = f"sqlite:///{tmp_path}/test_auth_query.db"
    old_db_url = os.environ.get("NOVA_DATABASE_URL")
    os.environ["NOVA_DATABASE_URL"] = db_url
    for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[mod_name]
    try:
        from fastapi.testclient import TestClient

        main = importlib.import_module("app.main")
        with TestClient(main.app) as client:
            r = client.post(
                "/auth/register",
                json={"email": "admin@test.com", "password": "secret123"},
            )
            assert r.status_code == 201
            assert r.json()["role"] == "admin"  # premier compte créé -> admin automatique

            r = client.post(
                "/auth/register", json={"email": "user@test.com", "password": "secret123"}
            )
            assert r.status_code == 201
            assert r.json()["role"] == "user"  # rôle par défaut pour tout compte suivant

            # Sécurité : un `role` fourni dans la charge utile de /auth/register
            # est ignoré (UserCreate ne porte plus de champ `role`) — un compte
            # qui n'est pas le premier ne peut PAS s'auto-attribuer "admin".
            r = client.post(
                "/auth/register",
                json={"email": "sneaky@test.com", "password": "secret123", "role": "admin"},
            )
            assert r.status_code == 201
            sneaky_id = r.json()["id"]
            assert r.json()["role"] == "user"

            r = client.post(
                "/auth/login", data={"username": "user@test.com", "password": "secret123"}
            )
            user_id = None  # récupéré via /auth/me juste après
            r2 = client.get("/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
            user_id = r2.json()["id"]

            # inscrire deux fois le même email doit échouer
            r = client.post(
                "/auth/register", json={"email": "admin@test.com", "password": "x"}
            )
            assert r.status_code == 400

            r = client.post(
                "/auth/login", data={"username": "admin@test.com", "password": "secret123"}
            )
            assert r.status_code == 200
            admin_token = r.json()["access_token"]

            r = client.post(
                "/auth/login", data={"username": "user@test.com", "password": "secret123"}
            )
            assert r.status_code == 200
            user_token = r.json()["access_token"]

            # mauvais mot de passe -> 401
            r = client.post(
                "/auth/login", data={"username": "admin@test.com", "password": "wrong"}
            )
            assert r.status_code == 401

            r = client.get("/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
            assert r.status_code == 200
            assert r.json()["email"] == "admin@test.com"

            admin_headers = {"Authorization": f"Bearer {admin_token}"}
            payload = {"nom": "Ordinateur", "prix": 1200, "stock": 5}
            # `api Produit { ... proteger: admin }` : toute l'API est protégée.
            assert client.post("/produits", json=payload).status_code == 401
            assert (
                client.post(
                    "/produits", json=payload, headers={"Authorization": f"Bearer {user_token}"}
                ).status_code
                == 403
            )
            r = client.post("/produits", json=payload, headers=admin_headers)
            assert r.status_code == 201
            ordinateur_id = r.json()["id"]

            produit_ids = {}
            for nom, prix in [("Stylo", 2), ("Chaise", 80), ("Bureau", 350)]:
                r = client.post(
                    "/produits", json={"nom": nom, "prix": prix, "stock": 1}, headers=admin_headers
                )
                produit_ids[nom] = r.json()["id"]

            r = client.get("/requetes/produits-chers")
            assert r.status_code == 200
            rows = r.json()
            assert [row["nom"] for row in rows] == ["Ordinateur", "Bureau"]
            assert all(row["prix"] > 100 for row in rows)

            # `requete ProduitsAlerte` : stock < 10 (vrai pour les 4
            # produits créés ci-dessus) ET (prix < 10 OU prix > 1000) ->
            # seuls Stylo (prix=2) et Ordinateur (prix=1200) correspondent ;
            # Chaise (80) et Bureau (350) sont exclus par le groupe OU.
            r = client.get("/requetes/produits-alerte")
            assert r.status_code == 200
            alerte_noms = {row["nom"] for row in r.json()}
            assert alerte_noms == {"Stylo", "Ordinateur"}

            # PATCH /auth/users/{id}/role : seul un admin peut promouvoir un
            # compte — un "user" simple se fait refuser (403), un admin peut
            # promouvoir "sneaky" (qui n'avait pas pu s'auto-attribuer
            # "admin" à l'inscription, voir ci-dessus).
            r = client.patch(
                f"/auth/users/{sneaky_id}/role",
                json={"role": "admin"},
                headers={"Authorization": f"Bearer {user_token}"},
            )
            assert r.status_code == 403

            r = client.patch(
                f"/auth/users/{sneaky_id}/role", json={"role": "admin"}, headers=admin_headers
            )
            assert r.status_code == 200
            assert r.json()["role"] == "admin"

            # Rôle inconnu (absent de `auth { roles: ... }`) refusé (422).
            r = client.patch(
                f"/auth/users/{user_id}/role", json={"role": "superadmin"}, headers=admin_headers
            )
            assert r.status_code == 422

            # `calendrier Ajouts sur Produit { champ_date: date_ajout ... }`,
            # protégé (hérite de `api Produit { proteger: admin }`) : sa
            # route d'export iCal `/ics/ajouts.ics` doit l'être aussi (401
            # sans jeton), et refléter les enregistrements réels une fois
            # authentifié (`date_ajout` est un champ `date_heure` -> DTSTART
            # horodaté, pas `;VALUE=DATE`, voir
            # test_calendar_ics_export_date_only_field_real_execution pour
            # le cas `date`).
            assert client.get("/ics/ajouts.ics").status_code == 401
            client.post(
                "/produits",
                json={"nom": "Lampe", "prix": 20, "stock": 3, "date_ajout": "2026-05-01T09:00:00"},
                headers=admin_headers,
            )
            r = client.get("/ics/ajouts.ics", headers=admin_headers)
            assert r.status_code == 200
            assert r.headers["content-type"].startswith("text/calendar")
            assert "BEGIN:VCALENDAR" in r.text
            assert "DTSTART:20260501T090000Z" in r.text
            assert "SUMMARY:Lampe" in r.text

            # `entité Produit { ... possede_plusieurs Accessoire }` +
            # `entité Accessoire { ... appartient_a Produit }` : `liste`/
            # `obtenir` sur Produit matérialisent un résumé texte des
            # Accessoire liés (`accessoires_text`, voir
            # api_fastapi._has_many_relation_info) — public (`api
            # Accessoire` n'est pas protégée), mais `/produits` reste
            # protégée par `proteger: admin` comme le reste de cette api.
            client.post("/accessoires", json={"nom": "Souris", "produit_id": ordinateur_id})
            client.post("/accessoires", json={"nom": "Clavier", "produit_id": ordinateur_id})
            r = client.get("/produits", headers=admin_headers)
            assert r.status_code == 200
            ordinateur_row = next(row for row in r.json() if row["id"] == ordinateur_id)
            assert ordinateur_row["accessoires_text"] == "Souris, Clavier"
            r = client.get(f"/produits/{ordinateur_id}", headers=admin_headers)
            assert r.status_code == 200
            assert r.json()["accessoires_text"] == "Souris, Clavier"
            # Un produit sans accessoire lié -> résumé texte vide (pas de
            # KeyError/None, voir `_related_text_lines` dans api_fastapi.py).
            stylo_row = next(row for row in client.get("/produits", headers=admin_headers).json() if row["nom"] == "Stylo")
            assert stylo_row["accessoires_text"] == ""

            # `requete AccessoiresAvecProduit sur Accessoire { jointure:
            # Produit sur produit_id = Produit.id filtre: Produit.prix > 100
            # }` : jointure explicite (voir ast_nodes.QueryJoin), filtre sur
            # un champ de l'entité JOINTE (Produit), pas de l'entité
            # principale (Accessoire) — Souris/Clavier (liés à Ordinateur,
            # prix=1200) doivent apparaître, un accessoire lié à Stylo
            # (prix=2) ne doit pas.
            client.post("/accessoires", json={"nom": "Housse", "produit_id": produit_ids["Stylo"]})
            r = client.get("/requetes/accessoires-avec-produit")
            assert r.status_code == 200
            join_rows = r.json()
            assert {row["nom"] for row in join_rows} == {"Souris", "Clavier"}
            assert all(row["produit"]["nom"] == "Ordinateur" for row in join_rows)
            assert all(row["produit"]["prix"] == 1200 for row in join_rows)
    finally:
        sys.path.remove(backend_dir)
        if old_db_url is None:
            os.environ.pop("NOVA_DATABASE_URL", None)
        else:
            os.environ["NOVA_DATABASE_URL"] = old_db_url
        for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
            del sys.modules[mod_name]


# ---------------------------------------------------- pages multi-entités ---

def test_multi_show_page_generates_one_state_per_entity_and_stacks_sections(tmp_path):
    """`page Dashboard { show Produit ... show Commande ... }` : chaque
    `show` doit produire son PROPRE state Reflex (`Dashboard<Entite>State`,
    voir codegen/ui_reflex.py::_state_class_name), chargé au montage via
    `on_mount=[...]` (une liste, pas un seul gestionnaire), et sa section
    (table/carte/formulaire) empilée dans l'ordre déclaré."""
    src = """
    entity Produit {
      field nom: string required
      field prix: float required
    }
    entity Commande {
      field client: string required
    }
    api Produit { liste creer }
    api Commande { liste creer }
    page Dashboard {
      show Produit as table titre "Produits"
      show Commande as card titre "Commandes"
    }
    """
    program = parse_source(src)
    generate_project(program, tmp_path)
    source = _frontend_main_source(tmp_path)

    assert "class DashboardProduitState(rx.State):" in source
    assert "class DashboardCommandeState(rx.State):" in source
    assert "on_mount=[DashboardProduitState.load_rows, DashboardCommandeState.load_rows]" in source
    dashboard_fn = source.split("def dashboard_page()")[1].split("\ndef ")[0]
    # La section Produit (table) précède la section Commande (carte), dans
    # l'ordre déclaré dans le fichier .nova.
    assert dashboard_fn.index("Produits") < dashboard_fn.index("Commandes")
    assert "rx.table.root(" in dashboard_fn
    assert "rx.grid(" in dashboard_fn


def test_single_show_page_state_naming_unchanged_for_backward_compatibility(tmp_path):
    """Une page à un seul `show` doit continuer à produire exactement le
    nom de state historique `<NomPage>State` (pas `<NomPage><Entite>State`)
    — non-régression explicite pour les projets déjà générés avant l'ajout
    des pages multi-entités."""
    src = """
    entity Produit { field nom: string required }
    api Produit { liste creer }
    page Produits { show Produit as table }
    """
    program = parse_source(src)
    generate_project(program, tmp_path)
    source = _frontend_main_source(tmp_path)
    assert "class ProduitsState(rx.State):" in source
    assert "ProduitsProduitState" not in source


# ---------------------------------------------------- relations has_many ---


def test_has_many_generates_read_schema_and_text_summary_in_router(tmp_path):
    """`entity Parent { has_many Child }` + `entity Child { belongs_to
    Parent }` : `models.py` doit générer un schéma `ParentRead` (portant un
    champ `<table_enfant>_text`), et le routeur de `Parent` doit
    matérialiser ce résumé pour `list`/`get` (`response_model=ParentRead`),
    tout en laissant `create`/`update` renvoyer `Parent` (le modèle de
    table) inchangé — voir `_has_many_relation_info` dans
    codegen/api_fastapi.py."""
    src = """
    entity Parent {
      field name: string required
      has_many Child
    }
    entity Child {
      field label: string required
      belongs_to Parent
    }
    api Parent { liste creer obtenir }
    api Child { liste creer }
    """
    program = parse_source(src)
    generate_project(program, tmp_path)

    models_src = (tmp_path / "backend/app/models.py").read_text(encoding="utf-8")
    assert "class ParentRead(SQLModel):" in models_src
    assert 'children_text: str = ""' in models_src

    router_src = (tmp_path / "backend/app/routers/parents.py").read_text(encoding="utf-8")
    assert 'response_model=list[ParentRead]' in router_src
    assert 'response_model=ParentRead' in router_src
    assert 'response_model=Parent, status_code=201' in router_src  # create : inchangé
    assert "Child.parent_id == item.id" in router_src
    assert 'data["children_text"]' in router_src


def test_has_many_child_without_reciprocal_belongs_to_is_never_generated(tmp_path):
    """Non-régression : sans `_validate_relations` (parser.py), une relation
    `has_many` mal déclarée pourrait atteindre la génération et planter au
    runtime (`AttributeError: Child has no attribute parent_id`). On
    vérifie ici que la validation intercepte bien le cas AVANT la
    génération — voir aussi test_parser.py::
    test_has_many_without_reciprocal_belongs_to_raises_syntax_error."""
    src = """
    entity Parent {
      field name: string required
      has_many Child
    }
    entity Child {
      field label: string required
    }
    """
    with pytest.raises(NovaSyntaxError):
        parse_source(src)


def test_has_many_materializes_related_records_as_text_summary_real_execution(tmp_path):
    """Exécution réelle (pas seulement `ast.parse`) : `GET /parents/` et
    `GET /parents/{id}` renvoient bien un résumé texte des `Child` liés
    (jointure faite côté backend via la clé étrangère générée par
    `belongs_to`), vide pour un parent sans enfant, et `create`/`update`
    continuent de fonctionner normalement (pas de régression sur le CRUD de
    base)."""
    src = """
    entity Parent {
      field name: string required
      has_many Child
    }
    entity Child {
      field label: string required
      belongs_to Parent
    }
    api Parent { liste creer obtenir }
    api Child { liste creer }
    """
    program = parse_source(src)
    generate_project(program, tmp_path)

    backend_dir = str(tmp_path / "backend")
    sys.path.insert(0, backend_dir)
    old_db_url = os.environ.get("NOVA_DATABASE_URL")
    os.environ["NOVA_DATABASE_URL"] = f"sqlite:///{tmp_path}/test_has_many.db"
    for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[mod_name]
    try:
        from fastapi.testclient import TestClient

        main = importlib.import_module("app.main")
        with TestClient(main.app) as client:
            r = client.post("/parents/", json={"name": "Alice"})
            assert r.status_code == 201
            alice_id = r.json()["id"]
            assert "children_text" not in r.json()  # create renvoie `Parent`, pas `ParentRead`

            r = client.post("/parents/", json={"name": "Bob"})
            bob_id = r.json()["id"]

            client.post("/children/", json={"label": "Tâche 1", "parent_id": alice_id})
            client.post("/children/", json={"label": "Tâche 2", "parent_id": alice_id})

            r = client.get("/parents/")
            assert r.status_code == 200
            rows = {row["id"]: row for row in r.json()}
            assert rows[alice_id]["children_text"] == "Tâche 1, Tâche 2"
            assert rows[bob_id]["children_text"] == ""  # aucun enfant lié

            r = client.get(f"/parents/{alice_id}")
            assert r.status_code == 200
            assert r.json()["children_text"] == "Tâche 1, Tâche 2"
    finally:
        sys.path.remove(backend_dir)
        if old_db_url is None:
            os.environ.pop("NOVA_DATABASE_URL", None)
        else:
            os.environ["NOVA_DATABASE_URL"] = old_db_url
        for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
            del sys.modules[mod_name]


# --------------------------------------------------- validation croisée ---


def test_validation_injects_check_in_create_and_update_router(tmp_path):
    """`validation <Nom> sur <Entite> { regle: ... message: "..." }` doit
    injecter une vérification dans `create`/`update` (pas `list`/`get`/
    `delete`, qui ne mutent pas les champs concernés) — voir
    `_validation_check_lines` dans codegen/api_fastapi.py."""
    src = """
    entity Reservation {
      field nom: string required
      field date_debut: datetime required
      field date_fin: datetime required
    }
    api Reservation { liste creer modifier supprimer }
    validation DatesCoherentes sur Reservation {
      regle: date_fin > date_debut message: "La date de fin doit etre apres le debut."
    }
    """
    program = parse_source(src)
    generate_project(program, tmp_path)
    router_src = (tmp_path / "backend/app/routers/reservations.py").read_text(encoding="utf-8")
    assert router_src.count("raise HTTPException(status_code=422") == 2  # create + update
    assert "item.date_fin is not None and item.date_debut is not None" in router_src
    assert "not (item.date_fin > item.date_debut)" in router_src
    assert "La date de fin doit etre apres le debut." in router_src


def test_validation_not_generated_without_validation_block(tmp_path):
    """Régression : sans bloc `validation`, aucune vérification 422
    supplémentaire n'est injectée (ex. blog.en.nova)."""
    program = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(program, tmp_path)
    for router_file in (tmp_path / "backend/app/routers").glob("*.py"):
        assert "status_code=422" not in router_file.read_text(encoding="utf-8")


def test_validation_enforced_real_execution(tmp_path):
    """Exécute réellement le backend généré : une règle violée renvoie 422
    (SANS toucher la base — vérifié en relisant la liste après une tentative
    de modification invalide), une règle respectée laisse passer create ET
    update normalement."""
    src = """
    entity Reservation {
      field nom: string required
      field date_debut: datetime required
      field date_fin: datetime required
    }
    api Reservation { liste creer modifier }
    validation DatesCoherentes sur Reservation {
      regle: date_fin > date_debut message: "La date de fin doit etre apres le debut."
    }
    """
    program = parse_source(src)
    generate_project(program, tmp_path)

    backend_dir = str(tmp_path / "backend")
    sys.path.insert(0, backend_dir)
    old_db_url = os.environ.get("NOVA_DATABASE_URL")
    os.environ["NOVA_DATABASE_URL"] = f"sqlite:///{tmp_path}/test_validation.db"
    for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[mod_name]
    try:
        from fastapi.testclient import TestClient

        main = importlib.import_module("app.main")
        with TestClient(main.app) as client:
            r = client.post(
                "/reservations/",
                json={
                    "nom": "Invalide",
                    "date_debut": "2026-01-10T10:00:00",
                    "date_fin": "2026-01-01T10:00:00",
                },
            )
            assert r.status_code == 422
            assert "date de fin" in r.json()["detail"]
            assert client.get("/reservations/").json() == []  # rien écrit en base

            r = client.post(
                "/reservations/",
                json={
                    "nom": "Valide",
                    "date_debut": "2026-01-01T10:00:00",
                    "date_fin": "2026-01-10T10:00:00",
                },
            )
            assert r.status_code == 201
            item_id = r.json()["id"]

            r = client.put(
                f"/reservations/{item_id}", json={"date_fin": "2025-12-31T10:00:00"}
            )
            assert r.status_code == 422
            unchanged = client.get("/reservations/").json()[0]
            assert unchanged["date_fin"] == "2026-01-10T10:00:00"  # update rejeté, pas appliqué

            r = client.put(
                f"/reservations/{item_id}", json={"date_fin": "2026-02-01T10:00:00"}
            )
            assert r.status_code == 200
            assert r.json()["date_fin"] == "2026-02-01T10:00:00"
    finally:
        sys.path.remove(backend_dir)
        if old_db_url is None:
            os.environ.pop("NOVA_DATABASE_URL", None)
        else:
            os.environ["NOVA_DATABASE_URL"] = old_db_url
        for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
            del sys.modules[mod_name]


def test_validation_rich_expressions_functions_and_arithmetic_real_execution(tmp_path):
    """Mini-langage de validation étendu (au-delà de la simple comparaison
    directe entre deux champs) : fonctions whitelist (min/max/round/abs,
    voir kw.VALIDATION_FUNCTIONS) et arithmétique (+/-) combinant PLUS de
    deux champs. Exécute réellement le backend généré : une règle violée
    renvoie 422 sans écrire en base, une règle respectée laisse passer."""
    src = """
    entity Invoice {
      field nom: string required
      field prix_ht: float required
      field frais_port: float required
      field prix_ttc: float required
      field remise: float required
    }
    api Invoice { liste creer }
    validation InvoiceCoherente sur Invoice {
      regle: prix_ttc == prix_ht + frais_port message: "Le TTC doit valoir HT + frais de port."
      regle: min(prix_ht, remise) >= 0 message: "Le prix HT et la remise doivent etre positifs ou nuls."
      regle: round(prix_ht, 2) == prix_ht message: "Le prix HT ne doit pas avoir plus de 2 decimales."
    }
    """
    program = parse_source(src)
    generate_project(program, tmp_path)

    router_src = (tmp_path / "backend/app/routers/invoices.py").read_text(encoding="utf-8")
    assert "not (item.prix_ttc == (item.prix_ht + item.frais_port))" in router_src
    assert "not (min(item.prix_ht, item.remise) >= 0)" in router_src
    assert "not (round(item.prix_ht, 2) == item.prix_ht)" in router_src

    backend_dir = str(tmp_path / "backend")
    sys.path.insert(0, backend_dir)
    old_db_url = os.environ.get("NOVA_DATABASE_URL")
    os.environ["NOVA_DATABASE_URL"] = f"sqlite:///{tmp_path}/test_validation_rich.db"
    for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[mod_name]
    try:
        from fastapi.testclient import TestClient

        main = importlib.import_module("app.main")
        with TestClient(main.app) as client:
            # TTC != HT + frais de port -> rejeté par la 1ère règle.
            r = client.post(
                "/invoices/",
                json={"nom": "Incohérente", "prix_ht": 100.0, "frais_port": 10.0, "prix_ttc": 999.0, "remise": 0.0},
            )
            assert r.status_code == 422
            assert "TTC doit valoir" in r.json()["detail"]
            assert client.get("/invoices/").json() == []

            # remise négative -> rejeté par la 2e règle (min(prix_ht, remise) >= 0).
            r = client.post(
                "/invoices/",
                json={"nom": "RemiseInvalide", "prix_ht": 100.0, "frais_port": 10.0, "prix_ttc": 110.0, "remise": -5.0},
            )
            assert r.status_code == 422
            assert "positifs ou nuls" in r.json()["detail"]

            # Tout cohérent -> accepté.
            r = client.post(
                "/invoices/",
                json={"nom": "Valide", "prix_ht": 100.0, "frais_port": 10.0, "prix_ttc": 110.0, "remise": 5.0},
            )
            assert r.status_code == 201
    finally:
        sys.path.remove(backend_dir)
        if old_db_url is None:
            os.environ.pop("NOVA_DATABASE_URL", None)
        else:
            os.environ["NOVA_DATABASE_URL"] = old_db_url
        for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
            del sys.modules[mod_name]


# ------------------------------------------------------------- i18n cfg ---


def test_app_languages_restricts_generated_columns_and_frontend_state(tmp_path):
    """`application { langues: fr, en }` doit restreindre les colonnes
    générées pour un champ `multilingue` (backend) ET les state vars/
    sélecteur de langue (frontend) aux seules langues actives — pas les 6
    langues du DSL par défaut. Vérifié par lecture du code source généré
    (pas d'import réel du module Reflex ici : un second test qui importerait
    un second module frontend généré entrerait en collision avec le
    singleton `rx.App()` déjà exercé par
    `test_chart_frontend_module_actually_imports_and_builds_all_pages` —
    voir sa docstring)."""
    src = """
    application Boutique {
      nom: "Boutique"
      langue: fr
      langues: fr, en
    }
    traductions {
      titre_catalogue {
        fr: "Catalogue"
        en: "Catalog"
      }
    }
    entity Produit {
      champ nom: chaine multilingue
      champ prix: decimal
    }
    api Produit { liste creer }
    page Produits {
      afficher Produit comme table titre titre_catalogue
    }
    page NouveauProduit {
      afficher Produit comme formulaire
    }
    """
    program = parse_source(src)
    generate_project(program, tmp_path)

    models_src = (tmp_path / "backend/app/models.py").read_text(encoding="utf-8")
    assert "nom_fr: Optional[str]" in models_src
    assert "nom_en: Optional[str]" in models_src
    assert "nom_es" not in models_src
    assert "nom_de" not in models_src

    frontend_src = _frontend_main_source(tmp_path)
    assert "new_nom_fr" in frontend_src
    assert "new_nom_en" in frontend_src
    assert "new_nom_es" not in frontend_src
    assert 'rx.Cookie("fr", name="nova_lang")' in frontend_src
    assert "['fr', 'en']" in frontend_src  # sélecteur de langue restreint


def test_app_without_languages_prop_keeps_all_six_languages(tmp_path):
    """Non-régression : sans `langues:`, un projet multilingue continue de
    générer les 6 langues du DSL (comportement historique)."""
    src = """
    application Boutique { nom: "Boutique" }
    traductions {
      titre_catalogue {
        fr: "Catalogue"
        en: "Catalog"
        es: "Catálogo"
        de: "Katalog"
        it: "Catalogo"
        pt: "Catálogo"
      }
    }
    entity Produit {
      champ nom: chaine multilingue
    }
    api Produit { liste creer }
    page Produits {
      afficher Produit comme table titre titre_catalogue
    }
    """
    program = parse_source(src)
    generate_project(program, tmp_path)
    models_src = (tmp_path / "backend/app/models.py").read_text(encoding="utf-8")
    for lang in ("fr", "en", "es", "de", "it", "pt"):
        assert f"nom_{lang}: Optional[str]" in models_src


def test_app_languages_enforced_real_execution(tmp_path):
    """Exécution réelle du backend généré (pas seulement `ast.parse`) : un
    champ `multilingue` restreint à `langues: fr, en` n'expose bien QUE les
    colonnes `_fr`/`_en` dans les réponses JSON."""
    src = """
    application Boutique {
      nom: "Boutique"
      langues: fr, en
    }
    entity Depliant {
      champ titre: chaine multilingue
    }
    api Depliant { liste creer }
    """
    program = parse_source(src)
    generate_project(program, tmp_path)

    backend_dir = str(tmp_path / "backend")
    sys.path.insert(0, backend_dir)
    old_db_url = os.environ.get("NOVA_DATABASE_URL")
    os.environ["NOVA_DATABASE_URL"] = f"sqlite:///{tmp_path}/test_i18n.db"
    for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[mod_name]
    try:
        from fastapi.testclient import TestClient

        main = importlib.import_module("app.main")
        with TestClient(main.app) as client:
            r = client.post(
                "/depliants/", json={"titre_fr": "Bonjour", "titre_en": "Hello"}
            )
            assert r.status_code == 201
            body = r.json()
            assert body["titre_fr"] == "Bonjour"
            assert body["titre_en"] == "Hello"
            assert "titre_es" not in body
            assert "titre_de" not in body
    finally:
        sys.path.remove(backend_dir)
        if old_db_url is None:
            os.environ.pop("NOVA_DATABASE_URL", None)
        else:
            os.environ["NOVA_DATABASE_URL"] = old_db_url
        for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
            del sys.modules[mod_name]


# --------------------------------------------------------- pluralisation ---

def test_pluralize_handles_irregular_english_plurals():
    """`pluralize` (utilisée pour les noms de tables/routes) doit gérer les
    pluriels irréguliers anglais courants (`inflect`), pas seulement le
    suffixe s/x/z/ch/sh -> es, y -> ies de l'ancienne heuristique — et ne
    pluraliser que le DERNIER segment d'un nom composé."""
    from nova_compiler.codegen.utils import pluralize

    assert pluralize("Category") == "categories"
    assert pluralize("Person") == "people"
    assert pluralize("Child") == "children"
    assert pluralize("Property") == "properties"
    assert pluralize("Bus") == "buses"
    assert pluralize("Produit") == "produits"  # cas régulier, comportement inchangé
    # Nom composé (PascalCase) : seul le dernier segment est pluralisé.
    assert pluralize("ProductCategory") == "product_categories"
    assert pluralize("OrderItem") == "order_items"


def test_entity_with_irregular_plural_name_generates_correct_routes(tmp_path):
    """Vérifie de bout en bout (génération réelle, pas seulement l'unitaire
    ci-dessus) qu'une entité au pluriel irrégulier produit une route API et
    une URL frontend correctement pluralisées."""
    src = """
    entity Category {
        field name: string required
    }
    api Category {
        list
        create
    }
    page Categories {
        show Category as table
    }
    """
    program = parse_source(src)
    generate_project(program, tmp_path)
    router_src = (tmp_path / "backend/app/routers/categories.py").read_text(encoding="utf-8")
    assert 'prefix="/categories"' in router_src
    frontend_src = _frontend_main_source(tmp_path)
    assert 'f"{BACKEND_URL}/categories/"' in frontend_src


def test_unprotected_api_has_no_role_dependency(tmp_path):
    """Une `api` sans `proteger: <role>` doit rester publique : le routeur
    généré ne doit référencer aucune dépendance `require_role`."""
    program = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(program, tmp_path)
    router_files = list((tmp_path / "backend/app/routers").glob("*.py"))
    router_files = [f for f in router_files if f.name != "__init__.py"]
    for f in router_files:
        assert "require_role" not in f.read_text(encoding="utf-8")


# ---------------------------------------------------------------- docker ---


def test_docker_compose_includes_jwt_secret_only_when_auth_enabled(tmp_path):
    with_auth = parse_file(EXAMPLES / "full_featured.nova")
    generate_project(with_auth, tmp_path / "with_auth")
    compose = (tmp_path / "with_auth/docker-compose.yml").read_text(encoding="utf-8")
    assert "NOVA_JWT_SECRET" in compose

    without_auth = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(without_auth, tmp_path / "without_auth")
    compose = (tmp_path / "without_auth/docker-compose.yml").read_text(encoding="utf-8")
    assert "NOVA_JWT_SECRET" not in compose
    # Le bloc `environment:` doit rester syntaxiquement propre même sans
    # ligne JWT injectée (pas de ligne vide parasite avant le prochain
    # champ, ce qui casserait l'indentation YAML).
    assert "NOVA_DATABASE_URL: sqlite:///./nova.db\n    volumes:" in compose


# ------------------------------------------------------ base sql config ---


def _app_with_database(engine: str | None) -> str:
    db_line = f'\n      database: {engine}' if engine else ""
    return f"""
    application Boutique {{
      nom: "Boutique"{db_line}
    }}
    entity Produit {{
      field nom: chaine requis
    }}
    api Produit {{
      liste creer
    }}
    """


def test_database_engine_defaults_to_sqlite_unchanged_requirements_and_compose(tmp_path):
    program = parse_source(_app_with_database(None))
    generate_project(program, tmp_path)
    requirements = (tmp_path / "backend/requirements.txt").read_text(encoding="utf-8")
    assert "psycopg2" not in requirements
    assert "pymysql" not in requirements
    assert "pyodbc" not in requirements
    assert "oracledb" not in requirements

    compose = (tmp_path / "docker-compose.yml").read_text(encoding="utf-8")
    assert "NOVA_DATABASE_URL: sqlite:///./nova.db" in compose
    assert "\n  db:\n" not in compose
    assert "db_data" not in compose

    database_py = (tmp_path / "backend/app/database.py").read_text(encoding="utf-8")
    assert 'os.environ.get("NOVA_DATABASE_URL", "sqlite:///./nova.db")' in database_py


@pytest.mark.parametrize(
    "engine,driver,scheme",
    [
        ("postgresql", "psycopg2-binary", "postgresql+psycopg2"),
        ("mysql", "pymysql", "mysql+pymysql"),
        ("sqlserver", "pyodbc", "mssql+pyodbc"),
        ("oracle", "oracledb", "oracle+oracledb"),
    ],
)
def test_database_engine_configures_driver_compose_service_and_helm(tmp_path, engine, driver, scheme):
    program = parse_source(_app_with_database(engine))
    out = tmp_path / engine
    generate_project(program, out)

    requirements = (out / "backend/requirements.txt").read_text(encoding="utf-8")
    assert driver in requirements

    database_py = (out / "backend/app/database.py").read_text(encoding="utf-8")
    assert scheme in database_py

    compose = (out / "docker-compose.yml").read_text(encoding="utf-8")
    assert "\n  db:\n" in compose
    assert "db_data:" in compose
    assert "depends_on:\n      - db" in compose

    chart_dir = next((out / "helm").iterdir())
    values = (chart_dir / "values.yaml").read_text(encoding="utf-8")
    assert scheme in values


def test_database_alias_postgres_is_canonicalized_in_generated_project(tmp_path):
    program = parse_source(_app_with_database("postgres"))
    generate_project(program, tmp_path)
    database_py = (tmp_path / "backend/app/database.py").read_text(encoding="utf-8")
    assert "postgresql+psycopg2" in database_py
    requirements = (tmp_path / "backend/requirements.txt").read_text(encoding="utf-8")
    assert "psycopg2-binary" in requirements


# ------------------------------------------------------- backend NoSQL Mongo ---
# `application { database: mongodb }` (tâche #29, codegen/api_mongo.py) : backend
# entièrement distinct (Beanie/Motor), voir la docstring du module pour les
# limites assumées de ce MVP (pas de requete/query, calendar, has_many).


@contextlib.contextmanager
def _mongo_mock():
    """Simule un vrai serveur MongoDB pour un test d'exécution réelle, SANS
    dépendance externe (voir pyproject.toml, extra `dev`, pour les versions
    exactes de beanie/motor/pymongo/mongomock-motor testées et confirmées
    compatibles entre elles — beanie>=2.x utilise une API pymongo async trop
    récente pour la dernière version de mongomock-motor au moment de
    l'écriture). Deux correctifs nécessaires par rapport à un simple
    remplacement de `AsyncIOMotorClient`, tous deux annulés à la sortie :
    1. `mongomock` ne connaît pas la commande `buildInfo` (utilisée par
       Beanie pour détecter la version du serveur à l'initialisation) —
       sans ce correctif, `init_beanie()` échoue avec un `NotImplementedError`
       même contre un projet généré parfaitement valide.
    2. Rien côté codegen : `_generate_mongo_database` utilise déjà un nom de
       base explicite (`_client[MONGO_DB_NAME]`) plutôt que
       `get_default_database()` — précisément pour rester compatible avec ce
       mock (voir son commentaire dans api_mongo.py)."""
    import motor.motor_asyncio
    from mongomock_motor import AsyncMongoMockClient
    import mongomock.database

    original_client = motor.motor_asyncio.AsyncIOMotorClient
    original_command = mongomock.database.Database.command

    def _patched_command(self, command, **kwargs):
        if isinstance(command, str):
            command = {command: 1}
        if "buildInfo" in command:
            return {"ok": 1.0, "version": "7.0.0"}
        return original_command(self, command, **kwargs)

    motor.motor_asyncio.AsyncIOMotorClient = AsyncMongoMockClient
    mongomock.database.Database.command = _patched_command
    try:
        yield
    finally:
        motor.motor_asyncio.AsyncIOMotorClient = original_client
        mongomock.database.Database.command = original_command


_MONGO_NOVA = """
application Boutique {
  nom: "Boutique"
  database: mongodb
  langues: fr, en
}

auth {
  roles: admin, user
}

entity Categorie {
  field nom: chaine requis
}

entity Produit {
  field nom: chaine requis unique
  field prix: decimal requis
  field prix_promo: decimal
  field description: texte multilingue
  field photo: image
  appartient_a Categorie
}

api Categorie { liste creer modifier supprimer obtenir }
api Produit {
  liste creer modifier supprimer obtenir
  proteger: admin
}

validation PromoInferieure sur Produit {
  regle: prix_promo < prix
  message: "le prix promo doit etre inferieur au prix"
}
"""


def test_mongo_backend_generates_beanie_documents_and_nosql_requirements(tmp_path):
    program = parse_source(_MONGO_NOVA)
    generate_project(program, tmp_path)

    models = (tmp_path / "backend/app/models.py").read_text(encoding="utf-8")
    assert "from beanie import Document, Indexed" in models
    assert "class Produit(Document):" in models
    assert "nom: Indexed(str, unique=True)" in models  # `unique` -> index Beanie, pas SQLModel
    assert "categorie_id: Optional[str]" in models  # belongs_to -> id texte, pas une FK entière
    assert "description_fr: Optional[str]" in models  # champ multilingue, actif fr/en seulement
    assert "description_es" not in models  # langues restreintes (voir `langues: fr, en`)

    requirements = (tmp_path / "backend/requirements.txt").read_text(encoding="utf-8")
    assert "beanie" in requirements
    assert "motor" in requirements
    assert "sqlmodel" not in requirements

    database_py = (tmp_path / "backend/app/database.py").read_text(encoding="utf-8")
    assert "init_beanie" in database_py
    assert "mongodb://nova:nova@db:27017/nova" in database_py

    compose = (tmp_path / "docker-compose.yml").read_text(encoding="utf-8")
    assert "image: mongo:7" in compose

    chart_dir = next((tmp_path / "helm").iterdir())
    values = (chart_dir / "values.yaml").read_text(encoding="utf-8")
    assert "mongodb://nova:nova@db:27017/nova" in values

    scaffold = (tmp_path / "backend/app/routers_custom/example.py").read_text(encoding="utf-8")
    assert "Beanie" in scaffold or "MongoDB" in scaffold
    assert "SQLModel" not in scaffold
    assert "get_session" not in scaffold  # variante Mongo du scaffold, pas la SQL

    # Migrations Alembic (tâche #38) : n'a de sens que pour un schéma SQL
    # figé — MongoDB/Beanie (schéma souple par document) ne doit générer ni
    # `alembic.ini` ni `migrations/`, ni tirer `alembic` en dépendance.
    assert not (tmp_path / "backend/alembic.ini").exists()
    assert not (tmp_path / "backend/migrations").exists()
    assert "alembic" not in requirements


def test_mongo_unsupported_features_rejected_at_compile_time():
    # Depuis la levée des limitations Mongo (query/calendrier/has_many),
    # seule la jointure explicite (`jointure:` dans une `requete`) reste
    # incompatible avec `database: mongodb` — voir aussi les tests
    # dédiés dans test_parser.py (test_mongo_backend_rejects_query_join_only,
    # test_mongo_backend_allows_query_calendar_and_has_many).
    src = (
        _MONGO_NOVA
        + "\n"
        + "requete Cher sur Produit {\n"
        + "  jointure: Categorie sur categorie_id = Categorie.id\n"
        + "  filtre: prix > 10\n"
        + "}\n"
    )
    with pytest.raises(NovaSyntaxError, match="mongodb"):
        parse_source(src)


def test_mongo_backend_real_execution_auth_crud_uniqueness_and_validation(tmp_path):
    """Vérification par exécution réelle (philosophie du projet, voir les
    autres tests `_real_execution`) : un vrai serveur Mongo est simulé
    (`_mongo_mock`, sans service externe) et le backend généré tourne
    dessus pour de vrai via `TestClient` — inscription (premier compte ->
    admin), connexion JWT, route protégée, CRUD complet (id `str`, pas
    `int`), contrainte `unique`, référence `appartient_a`, champ
    multilingue, et règle `validation` croisant deux champs (acceptée et
    rejetée) — pas seulement un `ast.parse` du code généré."""
    program = parse_source(_MONGO_NOVA)
    generate_project(program, tmp_path)
    backend_dir = str(tmp_path / "backend")
    sys.path.insert(0, backend_dir)
    for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[mod_name]
    try:
        with _mongo_mock():
            from fastapi.testclient import TestClient

            main = importlib.import_module("app.main")
            with TestClient(main.app) as client:
                # Premier compte inscrit -> admin automatiquement.
                r = client.post("/auth/register", json={"email": "alan@example.com", "password": "secret123"})
                assert r.status_code == 201
                assert r.json()["role"] == "admin"
                assert "password_hash" not in r.json()
                assert isinstance(r.json()["id"], str)  # id Mongo (ObjectId sérialisé), pas un int

                r = client.post("/auth/register", json={"email": "alan@example.com", "password": "x"})
                assert r.status_code == 400  # email déjà utilisé

                r = client.post("/auth/login", data={"username": "alan@example.com", "password": "secret123"})
                assert r.status_code == 200
                token = r.json()["access_token"]
                headers = {"Authorization": f"Bearer {token}"}

                assert client.get("/auth/me", headers=headers).json()["email"] == "alan@example.com"

                r = client.post("/categories/", json={"nom": "Electronique"})
                assert r.status_code == 201
                cat_id = r.json()["id"]

                # `proteger: admin` -> refusé sans jeton.
                assert client.get("/produits/").status_code == 401

                r = client.post(
                    "/produits/",
                    json={"nom": "Clavier", "prix": 49.9, "categorie_id": cat_id},
                    headers=headers,
                )
                assert r.status_code == 201
                prod = r.json()
                assert prod["categorie_id"] == cat_id
                assert prod["description_fr"] is None  # champ multilingue, non renseigné

                # Contrainte `unique` sur `nom` (index Beanie) : un doublon
                # est rejeté par MongoDB lui-même (E11000).
                dup = client.post("/produits/", json={"nom": "Clavier", "prix": 1.0}, headers=headers)
                assert dup.status_code >= 400

                prod_id = prod["id"]
                r = client.get(f"/produits/{prod_id}", headers=headers)
                assert r.status_code == 200 and r.json()["nom"] == "Clavier"

                r = client.put(f"/produits/{prod_id}", json={"prix": 39.9}, headers=headers)
                assert r.status_code == 200 and r.json()["prix"] == 39.9

                assert client.get("/produits/", headers=headers).status_code == 200

                # `validation PromoInferieure` : prix_promo < prix.
                bad = client.post(
                    "/produits/", json={"nom": "Souris", "prix": 10.0, "prix_promo": 20.0}, headers=headers
                )
                assert bad.status_code == 422
                ok = client.post(
                    "/produits/", json={"nom": "Ecran", "prix": 100.0, "prix_promo": 50.0}, headers=headers
                )
                assert ok.status_code == 201

                # id syntaxiquement invalide -> 404 propre, pas une 500.
                assert client.get("/produits/not-an-object-id", headers=headers).status_code == 404

                assert client.delete(f"/produits/{prod_id}", headers=headers).status_code == 204
                assert client.get(f"/produits/{prod_id}", headers=headers).status_code == 404
    finally:
        sys.path.remove(backend_dir)
        for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
            del sys.modules[mod_name]


_MONGO_FEATURES_NOVA = """
application BoutiqueMongoFeatures {
  nom: "BoutiqueMongoFeatures"
  database: mongodb
  langues: fr, en
}

entity Gadget {
  field nom: chaine requis
  field prix: decimal requis
  field date_ajout: date_heure
  possede_plusieurs Piece
}

entity Piece {
  field nom: chaine requis
  appartient_a Gadget
}

api Gadget { liste creer modifier supprimer obtenir }
api Piece { liste creer }

requete GadgetsChers sur Gadget {
  filtre: prix > 50
  trier_par: prix desc
  limite: 10
}

calendrier Ajouts sur Gadget {
  champ_date: date_ajout
  champ_titre: nom
}
"""


def test_mongo_backend_real_execution_query_calendar_and_has_many(tmp_path):
    """Vérification par exécution réelle (tâche #34, mêmes principes que
    `test_mongo_backend_real_execution_auth_crud_uniqueness_and_validation`)
    des trois fonctionnalités désormais levées côté MongoDB : `requete`
    (filtre/tri/limite, sans jointure — toujours interdite sur ce backend),
    `calendrier` (export `.ics`), et `possede_plusieurs` (résumé texte des
    enregistrements liés dans `liste`/`obtenir`)."""
    program = parse_source(_MONGO_FEATURES_NOVA)
    generate_project(program, tmp_path)
    backend_dir = str(tmp_path / "backend")
    sys.path.insert(0, backend_dir)
    for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[mod_name]
    try:
        with _mongo_mock():
            from fastapi.testclient import TestClient

            main = importlib.import_module("app.main")
            with TestClient(main.app) as client:
                r = client.post(
                    "/gadgets/",
                    json={"nom": "Cher", "prix": 100.0, "date_ajout": "2026-01-15T10:00:00"},
                )
                assert r.status_code == 201
                gadget_cher_id = r.json()["id"]

                r = client.post(
                    "/gadgets/",
                    json={"nom": "Pas cher", "prix": 5.0, "date_ajout": "2026-02-01T10:00:00"},
                )
                assert r.status_code == 201

                # `requete GadgetsChers` : filtre prix > 50, tri desc, limite
                # 10 -> ne doit renvoyer que "Cher", pas "Pas cher".
                r = client.get("/requetes/gadgets-chers")
                assert r.status_code == 200
                noms = [item["nom"] for item in r.json()]
                assert noms == ["Cher"]

                # `calendrier Ajouts` : export iCalendar réel.
                r = client.get("/ics/ajouts.ics")
                assert r.status_code == 200
                assert "BEGIN:VCALENDAR" in r.text
                assert "SUMMARY:Cher" in r.text
                assert "SUMMARY:Pas cher" in r.text

                # `possede_plusieurs Piece` : résumé texte sur liste/obtenir.
                r = client.post("/pieces/", json={"nom": "Vis", "gadget_id": gadget_cher_id})
                assert r.status_code == 201
                r = client.post("/pieces/", json={"nom": "Ecrou", "gadget_id": gadget_cher_id})
                assert r.status_code == 201

                r = client.get("/gadgets/")
                assert r.status_code == 200
                by_id = {g["id"]: g for g in r.json()}
                assert by_id[gadget_cher_id]["pieces_text"] in ("Vis, Ecrou", "Ecrou, Vis")
                assert by_id[gadget_cher_id]["pieces_text"] != ""
                # Le gadget sans pièce a un résumé vide, pas une erreur.
                pas_cher_id = next(g["id"] for g in r.json() if g["nom"] == "Pas cher")
                assert by_id[pas_cher_id]["pieces_text"] == ""

                r = client.get(f"/gadgets/{gadget_cher_id}")
                assert r.status_code == 200
                assert r.json()["pieces_text"] in ("Vis, Ecrou", "Ecrou, Vis")
    finally:
        sys.path.remove(backend_dir)
        for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
            del sys.modules[mod_name]


# --------------------------------------------------------------- helm k8s ---


def test_helm_chart_generates_configmap_secret_and_pvc_always(tmp_path):
    program = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(program, tmp_path)
    helm_dirs = list((tmp_path / "helm").iterdir())
    assert len(helm_dirs) == 1
    chart_dir = helm_dirs[0]

    values = (chart_dir / "values.yaml").read_text(encoding="utf-8")
    assert "config:" in values
    assert "secrets:" in values
    assert "databaseUrl:" in values
    assert "persistence:" in values
    assert "enabled: true" in values

    configmap = (chart_dir / "templates/configmap.yaml").read_text(encoding="utf-8")
    assert "kind: ConfigMap" in configmap
    assert "NOVA_BACKEND_URL:" in configmap
    # Ni auth, ni upload, ni email dans blog.en.nova -> pas de lignes en trop.
    assert "NOVA_PUBLIC_BACKEND_URL" not in configmap
    assert "NOVA_SMTP_HOST" not in configmap

    secret = (chart_dir / "templates/secret.yaml").read_text(encoding="utf-8")
    assert "kind: Secret" in secret
    assert "NOVA_DATABASE_URL:" in secret
    assert "NOVA_JWT_SECRET" not in secret
    assert "NOVA_SMTP_PASSWORD" not in secret

    pvc = (chart_dir / "templates/pvc.yaml").read_text(encoding="utf-8")
    assert "kind: PersistentVolumeClaim" in pvc
    assert "{{- if .Values.persistence.enabled }}" in pvc

    backend_deploy = (chart_dir / "templates/backend-deployment.yaml").read_text(encoding="utf-8")
    assert "configMapRef" in backend_deploy
    assert "secretRef" in backend_deploy
    assert "volumeMounts" in backend_deploy
    assert "claimName:" in backend_deploy

    frontend_deploy = (chart_dir / "templates/frontend-deployment.yaml").read_text(encoding="utf-8")
    assert "configMapRef" in frontend_deploy
    # Pas de PVC côté frontend (persistance backend uniquement, voir docstring k8s.py).
    assert "volumeMounts" not in frontend_deploy
    assert "claimName" not in frontend_deploy


def test_helm_secret_includes_jwt_only_when_auth_enabled(tmp_path):
    with_auth = parse_file(EXAMPLES / "full_featured.nova")
    generate_project(with_auth, tmp_path / "with_auth")
    chart_dir = next((tmp_path / "with_auth/helm").iterdir())
    secret = (chart_dir / "templates/secret.yaml").read_text(encoding="utf-8")
    assert "NOVA_JWT_SECRET" in secret

    without_auth = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(without_auth, tmp_path / "without_auth")
    chart_dir2 = next((tmp_path / "without_auth/helm").iterdir())
    secret2 = (chart_dir2 / "templates/secret.yaml").read_text(encoding="utf-8")
    assert "NOVA_JWT_SECRET" not in secret2


def test_helm_secret_and_configmap_include_smtp_only_when_email_block_present(tmp_path):
    with_email = parse_source(_EMAIL_NOVA)
    generate_project(with_email, tmp_path / "with_email")
    chart_dir = next((tmp_path / "with_email/helm").iterdir())
    secret = (chart_dir / "templates/secret.yaml").read_text(encoding="utf-8")
    assert "NOVA_SMTP_PASSWORD" in secret
    configmap = (chart_dir / "templates/configmap.yaml").read_text(encoding="utf-8")
    assert "NOVA_SMTP_HOST" in configmap

    without_email = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(without_email, tmp_path / "without_email")
    chart_dir2 = next((tmp_path / "without_email/helm").iterdir())
    secret2 = (chart_dir2 / "templates/secret.yaml").read_text(encoding="utf-8")
    assert "NOVA_SMTP_PASSWORD" not in secret2
    configmap2 = (chart_dir2 / "templates/configmap.yaml").read_text(encoding="utf-8")
    assert "NOVA_SMTP_HOST" not in configmap2


def test_helm_configmap_includes_public_backend_url_only_when_uploads_present(tmp_path):
    with_uploads = parse_file(EXAMPLES / "full_featured.nova")
    generate_project(with_uploads, tmp_path / "with_uploads")
    chart_dir = next((tmp_path / "with_uploads/helm").iterdir())
    configmap = (chart_dir / "templates/configmap.yaml").read_text(encoding="utf-8")
    assert "NOVA_PUBLIC_BACKEND_URL" in configmap

    without_uploads = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(without_uploads, tmp_path / "without_uploads")
    chart_dir2 = next((tmp_path / "without_uploads/helm").iterdir())
    configmap2 = (chart_dir2 / "templates/configmap.yaml").read_text(encoding="utf-8")
    assert "NOVA_PUBLIC_BACKEND_URL" not in configmap2


# ----------------------------------------------------------------- chart ---


def _frontend_main_source(tmp_path) -> str:
    frontend_files = [
        f
        for f in (tmp_path / "frontend").rglob("*.py")
        if f.name not in ("rxconfig.py", "__init__.py", "custom.py")
    ]
    assert frontend_files, "fichier frontend principal introuvable"
    return frontend_files[0].read_text(encoding="utf-8")


def test_chart_on_entity_generates_recharts_bar_and_route(tmp_path):
    program = parse_file(EXAMPLES / "full_featured.nova")
    generate_project(program, tmp_path, source_dir=EXAMPLES)
    source = _frontend_main_source(tmp_path)

    # Graphique sur l'entité Produit (protégée) : bar chart, en-tête auth.
    assert "class RepartitionPrixChartState(rx.State):" in source
    assert 'rx.recharts.bar_chart(' in source
    assert 'rx.recharts.bar(data_key="prix", fill=' in source
    assert 'rx.recharts.x_axis(data_key="nom")' in source
    assert 'resp = await client.get(f"{BACKEND_URL}/produits/", headers=headers)' in source
    assert 'app.add_page(repartition_prix_chart_page, route="/graphiques/repartition-prix"' in source


def test_chart_on_query_generates_pie_and_uses_unprotected_query_route(tmp_path):
    program = parse_file(EXAMPLES / "full_featured.nova")
    generate_project(program, tmp_path, source_dir=EXAMPLES)
    source = _frontend_main_source(tmp_path)

    # Graphique sur la requête ProduitsChers : camembert -> pie, source
    # `/requetes/produits-chers` jamais protégée (voir _generate_query_router).
    assert "class TopProduitsChersChartState(rx.State):" in source
    assert "rx.recharts.pie_chart(" in source
    assert 'rx.recharts.pie(data=TopProduitsChersChartState.rows, data_key="prix", name_key="nom"' in source
    assert 'resp = await client.get(f"{BACKEND_URL}/requetes/produits-chers")' in source
    # Pas d'en-tête Authorization pour une requête (toujours publique).
    query_chart_state = source.split("class TopProduitsChersChartState(rx.State):")[1].split("class ")[0]
    assert "headers" not in query_chart_state


def test_chart_types_line_and_area_generate_expected_recharts_components():
    from nova_compiler.codegen.ui_reflex import generate_frontend

    src = """
    entity Mesure {
        field jour: string required
        field valeur: float required
    }
    chart Ligne sur Mesure { type: line axe_x: jour axe_y: valeur }
    chart Aire sur Mesure { type: area axe_x: jour axe_y: valeur }
    """
    program = parse_source(src)
    files = generate_frontend(program)
    main_src = next(v for k, v in files.items() if k.endswith(".py") and "custom" not in k and "rxconfig" not in k)
    assert "rx.recharts.line_chart(" in main_src
    assert 'rx.recharts.line(data_key="valeur", stroke=' in main_src
    assert "rx.recharts.area_chart(" in main_src
    assert 'rx.recharts.area(data_key="valeur", fill=' in main_src


def test_chart_frontend_module_actually_imports_and_builds_all_pages(tmp_path):
    """Comme `test_generated_backend_actually_imports_and_wires_custom_router`,
    mais côté frontend : importe réellement le module Reflex généré (pas
    seulement une validation de syntaxe `ast.parse`) et appelle chaque
    fonction de page pour vérifier que l'arbre de composants se construit
    sans erreur — la seule façon de détecter un problème de signature
    d'API Reflex (voir leçon apprise en développant ce générateur : `data=`
    se pose différemment sur `pie` que sur les autres types de graphique).

    Regroupe aussi la vérification des pages `formulaire`/`carte` sur les
    champs riches (`image`/`fichier`/`couleur`/`booleen` ajoutés à `entité
    Produit` dans full_featured.nova), de la page `calendrier` (`calendrier
    Ajouts sur Produit { champ_date: date_ajout ... }`, ajoutée pour la même
    raison), du contenu multilingue (`traductions { titre_catalogue {
    ... } }` + `champ description: texte multilingue` sur `entité Produit`,
    ajoutés pour la même raison), et de la page multi-entités (`page
    TableauBord`, deux `afficher Produit` en table puis en carte, qui exerce
    à la fois l'empilement multi-sections et la désambiguïsation de nom de
    state par index quand la même entité apparaît deux fois sur une page) :
    `rx.App()` est un singleton process-wide chez Reflex
    (`ReflexRuntimeError: A RegistrationContext can only be associated with
    a single App instance`), donc un second test important un second module
    frontend généré échouerait s'il tournait à côté de celui-ci — même
    pattern que la collision de registre SQLAlchemy pour `app.main` (voir
    `test_auth_and_query_flow_end_to_end`). C'est précisément cette
    vérification qui a révélé le `ForeachVarError` initial rencontré pendant
    la conception du bloc `calendar` (foreach imbriqué sur une valeur
    `list[str]` dans un dict), corrigé en aplatissant les événements du jour
    en une seule chaîne (`events_text`, voir codegen/ui_reflex.py)."""
    program = parse_file(EXAMPLES / "full_featured.nova")
    generate_project(program, tmp_path, source_dir=EXAMPLES)

    frontend_dir = str(tmp_path / "frontend")
    pkg_dir = next(
        p for p in (tmp_path / "frontend").iterdir() if p.is_dir() and (p / "custom.py").exists()
    )
    pkg_name = pkg_dir.name

    sys.path.insert(0, frontend_dir)
    for mod_name in [m for m in sys.modules if m == pkg_name or m.startswith(pkg_name + ".")]:
        del sys.modules[mod_name]
    try:
        main = importlib.import_module(f"{pkg_name}.{pkg_name}")
        assert main.app is not None
        # Un graphique par source (entité protégée + requête publique).
        bar_page = main.repartition_prix_chart_page()
        pie_page = main.top_produits_chers_chart_page()
        assert type(bar_page).__name__ == "Box"
        assert type(pie_page).__name__ == "Box"
        # Nouveaux types de graphique (radar/scatter) et multi-séries
        # (bar avec plusieurs champs sur `axe_y`) — voir full_featured.nova
        # (`ProfilProduit`/`NuagePrix`/`PrixEtStock`). Regroupé ici plutôt
        # que dans un test séparé, même contrainte de singleton `rx.App()`.
        multi_series_page = main.prix_et_stock_chart_page()
        radar_page = main.profil_produit_chart_page()
        scatter_page = main.nuage_prix_chart_page()
        assert type(multi_series_page).__name__ == "Box"
        assert type(radar_page).__name__ == "Box"
        assert type(scatter_page).__name__ == "Box"
        # Nouveaux types de graphique (tâche #35) : donut (anneau) et funnel
        # (entonnoir) — voir full_featured.nova (`PrixParProduit`/
        # `StockEntonnoir`). Même contrainte de singleton `rx.App()`.
        donut_page = main.prix_par_produit_chart_page()
        funnel_page = main.stock_entonnoir_chart_page()
        assert type(donut_page).__name__ == "Box"
        assert type(funnel_page).__name__ == "Box"
        # Agrégation (tâche #35) : `NombreProduits` (`agregation: compte`,
        # sans `axe_y`) — la page se construit, et le helper Python généré
        # `_nova_chart_aggregate` est vérifié directement par exécution
        # réelle avec des données synthétiques (plusieurs lignes par groupe).
        aggregate_page = main.nombre_produits_chart_page()
        assert type(aggregate_page).__name__ == "Box"
        assert hasattr(main, "_nova_chart_aggregate")
        agg = main._nova_chart_aggregate(
            [
                {"nom": "Stylo", "prix": 10},
                {"nom": "Stylo", "prix": 12},
                {"nom": "Chaise", "prix": 100},
            ],
            "nom",
            ["y"],
            "count",
        )
        assert {"nom": "Stylo", "y": 2} in agg
        assert {"nom": "Chaise", "y": 1} in agg
        agg_sum = main._nova_chart_aggregate(
            [
                {"nom": "Stylo", "prix": 10},
                {"nom": "Stylo", "prix": 12},
                {"nom": "Chaise", "prix": 100},
            ],
            "nom",
            ["prix"],
            "sum",
        )
        assert {"nom": "Stylo", "prix": 22.0} in agg_sum
        assert {"nom": "Chaise", "prix": 100.0} in agg_sum
        agg_avg = main._nova_chart_aggregate(
            [{"nom": "Stylo", "prix": 10}, {"nom": "Stylo", "prix": 20}],
            "nom",
            ["prix"],
            "avg",
        )
        assert agg_avg == [{"nom": "Stylo", "prix": 15.0}]
        # Valeur manquante/non numérique ignorée silencieusement, pas d'erreur.
        agg_missing = main._nova_chart_aggregate(
            [{"nom": "Stylo", "prix": None}, {"nom": "Stylo", "prix": "n/a"}],
            "nom",
            ["prix"],
            "max",
        )
        assert agg_missing == [{"nom": "Stylo", "prix": None}]
        # Champs riches sur `entité Produit` : formulaire (upload + color
        # picker) et carte (miniature/lien/pastille/badge) se construisent.
        form_page = main.nouveau_produit_page()
        card_page = main.fiches_produits_page()
        assert type(form_page).__name__ == "Box"
        assert type(card_page).__name__ == "Box"
        # Calendrier sur `entité Produit` (protégé, `champ_date: date_ajout`).
        calendar_page = main.ajouts_calendar_page()
        assert type(calendar_page).__name__ == "Box"
        # `_build_days` construit une grille de jours plate (pas de valeur
        # imbriquée de type liste) : vérifié directement, indépendamment du
        # rendu Reflex.
        state = main.AjoutsCalendarState()
        state.rows = [
            {"nom": "Chaise", "date_ajout": f"{state.year:04d}-{state.month:02d}-01T10:00:00"}
        ]
        state._build_days()
        assert len(state.days) % 7 == 0
        first_of_month = next(d for d in state.days if d["day"] == 1 and d["in_month"])
        assert first_of_month["events_text"] == "Chaise"
        assert all(set(d.keys()) == {"date", "day", "in_month", "events_text"} for d in state.days)
        # Vue semaine (`_build_week_days`) : 7 jours plats à partir de
        # `week_start`, incluant le jour de l'enregistrement -> son
        # `events_text` doit s'y retrouver aussi.
        state.week_start = f"{state.year:04d}-{state.month:02d}-01"
        state._build_week_days()
        assert len(state.week_days) == 7
        assert all(
            set(d.keys()) == {"date", "day", "weekday", "events_text"} for d in state.week_days
        )
        assert state.week_days[0]["events_text"] == "Chaise"
        # Vue jour (`_build_day_events`) : liste d'événements (pas un texte
        # joint) pour `selected_day` — voir le commentaire sur
        # `_build_day_events` dans codegen/ui_reflex.py (ForeachVarError
        # évité en aplatissant chaque événement en {"title": ...}).
        state.selected_day = f"{state.year:04d}-{state.month:02d}-01"
        state._build_day_events()
        assert state.day_events == [{"title": "Chaise"}]
        state.selected_day = f"{state.year:04d}-{state.month:02d}-02"
        state._build_day_events()
        assert state.day_events == []
        # `prev`/`next` respectent la vue active (`self.view`) plutôt que de
        # toujours avancer le mois — voir codegen/ui_reflex.py.
        state.view = "week"
        original_week_start = state.week_start
        state.next()
        assert state.week_start != original_week_start
        assert state.days  # le mois affiché, lui, n'a pas bougé
        state.view = "day"
        original_selected_day = state.selected_day
        state.prev()
        assert state.selected_day != original_selected_day
        # Glisser-déposer du calendrier (tâche #36) : `NovaDnd` (voir
        # codegen/ui_reflex.py::_CALENDAR_DND_HELPER) est bien injecté une
        # fois dans le module, et `drop_on_day` (déplacement + création
        # rapide) est appelé pour de vrai — la couche réseau (httpx) est
        # remplacée par un faux client qui enregistre les appels, mais tout
        # le reste (résolution du premier événement du jour source,
        # préservation de l'heure pour `date_heure`, construction du
        # payload) est le VRAI code généré qui s'exécute.
        dnd_pkg_source = (pkg_dir / f"{pkg_name}.py").read_text(encoding="utf-8")
        assert "NovaDnd" in dnd_pkg_source
        assert hasattr(main, "NovaDnd")
        assert hasattr(main.AjoutsCalendarState, "drop_on_day")
        assert hasattr(main.AjoutsCalendarState, "start_drag_day")
        # `entité Produit` n'a aucun autre champ requis que `nom` (= le
        # `champ_titre` du calendrier) et `date_ajout` (= `champ_date`), et
        # aucune relation `appartient_a` -> `_calendar_quick_create_safe`
        # doit avoir généré le chip de création rapide.
        assert hasattr(main.AjoutsCalendarState, "start_drag_new")
        assert "+ Nouvel évènement / + New event" in dnd_pkg_source

        dnd_recorded = []

        class _FakeDndResponse:
            def __init__(self, status_code=200, data=None):
                self.status_code = status_code
                self._data = data if data is not None else []

            def json(self):
                return self._data

        class _FakeDndClient:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *exc_info):
                return False

            async def get(self, url, **kwargs):
                dnd_recorded.append(("GET", url, kwargs))
                return _FakeDndResponse(200, [])

            async def post(self, url, **kwargs):
                dnd_recorded.append(("POST", url, kwargs))
                return _FakeDndResponse(201, {"id": "new-1"})

            async def put(self, url, **kwargs):
                dnd_recorded.append(("PUT", url, kwargs))
                return _FakeDndResponse(200, {"id": "p1"})

        from unittest.mock import patch as _dnd_patch

        # `RappelsCalendarState` (calendrier NON protégé sur `entité
        # Rappel`) plutôt que `AjoutsCalendarState` : `drop_on_day` d'un
        # calendrier protégé appelle `await self.get_state(AuthState)`, qui
        # a besoin d'un `EventContext` Reflex actif (une vraie requête) —
        # absent quand un test instancie un state directement et appelle sa
        # coroutine avec `asyncio.run`, d'où `entité Rappel` dédiée (voir
        # full_featured.nova) pour exercer le VRAI code généré de bout en
        # bout sans avoir à simuler tout le runtime Reflex.
        assert hasattr(main.RappelsCalendarState, "start_drag_new")
        assert hasattr(main.RappelsCalendarState, "drop_on_day")
        cal_state = main.RappelsCalendarState()
        cal_state.rows = [
            {"id": "r1", "titre": "Appel client", "date_rappel": "2026-09-05T10:00:00"},
        ]
        with _dnd_patch.object(main.httpx, "AsyncClient", _FakeDndClient):
            # Déplacement : le jour source (2026-09-05) porte "Appel client"
            # -> déposé sur 2026-09-10, PUT sur son id avec l'heure
            # (10:00:00) préservée (date_rappel est `date_heure`/datetime).
            cal_state.dragging = "2026-09-05"
            asyncio.run(cal_state.drop_on_day("2026-09-10"))
        assert cal_state.dragging == ""
        put_calls = [c for c in dnd_recorded if c[0] == "PUT"]
        assert len(put_calls) == 1
        _, put_url, put_kwargs = put_calls[0]
        assert put_url.endswith("/rappels/r1")
        assert put_kwargs["json"]["date_rappel"] == "2026-09-10T10:00:00"

        dnd_recorded.clear()
        with _dnd_patch.object(main.httpx, "AsyncClient", _FakeDndClient):
            # Création rapide : le chip "+" (dragging == "__new__") déposé
            # sur 2026-09-20 -> POST avec seulement date_rappel (minuit,
            # aucune heure à préserver) + titre (libellé par défaut).
            cal_state.dragging = "__new__"
            asyncio.run(cal_state.drop_on_day("2026-09-20"))
        post_calls = [c for c in dnd_recorded if c[0] == "POST"]
        assert len(post_calls) == 1
        _, post_url, post_kwargs = post_calls[0]
        assert post_url.endswith("/rappels/")
        assert post_kwargs["json"]["date_rappel"] == "2026-09-20T00:00:00"
        assert post_kwargs["json"]["titre"] == "Nouvel évènement / New event"

        # Déposer un jour sur lui-même (ou sans glisser-déposer en cours)
        # est un no-op silencieux : aucun appel réseau.
        dnd_recorded.clear()
        cal_state.dragging = "2026-09-20"
        asyncio.run(cal_state.drop_on_day("2026-09-20"))
        assert dnd_recorded == []
        cal_state.dragging = ""
        asyncio.run(cal_state.drop_on_day("2026-09-21"))
        assert dnd_recorded == []
        # Contenu multilingue : `LangState` + fonction de traduction générée
        # pour `titre_catalogue`, et champ `description` (multilingue) sur
        # `entité Produit` porté par 6 state vars sur la page formulaire.
        assert main.LangState is not None
        assert main.t_titre_catalogue() is not None
        lang_state = main.LangState()
        assert lang_state.lang == "fr"
        form_state = main.NouveauProduitState()
        for lang in ("fr", "en", "es", "de", "it", "pt"):
            assert getattr(form_state, f"new_description_{lang}") == ""
        table_page = main.produits_page()
        assert type(table_page).__name__ == "Box"
        # `has_many` (`entité Produit { ... possede_plusieurs Accessoire }`
        # + `entité Accessoire { ... appartient_a Produit }`) : la
        # table/carte Produit affiche un résumé texte des Accessoire liés
        # (`accessoires_text`, voir ui_reflex._has_many_text_fields), lu
        # directement depuis `row[...]` — jamais de `rx.foreach` imbriqué
        # (même contrainte que le calendrier, voir `events_text` ci-dessus).
        pkg_source = (pkg_dir / f"{pkg_name}.py").read_text(encoding="utf-8")
        assert "accessoires_text" in pkg_source
        # Page multi-entités (`page TableauBord`) : deux `afficher Produit`
        # (table puis carte) sur la MÊME entité -> deux states distincts,
        # désambiguïsés par index (voir `_state_class_name`), chacun chargé
        # au montage. Regroupé ici, même contrainte de singleton `rx.App()`.
        dashboard_page = main.tableau_bord_page()
        assert type(dashboard_page).__name__ == "Box"
        produit_state_1 = main.TableauBordProduit1State
        produit_state_2 = main.TableauBordProduit2State
        assert produit_state_1 is not produit_state_2
        assert hasattr(produit_state_1, "load_rows")
        assert hasattr(produit_state_2, "load_rows")
    finally:
        sys.path.remove(frontend_dir)
        for mod_name in [m for m in sys.modules if m == pkg_name or m.startswith(pkg_name + ".")]:
            del sys.modules[mod_name]


# ----------------------------------------------------------- rich fields ---
# Champs `file`/`image`/`color` (upload + aperçu + sélecteur natif) et
# rendu enrichi des types existants `bool`/`date`/`datetime`/`int`/`float`
# dans les vues table/form/card.

_RICH_FIELDS_NOVA = """
app Boutique {
  name: "Boutique"
}

entity Article {
  field nom: string required
  field photo: image
  field fiche: file
  field couleur: color
  field disponible: bool
  field prix: float required
  field rdv: datetime
  field sortie: date
}

api Article {
  list
  create
}

page Catalogue {
  show Article as table
}

page NouveauArticle {
  show Article as form
}

page Fiches {
  show Article as card
}
"""


def _rich_fields_frontend_source(tmp_path) -> str:
    program = parse_source(_RICH_FIELDS_NOVA)
    generate_project(program, tmp_path)
    frontend_files = [
        f
        for f in (tmp_path / "frontend").rglob("*.py")
        if f.name not in ("rxconfig.py", "__init__.py", "custom.py")
    ]
    assert frontend_files, "fichier frontend principal introuvable"
    return frontend_files[0].read_text(encoding="utf-8")


def test_rich_field_types_map_to_str_columns_in_models(tmp_path):
    program = parse_source(_RICH_FIELDS_NOVA)
    generate_project(program, tmp_path)
    models_src = (tmp_path / "backend/app/models.py").read_text(encoding="utf-8")
    # file/image/color sont stockés comme de simples chaînes (chemin/URL ou
    # code hex) : aucune colonne SQL dédiée, tout l'enrichissement est
    # côté frontend.
    assert "photo: Optional[str]" in models_src
    assert "fiche: Optional[str]" in models_src
    assert "couleur: Optional[str]" in models_src


def test_uploads_router_and_static_mount_generated_when_file_field_present(tmp_path):
    program = parse_source(_RICH_FIELDS_NOVA)
    generate_project(program, tmp_path)

    uploads_router = (tmp_path / "backend/app/routers/_uploads.py").read_text(encoding="utf-8")
    assert 'router = APIRouter(prefix="/uploads"' in uploads_router
    assert 'return {"url": f"/files/{stored_name}"}' in uploads_router

    main_src = (tmp_path / "backend/app/main.py").read_text(encoding="utf-8")
    assert "from fastapi.staticfiles import StaticFiles" in main_src
    assert 'app.mount("/files", StaticFiles(directory=str(UPLOADS_DIR)), name="files")' in main_src
    assert "app.include_router(uploads_router)" in main_src

    requirements = (tmp_path / "backend/requirements.txt").read_text(encoding="utf-8")
    assert "python-multipart" in requirements


def test_uploads_not_generated_without_file_or_image_fields(tmp_path):
    """Régression : un projet sans champ `file`/`image` (ex. blog.en.nova)
    ne doit générer ni routeur d'upload, ni montage de fichiers statiques,
    ni dépendance python-multipart superflue."""
    program = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(program, tmp_path)
    assert not (tmp_path / "backend/app/routers/_uploads.py").exists()
    main_src = (tmp_path / "backend/app/main.py").read_text(encoding="utf-8")
    assert "StaticFiles" not in main_src
    requirements = (tmp_path / "backend/requirements.txt").read_text(encoding="utf-8")
    assert "python-multipart" not in requirements


def test_form_page_uses_native_pickers_for_date_datetime_number_color(tmp_path):
    source = _rich_fields_frontend_source(tmp_path)
    assert 'type="color"' in source
    assert 'type="date"' in source
    assert 'type="datetime-local"' in source
    assert 'type="number", step="any"' in source  # champ float
    # Upload : zone de dépôt + gestionnaire dédié, pas un rx.input texte.
    assert "rx.upload(" in source
    assert "async def handle_upload_photo(self, files: list[rx.UploadFile]) -> None:" in source
    assert "async def handle_upload_fiche(self, files: list[rx.UploadFile]) -> None:" in source


def test_table_and_card_render_image_file_color_bool_specially(tmp_path):
    source = _rich_fields_frontend_source(tmp_path)
    # Miniature d'image (table ET card).
    assert source.count('rx.image(src=f"{PUBLIC_BACKEND_URL}{') >= 2
    # Lien de téléchargement pour un champ `file`.
    assert 'rx.link("Télécharger / Download"' in source
    # Pastille de couleur.
    assert 'background=row[\'couleur\']' in source
    # Badge Oui/Non pour un booléen.
    assert 'rx.badge("Oui / Yes", color_scheme="green")' in source
    assert 'rx.badge("Non / No", color_scheme="gray")' in source


def test_docker_compose_includes_public_backend_url_only_when_uploads_present(tmp_path):
    with_uploads = parse_source(_RICH_FIELDS_NOVA)
    generate_project(with_uploads, tmp_path / "with_uploads")
    compose = (tmp_path / "with_uploads/docker-compose.yml").read_text(encoding="utf-8")
    assert "NOVA_PUBLIC_BACKEND_URL: http://localhost:8000" in compose

    without_uploads = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(without_uploads, tmp_path / "without_uploads")
    compose = (tmp_path / "without_uploads/docker-compose.yml").read_text(encoding="utf-8")
    assert "NOVA_PUBLIC_BACKEND_URL" not in compose


def test_upload_endpoint_stores_file_and_is_served_by_static_mount(tmp_path):
    """Exécute réellement le backend généré (pas seulement `ast.parse`) :
    envoie un fichier à `POST /uploads/`, vérifie qu'il est bien écrit sur
    disque et re-servi tel quel via le montage `/files`, puis qu'un
    enregistrement peut être créé avec l'URL retournée dans un champ
    `image`/`color`/`bool`/`date`/`datetime`."""
    program = parse_source(_RICH_FIELDS_NOVA)
    generate_project(program, tmp_path)

    backend_dir = str(tmp_path / "backend")
    sys.path.insert(0, backend_dir)
    old_db_url = os.environ.get("NOVA_DATABASE_URL")
    old_uploads_dir = os.environ.get("NOVA_UPLOADS_DIR")
    os.environ["NOVA_DATABASE_URL"] = f"sqlite:///{tmp_path}/test_uploads.db"
    os.environ["NOVA_UPLOADS_DIR"] = str(tmp_path / "uploads")
    for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[mod_name]
    try:
        from fastapi.testclient import TestClient

        main = importlib.import_module("app.main")
        with TestClient(main.app) as client:
            resp = client.post("/uploads/", files={"file": ("photo.png", b"fake-bytes", "image/png")})
            assert resp.status_code == 200
            url = resp.json()["url"]
            assert url.startswith("/files/")

            served = client.get(url)
            assert served.status_code == 200
            assert served.content == b"fake-bytes"

            payload = {
                "nom": "Chaise",
                "photo": url,
                "fiche": "",
                "couleur": "#ff0000",
                "disponible": True,
                "prix": 49.9,
                "rdv": "2026-09-10T10:00:00",
                "sortie": "2026-09-08",
            }
            created = client.post("/articles", json=payload)
            assert created.status_code == 201

            rows = client.get("/articles").json()
            assert rows[0]["photo"] == url
            assert rows[0]["couleur"] == "#ff0000"
            assert rows[0]["disponible"] is True
    finally:
        sys.path.remove(backend_dir)
        if old_db_url is None:
            os.environ.pop("NOVA_DATABASE_URL", None)
        else:
            os.environ["NOVA_DATABASE_URL"] = old_db_url
        if old_uploads_dir is None:
            os.environ.pop("NOVA_UPLOADS_DIR", None)
        else:
            os.environ["NOVA_UPLOADS_DIR"] = old_uploads_dir
        for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
            del sys.modules[mod_name]


@contextlib.contextmanager
def _run_generated_backend(tmp_path, program, db_name, **env_overrides):
    """Génère `program`, importe réellement `app.main` (backend/ ajouté à
    `sys.path`, module purgé avant/après), et fournit un `TestClient` prêt
    à l'emploi — factorise le boilerplate répété par chaque test
    d'exécution réelle du backend (import/purge de `sys.modules`,
    variables d'environnement `NOVA_DATABASE_URL`/autres, nettoyage dans
    tous les cas y compris en cas d'exception)."""
    from fastapi.testclient import TestClient

    generate_project(program, tmp_path)
    backend_dir = str(tmp_path / "backend")
    sys.path.insert(0, backend_dir)
    env_overrides = {"NOVA_DATABASE_URL": f"sqlite:///{tmp_path}/{db_name}.db", **env_overrides}
    old_values = {k: os.environ.get(k) for k in env_overrides}
    os.environ.update(env_overrides)
    for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[mod_name]
    try:
        main = importlib.import_module("app.main")
        with TestClient(main.app) as client:
            yield client
    finally:
        sys.path.remove(backend_dir)
        for k, v in old_values.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
            del sys.modules[mod_name]


def _upload_only_program(entity_name: str):
    """Un mini-projet à une seule entité, nom paramétrable — chaque test
    d'exécution réelle ci-dessous importe `app.main` une seule fois avec un
    nom d'entité qui lui est propre : réutiliser le même nom de table
    (donc `Article`/`_RICH_FIELDS_NOVA`) entre plusieurs imports dans le
    même process pytest lève `InvalidRequestError: Table already defined`
    (même contrainte SQLAlchemy déjà documentée pour `nova_users`/
    `Produit` ailleurs dans ce fichier) — dès qu'un test a besoin d'un
    SECOND import avec une configuration différente (variable
    d'environnement lue une seule fois à l'import du module), il lui faut
    donc sa propre entité, jamais réutilisée par un autre test."""
    src = f"""
    app UploadTest {{
      name: "Upload Test"
    }}

    entity {entity_name} {{
      field name: string required
      field photo: image
    }}

    api {entity_name} {{
      list
      create
    }}
    """
    return parse_source(src)


def test_upload_rejects_disallowed_file_extension_by_default(tmp_path):
    """Une extension absente de la liste par défaut (`.exe` notamment) est
    refusée avec 415, avant même l'écriture sur disque — une extension
    autorisée par défaut (`.txt`) passe normalement."""
    program = _upload_only_program("UploadDefaultExt")
    with _run_generated_backend(
        tmp_path, program, "test_upload_default_ext", NOVA_UPLOADS_DIR=str(tmp_path / "uploads")
    ) as client:
        resp = client.post(
            "/uploads/", files={"file": ("malware.exe", b"whatever", "application/octet-stream")}
        )
        assert resp.status_code == 415
        assert not list((tmp_path / "uploads").iterdir())

        resp = client.post("/uploads/", files={"file": ("note.txt", b"hello", "text/plain")})
        assert resp.status_code == 200


def test_upload_allowed_extensions_configurable_via_env(tmp_path):
    """NOVA_UPLOAD_ALLOWED_EXTENSIONS permet d'élargir la liste par défaut
    sans recompiler — une extension normalement refusée (`.exe`) passe une
    fois ajoutée à la variable d'environnement."""
    program = _upload_only_program("UploadCustomExt")
    with _run_generated_backend(
        tmp_path,
        program,
        "test_upload_custom_ext",
        NOVA_UPLOADS_DIR=str(tmp_path / "uploads"),
        NOVA_UPLOAD_ALLOWED_EXTENSIONS=".exe",
    ) as client:
        resp = client.post(
            "/uploads/", files={"file": ("tool.exe", b"whatever", "application/octet-stream")}
        )
        assert resp.status_code == 200


def test_upload_rejects_oversized_file(tmp_path):
    """Un fichier dépassant NOVA_UPLOAD_MAX_BYTES est refusé avec 413 ; un
    fichier sous la limite passe normalement."""
    program = _upload_only_program("UploadSizeLimit")
    with _run_generated_backend(
        tmp_path,
        program,
        "test_upload_size",
        NOVA_UPLOADS_DIR=str(tmp_path / "uploads"),
        NOVA_UPLOAD_MAX_BYTES="10",
    ) as client:
        resp = client.post(
            "/uploads/", files={"file": ("note.txt", b"this is way more than 10 bytes", "text/plain")}
        )
        assert resp.status_code == 413

        resp = client.post("/uploads/", files={"file": ("note.txt", b"tiny", "text/plain")})
        assert resp.status_code == 200


def test_upload_resizes_oversized_image(tmp_path):
    """Une image dont une dimension dépasse NOVA_UPLOAD_MAX_IMAGE_DIMENSION
    est automatiquement redimensionnée (aspect ratio conservé) avant
    d'être écrite sur disque — vérifié en relisant le fichier servi et en
    mesurant ses dimensions réelles avec Pillow, pas seulement la taille
    en octets."""
    from PIL import Image as PILImage

    buf = io.BytesIO()
    PILImage.new("RGB", (400, 200), color=(255, 0, 0)).save(buf, format="PNG")
    big_image_bytes = buf.getvalue()

    program = _upload_only_program("UploadImageResize")
    with _run_generated_backend(
        tmp_path,
        program,
        "test_upload_resize",
        NOVA_UPLOADS_DIR=str(tmp_path / "uploads"),
        NOVA_UPLOAD_MAX_IMAGE_DIMENSION="100",
    ) as client:
        resp = client.post("/uploads/", files={"file": ("photo.png", big_image_bytes, "image/png")})
        assert resp.status_code == 200
        url = resp.json()["url"]

        served = client.get(url)
        assert served.status_code == 200
        resized = PILImage.open(io.BytesIO(served.content))
        assert max(resized.size) <= 100
        # Aspect ratio (2:1) conservé.
        assert abs(resized.width / resized.height - 2.0) < 0.05


# ------------------------------------------------------------------ email ---
# Bloc `email { smtp: ... }` + `notifier:` sur `api` : notification simple
# envoyée après create/update/delete, voir codegen/api_fastapi.py.

_EMAIL_NOVA = """
app Boutique {
  name: "Boutique"
}

entity Commande {
  field client: string required
  field contact: string required
  field montant: float
}

email {
  host: "smtp.example.com"
  port: 2525
  from: "noreply@example.com"
  to: "ops@example.com"
}

api Commande {
  list
  create
  update
  delete
  notifier: create, delete
  destinataire: contact
}
"""


def test_email_block_generates_emailer_module_with_smtp_config_and_defaults(tmp_path):
    program = parse_source(_EMAIL_NOVA)
    generate_project(program, tmp_path)

    emailer_src = (tmp_path / "backend/app/emailer.py").read_text(encoding="utf-8")
    assert 'SMTP_HOST = os.environ.get("NOVA_SMTP_HOST", "smtp.example.com")' in emailer_src
    assert 'SMTP_PORT = int(os.environ.get("NOVA_SMTP_PORT", "2525"))' in emailer_src
    assert 'SMTP_FROM = os.environ.get("NOVA_SMTP_FROM", "noreply@example.com")' in emailer_src
    assert 'SMTP_TO = os.environ.get("NOVA_SMTP_TO", "ops@example.com")' in emailer_src
    # Le mot de passe n'est JAMAIS écrit en dur : uniquement lu depuis l'env,
    # sans valeur par défaut issue du fichier .nova (voir ast_nodes.Email).
    assert 'SMTP_PASSWORD = os.environ.get("NOVA_SMTP_PASSWORD", "")' in emailer_src


def test_emailer_not_generated_without_email_block(tmp_path):
    """Régression : un projet sans bloc `email { ... }` (ex. blog.en.nova)
    ne doit générer ni `emailer.py`, ni référence à `send_email`."""
    program = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(program, tmp_path)
    assert not (tmp_path / "backend/app/emailer.py").exists()
    for router_file in (tmp_path / "backend/app/routers").glob("*.py"):
        assert "send_email" not in router_file.read_text(encoding="utf-8")


def test_notify_stmt_injects_send_email_call_only_for_listed_actions(tmp_path):
    """`notifier: create, delete` (pas `update`) : seuls les gestionnaires
    create/delete du routeur généré doivent appeler `send_email`."""
    program = parse_source(_EMAIL_NOVA)
    generate_project(program, tmp_path)
    router_src = (tmp_path / "backend/app/routers/commandes.py").read_text(encoding="utf-8")
    assert "from ..emailer import send_email" in router_src

    def _function_body(name: str) -> str:
        marker = f"def {name}("
        start = router_src.index(marker)
        try:
            end = router_src.index("\n\n\n", start)
        except ValueError:
            end = len(router_src)  # dernière fonction du fichier
        return router_src[start:end]

    assert "send_email(" in _function_body("create_commande")
    assert "send_email(" in _function_body("delete_commande")
    assert "send_email(" not in _function_body("update_commande")


def test_docker_compose_includes_smtp_password_placeholder_only_when_email_block_present(tmp_path):
    with_email = parse_source(_EMAIL_NOVA)
    generate_project(with_email, tmp_path / "with_email")
    compose = (tmp_path / "with_email/docker-compose.yml").read_text(encoding="utf-8")
    assert 'NOVA_SMTP_PASSWORD: ""' in compose

    without_email = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(without_email, tmp_path / "without_email")
    compose = (tmp_path / "without_email/docker-compose.yml").read_text(encoding="utf-8")
    assert "NOVA_SMTP_PASSWORD" not in compose


def test_email_notification_sent_on_create_and_delete_real_execution(tmp_path):
    """Exécute réellement le backend généré (pas seulement `ast.parse`) :
    la connexion SMTP elle-même est simulée (`unittest.mock.patch` sur
    `smtplib.SMTP`, pas de vrai serveur mail dans la CI), mais tout le
    reste — routage FastAPI, construction du message, choix du
    destinataire/sujet/corps, et le fait qu'aucun email ne parte pour
    `update` (absent de `notifier:`) — passe par le vrai code généré."""
    from unittest.mock import MagicMock, patch

    program = parse_source(_EMAIL_NOVA)
    generate_project(program, tmp_path)

    backend_dir = str(tmp_path / "backend")
    sys.path.insert(0, backend_dir)
    old_db_url = os.environ.get("NOVA_DATABASE_URL")
    os.environ["NOVA_DATABASE_URL"] = f"sqlite:///{tmp_path}/test_email.db"
    for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[mod_name]
    try:
        from fastapi.testclient import TestClient

        main = importlib.import_module("app.main")
        with patch("app.emailer.smtplib.SMTP") as mock_smtp:
            smtp_instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = smtp_instance
            with TestClient(main.app) as client:
                created = client.post(
                    "/commandes",
                    json={"client": "Alan", "contact": "alan@example.com", "montant": 42.5},
                )
                assert created.status_code == 201
                item_id = created.json()["id"]

                updated = client.put(
                    f"/commandes/{item_id}",
                    json={"client": "Alan", "contact": "alan@example.com", "montant": 99.0},
                )
                assert updated.status_code == 200

                deleted = client.delete(f"/commandes/{item_id}")
                assert deleted.status_code == 204

            # create + delete -> 2 emails ; update n'en déclenche aucun.
            assert smtp_instance.send_message.call_count == 2
            sent = [call.args[0] for call in smtp_instance.send_message.call_args_list]
            # `destinataire: contact` (voir _EMAIL_NOVA) : le destinataire de
            # l'ENREGISTREMENT prime sur le SMTP_TO fixe ("ops@example.com").
            assert sent[0]["To"] == "alan@example.com"
            assert sent[0]["From"] == "noreply@example.com"
            assert "Nouveau Commande" in sent[0]["Subject"]
            # Message multipart/alternative (texte brut + HTML) depuis l'ajout
            # de `html_body` à `send_email` — voir emailer.py::send_email.
            assert sent[0].is_multipart()
            plain_part = sent[0].get_body(preferencelist=("plain",))
            html_part = sent[0].get_body(preferencelist=("html",))
            assert f"#{item_id}" in plain_part.get_content()
            assert html_part is not None
            assert f"#{item_id}" in html_part.get_content()
            assert "<html>" in html_part.get_content()
            assert "supprimé" in sent[1]["Subject"]
            # Destinataire dynamique aussi respecté pour la notification de
            # suppression (capturé avant `session.delete`, voir codegen).
            assert sent[1]["To"] == "alan@example.com"
    finally:
        sys.path.remove(backend_dir)
        if old_db_url is None:
            os.environ.pop("NOVA_DATABASE_URL", None)
        else:
            os.environ["NOVA_DATABASE_URL"] = old_db_url
        for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
            del sys.modules[mod_name]


def test_email_multiple_recipients_separated_by_semicolon_real_execution(tmp_path):
    """Comme sur les mails standard : `destinataire: <champ>` peut contenir
    PLUSIEURS adresses séparées par `;` (ou `,`) dans une seule chaîne — le
    champ n'est jamais une vraie liste côté DSL, seulement du texte, mais
    `send_email`/`_split_recipients` (emailer.py généré) les retrouve
    toutes et les envoie ensemble dans un seul message (`To` joint par
    `, `). Vérifie aussi que le `to:` fixe du bloc `email {{ ... }}`
    (`SMTP_TO`) accepte la même syntaxe multi-adresses quand aucun
    `destinataire:` dynamique ne s'applique (entité sans le champ).

    Entité `Facture`, distincte de `Commande`/`Livraison`/`Recu` (voir leurs
    docstrings respectifs) pour la même raison : éviter une collision de
    registre SQLAlchemy entre deux tests qui importent chacun `app.main`."""
    from unittest.mock import MagicMock, patch

    src = _EMAIL_NOVA.replace("entity Commande {", "entity Facture {").replace(
        "api Commande {", "api Facture {"
    ).replace('to: "ops@example.com"', 'to: "ops1@example.com; ops2@example.com"')
    program = parse_source(src)
    generate_project(program, tmp_path)

    backend_dir = str(tmp_path / "backend")
    sys.path.insert(0, backend_dir)
    old_db_url = os.environ.get("NOVA_DATABASE_URL")
    os.environ["NOVA_DATABASE_URL"] = f"sqlite:///{tmp_path}/test_email_multi.db"
    for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[mod_name]
    try:
        from fastapi.testclient import TestClient

        main = importlib.import_module("app.main")
        with patch("app.emailer.smtplib.SMTP") as mock_smtp:
            smtp_instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = smtp_instance
            with TestClient(main.app) as client:
                # `destinataire: contact` avec plusieurs adresses ";"-séparées
                # dans le champ lui-même (comme un utilisateur les taperait
                # dans un client mail standard).
                created = client.post(
                    "/factures",
                    json={
                        "client": "Alan",
                        "contact": "alan@example.com; equipe@example.com",
                        "montant": 42.5,
                    },
                )
                assert created.status_code == 201
                deleted_id = created.json()["id"]
                client.delete(f"/factures/{deleted_id}")

                # Sans `destinataire:` (champ vide) -> repli sur SMTP_TO, lui
                # aussi multi-adresses (`to: "ops1@..."; ops2@..."` ci-dessus).
                created2 = client.post(
                    "/factures", json={"client": "Bob", "contact": "", "montant": 1.0}
                )
                assert created2.status_code == 201

            sent = [call.args[0] for call in smtp_instance.send_message.call_args_list]
            assert sent[0]["To"] == "alan@example.com, equipe@example.com"
            assert sent[1]["To"] == "alan@example.com, equipe@example.com"  # delete, même destinataire
            assert sent[2]["To"] == "ops1@example.com, ops2@example.com"  # repli SMTP_TO
    finally:
        sys.path.remove(backend_dir)
        if old_db_url is None:
            os.environ.pop("NOVA_DATABASE_URL", None)
        else:
            os.environ["NOVA_DATABASE_URL"] = old_db_url
        for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
            del sys.modules[mod_name]


def test_email_send_failure_never_breaks_the_api_response(tmp_path):
    """Un serveur SMTP injoignable (ici : port fermé sur localhost) ne doit
    jamais faire échouer la création qui a déclenché la notification —
    `send_email` avale et logue l'erreur (voir emailer.py généré).

    Entité `Livraison` distincte de `Commande` (utilisée par le test
    précédent) : importer deux fois un module qui définit une classe
    SQLModel du même nom dans le même process pytest fait planter le
    registre de métadonnées SQLAlchemy — même contrainte déjà documentée
    pour `nova_users`/`Produit`/`Article` ailleurs dans ce fichier."""
    program = parse_source(
        _EMAIL_NOVA.replace("entity Commande {", "entity Livraison {")
        .replace("api Commande {", "api Livraison {")
        .replace('host: "smtp.example.com"', 'host: "127.0.0.1"')
        .replace("port: 2525", "port: 1")
    )
    generate_project(program, tmp_path)

    backend_dir = str(tmp_path / "backend")
    sys.path.insert(0, backend_dir)
    old_db_url = os.environ.get("NOVA_DATABASE_URL")
    os.environ["NOVA_DATABASE_URL"] = f"sqlite:///{tmp_path}/test_email_failure.db"
    for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[mod_name]
    try:
        from fastapi.testclient import TestClient

        main = importlib.import_module("app.main")
        with TestClient(main.app) as client:
            created = client.post(
                "/livraisons", json={"client": "Alan", "contact": "alan@example.com", "montant": 1.0}
            )
            assert created.status_code == 201
    finally:
        sys.path.remove(backend_dir)
        if old_db_url is None:
            os.environ.pop("NOVA_DATABASE_URL", None)
        else:
            os.environ["NOVA_DATABASE_URL"] = old_db_url
        for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
            del sys.modules[mod_name]


def test_email_attachment_field_attaches_uploaded_file_real_execution(tmp_path):
    """`api Recu { ... piece_jointe: justificatif }` (champ `file`) : le
    fichier réellement uploadé via `/uploads` (voir `_uploads.py` généré)
    doit se retrouver en pièce jointe du message envoyé — vérifié par
    exécution réelle (upload HTTP réel, écrit sur disque, puis relu par
    `send_email` via `UPLOADS_DIR`), pas seulement par inspection du code
    généré. Couvre aussi le cas où le champ est vide (aucune pièce jointe,
    pas d'erreur) : entité `Recu` distincte de `Commande`/`Livraison`
    (contrainte du registre de métadonnées SQLAlchemy, voir tests
    précédents)."""
    from unittest.mock import MagicMock, patch

    src = """
    entity Recu {
      field client: string required
      field justificatif: file
    }
    email {
      host: "smtp.example.com"
      port: 2525
      from: "noreply@example.com"
      to: "ops@example.com"
    }
    api Recu {
      list
      create
      notifier: create
      piece_jointe: justificatif
    }
    """
    program = parse_source(src)
    generate_project(program, tmp_path)

    backend_dir = str(tmp_path / "backend")
    sys.path.insert(0, backend_dir)
    old_db_url = os.environ.get("NOVA_DATABASE_URL")
    old_uploads_dir = os.environ.get("NOVA_UPLOADS_DIR")
    os.environ["NOVA_DATABASE_URL"] = f"sqlite:///{tmp_path}/test_email_attachment.db"
    os.environ["NOVA_UPLOADS_DIR"] = str(tmp_path / "uploads")
    for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[mod_name]
    try:
        from fastapi.testclient import TestClient

        main = importlib.import_module("app.main")
        with patch("app.emailer.smtplib.SMTP") as mock_smtp:
            smtp_instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = smtp_instance
            with TestClient(main.app) as client:
                upload_resp = client.post(
                    "/uploads/", files={"file": ("justificatif.txt", b"contenu du justificatif", "text/plain")}
                )
                assert upload_resp.status_code == 200
                file_url = upload_resp.json()["url"]

                with_attachment = client.post(
                    "/recus", json={"client": "Alan", "justificatif": file_url}
                )
                assert with_attachment.status_code == 201

                without_attachment = client.post("/recus", json={"client": "Bob", "justificatif": ""})
                assert without_attachment.status_code == 201

            assert smtp_instance.send_message.call_count == 2
            sent = [call.args[0] for call in smtp_instance.send_message.call_args_list]

            attachments_with = list(sent[0].iter_attachments())
            assert len(attachments_with) == 1
            assert attachments_with[0].get_filename() == Path(file_url).name
            assert attachments_with[0].get_content() == "contenu du justificatif"

            # Champ vide -> pas de pièce jointe, et surtout pas d'erreur qui
            # aurait fait échouer la création (voir send_email : `attachment_path`
            # falsy -> ignoré silencieusement, voir _notify_kwargs).
            assert list(sent[1].iter_attachments()) == []
    finally:
        sys.path.remove(backend_dir)
        if old_db_url is None:
            os.environ.pop("NOVA_DATABASE_URL", None)
        else:
            os.environ["NOVA_DATABASE_URL"] = old_db_url
        if old_uploads_dir is None:
            os.environ.pop("NOVA_UPLOADS_DIR", None)
        else:
            os.environ["NOVA_UPLOADS_DIR"] = old_uploads_dir
        for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
            del sys.modules[mod_name]


def test_email_template_file_copied_and_used_for_render_real_execution(tmp_path):
    """`email { ... template: "gabarit.html" }` (tâche #37) : le fichier
    HTML externe référencé, placé à côté du .nova source, doit (1) être
    copié tel quel dans `backend/app/email_templates/notification.html`
    (même mécanisme que `application { css: "..." }`, voir
    codegen/__init__.py::generate_project) et (2) réellement piloter le
    sujet/corps des notifications envoyées : sujet extrait de <title>,
    placeholders `{{champ}}` substitués par les valeurs de l'enregistrement
    (y compris pour `delete`, où l'enregistrement est capturé AVANT la
    suppression — voir _generate_router/deleted_values), à la place du
    sujet/corps codés en dur (comportement par défaut sans `template:`,
    déjà couvert par test_email_notification_sent_on_create_and_delete_
    real_execution)."""
    from unittest.mock import MagicMock, patch

    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "gabarit.html").write_text(
        "<html><head><title>[NOVA] {{entity}} {{action}} — {{client}}</title></head>"
        "<body><h1>Bonjour {{client}}</h1>"
        "<p>Message : {{message}}</p>"
        "<p>Contact : {{contact}}</p></body></html>",
        encoding="utf-8",
    )

    src = """
    entity Notice {
      field client: string required
      field contact: string required
      field message: string
    }
    email {
      host: "smtp.example.com"
      port: 2525
      from: "noreply@example.com"
      to: "ops@example.com"
      template: "gabarit.html"
    }
    api Notice {
      list
      create
      delete
      notifier: create, delete
      destinataire: contact
    }
    """
    program = parse_source(src)
    out_dir = tmp_path / "out"
    generate_project(program, out_dir, source_dir=source_dir)

    # (1) Le contenu réel du fichier référencé remplace le placeholder.
    copied = (out_dir / "backend/app/email_templates/notification.html").read_text(encoding="utf-8")
    assert "Bonjour {{client}}" in copied

    backend_dir = str(out_dir / "backend")
    sys.path.insert(0, backend_dir)
    old_db_url = os.environ.get("NOVA_DATABASE_URL")
    os.environ["NOVA_DATABASE_URL"] = f"sqlite:///{out_dir}/test_email_template.db"
    for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[mod_name]
    try:
        from fastapi.testclient import TestClient

        main = importlib.import_module("app.main")
        with patch("app.emailer.smtplib.SMTP") as mock_smtp:
            smtp_instance = MagicMock()
            mock_smtp.return_value.__enter__.return_value = smtp_instance
            with TestClient(main.app) as client:
                created = client.post(
                    "/notices",
                    json={"client": "Alan", "contact": "alan@example.com", "message": "Tout va bien"},
                )
                assert created.status_code == 201
                item_id = created.json()["id"]

                deleted = client.delete(f"/notices/{item_id}")
                assert deleted.status_code == 204

            # create + delete -> 2 emails.
            assert smtp_instance.send_message.call_count == 2
            sent = [call.args[0] for call in smtp_instance.send_message.call_args_list]

            # (2a) create : sujet extrait de <title>, placeholders substitués.
            assert sent[0]["Subject"] == "[NOVA] Notice created — Alan"
            html_part = sent[0].get_body(preferencelist=("html",))
            plain_part = sent[0].get_body(preferencelist=("plain",))
            assert "Bonjour Alan" in html_part.get_content()
            assert "Message : Tout va bien" in html_part.get_content()
            assert "Contact : alan@example.com" in html_part.get_content()
            # Repli texte brut : mêmes valeurs, sans balises HTML.
            assert "Bonjour Alan" in plain_part.get_content()
            assert "<h1>" not in plain_part.get_content()

            # (2b) delete : l'enregistrement est déjà expiré côté SQLAlchemy à
            # cet instant, mais deleted_values (capturé avant la suppression,
            # voir codegen) permet quand même au template de retrouver "Alan".
            assert sent[1]["Subject"] == "[NOVA] Notice deleted — Alan"
            html_part_del = sent[1].get_body(preferencelist=("html",))
            assert "Bonjour Alan" in html_part_del.get_content()
    finally:
        sys.path.remove(backend_dir)
        if old_db_url is None:
            os.environ.pop("NOVA_DATABASE_URL", None)
        else:
            os.environ["NOVA_DATABASE_URL"] = old_db_url
        for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
            del sys.modules[mod_name]


def test_email_template_placeholder_used_when_referenced_file_missing(tmp_path):
    """Sans `source_dir`, ou si le fichier référencé n'existe pas à
    l'emplacement attendu, la compilation ne doit jamais échouer (même
    philosophie « best-effort » que `application { css: "..." }`) : un
    placeholder commenté est laissé à la place du vrai template, et le
    module `emailer.py` généré reste syntaxiquement valide (render_email_
    template renvoie alors un HTML vide plutôt que de planter)."""
    import ast

    src = """
    entity Rapport {
      field client: string required
    }
    email {
      host: "smtp.example.com"
      template: "gabarit_absent.html"
    }
    api Rapport {
      create
      notifier: create
    }
    """
    program = parse_source(src)
    generate_project(program, tmp_path)  # pas de source_dir
    placeholder = (tmp_path / "backend/app/email_templates/notification.html").read_text(encoding="utf-8")
    assert "Remplacé par le contenu" in placeholder
    ast.parse((tmp_path / "backend/app/emailer.py").read_text(encoding="utf-8"))
    ast.parse((tmp_path / "backend/app/routers/rapports.py").read_text(encoding="utf-8"))


# --------------------------------------------------------------- calendar ---
# Bloc `calendar <Nom> sur <Entite> { ... }` : vue calendrier mensuelle,
# grille calculée côté serveur avec la seule stdlib (`calendar`/`datetime`),
# voir codegen/ui_reflex.py.

_CALENDAR_NOVA = """
app Agenda {
  name: "Agenda"
}

entity Event {
  field title: string required
  field starts_at: datetime required
  field location: string
}

api Event {
  list
  create
  get
}

page Events {
  show Event as table
}

calendar EventCal sur Event {
  champ_date: starts_at
  champ_titre: title
}
"""


def test_calendar_generates_state_route_and_navbar_link(tmp_path):
    program = parse_source(_CALENDAR_NOVA)
    generate_project(program, tmp_path)
    source = _frontend_main_source(tmp_path)

    assert "import calendar" in source
    assert "from datetime import date" in source
    assert "class EventCalCalendarState(rx.State):" in source
    assert 'resp = await client.get(f"{BACKEND_URL}/events/")' in source
    assert 'str(row.get("starts_at", ""))[:10] == iso' in source
    assert 'str(row.get("title", ""))' in source
    assert "def event_cal_calendar_page() -> rx.Component:" in source
    assert 'app.add_page(event_cal_calendar_page, route="/calendriers/event-cal"' in source
    # Lien de navigation vers le calendrier, comme pour une page/un graphique.
    assert 'rx.link("EventCal", href="/calendriers/event-cal"' in source
    # Vues semaine/jour + lien d'export iCal — voir codegen/ui_reflex.py.
    assert 'rx.button("Semaine / Week"' in source
    assert 'rx.button("Jour / Day"' in source
    assert 'href=f"{PUBLIC_BACKEND_URL}/ics/event-cal.ics"' in source
    # Glisser-déposer (tâche #36) : `NovaDnd` émis une fois, cellules-jour
    # mois/semaine draggable + droppable, et chip de création rapide généré
    # (`entity Event` n'a aucun autre champ requis que `title`/`starts_at`,
    # et `location` a un défaut implicite car non requis — voir
    # `_calendar_quick_create_safe`).
    assert "class NovaDnd(rx.el.Div):" in source
    assert 'on_drag_start=lambda: EventCalCalendarState.start_drag_day(day["date"]),' in source
    assert 'on_drop=lambda: EventCalCalendarState.drop_on_day(day["date"]),' in source
    assert "on_drag_over=rx.prevent_default," in source
    assert "async def drop_on_day(self, target_iso: str):" in source
    assert "def start_drag_new(self):" in source
    assert '"+ Nouvel évènement / + New event"' in source


def test_calendar_ics_export_real_execution(tmp_path):
    """Vérifie par exécution réelle (pas seulement `ast.parse`) que
    `GET /ics/<slug>.ics` renvoie un flux iCalendar valide et correctement
    rempli à partir des enregistrements réels de l'entité — un `DTSTART`
    horodaté (champ `datetime`) pour `EventCal`/`Event`."""
    program = parse_source(_CALENDAR_NOVA)
    generate_project(program, tmp_path)

    ics_src = (tmp_path / "backend/app/routers/_ics.py").read_text(encoding="utf-8")
    assert 'router = APIRouter(prefix="/ics", tags=["calendriers"])' in ics_src
    assert '@router.get("/event-cal.ics")' in ics_src  # pas protégé (pas de `proteger:` sur `api Event`)

    backend_dir = str(tmp_path / "backend")
    sys.path.insert(0, backend_dir)
    old_db_url = os.environ.get("NOVA_DATABASE_URL")
    os.environ["NOVA_DATABASE_URL"] = f"sqlite:///{tmp_path}/test_ics.db"
    for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[mod_name]
    try:
        from fastapi.testclient import TestClient

        main = importlib.import_module("app.main")
        with TestClient(main.app) as client:
            created = client.post(
                "/events",
                json={"title": "Réunion, équipe; export", "starts_at": "2026-03-15T14:30:00", "location": "Salle A"},
            )
            assert created.status_code == 201
            item_id = created.json()["id"]

            resp = client.get("/ics/event-cal.ics")
            assert resp.status_code == 200
            assert resp.headers["content-type"].startswith("text/calendar")
            body = resp.text
            assert "BEGIN:VCALENDAR" in body
            assert "END:VCALENDAR" in body
            assert "BEGIN:VEVENT" in body
            assert f"UID:event-{item_id}@nova.local" in body
            assert "DTSTART:20260315T143000Z" in body
            # Virgule/point-virgule échappés (RFC 5545) dans SUMMARY.
            assert "SUMMARY:Réunion\\, équipe\\; export" in body
    finally:
        sys.path.remove(backend_dir)
        if old_db_url is None:
            os.environ.pop("NOVA_DATABASE_URL", None)
        else:
            os.environ["NOVA_DATABASE_URL"] = old_db_url
        for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
            del sys.modules[mod_name]


def test_calendar_ics_export_date_only_field_real_execution(tmp_path):
    """Cas non couvert par `test_calendar_ics_export_real_execution` : un
    champ `date` (pas `datetime`) produit `DTSTART;VALUE=DATE:...` (sans
    heure). Le cas "calendrier protégé -> route `/ics/...` protégée aussi"
    est vérifié séparément dans `test_auth_and_query_flow_end_to_end`
    (réutilise son backend déjà généré avec `auth { ... }` : le nom de
    table `nova_users` est fixe, un SECOND projet avec `auth` importé dans
    le même process pytest ferait à nouveau collisionner le registre de
    métadonnées SQLAlchemy — même contrainte que Produit/Article/Commande
    ailleurs dans ce fichier, mais ici valable pour N'IMPORTE QUELLE entité
    dès que `auth` est activé, puisque `nova_users` ne dépend pas du nom de
    l'entité source)."""
    src = """
    entity Conge {
      field employe: string required
      field jour: date required
    }
    api Conge {
      liste
      creer
    }
    calendar CongesCal sur Conge {
      champ_date: jour
      champ_titre: employe
    }
    """
    program = parse_source(src)
    generate_project(program, tmp_path)

    ics_src = (tmp_path / "backend/app/routers/_ics.py").read_text(encoding="utf-8")
    assert '@router.get("/conges-cal.ics")' in ics_src
    assert "raw_date.strftime('%Y%m%d')" in ics_src
    assert "DTSTART;VALUE=DATE:" in ics_src

    backend_dir = str(tmp_path / "backend")
    sys.path.insert(0, backend_dir)
    old_db_url = os.environ.get("NOVA_DATABASE_URL")
    os.environ["NOVA_DATABASE_URL"] = f"sqlite:///{tmp_path}/test_ics_date_only.db"
    for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[mod_name]
    try:
        from fastapi.testclient import TestClient

        main = importlib.import_module("app.main")
        with TestClient(main.app) as client:
            created = client.post("/conges", json={"employe": "Alan", "jour": "2026-07-01"})
            assert created.status_code == 201

            resp = client.get("/ics/conges-cal.ics")
            assert resp.status_code == 200
            assert "DTSTART;VALUE=DATE:20260701" in resp.text
            assert "SUMMARY:Alan" in resp.text
    finally:
        sys.path.remove(backend_dir)
        if old_db_url is None:
            os.environ.pop("NOVA_DATABASE_URL", None)
        else:
            os.environ["NOVA_DATABASE_URL"] = old_db_url
        for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
            del sys.modules[mod_name]


def test_calendar_without_title_field_uses_bullet_marker():
    from nova_compiler.codegen.ui_reflex import generate_frontend

    src = """
    entity Event {
        field starts_at: date required
    }
    calendar C sur Event { }
    """
    program = parse_source(src)
    files = generate_frontend(program)
    main_src = next(v for k, v in files.items() if k.endswith(".py") and "custom" not in k and "rxconfig" not in k)
    assert 'events_text = ", ".join(' in main_src
    assert '"•"' in main_src


def test_calendar_quick_create_chip_omitted_when_entity_has_other_required_field():
    """Tâche #36 : le chip "+ Nouvel évènement" (création par glisser-
    déposer) exige de pouvoir poster un enregistrement valide avec pour
    seule charge utile `date_field` (+ `title_field`, toujours rempli d'un
    libellé par défaut) — voir `_calendar_quick_create_safe`. Un troisième
    champ requis sans valeur par défaut rend ça impossible : le chip est
    omis, mais le déplacement (`drop_on_day`/`start_drag_day`, un simple
    PUT sur `date_field`) reste, lui, toujours généré."""
    from nova_compiler.codegen.ui_reflex import generate_frontend

    src = """
    entity Event {
        field title: string required
        field starts_at: date required
        field price: float required
    }
    calendar C sur Event { champ_date: starts_at champ_titre: title }
    """
    program = parse_source(src)
    files = generate_frontend(program)
    main_src = next(v for k, v in files.items() if k.endswith(".py") and "custom" not in k and "rxconfig" not in k)
    assert "def start_drag_new(self):" not in main_src
    assert "Nouvel évènement" not in main_src
    assert "async def drop_on_day(self, target_iso: str):" in main_src
    assert "def start_drag_day(self, day_iso: str):" in main_src


def test_calendar_quick_create_chip_omitted_when_entity_has_belongs_to():
    """Même restriction que ci-dessus, pour une relation `appartient_a` :
    la clé étrangère générée est requise et on n'a aucune valeur valable à
    lui donner depuis un simple glisser-déposer."""
    from nova_compiler.codegen.ui_reflex import generate_frontend

    src = """
    entity Category { field name: string required }
    entity Event {
        field title: string required
        field starts_at: date required
        belongs_to Category
    }
    calendar C sur Event { champ_date: starts_at champ_titre: title }
    """
    program = parse_source(src)
    files = generate_frontend(program)
    main_src = next(v for k, v in files.items() if k.endswith(".py") and "custom" not in k and "rxconfig" not in k)
    assert "def start_drag_new(self):" not in main_src
    assert "async def drop_on_day(self, target_iso: str):" in main_src


def test_calendar_quick_create_chip_present_when_extra_field_has_default():
    """Un champ requis avec une valeur par défaut ne bloque pas la création
    rapide (le POST minimal reste valide sans lui, le backend appliquera
    le défaut) — seul un champ requis SANS défaut est bloquant."""
    from nova_compiler.codegen.ui_reflex import generate_frontend

    src = """
    entity Event {
        field title: string required
        field starts_at: date required
        field status: string required default = "planned"
    }
    calendar C sur Event { champ_date: starts_at champ_titre: title }
    """
    program = parse_source(src)
    files = generate_frontend(program)
    main_src = next(v for k, v in files.items() if k.endswith(".py") and "custom" not in k and "rxconfig" not in k)
    assert "def start_drag_new(self):" in main_src


def test_calendar_quick_create_safe_helper_unit():
    """Vérification directe de `_calendar_quick_create_safe` (pas seulement
    via le code généré ci-dessus) : True quand `date_field`/`title_field`
    sont les seuls champs requis et qu'il n'y a pas de relation
    `appartient_a`, False sinon."""
    from nova_compiler.ast_nodes import Calendar, Entity, Field, Relation
    from nova_compiler.codegen.ui_reflex import _calendar_quick_create_safe

    cal = Calendar(name="C", entity="Event", date_field="starts_at", title_field="title")

    safe_entity = Entity(
        name="Event",
        fields=[
            Field(name="title", type="string", required=True),
            Field(name="starts_at", type="date", required=True),
            Field(name="location", type="string", required=False),
        ],
    )
    assert _calendar_quick_create_safe(safe_entity, cal) is True

    unsafe_required = Entity(
        name="Event",
        fields=[
            Field(name="title", type="string", required=True),
            Field(name="starts_at", type="date", required=True),
            Field(name="price", type="float", required=True),
        ],
    )
    assert _calendar_quick_create_safe(unsafe_required, cal) is False

    unsafe_relation = Entity(
        name="Event",
        fields=[
            Field(name="title", type="string", required=True),
            Field(name="starts_at", type="date", required=True),
        ],
        relations=[Relation(kind="belongs_to", target="Category")],
    )
    assert _calendar_quick_create_safe(unsafe_relation, cal) is False

    safe_with_default = Entity(
        name="Event",
        fields=[
            Field(name="title", type="string", required=True),
            Field(name="starts_at", type="date", required=True),
            Field(name="status", type="string", required=True, default="planned"),
        ],
    )
    assert _calendar_quick_create_safe(safe_with_default, cal) is True


def test_calendar_not_generated_without_calendar_block(tmp_path):
    """Régression : un projet sans bloc `calendar` (ex. blog.en.nova) ne
    doit générer ni état calendrier, ni import de la stdlib `calendar`."""
    program = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(program, tmp_path)
    source = _frontend_main_source(tmp_path)
    assert "CalendarState" not in source
    assert "import calendar" not in source
    assert "from datetime import date" not in source
    assert not (tmp_path / "backend/app/routers/_ics.py").exists()


# ------------------------------------------------------------------ i18n ---
# Bloc `traductions { ... }` (textes d'interface) + modificateur
# `multilingue`/`multilingual` sur un champ `chaine`/`texte` (données) :
# `LangState` (langue courante, cookie), sélecteur de langue dans la
# navbar, une fonction `t_<cle>()` par entrée de `traductions`, et le
# rendu table/carte/formulaire des champs multilingues via `rx.match`
# (colonnes `<champ>_fr`...`<champ>_pt` côté backend).

_I18N_NOVA = """
app Boutique {
  name: "Boutique"
}

translations {
  accueil_titre {
    fr: "Bienvenue"
    en: "Welcome"
    es: "Bienvenido"
    de: "Willkommen"
    it: "Benvenuto"
    pt: "Bem-vindo"
  }
}

entity Produit {
  field nom: string required
  field titre: string multilingual
}

api Produit {
  list
  create
}

page Accueil {
  show Produit as table title accueil_titre
}

page NouveauProduit {
  show Produit as form
}

page Fiches {
  show Produit as card
}
"""


def test_multilingual_backend_generates_one_column_per_language(tmp_path):
    program = parse_source(_I18N_NOVA)
    generate_project(program, tmp_path)
    models_src = (tmp_path / "backend/app/models.py").read_text(encoding="utf-8")
    for lang in ("fr", "en", "es", "de", "it", "pt"):
        assert f"titre_{lang}: Optional[str]" in models_src
    # Le champ `nom` (non multilingue) reste une colonne unique.
    assert "nom: str" in models_src or "nom: Optional[str]" in models_src


def test_translations_block_generates_lang_state_and_translation_function(tmp_path):
    program = parse_source(_I18N_NOVA)
    generate_project(program, tmp_path)
    source = _frontend_main_source(tmp_path)

    assert "class LangState(rx.State):" in source
    assert 'lang: str = rx.Cookie("fr", name="nova_lang")' in source
    assert "def t_accueil_titre():" in source
    assert "rx.match(LangState.lang," in source
    assert "('fr', 'Bienvenue')" in source
    assert "('pt', 'Bem-vindo')" in source
    # Sélecteur de langue dans la navbar.
    assert "value=LangState.lang" in source
    assert "on_change=LangState.set_lang" in source
    # Le titre de la page `Accueil` (`titre accueil_titre`) appelle la
    # fonction de traduction plutôt qu'une chaîne littérale figée.
    assert 'rx.heading(t_accueil_titre(), size="7")' in source


def test_multilingual_field_generates_six_state_vars_and_form_inputs(tmp_path):
    program = parse_source(_I18N_NOVA)
    generate_project(program, tmp_path)
    source = _frontend_main_source(tmp_path)

    for lang in ("fr", "en", "es", "de", "it", "pt"):
        assert f'new_titre_{lang}: str = ""' in source
        assert f"def set_new_titre_{lang}(self, value: str) -> None:" in source
        assert f'placeholder="titre ({lang})"' in source
        assert f'"titre_{lang}": self.new_titre_{lang}' in source


def test_multilingual_field_rendered_via_reactive_match_in_table_and_card(tmp_path):
    program = parse_source(_I18N_NOVA)
    generate_project(program, tmp_path)
    source = _frontend_main_source(tmp_path)

    assert 'rx.match(LangState.lang, ("fr", row["titre_fr"])' in source
    assert 'row["titre_pt"])' in source


def test_i18n_not_generated_without_translations_or_multilingual_field(tmp_path):
    """Régression : un projet sans bloc `traductions` ni champ `multilingue`
    (ex. blog.en.nova) ne doit générer ni `LangState`, ni sélecteur de
    langue, ni fonction de traduction."""
    program = parse_file(EXAMPLES / "blog.en.nova")
    generate_project(program, tmp_path)
    source = _frontend_main_source(tmp_path)
    assert "LangState" not in source
    assert "value=LangState.lang" not in source


# NB : la vérification d'exécution réelle (import du module Reflex généré +
# construction du composant de page calendrier) est regroupée dans
# `test_chart_frontend_module_actually_imports_and_builds_all_pages`
# ci-dessus, sur `full_featured.nova` (`calendrier Ajouts sur Produit`) —
# pas un test séparé ici : `rx.App()` est un singleton process-wide chez
# Reflex, voir le docstring de ce test.


