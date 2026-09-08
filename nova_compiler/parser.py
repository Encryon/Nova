"""
Parser NOVA : source .nova (FR/EN) -> AST canonique (nova_compiler.ast_nodes).
"""

from __future__ import annotations

from pathlib import Path

from lark import Lark, Transformer, v_args
from lark.exceptions import LarkError

from . import keywords as kw
from .ast_nodes import (
    Api,
    App,
    Auth,
    Calendar,
    Chart,
    Email,
    Entity,
    Field,
    NovaProgram,
    Page,
    PageShow,
    Query,
    QueryFilter,
    Relation,
)

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
        # ("required",) | ("unique",) | ("multilingual",) | ("default", value) | ("pattern", regex)
        if len(parts) == 1:
            key = str(parts[0])
            if key in kw.REQUIRED_WORDS:
                return ("required", True)
            if key in kw.UNIQUE_WORDS:
                return ("unique", True)
            if key in kw.MULTILINGUAL_WORDS:
                return ("multilingual", True)
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
            elif key == "multilingual":
                f.multilingual = True
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

    def notify_action(self, tok):
        return kw.ACTIONS.get(str(tok), str(tok))

    def notify_stmt(self, _kw_tok, *actions):
        return ("notify", list(actions))

    def api_member(self, member):
        return member

    def api_decl(self, _kw_tok, name_tok, *members):
        api = Api(entity=str(name_tok))
        for m in members:
            if isinstance(m, tuple) and m[0] == "protect":
                api.protected_role = m[1]
            elif isinstance(m, tuple) and m[0] == "notify":
                api.notify_actions = m[1]
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

    def title_value(self, tok):
        # `titre "Texte litteral"` (STRING, affiché tel quel dans toutes les
        # langues) vs `titre cle_traduction` (NAME nu, référence une entrée
        # du bloc `traductions { ... }`, résolue au moment de la génération —
        # voir `_validate_translations` pour l'erreur si la clé n'existe pas).
        text = str(tok)
        if text.startswith('"'):
            return ("literal", kw.strip_quotes(text))
        return ("key", text)

    def page_stmt(self, _kw_tok, name_tok, *rest):
        mode = "table"
        title = None
        title_key = None
        style: dict[str, str] = {}
        for r in rest:
            # Ignore les tokens de mot-clé eux-mêmes (AS_KW / TITLE_KW) : seuls
            # les enfants déjà résolus (display_mode -> str canonique, le
            # tuple issu de title_value, ou le dict issu de style_block) nous
            # intéressent ici.
            tok_type = getattr(r, "type", None)
            if tok_type in ("AS_KW", "TITLE_KW"):
                continue
            if isinstance(r, tuple) and r[0] == "literal":
                title = r[1]
            elif isinstance(r, tuple) and r[0] == "key":
                title_key = r[1]
            elif isinstance(r, dict):
                style = r
            elif isinstance(r, str) and r in ("table", "form", "card"):
                mode = r
        return PageShow(entity=str(name_tok), mode=mode, title=title, title_key=title_key, style=style)

    def page_decl(self, _kw_tok, name_tok, *shows):
        return Page(name=str(name_tok), shows=list(shows))

    # ---- auth --------------------------------------------------------------
    def name_list(self, *names):
        return [str(n) for n in names]

    def auth_prop(self, kw_tok, value):
        # Comparer le *type* du token (ROLES_KW / DEFAULT_ROLE_KW) plutôt que
        # son texte : chaque mot-clé a des synonymes dans 6 langues (voir
        # grammar/nova.lark) et un test sur le texte brut en oublierait la
        # plupart (bug réel trouvé lors de l'extension ES/DE/IT/PT).
        if kw_tok.type == "ROLES_KW":
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
        # Même principe que `auth_prop` ci-dessus : comparer `kw_tok.type`
        # (FILTRE_KW / TRIER_KW / LIMITE_KW) et non le texte du token, qui
        # varie selon la langue source (`filtro`, `ordina_per`, `límite`...).
        if kw_tok.type == "FILTRE_KW":
            field_tok, comparator_tok, val = rest
            return ("filter", QueryFilter(field=str(field_tok), op=str(comparator_tok), value=val))
        if kw_tok.type == "TRIER_KW":
            field_tok = rest[0]
            direction = "asc"
            if len(rest) > 1 and getattr(rest[1], "type", None) == "DESC_KW":
                direction = "desc"
            return ("order", (str(field_tok), direction))
        if kw_tok.type == "LIMITE_KW":
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

    # ---- chart -----------------------------------------------------------
    def chart_value(self, tok):
        # Non-terminal dédié (STRING | NAME) plutôt que le `value` générique
        # (voir le commentaire dans grammar/nova.lark juste au-dessus de
        # `chart_prop` : réutiliser `value` ici cassait le parsing ailleurs
        # dans la grammaire à cause d'un conflit LALR).
        text = str(tok)
        return kw.strip_quotes(text) if text.startswith('"') else text

    def chart_prop(self, key_tok, value):
        # Comme le bloc `style` : la clé est un NAME libre résolu via un
        # dict Python (kw.CHART_PROP_ALIASES), pas un terminal Lark dédié par
        # langue — ça évite complètement le bug de comparaison texte-vs-type
        # corrigé plus haut dans auth_prop/query_prop, puisqu'il n'y a pas de
        # mot-clé de grammaire par langue à oublier ici.
        key = kw.CHART_PROP_ALIASES.get(str(key_tok), str(key_tok))
        if key == "type" and isinstance(value, str):
            value = kw.CHART_TYPES.get(value, value)
        return (key, value)

    def chart_decl(self, _kw_tok, name_tok, _sur_tok, source_tok, *props):
        chart = Chart(name=str(name_tok), source=str(source_tok))
        for key, val in props:
            if key == "type":
                chart.type = val
            elif key == "x":
                chart.x_field = str(val)
            elif key == "y":
                chart.y_field = str(val)
            elif key == "title":
                chart.title = str(val)
        return chart

    # ---- email -------------------------------------------------------------
    def email_value(self, tok):
        # Même logique que `value()` (bool/string/int/identifiant nu), mais
        # via un non-terminal dédié — voir le commentaire sur `email_decl`
        # dans grammar/nova.lark (même raison que `chart_value`).
        text = str(tok)
        if text in kw.BOOLEANS:
            return kw.BOOLEANS[text]
        if text.startswith('"'):
            return kw.strip_quotes(text)
        try:
            return int(text)
        except ValueError:
            return text

    def email_prop(self, key_tok, value):
        # Comme `chart_prop` : clé NAME libre résolue via un dict Python
        # (kw.EMAIL_PROP_ALIASES), pas un mot-clé de grammaire par langue.
        key = kw.EMAIL_PROP_ALIASES.get(str(key_tok), str(key_tok))
        return (key, value)

    def email_decl(self, _kw_tok, *props):
        email = Email()
        for key, val in props:
            if key == "host":
                email.host = str(val)
            elif key == "port":
                email.port = int(val)
            elif key == "user":
                email.user = str(val)
            elif key == "from":
                email.from_addr = str(val)
            elif key == "to":
                email.to_addr = str(val)
            elif key == "tls":
                email.tls = bool(val) if isinstance(val, bool) else str(val) not in ("0", "false", "non", "no")
        return email

    # ---- calendar ----------------------------------------------------------
    def calendar_value(self, tok):
        # Non-terminal dédié (STRING | NAME) plutôt que le `value` générique —
        # même raison que `chart_value`/`email_value` (voir grammar/nova.lark).
        text = str(tok)
        return kw.strip_quotes(text) if text.startswith('"') else text

    def calendar_prop(self, key_tok, value):
        # Comme `chart_prop`/`email_prop` : clé NAME libre résolue via un
        # dict Python (kw.CALENDAR_PROP_ALIASES).
        key = kw.CALENDAR_PROP_ALIASES.get(str(key_tok), str(key_tok))
        return (key, value)

    def calendar_decl(self, _kw_tok, name_tok, _sur_tok, entity_tok, *props):
        cal = Calendar(name=str(name_tok), entity=str(entity_tok))
        for key, val in props:
            if key == "date_field":
                cal.date_field = str(val)
            elif key == "title_field":
                cal.title_field = str(val)
        return cal

    # ---- i18n (bloc `traductions { ... }`) ----------------------------------
    def lang_prop(self, lang_tok, str_tok):
        # Clé de langue NAME libre (`fr`/`en`/`es`/`de`/`it`/`pt`), validée
        # en Python (kw.LANG_CODES) plutôt qu'un terminal Lark par langue —
        # même raison que chart/email/calendar : voir grammar/nova.lark.
        return (str(lang_tok), kw.strip_quotes(str(str_tok)))

    def translation_entry(self, key_tok, *lang_props):
        return (str(key_tok), dict(lang_props))

    def translations_decl(self, _kw_tok, *entries):
        return ("translations", dict(entries))

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
            elif isinstance(s, Chart):
                program.charts.append(s)
            elif isinstance(s, Email):
                program.email = s
            elif isinstance(s, Calendar):
                program.calendars.append(s)
            elif isinstance(s, tuple) and s[0] == "translations":
                # Plusieurs blocs `traductions { ... }` sont autorisés (fusion
                # des dicts) ; une même clé redéclarée dans un second bloc
                # écrase la première — pas d'erreur levée, comportement jugé
                # suffisant pour ce MVP.
                program.translations.update(s[1])
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
    program = _NovaTransformer().transform(tree)
    _validate_charts(program)
    _validate_notifiers(program)
    _validate_calendars(program)
    _validate_multilingual_fields(program)
    _validate_translations(program)
    return program


def _validate_charts(program: NovaProgram) -> None:
    """`chart <Nom> sur <X>` : X doit être une entité ou une requête déjà
    déclarée. Contrairement à `query_decl` (pas de vérification équivalente
    aujourd'hui), on valide ici explicitement : une faute de frappe dans
    `sur` ne doit pas produire un projet généré qui échoue silencieusement
    au runtime — leçon tirée du bug auth_prop/query_prop plus haut."""
    known_entities = {e.name for e in program.entities}
    known_queries = {q.name for q in program.queries}
    for chart in program.charts:
        if chart.source not in known_entities and chart.source not in known_queries:
            raise NovaSyntaxError(
                f"chart '{chart.name}': la source '{chart.source}' (après 'sur') "
                f"ne correspond à aucune entité ni requête déclarée."
            )


def _validate_notifiers(program: NovaProgram) -> None:
    """`api <Entité> { ... notifier: creer, ... }` nécessite un bloc `email
    { ... }` déclaré quelque part dans le fichier : sans lui, il n'y a
    aucune configuration SMTP à utiliser au moment d'envoyer la
    notification. Comme pour `_validate_charts`, on le détecte à la
    compilation (`nova check`/`nova compile`) plutôt que de générer un
    projet dont la notification échouerait silencieusement (ou lèverait une
    NameError à l'import faute de module `emailer` généré)."""
    if any(api.notify_actions for api in program.apis) and program.email is None:
        offending = next(api for api in program.apis if api.notify_actions)
        raise NovaSyntaxError(
            f"api '{offending.entity}': 'notifier:' nécessite un bloc "
            f"'email {{ ... }}' déclaré dans le projet (configuration SMTP)."
        )


def _validate_calendars(program: NovaProgram) -> None:
    """`calendar <Nom> sur <Entite> { ... }` : l'entité doit exister ; le
    champ date (explicite via `champ_date`/`date_field`, ou déduit sinon)
    doit être un champ date/datetime réel de l'entité ; le champ titre
    (`champ_titre`/`title_field`), s'il est précisé, doit exister sur
    l'entité. Comme `_validate_charts`/`_validate_notifiers`, on préfère
    échouer à la compilation plutôt que de générer une page calendrier dont
    le champ date n'existe pas (KeyError/AttributeError silencieux au
    runtime)."""
    known_entities = {e.name: e for e in program.entities}
    for cal in program.calendars:
        entity = known_entities.get(cal.entity)
        if entity is None:
            raise NovaSyntaxError(
                f"calendar '{cal.name}': l'entité '{cal.entity}' (après 'sur') "
                f"n'est pas déclarée."
            )
        date_fields = [f.name for f in entity.fields if f.type in ("date", "datetime")]
        if cal.date_field is None:
            if not date_fields:
                raise NovaSyntaxError(
                    f"calendar '{cal.name}': l'entité '{cal.entity}' n'a aucun "
                    f"champ 'date'/'datetime' — précisez 'champ_date'/'date_field' "
                    f"ou ajoutez un tel champ à l'entité."
                )
            cal.date_field = date_fields[0]
        elif cal.date_field not in date_fields:
            raise NovaSyntaxError(
                f"calendar '{cal.name}': le champ '{cal.date_field}' "
                f"('champ_date'/'date_field') n'est pas un champ date/datetime "
                f"de l'entité '{cal.entity}'."
            )
        if cal.title_field is not None:
            known_fields = {f.name for f in entity.fields}
            if cal.title_field not in known_fields:
                raise NovaSyntaxError(
                    f"calendar '{cal.name}': le champ '{cal.title_field}' "
                    f"('champ_titre'/'title_field') n'existe pas sur l'entité "
                    f"'{cal.entity}'."
                )


def _validate_multilingual_fields(program: NovaProgram) -> None:
    """Le modificateur `multilingue`/`multilingual` (voir `field_decl`) n'est
    accepté que sur un champ `chaine`/`string` ou `texte`/`text` (les autres
    types — nombre, date, fichier... — n'ont pas de sens à traduire), et ne
    peut pas être combiné avec `requis`/`unique`/`motif` sur ce MVP : la
    sémantique de "quelle langue est requise/unique" n'est pas définie —
    plutôt que de deviner, on lève une erreur claire à la compilation (même
    philosophie que les autres `_validate_*` de ce module)."""
    for entity in program.entities:
        for f in entity.fields:
            if not f.multilingual:
                continue
            if f.type not in ("string", "text"):
                raise NovaSyntaxError(
                    f"entité '{entity.name}', champ '{f.name}': le modificateur "
                    f"'multilingue'/'multilingual' n'est valide que sur un champ "
                    f"'chaine'/'string' ou 'texte'/'text' (type actuel : '{f.type}')."
                )
            if f.required or f.unique or f.pattern:
                raise NovaSyntaxError(
                    f"entité '{entity.name}', champ '{f.name}': le modificateur "
                    f"'multilingue'/'multilingual' ne peut pas être combiné avec "
                    f"'requis'/'unique'/'motif' dans ce MVP."
                )


def _validate_translations(program: NovaProgram) -> None:
    """Chaque entrée du bloc `traductions { ... }` doit fournir les 6 langues
    du DSL (`keywords.LANG_CODES`) — pas de traduction manquante à découvrir
    au runtime (page affichant une clé au lieu d'un texte). Chaque `titre
    <cle>` référencé par un `page_stmt` (voir `title_value`/`page_stmt`)
    doit correspondre à une entrée déclarée quelque part dans le fichier —
    même philosophie que `_validate_charts`/`_validate_calendars` : une
    faute de frappe dans la clé doit être détectée à `nova check`/`nova
    compile`, jamais au premier chargement de la page."""
    for key, texts in program.translations.items():
        missing = [lang for lang in kw.LANG_CODES if lang not in texts]
        if missing:
            raise NovaSyntaxError(
                f"traductions '{key}': langue(s) manquante(s) : {', '.join(missing)} "
                f"(les 6 langues {', '.join(kw.LANG_CODES)} sont requises pour chaque clé)."
            )
    for page in program.pages:
        for show in page.shows:
            if show.title_key is not None and show.title_key not in program.translations:
                raise NovaSyntaxError(
                    f"page '{page.name}': titre '{show.title_key}' ne correspond à "
                    f"aucune entrée déclarée dans un bloc 'traductions'/'translations'."
                )


def parse_file(path: str | Path) -> NovaProgram:
    text = Path(path).read_text(encoding="utf-8")
    return parse_source(text)
