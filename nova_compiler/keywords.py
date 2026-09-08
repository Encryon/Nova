"""
Tables de canonicalisation bilingues FR/EN.

Chaque table associe un mot-clé (français ou anglais, tel qu'il apparaît
dans le fichier .nova) à sa forme canonique interne, utilisée partout
ailleurs dans le compilateur. Ajouter une langue ou un synonyme se fait
uniquement ici, sans toucher à la grammaire ni au codegen.
"""

TYPES = {
    "string": "string", "chaine": "string", "chaîne": "string",
    "text": "text", "texte": "text",
    "int": "int", "integer": "int", "entier": "int",
    "float": "float", "decimal": "float", "décimal": "float",
    "bool": "bool", "boolean": "bool", "booleen": "bool", "booléen": "bool",
    "date": "date",
    "datetime": "datetime", "date_heure": "datetime",
}

ACTIONS = {
    "list": "list", "liste": "list",
    "create": "create", "creer": "create", "créer": "create",
    "update": "update", "modifier": "update",
    "mettre_a_jour": "update", "mettre_à_jour": "update",
    "delete": "delete", "supprimer": "delete",
    "get": "get", "obtenir": "get", "lire": "get",
}

RELATIONS = {
    "has_many": "has_many", "possede_plusieurs": "has_many", "possède_plusieurs": "has_many",
    "belongs_to": "belongs_to", "appartient_a": "belongs_to", "appartient_à": "belongs_to",
}

DISPLAY_MODES = {
    "table": "table",
    "form": "form", "formulaire": "form",
    "card": "card", "carte": "card",
}

BOOLEANS = {
    "true": True, "vrai": True,
    "false": False, "faux": False,
}

PROP_NAMES = {
    "name": "name", "nom": "name",
    "description": "description",
    "lang": "lang", "langue": "lang",
    "version": "version",
}


def strip_quotes(raw: str) -> str:
    """'"Hello"' -> 'Hello'"""
    return raw[1:-1] if raw.startswith('"') and raw.endswith('"') else raw
