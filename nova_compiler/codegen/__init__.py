"""
Codegen NOVA : AST canonique -> projet exécutable
(backend FastAPI, UI Reflex, Docker, Kubernetes/Helm).

Chaque sous-module renvoie un dict {chemin_relatif: contenu} ; ce module
se contente de les fusionner et de les écrire sur disque.
"""

from __future__ import annotations

from pathlib import Path

from ..ast_nodes import NovaProgram
from .api_fastapi import generate_backend, generate_backend_scaffold
from .docker import generate_docker
from .k8s import generate_k8s
from .ui_reflex import generate_frontend, generate_frontend_scaffold

__all__ = ["generate_project", "generate_backend", "generate_frontend", "generate_docker", "generate_k8s"]


def generate_project(program: NovaProgram, output_dir: str | Path, source_dir: str | Path | None = None) -> list[Path]:
    """
    Génère un projet complet à partir de l'AST NOVA dans `output_dir`.
    Retourne la liste des fichiers écrits.

    `source_dir`, quand fourni (le dossier contenant le fichier .nova source
    — voir `cli.py`), sert uniquement à résoudre le chemin d'une éventuelle
    feuille de style externe (`application { css: "chemin/relatif.css" }`) :
    si le fichier existe à cet emplacement, son contenu réel est copié dans
    `frontend/<app>/assets/` ; sinon un fichier vide (placeholder) est laissé
    à la place attendue par Reflex.

    Deux catégories de fichiers :
    - les fichiers "générés" (models.py, routers/*.py, main.py, la page
      Reflex principale...) sont TOUJOURS réécrits à partir de l'AST — ne
      jamais les éditer à la main, ils seraient écrasés au prochain
      `nova compile` ;
    - les fichiers "scaffold" (routers_custom/example.py, custom.py) sont
      créés une seule fois, uniquement s'ils n'existent pas déjà, et jamais
      réécrits ensuite : c'est l'endroit prévu pour du code métier écrit à
      la main (validations avancées, requêtes complexes, écritures en base
      sur mesure, UI hors DSL...), qui survit donc aux recompilations.
    """
    out = Path(output_dir)
    files: dict[str, str] = {}
    files.update(generate_backend(program))
    files.update(generate_frontend(program))
    files.update(generate_docker(program))
    files.update(generate_k8s(program))

    written: list[Path] = []
    for rel_path, content in files.items():
        target = out / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(target)

    # `application { css: "..." }` : si le fichier référencé existe bien à
    # côté du .nova source, son contenu réel remplace le placeholder généré
    # ci-dessus dans generate_frontend().
    css_path = program.app.props.get("css") if program.app else None
    if css_path and source_dir is not None:
        candidate = Path(source_dir) / css_path
        if candidate.is_file():
            for rel_path in list(files):
                if rel_path.endswith("/assets/" + candidate.name):
                    target = out / rel_path
                    target.write_bytes(candidate.read_bytes())

    scaffold_files: dict[str, str] = {}
    scaffold_files.update(generate_backend_scaffold())
    scaffold_files.update(generate_frontend_scaffold(program))
    for rel_path, content in scaffold_files.items():
        target = out / rel_path
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        written.append(target)

    return written
