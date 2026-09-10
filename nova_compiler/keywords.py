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
    "file": "file", "fichier": "file", "archivo": "file", "datei": "file", "arquivo": "file",
    "image": "image", "imagen": "image", "bild": "image", "immagine": "image", "imagem": "image",
    "color": "color", "couleur": "color", "farbe": "color", "colore": "color", "cor": "color",
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
    "database": "database", "base_donnees": "database", "base_données": "database",
    "base_datos": "database", "datenbank": "database", "banco_dados": "database",
}

# ---- bloc `application { database: ... }` (moteur SQL, tâche #28) --------
# Les noms de moteur eux-mêmes sont des noms propres (pas de traduction par
# langue, contrairement au reste du DSL) : quelques alias usuels tolérés
# (`postgres` pour `postgresql`, `mssql`/`sql_server` pour `sqlserver`) pour
# rester tolérant, mais la valeur canonique (à droite) est la seule utilisée
# ensuite par tout le codegen (`NovaProgram.database_engine`, voir
# codegen/api_fastapi.py::_generate_database, codegen/docker.py::_compose,
# codegen/k8s.py::_values_yaml) : driver requirements.txt à installer, URL de
# connexion par défaut, service `db` docker-compose. Absent de `application
# { ... }` = "sqlite" (comportement historique inchangé, aucune dépendance
# supplémentaire).
DATABASE_ENGINES = {
    "sqlite": "sqlite",
    "postgresql": "postgresql", "postgres": "postgresql", "postgre": "postgresql",
    "mysql": "mysql", "mariadb": "mysql", "maria": "mysql",
    "sqlserver": "sqlserver", "sql_server": "sqlserver", "mssql": "sqlserver",
    "oracle": "oracle",
    # NoSQL (tâche #29, voir codegen/api_mongo.py) : backend généré
    # entièrement différent (Beanie/Motor), pas un simple driver
    # supplémentaire — voir generate_backend_mongo, jamais DB_DRIVER_
    # REQUIREMENTS/_generate_database ci-dessous (spécifiques SQLModel/SQL).
    "mongodb": "mongodb", "mongo": "mongodb",
}

# URL de connexion par défaut par moteur (utilisée UNIQUEMENT si
# NOVA_DATABASE_URL n'est pas fournie à l'exécution, voir codegen/
# api_fastapi.py::_generate_database) : identifiants de développement en
# clair, jamais destinés à la production (toujours surchargeables via
# variable d'environnement / Secret Helm). L'hôte "db" et ces mêmes
# identifiants correspondent au service `db` docker-compose généré par
# codegen/docker.py::_compose pour tout moteur autre que sqlite — une seule
# source de vérité partagée par les deux générateurs.
DB_DEFAULT_URLS = {
    "sqlite": "sqlite:///./nova.db",
    "postgresql": "postgresql+psycopg2://nova:nova@db:5432/nova",
    "mysql": "mysql+pymysql://nova:nova@db:3306/nova",
    "sqlserver": (
        "mssql+pyodbc://sa:NovaDev123!@db:1433/nova"
        "?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes"
    ),
    "oracle": "oracle+oracledb://system:nova@db:1521/?service_name=FREEPDB1",
    "mongodb": "mongodb://nova:nova@db:27017/nova?authSource=admin",
}

# Driver Python à ajouter à requirements.txt selon le moteur choisi — sqlite
# n'en a besoin d'aucun (module `sqlite3` de la stdlib).
DB_DRIVER_REQUIREMENTS = {
    "postgresql": "psycopg2-binary>=2.9",
    "mysql": "pymysql>=1.1",
    "sqlserver": "pyodbc>=5.0",
    "oracle": "oracledb>=2.0",
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
MULTILINGUAL_WORDS = {
    "multilingual", "multilingue", "multilingüe", "mehrsprachig", "multilingua", "multilíngue",
}

# ---- bloc `traductions { ... }` (textes d'interface multilingues) --------
# Les 6 langues du DSL, dans un ordre canonique réutilisé partout où une
# liste ordonnée est nécessaire : suffixes de colonnes générées pour un
# champ `multilingue` (voir codegen/api_fastapi.py), cas du sélecteur de
# langue et des fonctions `t_<cle>()` générées (voir codegen/ui_reflex.py).
LANG_CODES = ["fr", "en", "es", "de", "it", "pt"]

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

# ---- bloc `chart { ... }` (graphiques) ------------------------------------
# Même philosophie que STYLE_ALIASES ci-dessus : les clés du bloc `chart`
# (`type`, `axe_x`/`x`, `axe_y`/`y`, `titre`/`title`) sont des NAME libres
# résolues ici plutôt que des mots-clés de grammaire — pas besoin de toucher
# `grammar/nova.lark` pour ajouter un synonyme. Seul le mot-clé du bloc
# lui-même (`chart`/`graphique`/...) est un terminal Lark (voir CHART_KW).
CHART_PROP_ALIASES = {
    "type": "type", "tipo": "type", "typ": "type",
    "axe_x": "x", "x": "x", "x_axis": "x",
    "eje_x": "x", "x_achse": "x", "asse_x": "x", "eixo_x": "x",
    "axe_y": "y", "y": "y", "y_axis": "y",
    "eje_y": "y", "y_achse": "y", "asse_y": "y", "eixo_y": "y",
    "titre": "title", "title": "title",
    "titulo": "title", "título": "title", "titel": "title", "titolo": "title",
    # Agrégation (tâche #35) : regroupe les lignes par `axe_x` puis agrège
    # `axe_y` avec une fonction de CHART_AGGREGATIONS ci-dessous — voir
    # codegen/ui_reflex.py::_CHART_AGGREGATE_HELPER pour le calcul.
    "agregation": "aggregation", "agrégation": "aggregation", "aggregation": "aggregation",
    "agregacion": "aggregation", "agregación": "aggregation",
    "aggregierung": "aggregation", "aggregazione": "aggregation",
    "agregacao": "aggregation", "agregação": "aggregation",
}
# Type de graphique : sous-ensemble volontairement restreint de rx.recharts
# (bar/line/area/pie) — le plus utile pour un tableau de bord simple.
CHART_TYPES = {
    "bar": "bar", "barres": "bar", "barre": "bar", "barra": "bar", "barras": "bar", "balken": "bar",
    "line": "line", "ligne": "line", "linea": "line", "línea": "line", "linie": "line", "linha": "line",
    "pie": "pie", "camembert": "pie", "tarta": "pie", "torta": "pie", "kreis": "pie", "pizza": "pie", "circular": "pie",
    "area": "area", "aire": "area", "área": "area", "flaeche": "area", "fläche": "area",
    "radar": "radar", "radial": "radar", "araignee": "radar", "araignée": "radar", "radarchart": "radar",
    "scatter": "scatter", "nuage": "scatter", "nuage_de_points": "scatter", "dispersion": "scatter",
    "streudiagramm": "scatter", "punktdiagramm": "scatter", "dispersao": "scatter", "dispersão": "scatter",
    # Nouveaux types (tâche #35) : "donut" = anneau (pie avec inner_radius,
    # voir codegen/ui_reflex.py) ; "funnel" = entonnoir (rx.recharts.funnel_chart).
    "donut": "donut", "anneau": "donut", "beignet": "donut",
    "rosquilla": "donut", "dona": "donut", "ciambella": "donut", "rosca": "donut",
    "funnel": "funnel", "entonnoir": "funnel", "embudo": "funnel",
    "trichter": "funnel", "imbuto": "funnel", "funil": "funnel",
}
# Types de graphique acceptant plusieurs séries (`axe_y` avec plusieurs
# champs séparés par des virgules) : bar/line/area se prêtent naturellement
# à un rendu multi-séries superposé ; pie (un seul anneau) et radar/scatter
# (un seul jeu de points par rapport à axe_x) n'ont pas de rendu multi-séries
# simple dans rx.recharts — restreint volontairement, voir _validate_charts.
CHART_MULTI_SERIES_TYPES = {"bar", "line", "area"}

# Fonction d'agrégation de la propriété `agregation`/`aggregation` du bloc
# `chart` (tâche #35) : regroupe les lignes par `axe_x` puis agrège chaque
# champ de `axe_y` — même philosophie de mini-dictionnaire d'alias que
# VALIDATION_FUNCTIONS plus bas. "count" ignore `axe_y` (compte les lignes
# du groupe) ; les autres agrègent une valeur numérique par groupe.
CHART_AGGREGATIONS = {
    "count": "count", "compte": "count", "nombre": "count", "cantidad": "count",
    "anzahl": "count", "conteggio": "count", "contagem": "count",
    "sum": "sum", "somme": "sum", "suma": "sum", "summe": "sum", "soma": "sum",
    "avg": "avg", "average": "avg", "moyenne": "avg", "promedio": "avg",
    "durchschnitt": "avg", "media": "avg",
    "min": "min", "minimum": "min", "mindestens": "min",
    "max": "max", "maximum": "max", "hoechstens": "max", "höchstens": "max",
}
# Valeurs canoniques valides (après résolution des alias ci-dessus) —
# utilisé par `_validate_charts` (parser.py) pour rejeter une fonction
# d'agrégation inconnue à la compilation.
CHART_AGGREGATION_CANONICAL = {"count", "sum", "avg", "min", "max"}


# ---- bloc `email { ... }` (configuration SMTP) ---------------------------
# Même philosophie que CHART_PROP_ALIASES ci-dessus : les clés du bloc
# `email` sont des NAME libres résolues ici plutôt que des mots-clés de
# grammaire. Volontairement PAS de clé pour le mot de passe : voir le
# commentaire sur `email_decl` dans grammar/nova.lark et
# codegen/api_fastapi.py::_generate_emailer — toujours NOVA_SMTP_PASSWORD.
EMAIL_PROP_ALIASES = {
    "hote": "host", "hôte": "host", "serveur": "host", "host": "host", "servidor": "host",
    "port": "port", "puerto": "port", "porta": "port",
    "utilisateur": "user", "user": "user", "usuario": "user", "benutzer": "user", "utente": "user",
    "expediteur": "from", "expéditeur": "from", "from": "from",
    "remitente": "from", "absender": "from", "mittente": "from", "remetente": "from",
    "destinataire": "to", "to": "to", "destinatario": "to",
    "empfaenger": "to", "empfänger": "to",
    "tls": "tls", "ssl": "tls",
    # Template HTML externe personnalisable (tâche #37) : chemin d'un
    # fichier .html, résolu relativement au fichier .nova source — même
    # mécanisme que `application { css: "..." }` (voir codegen/__init__.py
    # generate_project). Optionnel : sans lui, comportement historique
    # inchangé (sujet/corps HTML générés automatiquement).
    "modele": "template", "modèle": "template", "template": "template",
    "plantilla": "template", "vorlage": "template", "modello": "template",
    "modelo": "template",
}


# ---- bloc `calendar { ... }` (vue calendrier) -----------------------------
# Même philosophie que CHART_PROP_ALIASES/EMAIL_PROP_ALIASES ci-dessus : les
# clés du bloc `calendar` (`champ_date`/`date_field`, `champ_titre`/
# `title_field`) sont des NAME libres résolues ici plutôt que des mots-clés
# de grammaire.
CALENDAR_PROP_ALIASES = {
    "champ_date": "date_field", "date_field": "date_field",
    "campo_fecha": "date_field", "datumsfeld": "date_field",
    "campo_data": "date_field",
    "champ_titre": "title_field", "title_field": "title_field",
    "campo_titulo": "title_field", "campo_título": "title_field",
    "titelfeld": "title_field", "campo_titolo": "title_field",
}


# ---- bloc `validation { regle: ... }` (mini-langage d'expression) --------
# Même philosophie que CHART_PROP_ALIASES/EMAIL_PROP_ALIASES ci-dessus : le
# nom de fonction dans un appel `regle: min(a, b) > c message: "..."` est un
# NAME libre résolu ici plutôt qu'un mot-clé de grammaire par langue — un
# nouveau terminal Lark par fonction et par langue n'apporterait rien (pas
# de risque d'ambiguïté texte-vs-type comme sur ROLES_KW/FILTRE_KW, voir
# grammar/nova.lark) et alourdirait la grammaire pour rien. Chaque valeur
# canonique correspond directement à une fonction Python native de même
# nom (`min`/`max`/`round`/`abs`) — codegen/api_fastapi.py les émet telles
# quelles, sans dispatch supplémentaire.
VALIDATION_FUNCTIONS = {
    "min": "min", "minimum": "min", "mindestens": "min",
    "max": "max", "maximum": "max", "hoechstens": "max", "höchstens": "max",
    "round": "round", "arrondi": "round", "arrondir": "round",
    "redondear": "round", "runden": "round",
    "arrotonda": "round", "arrotondare": "round", "arredondar": "round",
    "abs": "abs", "valeur_absolue": "abs", "valor_absoluto": "abs",
    "betrag": "abs", "valore_assoluto": "abs",
}


def strip_quotes(raw: str) -> str:
    """'"Hello"' -> 'Hello'"""
    return raw[1:-1] if raw.startswith('"') and raw.endswith('"') else raw
