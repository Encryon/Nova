"""Tests du codegen : le code généré doit être syntaxiquement valide."""

import ast
import importlib
import os
import sys
from pathlib import Path

from nova_compiler.codegen import generate_project
from nova_compiler.parser import parse_file, parse_source

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
                json={"email": "admin@test.com", "password": "secret123", "role": "admin"},
            )
            assert r.status_code == 201
            assert r.json()["role"] == "admin"

            r = client.post(
                "/auth/register", json={"email": "user@test.com", "password": "secret123"}
            )
            assert r.status_code == 201
            assert r.json()["role"] == "user"  # rôle par défaut, non fourni

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

            for nom, prix in [("Stylo", 2), ("Chaise", 80), ("Bureau", 350)]:
                client.post(
                    "/produits", json={"nom": nom, "prix": prix, "stock": 1}, headers=admin_headers
                )

            r = client.get("/requetes/produits-chers")
            assert r.status_code == 200
            rows = r.json()
            assert [row["nom"] for row in rows] == ["Ordinateur", "Bureau"]
            assert all(row["prix"] > 100 for row in rows)
    finally:
        sys.path.remove(backend_dir)
        if old_db_url is None:
            os.environ.pop("NOVA_DATABASE_URL", None)
        else:
            os.environ["NOVA_DATABASE_URL"] = old_db_url
        for mod_name in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
            del sys.modules[mod_name]


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
    fonction de page de graphique pour vérifier que l'arbre de composants
    `rx.recharts` se construit sans erreur — la seule façon de détecter un
    problème de signature d'API Reflex (voir leçon apprise en développant
    ce générateur : `data=` se pose différemment sur `pie` que sur les
    autres types)."""
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
    finally:
        sys.path.remove(frontend_dir)
        for mod_name in [m for m in sys.modules if m == pkg_name or m.startswith(pkg_name + ".")]:
            del sys.modules[mod_name]
