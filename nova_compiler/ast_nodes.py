"""
AST canonique de NOVA.

Peu importe que le fichier source ait été écrit en français ou en anglais
(ou un mélange des deux) : le parser produit toujours les mêmes objets
Python ci-dessous. Tout le reste du compilateur (codegen FastAPI, Reflex,
Docker, K8s...) ne travaille que sur cet AST, jamais sur le texte source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Union

from .keywords import LANG_CODES


# --------------------------------------------------------------------------- #
# Types de champs canoniques
# --------------------------------------------------------------------------- #

@dataclass
class Field:
    name: str
    type: str                      # "string" | "text" | "int" | "float" | "bool" | "date" | "datetime" | <EntityName>
    required: bool = False
    unique: bool = False
    default: Optional[Union[str, int, float, bool]] = None
    pattern: Optional[str] = None  # expression régulière de validation (pattern/motif/regex)
    multilingual: bool = False     # modificateur `multilingue`/`multilingual` (chaine/texte uniquement)

    @property
    def is_reference(self) -> bool:
        """True si ce champ référence une autre entité plutôt qu'un type scalaire."""
        return self.type not in _SCALAR_TYPES


_SCALAR_TYPES = {"string", "text", "int", "float", "bool", "date", "datetime", "file", "image", "color"}


@dataclass
class Relation:
    kind: str          # "has_many" | "belongs_to"
    target: str        # nom de l'entité liée


@dataclass
class Entity:
    name: str
    fields: list[Field] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)


@dataclass
class Api:
    entity: str
    actions: list[str] = field(default_factory=list)  # subset of list/create/update/delete/get
    protected_role: Optional[str] = None  # `proteger: <role>` — None = API publique
    notify_actions: list[str] = field(default_factory=list)  # subset of create/update/delete (`notifier:`)
    # `destinataire: <champ>` : champ de l'entité (string) contenant l'adresse
    # email du destinataire pour CETTE notification — si absent, retombe sur
    # le destinataire fixe du bloc `email`/NOVA_SMTP_TO (comportement
    # historique inchangé). Validé par parser.py::_validate_notifiers.
    notify_recipient_field: Optional[str] = None
    # `piece_jointe: <champ>` : champ `file`/`image` de l'entité dont le
    # fichier stocké est joint à la notification (aucune pièce jointe si le
    # champ est vide sur l'enregistrement). Même validation.
    notify_attachment_field: Optional[str] = None


@dataclass
class PageShow:
    entity: str
    mode: str = "table"        # "table" | "form" | "card"
    title: Optional[str] = None
    title_key: Optional[str] = None  # `titre <cle>` référençant un bloc `traductions` (mutuellement exclusif avec `title`)
    style: dict[str, str] = field(default_factory=dict)  # bloc `style { ... }` (voir keywords.STYLE_ALIASES)


@dataclass
class Page:
    name: str
    shows: list[PageShow] = field(default_factory=list)


@dataclass
class App:
    name: str
    props: dict[str, Union[str, int, float, bool]] = field(default_factory=dict)
    # `application { langues: fr, en }` (alias `languages`/`idiomas`/
    # `sprachen`/`lingue`) : restreint les langues ACTIVES du projet généré
    # (colonnes `champ multilingue`, bloc `traductions`, sélecteur de langue
    # frontend) à ce sous-ensemble, dans l'ordre déclaré. Vide (défaut) =
    # pas de restriction, les 6 langues du DSL (`keywords.LANG_CODES`)
    # restent actives — comportement historique inchangé. Voir
    # `NovaProgram.active_languages` et parser._validate_app_languages.
    languages: list[str] = field(default_factory=list)


@dataclass
class Auth:
    """Bloc `auth { ... }` : active l'authentification JWT + rôles pour tout
    le projet généré. Absent (NovaProgram.auth is None) = pas d'auth."""
    enabled: bool = True
    roles: list[str] = field(default_factory=lambda: ["user"])
    default_role: str = "user"


@dataclass
class QueryFilter:
    field: str
    op: str                                    # ">" | "<" | ">=" | "<=" | "==" | "!="
    value: Union[str, int, float, bool] = None


@dataclass
class QueryFilterGroup:
    """Groupe de filtres combinés par OU entre eux (bloc `ou: { filtre: ...
    filtre: ... }` dans un `requete`/`query`), le groupe entier étant
    lui-même combiné par ET avec le reste des `filtre:` de premier niveau et
    les autres groupes `ou:` — voir Query.filter_groups ci-dessous."""
    filters: list[QueryFilter] = field(default_factory=list)


@dataclass
class Query:
    """Bloc `requete <Nom> sur <Entite> { ... }` : requête déclarative
    au-delà du CRUD simple (filtre/tri/limite), sans SQL à écrire.
    `filters` (premier niveau) sont toujours combinés par ET entre eux et
    avec chaque groupe de `filter_groups` (`ou: { ... }`) ; à l'intérieur
    d'un même groupe, les filtres sont combinés par OU."""
    name: str
    entity: str
    filters: list[QueryFilter] = field(default_factory=list)
    filter_groups: list[QueryFilterGroup] = field(default_factory=list)
    order_by: Optional[str] = None
    order_dir: str = "asc"                      # "asc" | "desc"
    limit: Optional[int] = None


@dataclass
class Chart:
    """Bloc `chart <Nom> sur <Entite|Requete> { ... }` : graphique déclaratif.
    `source` référence soit une Entity (données = son API liste), soit une
    Query déjà déclarée (données déjà filtrées/triées) — résolu au moment de
    la génération (voir codegen/ui_reflex.py), pas au moment du parsing."""
    name: str
    source: str
    type: str = "bar"                  # "bar" | "line" | "pie" | "area" | "radar" | "scatter"
    x_field: Optional[str] = None
    y_field: Optional[str] = None      # première (ou unique) série — conservé pour compatibilité
    y_fields: list = field(default_factory=list)  # toutes les séries (multi-séries bar/line/area)
    title: Optional[str] = None


@dataclass
class Email:
    """Bloc `email { ... }` optionnel : configuration SMTP par défaut pour
    les notifications déclenchées par `notifier:` sur un bloc `api`. Le mot
    de passe SMTP n'est JAMAIS porté par cet objet (donc jamais lu depuis le
    fichier .nova) : toujours fourni au runtime via la variable
    d'environnement NOVA_SMTP_PASSWORD, comme NOVA_JWT_SECRET pour l'auth
    (voir codegen/api_fastapi.py::_generate_emailer)."""
    host: str = "localhost"
    port: int = 587
    user: str = ""
    from_addr: str = ""
    to_addr: str = ""
    tls: bool = True


@dataclass
class ValidationRule:
    """Une règle d'un bloc `validation` : compare DEUX champs d'une même
    entité entre eux (`field_a <op> field_b`), avec son propre message
    d'erreur — voir `Validation` ci-dessous."""
    field_a: str
    op: str                                    # ">" | "<" | ">=" | "<=" | "==" | "!="
    field_b: str
    message: str


@dataclass
class Validation:
    """Bloc `validation <Nom> sur <Entite> { regle: ... message: "..." }` :
    validation croisant plusieurs champs, appliquée à la création ET à la
    modification (voir codegen/api_fastapi.py::_validation_check_lines) —
    au-delà de ce qu'un `modifier` sur UN SEUL `field_decl` peut exprimer
    (requis/unique/motif/default)."""
    name: str
    entity: str
    rules: list[ValidationRule] = field(default_factory=list)


@dataclass
class Calendar:
    """Bloc `calendar <Nom> sur <Entite> { ... }` : vue calendrier mensuelle
    déclarative. `date_field` : champ date/date_heure de l'entité utilisé
    pour placer chaque enregistrement dans la grille du mois — si omis,
    résolu au premier champ date/datetime de l'entité (voir
    parser.py::_validate_calendars). `title_field` : champ affiché dans
    chaque cellule du jour — si omis, aucun libellé n'est affiché au-delà du
    numéro du jour (voir codegen/ui_reflex.py)."""
    name: str
    entity: str
    date_field: Optional[str] = None
    title_field: Optional[str] = None


@dataclass
class NovaProgram:
    app: Optional[App] = None
    entities: list[Entity] = field(default_factory=list)
    apis: list[Api] = field(default_factory=list)
    pages: list[Page] = field(default_factory=list)
    auth: Optional[Auth] = None
    queries: list[Query] = field(default_factory=list)
    charts: list[Chart] = field(default_factory=list)
    email: Optional[Email] = None
    calendars: list[Calendar] = field(default_factory=list)
    validations: list[Validation] = field(default_factory=list)
    # Bloc(s) `traductions { cle: { fr: "..." ... } }` : cle -> {code_langue: texte}.
    # Toutes les 6 langues sont requises par entrée (voir parser._validate_translations).
    translations: dict[str, dict[str, str]] = field(default_factory=dict)

    def get_entity(self, name: str) -> Optional[Entity]:
        return next((e for e in self.entities if e.name == name), None)

    def get_query(self, name: str) -> Optional[Query]:
        return next((q for q in self.queries if q.name == name), None)

    def active_languages(self) -> list[str]:
        """Langues actives du projet : `application { langues: ... }` si
        déclaré (sous-ensemble, dans l'ordre déclaré), sinon les 6 langues
        du DSL (comportement historique). Utilisée partout où une colonne/
        un state var/une entrée de traduction est générée par langue,
        plutôt que `keywords.LANG_CODES` codé en dur — voir
        codegen/api_fastapi.py et codegen/ui_reflex.py."""
        if self.app and self.app.languages:
            return self.app.languages
        return LANG_CODES

    def database_engine(self) -> str:
        """Moteur de base de données du projet : `application { database:
        postgresql }` (valeur canonique, voir parser._validate_app_database
        et keywords.DATABASE_ENGINES) si déclaré, sinon "sqlite"
        (comportement historique inchangé). Utilisée par tout le codegen
        backend/docker/k8s pour choisir le driver, l'URL de connexion par
        défaut et le service `db` docker-compose."""
        if self.app:
            return self.app.props.get("database", "sqlite")
        return "sqlite"
