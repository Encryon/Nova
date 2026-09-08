"""
Parser NOVA : source .nova (FR/EN) -> AST canonique (nova_compiler.ast_nodes).
"""

from __future__ import annotations

from pathlib import Path

from lark import Lark, Transformer, v_args
from lark.exceptions import LarkError

from . import keywords as kw
from .ast_nodes import Api, App, Auth, Entity, Field, NovaProgram, Page, PageShow, Query, QueryFilter, Relation

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
            if key in kw.REQUIRED_WORDS:
                return ("required", True)
            if key in kw.UNIQUE_WORDS:
                return ("unique", True)
        else:
            first_key = str(parts[0])
            if first_key in kw.PATTERN_WORDS:
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

    def protect_stmt(self, _kw_tok, role_tok):
        return ("protect", str(role_tok))

    def api_member(self, member):
        return member

    def api_decl(self, _kw_tok, name_tok, *members):
        api = Api(entity=str(name_tok))
        for m in members:
            if isinstance(m, tuple) and m[0] == "protect":
                api.protected_role = m[1]
            else:
                api.actions.append(m)
        return api

    # ---- page --------------------------------------------------------------
    def display_mode(self, tok):
        return kw.DISPLAY_MODES.get(str(tok), str(tok))

    def style_prop(self, key_tok, val_tok):
        return (str(key_tok), kw.strip_quotes(str(val_tok)))

    def style_block(self, _kw_tok, *props):
        return dict(props)

    def page_stmt(self, _kw_tok, name_tok, *rest):
        mode = "table"
        title = None
        style: dict[str, str] = {}
        for r in rest:
            # Ignore les tokens de mot-clé eux-mêmes (AS_KW / TITLE_KW) : seuls
            # les enfants déjà résolus (display_mode -> str canonique, le
            # token STRING du titre, ou le dict issu de style_block) nous
            # intéressent ici.
            tok_type = getattr(r, "type", None)
            if tok_type in ("AS_KW", "TITLE_KW"):
                continue
            if tok_type == "STRING":
                title = kw.strip_quotes(str(r))
            elif isinstance(r, dict):
                style = r
            elif isinstance(r, str) and r in ("table", "form", "card"):
                mode = r
        return PageShow(entity=str(name_tok), mode=mode, title=title, style=style)

    def page_decl(self, _kw_tok, name_tok, *shows):
        return Page(name=str(name_tok), shows=list(shows))

    # ---- auth --------------------------------------------------------------
    def name_list(self, *names):
        return [str(n) for n in names]

    def auth_prop(self, kw_tok, value):
        key = str(kw_tok)
        if key in ("roles", "rôles"):
            return ("roles", value)
        return ("default_role", str(value))

    def auth_decl(self, _kw_tok, *props):
        auth = Auth(enabled=True)
        for key, val in props:
            if key == "roles":
                auth.roles = val
            elif key == "default_role":
                auth.default_role = val
                if val not in auth.roles:
                    auth.roles.append(val)
        return auth

    # ---- query ---------------------------------------------------------------
    def query_prop(self, kw_tok, *rest):
        key = str(kw_tok)
        if key in ("filtre", "filter"):
            field_tok, comparator_tok, val = rest
            return ("filter", QueryFilter(field=str(field_tok), op=str(comparator_tok), value=val))
        if key in ("trier_par", "sort_by", "order_by"):
            field_tok = rest[0]
            direction = "asc"
            if len(rest) > 1 and getattr(rest[1], "type", None) == "DESC_KW":
                direction = "desc"
            return ("order", (str(field_tok), direction))
        if key in ("limite", "limit"):
            return ("limit", int(str(rest[0])))
        return ("unknown", None)

    def query_decl(self, _kw_tok, name_tok, _sur_tok, entity_tok, *props):
        q = Query(name=str(name_tok), entity=str(entity_tok))
        for key, val in props:
            if key == "filter":
                q.filters.append(val)
            elif key == "order":
                q.order_by, q.order_dir = val
            elif key == "limit":
                q.limit = val
        return q

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
            elif isinstance(s, Auth):
                program.auth = s
            elif isinstance(s, Query):
                program.queries.append(s)
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
