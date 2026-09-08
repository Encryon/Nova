"""
NOVA — DSL bilingue (FR/EN) d'intention métier et compilateur associé.

Usage rapide :

    from nova_compiler.parser import parse_file
    from nova_compiler.codegen import generate_project

    program = parse_file("app.nova")
    generate_project(program, output_dir="build/")
"""

from .parser import NovaSyntaxError, parse_file, parse_source

__all__ = ["parse_file", "parse_source", "NovaSyntaxError"]
__version__ = "0.2.0"
