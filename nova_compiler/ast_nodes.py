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


@dataclass
class PageShow:
    entity: str
    mode: str = "table"        # "table" | "form" | "card"
    title: Optional[str] = None


@dataclass
class Page:
    name: str
    shows: list[PageShow] = field(default_factory=list)


@dataclass
class App:
    name: str
    props: dict[str, Union[str, int, float, bool]] = field(default_factory=dict)


@dataclass
class NovaProgram:
    app: Optional[App] = None
    entities: list[Entity] = field(default_factory=list)
    apis: list[Api] = field(default_factory=list)
    pages: list[Page] = field(default_factory=list)

    def get_entity(self, name: str) -> Optional[Entity]:
        return next((e for e in self.entities if e.name == name), None)
