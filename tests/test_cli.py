"""
Tests de la CLI `nova` (nova_compiler/cli.py) — en particulier `nova
migrate` (tâche #38), qui shell-e vers un VRAI process `alembic` (pas de
mock : la philosophie de test de ce projet est l'exécution réelle, voir
tests/test_codegen.py). `check`/`compile`/`run`/`new` sont déjà couverts
indirectement par tests/test_codegen.py (qui appelle `generate_project`
directement) ; ce fichier se concentre sur ce que seule la CLI ajoute :
l'orchestration `compile` -> `alembic revision --autogenerate` -> `alembic
upgrade head`, et la garantie que `backend/migrations/`/`alembic.ini` sont
générés UNE SEULE FOIS (jamais réécrits par une compilation suivante,
choix confirmé par Alan pour la tâche #38 — voir README/REFERENCE.md)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from nova_compiler.cli import app

runner = CliRunner()

_WIDGET_NOVA = """\
app TestMigrate {
  name: "TestMigrate"
}

entity Widget {
  field name: string required
  field price: float
}

api Widget {
  list
  create
}
"""

_MONGO_NOVA = """\
app TestMigrateMongo {
  name: "TestMigrateMongo"
  database: mongodb
}

entity Gizmo {
  field name: string required
}

api Gizmo {
  list
}
"""


def test_nova_migrate_generates_and_applies_real_alembic_migration(tmp_path):
    """Bout en bout, process `alembic` réel (pas de mock) : `nova migrate`
    doit (1) compiler le projet, (2) générer une révision Alembic par
    autogénération reflétant `entity Widget`, et (3) l'appliquer — la table
    `widgets` doit réellement exister dans le fichier sqlite ensuite, avec
    les bonnes colonnes."""
    nova_file = tmp_path / "app.nova"
    nova_file.write_text(_WIDGET_NOVA, encoding="utf-8")
    output = tmp_path / "build"
    db_path = tmp_path / "widgets.db"

    result = runner.invoke(
        app,
        ["migrate", str(nova_file), "-o", str(output), "-m", "initial"],
        env={"NOVA_DATABASE_URL": f"sqlite:///{db_path}"},
    )
    assert result.exit_code == 0, result.output
    assert "Migration générée et appliquée" in result.output

    revisions = list((output / "backend/migrations/versions").glob("*.py"))
    assert len(revisions) == 1
    assert "initial" in revisions[0].name

    assert db_path.exists()
    con = sqlite3.connect(db_path)
    try:
        tables = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
        assert "widgets" in tables
        columns = {r[1] for r in con.execute("PRAGMA table_info(widgets)")}
        assert {"id", "name", "price"} <= columns
        # `alembic_version` : preuve que la migration a bien été APPLIQUÉE
        # (pas seulement générée) — voir alembic upgrade head dans cli.py.
        assert "alembic_version" in tables
    finally:
        con.close()


def test_nova_migrate_rejects_mongodb_database(tmp_path):
    """`database: mongodb` (Beanie/Motor, pas de schéma SQL figé) : `nova
    migrate` doit refuser explicitement plutôt que d'essayer d'exécuter
    `alembic` sur un projet qui n'a ni `backend/alembic.ini` ni
    `backend/app/database.py` au sens SQLModel — aucun fichier ne doit être
    généré (échec avant même `generate_project`)."""
    nova_file = tmp_path / "app.nova"
    nova_file.write_text(_MONGO_NOVA, encoding="utf-8")
    output = tmp_path / "build"

    result = runner.invoke(app, ["migrate", str(nova_file), "-o", str(output)])
    assert result.exit_code == 1
    assert "MongoDB" in result.output
    assert not output.exists()


def test_nova_migrate_scaffold_never_overwritten_on_recompile(tmp_path):
    """Choix confirmé par Alan pour la tâche #38 (« Structure générée une
    fois + nova migrate ») : `backend/alembic.ini` et les révisions déjà
    générées dans `backend/migrations/versions/` ne doivent JAMAIS être
    réécrits par une compilation suivante (`nova compile`, appelée en
    interne par `nova migrate` elle-même aussi) — exactement comme
    `routers_custom/example.py` (voir generate_backend_scaffold). Sans
    cette garantie, l'historique réel des migrations appliquées à une base
    de production serait détruit à chaque `nova compile`."""
    nova_file = tmp_path / "app.nova"
    nova_file.write_text(_WIDGET_NOVA, encoding="utf-8")
    output = tmp_path / "build"
    db_path = tmp_path / "widgets2.db"

    first = runner.invoke(
        app,
        ["migrate", str(nova_file), "-o", str(output), "-m", "initial"],
        env={"NOVA_DATABASE_URL": f"sqlite:///{db_path}"},
    )
    assert first.exit_code == 0, first.output
    revisions_after_first = sorted((output / "backend/migrations/versions").glob("*.py"))
    assert len(revisions_after_first) == 1
    revision_content_before = revisions_after_first[0].read_text(encoding="utf-8")

    # Un humain (ou un autre outil) modifie l'alembic.ini généré à la main.
    alembic_ini = output / "backend/alembic.ini"
    marker = "\n# MARQUEUR-DE-TEST-NE-DOIT-PAS-DISPARAITRE\n"
    alembic_ini.write_text(alembic_ini.read_text(encoding="utf-8") + marker, encoding="utf-8")

    # Une simple recompilation (pas `migrate`) ne doit toucher ni le fichier
    # marqué à la main, ni la révision déjà générée.
    second = runner.invoke(app, ["compile", str(nova_file), "-o", str(output)])
    assert second.exit_code == 0, second.output

    assert marker in alembic_ini.read_text(encoding="utf-8")
    revisions_after_second = sorted((output / "backend/migrations/versions").glob("*.py"))
    assert revisions_after_second == revisions_after_first
    assert revisions_after_second[0].read_text(encoding="utf-8") == revision_content_before
