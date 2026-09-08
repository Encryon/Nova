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

    @property
    def is_reference(self) -> bool:
        """True si ce champ référence une autre entité plutôt qu'un type scalaire."""
        return self.type not in _SCALAR_TYPES


_SCALAR_TYPES = {"string", "text", "int", "float", "bool", "date", "datetime"}


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


@dataclass
class PageShow:
    entity: str
    mode: str = "table"        # "table" | "form" | "card"
    title: Optional[str] = None
    style: dict[str, str] = field(default_factory=dict)  # bloc `style { ... }` (voir keywords.STYLE_ALIASES)


@dataclass
class Page:
    name: str
    shows: list[PageShow] = field(default_factory=list)


@dataclass
class App:
    name: str
    props: dict[str, Union[str, int, float, bool]] = field(default_factory=dict)


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
class Query:
    """Bloc `requete <Nom> sur <Entite> { ... }` : requête déclarative
    au-delà du CRUD simple (filtre/tri/limite), sans SQL à écrire."""
    name: str
    entity: str
    filters: list[QueryFilter] = field(default_factory=list)
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
    type: str = "bar"                  # "bar" | "line" | "pie" | "area"
    x_field: Optional[str] = None
    y_field: Optional[str] = None
    title: Optional[str] = None


@dataclass
class NovaProgram:
    app: Optional[App] = None
    entities: list[Entity] = field(default_factory=list)
    apis: list[Api] = field(default_factory=list)
    pages: list[Page] = field(default_factory=list)
    auth: Optional[Auth] = None
    queries: list[Query] = field(default_factory=list)
    charts: list[Chart] = field(default_factory=list)

    def get_entity(self, name: str) -> Optional[Entity]:
        return next((e for e in self.entities if e.name == name), None)

    def get_query(self, name: str) -> Optional[Query]:
        return next((q for q in self.queries if q.name == name), None)
