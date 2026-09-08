"""Tests du codegen : le code généré doit être syntaxiquement valide."""

import ast
import importlib
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
