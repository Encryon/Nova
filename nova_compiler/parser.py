"""
Parser NOVA : source .nova (FR/EN) -> AST canonique (nova_compiler.ast_nodes).
"""

from __future__ import annotations

from pathlib import Path

from lark import Lark, Transformer, v_args
from lark.exceptions import LarkError

from . import keywords as kw
from .ast_nodes import Api, App, Entity, Field, NovaProgram, Page, PageShow, Relation

_GRAMMAR_PATH = Path(__file__).parent / "grammar" / "nova.lark"


class NovaSyntaxError(Exception):
    """Erreur de syntaxe dans un fichier .nova, avec position si connue."""


@v_args(inline=True)
class _NovaTransformer(Transformer):
    """Transforme l'arbre Lark brut en objets AST canoniques."""

    # ---- valeurs scalaires -------------------------------------------------
    def value(self, tok):
        text = str(tok)
        if text in kw.BOOLEANS:
            return kw.BOOLEANS[text]
        if text.startswith('"'):
            return kw.strip_quotes(text)
        try:
            if "." in text:
                return float(text)
            return int(text)
        except ValueError:
            return text  # identifiant nu (ex: lang: fr)

    # ---- app ---------------------------------------------------------------
    def app_prop(self, prop_name_tok, value):
        canonical = kw.PROP_NAMES.get(str(prop_name_tok), str(prop_name_tok))
        return (canonical, value)

    def app_decl(self, _kw_tok, name_tok, *props):
        return App(name=str(name_tok), props=dict(props))

    # ---- entity --------------------------------------------------------------
    def type_ref(self, tok):
        text = str(tok)
        return kw.TYPES.get(text, text)  # sinon: référence à une autre entité

    def modifier(self, *parts):
        # ("required",) | ("unique",) | ("default", value) | ("pattern", regex)
        if len(parts) == 1:
            key = str(parts[0])
            if key in ("required", "requis"):
                return ("required", True)
            if key == "unique":
                return ("unique", True)
        else:
            first_key = str(parts[0])
            if first_key in ("pattern", "motif", "regex"):
                return ("pattern", kw.strip_quotes(str(parts[-1])))
            return ("default", parts[-1])
        return ("unknown", True)

    def field_decl(self, _kw_tok, name_tok, type_ref, *modifiers):
        f = Field(name=str(name_tok), type=type_ref)
        for key, val in modifiers:
            if key == "required":
                f.required = True
            elif key == "unique":
                f.unique = True
            elif key == "default":
                f.default = val
            elif key == "pattern":
                f.pattern = val
        return f

    def relation_decl(self, kw_tok, name_tok):
        kind = kw.RELATIONS.get(str(kw_tok), str(kw_tok))
        return Relation(kind=kind, target=str(name_tok))

    def entity_member(self, member):
        return member

    def entity_decl(self, _kw_tok, name_tok, *members):
        entity = Entity(name=str(name_tok))
        for m in members:
            if isinstance(m, Field):
                entity.fields.append(m)
            elif isinstance(m, Relation):
                entity.relations.append(m)
        return entity

    # ---- api -------------------------------------------------------------
    def api_action(self, tok):
        return kw.ACTIONS.get(str(tok), str(tok))

    def api_decl(self, _kw_tok, name_tok, *actions):
        return Api(entity=str(name_tok), actions=list(actions))

    # ---- page --------------------------------------------------------------
    def display_mode(self, tok):
        return kw.DISPLAY_MODES.get(str(tok), str(tok))

    def page_stmt(self, _kw_tok, name_tok, *rest):
        mode = "table"
        title = None
        for r in rest:
            # Ignore les tokens de mot-clé eux-mêmes (AS_KW / TITLE_KW) : seuls
            # les enfants déjà résolus (display_mode -> str canonique, ou le
            # token STRING du titre) nous intéressent ici.
            tok_type = getattr(r, "type", None)
            if tok_type in ("AS_KW", "TITLE_KW"):
                continue
            if tok_type == "STRING":
                title = kw.strip_quotes(str(r))
            elif isinstance(r, str) and r in ("table", "form", "card"):
                mode = r
        return PageShow(entity=str(name_tok), mode=mode, title=title)

    def page_decl(self, _kw_tok, name_tok, *shows):
        return Page(name=str(name_tok), shows=list(shows))

    # ---- programme -----------------------------------------------------
    def statement(self, stmt):
        return stmt

    def start(self, *statements):
        program = NovaProgram()
        for s in statements:
            if isinstance(s, App):
                program.app = s
            elif isinstance(s, Entity):
                program.entities.append(s)
            elif isinstance(s, Api):
                program.apis.append(s)
            elif isinstance(s, Page):
                program.pages.append(s)
        return program


def _build_parser() -> Lark:
    grammar_text = _GRAMMAR_PATH.read_text(encoding="utf-8")
    return Lark(grammar_text, parser="lalr", maybe_placeholders=False)


_parser = _build_parser()


def parse_source(source: str) -> NovaProgram:
    """Parse le texte d'un fichier .nova et retourne l'AST (NovaProgram)."""
    try:
        tree = _parser.parse(source)
    except LarkError as exc:
        raise NovaSyntaxError(str(exc)) from exc
    return _NovaTransformer().transform(tree)


def parse_file(path: str | Path) -> NovaProgram:
    text = Path(path).read_text(encoding="utf-8")
    return parse_source(text)
