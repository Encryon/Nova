"""
Tables de canonicalisation multilingues.

Chaque table associe un mot-clé (dans n'importe laquelle des langues
supportées : français, anglais, espagnol, allemand, italien, portugais, tel
qu'il apparaît dans le fichier .nova) à sa forme canonique interne, utilisée
partout ailleurs dans le compilateur. Ajouter une langue ou un synonyme se
fait uniquement ici et dans la grammaire (`grammar/nova.lark`), sans toucher
au reste du compilateur.
"""

TYPES = {
    "string": "string", "chaine": "string", "chaîne": "string",
    "cadena": "string", "zeichenkette": "string", "stringa": "string", "cadeia": "string",
    "text": "text", "texte": "text",
    "texto": "text", "testo": "text",
    "int": "int", "integer": "int", "entier": "int",
    "entero": "int", "ganzzahl": "int", "intero": "int", "inteiro": "int",
    "float": "float", "decimal": "float", "décimal": "float",
    "flotante": "float", "gleitkomma": "float", "decimale": "float",
    "bool": "bool", "boolean": "bool", "booleen": "bool", "booléen": "bool",
    "booleano": "bool", "boolesch": "bool",
    "date": "date", "fecha": "date", "datum": "date", "data": "date",
    "datetime": "datetime", "date_heure": "datetime",
    "fecha_hora": "datetime", "datum_zeit": "datetime", "data_ora": "datetime", "data_hora": "datetime",
}

ACTIONS = {
    "list": "list", "liste": "list", "listar": "list", "lista": "list",
    "elenco": "list", "auflisten": "list",
    "create": "create", "creer": "create", "créer": "create",
    "crear": "create", "erstellen": "create", "creare": "create", "criar": "create",
    "update": "update", "modifier": "update",
    "mettre_a_jour": "update", "mettre_à_jour": "update",
    "actualizar": "update", "aktualisieren": "update", "aggiornare": "update", "atualizar": "update",
    "delete": "delete", "supprimer": "delete",
    "eliminar": "delete", "borrar": "delete", "loeschen": "delete", "löschen": "delete",
    "eliminare": "delete", "excluir": "delete",
    "get": "get", "obtenir": "get", "lire": "get",
    "obtener": "get", "erhalten": "get", "holen": "get", "ottenere": "get", "obter": "get",
}

RELATIONS = {
    "has_many": "has_many", "possede_plusieurs": "has_many", "possède_plusieurs": "has_many",
    "tiene_muchos": "has_many", "hat_viele": "has_many", "ha_molti": "has_many", "tem_muitos": "has_many",
    "belongs_to": "belongs_to", "appartient_a": "belongs_to", "appartient_à": "belongs_to",
    "pertenece_a": "belongs_to", "gehoert_zu": "belongs_to", "gehört_zu": "belongs_to",
    "appartiene_a": "belongs_to", "pertence_a": "belongs_to",
}

DISPLAY_MODES = {
    "table": "table", "tabla": "table", "tabelle": "table", "tabella": "table", "tabela": "table",
    "form": "form", "formulaire": "form",
    "formulario": "form", "formulário": "form", "formular": "form", "modulo": "form",
    "card": "card", "carte": "card",
    "tarjeta": "card", "karte": "card", "scheda": "card", "cartao": "card", "cartão": "card",
}

BOOLEANS = {
    "true": True, "vrai": True, "verdadero": True, "wahr": True, "vero": True, "verdadeiro": True,
    "false": False, "faux": False, "falso": False, "falsch": False,
}

PROP_NAMES = {
    "name": "name", "nom": "name", "nombre": "name", "nome": "name",
    "description": "description", "descripcion": "description", "descripción": "description",
    "beschreibung": "description", "descrizione": "description",
    "descricao": "description", "descrição": "description",
    "lang": "lang", "langue": "lang", "idioma": "lang", "lingua": "lang", "sprache": "lang",
    "version": "version",
    "css": "css", "feuille_style": "css", "stylesheet": "css",
    "hoja_estilo": "css", "stildatei": "css", "foglio_stile": "css", "folha_estilo": "css",
}

# ---- modificateurs de champ (`required`/`unique`/`pattern`) --------------
# Utilisés directement par le parser (nova_compiler.parser._NovaTransformer.
# modifier) plutôt que via un dict de canonicalisation à une seule valeur,
# car chaque mot-clé y déclenche une logique légèrement différente.
REQUIRED_WORDS = {
    "required", "requis", "requerido", "obligatorio",
    "erforderlich", "richiesto", "obbligatorio", "obrigatorio", "obrigatório",
}
UNIQUE_WORDS = {"unique", "unico", "único", "eindeutig"}
PATTERN_WORDS = {
    "pattern", "motif", "regex", "patron", "patrón", "muster", "modello", "formato",
}

# ---- alias de propriétés de style (bloc `style { ... }`) -----------------
# Un alias bilingue pratique pour les propriétés CSS les plus courantes ;
# toute clé absente de cette table est passée telle quelle (kebab-case ou
# snake_case), convertie en camelCase pour Reflex — c'est la "porte de
# sortie" qui garde le bloc `style` aussi souple que du CSS brut.
STYLE_ALIASES = {
    "couleur": "color", "color": "color",
    "couleur_texte": "color", "text_color": "color",
    "couleur_fond": "background-color", "fond": "background-color",
    "background": "background-color", "background_color": "background-color",
    "bordure": "border", "border": "border",
    "arrondi": "border-radius", "border_radius": "border-radius",
    "police": "font-family", "font_family": "font-family",
    "taille_police": "font-size", "font_size": "font-size",
    "epaisseur": "font-weight", "font_weight": "font-weight",
    "marge": "margin", "margin": "margin",
    "espacement": "padding", "padding": "padding",
    "ombre": "box-shadow", "box_shadow": "box-shadow",
    "largeur": "width", "width": "width",
    "hauteur": "height", "height": "height",
}
# Clé spéciale : nom de classe CSS (voir aussi le fichier chargé via
# `application { css: "..." }`) plutôt qu'une propriété de style inline.
STYLE_CLASS_KEYS = {"classe", "class", "class_name"}


def strip_quotes(raw: str) -> str:
    """'"Hello"' -> 'Hello'"""
    return raw[1:-1] if raw.startswith('"') and raw.endswith('"') else raw
