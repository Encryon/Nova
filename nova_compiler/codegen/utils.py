"""Petits utilitaires partagés par les générateurs de code."""

from __future__ import annotations

import unicodedata

try:
    import inflect as _inflect_module

    _INFLECT = _inflect_module.engine()
except ImportError:  # pragma: no cover - `inflect` est une dépendance du
    # compilateur (voir pyproject.toml) ; ce filet de sécurité évite
    # seulement de planter si le paquet n'est, malgré tout, pas installé.
    _INFLECT = None


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


def _pluralize_naive(word: str) -> str:
    """Filet de sécurité si `inflect` n'est pas installé (voir import
    ci-dessus) — l'ancienne heuristique suffixe-only de ce compilateur,
    volontairement limitée (pas de pluriel irrégulier)."""
    lower = word.lower()
    if lower.endswith(("s", "x", "z", "ch", "sh")):
        return word + "es"
    if lower.endswith("y") and lower[-2:-1] not in "aeiou":
        return word[:-1] + "ies"
    return word + "s"


def pluralize(name: str) -> str:
    """Pluriel anglais du nom d'entité, utilisé pour les noms de
    tables/routes générés. Le nom peut être composé (`ProductCategory`,
    `product_category`) : ramené en snake_case, seul le DERNIER segment —
    la tête du composé en anglais — est mis au pluriel (`product_category`
    -> `product_categories`, jamais `product_categorys` ni
    `products_category`). Le résultat est renvoyé déjà en snake_case, ce
    qui rend un éventuel appel englobant `to_snake_case(pluralize(...))`
    (fait par tous les appelants actuels) idempotent.

    Utilise la bibliothèque `inflect`, qui couvre les pluriels irréguliers
    anglais (`category` -> `categories`, `person` -> `people`, `child` ->
    `children`, `property` -> `properties`...) plutôt que la seule
    heuristique suffixe s/x/z/ch/sh -> es, y -> ies de l'ancienne version —
    reste malgré tout un pluriel ANGLAIS uniquement, y compris pour un nom
    d'entité déclaré dans une autre langue du DSL (limitation documentée :
    NOVA ne pluralise pas en français/espagnol/etc.)."""
    snake = to_snake_case(name)
    if not snake:
        return snake
    parts = snake.split("_")
    last = parts[-1]
    if _INFLECT is not None:
        plural_last = _INFLECT.plural(last) if last else last
    else:  # pragma: no cover
        plural_last = _pluralize_naive(last)
    parts[-1] = plural_last or last
    return "_".join(parts)


# Types NOVA canoniques -> types Python
# `file`/`image`/`color` sont stockés comme de simples chaînes côté backend
# (chemin/URL pour file/image — voir codegen/api_fastapi._generate_uploads_router,
# code hexadécimal "#rrggbb" pour color) : aucune colonne SQL spécifique
# n'est nécessaire, tout l'enrichissement (upload, aperçu, sélecteur natif)
# se fait côté frontend (codegen/ui_reflex.py).
PY_TYPE_MAP = {
    "string": "str",
    "text": "str",
    "int": "int",
    "float": "float",
    "bool": "bool",
    "date": "date",
    "datetime": "datetime",
    "file": "str",
    "image": "str",
    "color": "str",
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
    "file": '""',
    "image": '""',
    "color": '""',
}
