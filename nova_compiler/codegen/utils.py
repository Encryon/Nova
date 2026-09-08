"""Petits utilitaires partagés par les générateurs de code."""

from __future__ import annotations

import unicodedata


def to_ascii_identifier(name: str) -> str:
    """
    'Utilisateur' -> 'Utilisateur' ; 'Événement' -> 'Evenement'.
    Les noms d'entités NOVA peuvent contenir des accents (français) ; le
    code Python/YAML généré, lui, doit rester en identifiants ASCII stricts.
    """
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_name or name


def to_pascal_case(name: str) -> str:
    ascii_name = to_ascii_identifier(name)
    if "_" not in ascii_name and ascii_name[:1].isupper():
        return ascii_name
    parts = ascii_name.replace("-", "_").split("_")
    return "".join(p[:1].upper() + p[1:] for p in parts if p)


def to_snake_case(name: str) -> str:
    ascii_name = to_ascii_identifier(name)
    out = []
    for i, ch in enumerate(ascii_name):
        if ch.isupper() and i > 0 and not ascii_name[i - 1].isupper():
            out.append("_")
        out.append(ch.lower())
    return "".join(out)


def pluralize(name: str) -> str:
    """Pluriel anglais naïf, suffisant pour un MVP (limitation documentée)."""
    lower = name.lower()
    if lower.endswith(("s", "x", "z", "ch", "sh")):
        return name + "es"
    if lower.endswith("y") and lower[-2:-1] not in "aeiou":
        return name[:-1] + "ies"
    return name + "s"


# Types NOVA canoniques -> types Python
PY_TYPE_MAP = {
    "string": "str",
    "text": "str",
    "int": "int",
    "float": "float",
    "bool": "bool",
    "date": "date",
    "datetime": "datetime",
}

# Types NOVA canoniques -> types TypeScript/JS (pour d'éventuels générateurs
# frontend alternatifs ; utilisé aussi pour les valeurs par défaut Reflex)
DEFAULT_VALUE_MAP = {
    "string": '""',
    "text": '""',
    "int": "0",
    "float": "0.0",
    "bool": "False",
    "date": "None",
    "datetime": "None",
}
