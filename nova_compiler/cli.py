"""
CLI `nova` — interface en ligne de commande du framework NOVA.

    nova new mon_projet --lang fr        # crée un fichier .nova de départ
    nova check app.nova                  # valide la syntaxe sans générer
    nova compile app.nova -o build/      # génère backend/frontend/docker/k8s
    nova run app.nova                    # compile puis lance via docker compose
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .codegen import generate_project
from .parser import NovaSyntaxError, parse_file

app = typer.Typer(
    name="nova",
    help="NOVA — DSL bilingue (FR/EN) et compilateur (FastAPI + Reflex + Docker + K8s).",
    add_completion=False,
)
console = Console()

_STARTER_EN = """\
app MyApp {
  name: "My App"
  lang: en
}

entity Task {
  field title: string required
  field done: bool default = false
}

api Task {
  list
  create
  update
  delete
}

page Tasks {
  show Task as table title "Tasks"
}
"""

_STARTER_FR = """\
application MonApplication {
  nom: "Mon Application"
  langue: fr
}

entité Tache {
  champ titre: chaine requis
  champ terminee: booleen default = false
}

api Tache {
  liste
  créer
  modifier
  supprimer
}

page Taches {
  afficher Tache comme table titre "Tâches"
}
"""


@app.command()
def new(
    name: str = typer.Argument(..., help="Nom du projet / project name"),
    lang: str = typer.Option("fr", "--lang", "-l", help="fr | en — langue du fichier de départ généré"),
):
    """Crée un nouveau projet NOVA avec un fichier .nova de démarrage."""
    target_dir = Path(name)
    target_dir.mkdir(parents=True, exist_ok=True)
    content = _STARTER_FR if lang.lower().startswith("fr") else _STARTER_EN
    nova_file = target_dir / "app.nova"
    nova_file.write_text(content, encoding="utf-8")
    console.print(f"[green]✓[/green] Projet créé / Project created: [bold]{nova_file}[/bold]")
    console.print("Prochaine étape / Next step:")
    console.print(f"  nova compile {nova_file} -o {target_dir}/build")


@app.command()
def check(source: Path = typer.Argument(..., exists=True, help="Fichier .nova à valider")):
    """Valide la syntaxe d'un fichier .nova sans rien générer."""
    try:
        program = parse_file(source)
    except NovaSyntaxError as exc:
        console.print(f"[red]✗ Erreur de syntaxe / Syntax error[/red]\n{exc}")
        raise typer.Exit(code=1)

    table = Table(title=f"NOVA — {source}")
    table.add_column("Élément / Element")
    table.add_column("Nombre / Count", justify="right")
    table.add_row("Entités / Entities", str(len(program.entities)))
    table.add_row("API", str(len(program.apis)))
    table.add_row("Pages", str(len(program.pages)))
    console.print(table)
    console.print("[green]✓[/green] Syntaxe valide / Valid syntax")


@app.command()
def compile(
    source: Path = typer.Argument(..., exists=True, help="Fichier .nova source"),
    output: Path = typer.Option(Path("build"), "-o", "--output", help="Dossier de sortie"),
):
    """Compile un fichier .nova en projet complet (backend + frontend + docker + k8s)."""
    try:
        program = parse_file(source)
    except NovaSyntaxError as exc:
        console.print(f"[red]✗ Erreur de syntaxe / Syntax error[/red]\n{exc}")
        raise typer.Exit(code=1)

    written = generate_project(program, output, source_dir=source.parent)
    console.print(f"[green]✓[/green] {len(written)} fichiers générés dans / files generated in [bold]{output}[/bold]")
    for f in sorted(written):
        console.print(f"  {f}")


@app.command()
def run(
    source: Path = typer.Argument(..., exists=True, help="Fichier .nova source"),
    output: Path = typer.Option(Path("build"), "-o", "--output", help="Dossier de sortie"),
):
    """Compile puis lance le projet généré avec `docker compose up --build`."""
    try:
        program = parse_file(source)
    except NovaSyntaxError as exc:
        console.print(f"[red]✗ Erreur de syntaxe / Syntax error[/red]\n{exc}")
        raise typer.Exit(code=1)

    generate_project(program, output, source_dir=source.parent)
    console.print(f"[green]✓[/green] Projet compilé dans / project compiled in [bold]{output}[/bold]")
    console.print("[cyan]→[/cyan] docker compose up --build")
    subprocess.run(["docker", "compose", "up", "--build"], cwd=output, check=False)


if __name__ == "__main__":
    app()
