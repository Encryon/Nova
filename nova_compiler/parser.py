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
    QueryFilterGroup,
    Relation,
    Validation,
    ValidationRule,
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
        return ("prop", (canonical, value))

    def languages_prop(self, _kw_tok, *lang_toks):
        # `langues: fr, en` (voir grammar/nova.lark) : liste de codes de
        # langue, validée par parser._validate_app_languages (existence
        # dans kw.LANG_CODES) plutôt qu'ici — cohérent avec le reste du
        # fichier (les erreurs sémantiques sont des `_validate_*` séparés,
        # jamais dans le transformer lui-même).
        return ("languages", [str(t) for t in lang_toks])

    def app_member(self, member):
        return member

    def app_decl(self, _kw_tok, name_tok, *members):
        app = App(name=str(name_tok))
        for kind, val in members:
            if kind == "languages":
                app.languages = val
            else:
                key, value = val
                app.props[key] = value
        return app

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

    def notify_recipient_stmt(self, _kw_tok, field_tok):
        return ("notify_recipient", str(field_tok))

    def notify_attachment_stmt(self, _kw_tok, field_tok):
        return ("notify_attachment", str(field_tok))

    def api_member(self, member):
        return member

    def api_decl(self, _kw_tok, name_tok, *members):
        api = Api(entity=str(name_tok))
        for m in members:
            if isinstance(m, tuple) and m[0] == "protect":
                api.protected_role = m[1]
            elif isinstance(m, tuple) and m[0] == "notify":
                api.notify_actions = m[1]
            elif isinstance(m, tuple) and m[0] == "notify_recipient":
                api.notify_recipient_field = m[1]
            elif isinstance(m, tuple) and m[0] == "notify_attachment":
                api.notify_attachment_field = m[1]
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
    def or_filter(self, kw_tok, field_tok, comparator_tok, val):
        # Même corps que la branche FILTRE_KW de `query_prop` ci-dessous,
        # mais dans le non-terminal dédié `or_filter` (voir grammar/nova.lark
        # sur `query_decl`) : un `filtre:` à l'intérieur d'un bloc `ou: { }`.
        return QueryFilter(field=str(field_tok), op=str(comparator_tok), value=val)

    def query_prop(self, kw_tok, *rest):
        # Même principe que `auth_prop` ci-dessus : comparer `kw_tok.type`
        # (FILTRE_KW / OU_KW / TRIER_KW / LIMITE_KW) et non le texte du
        # token, qui varie selon la langue source (`filtro`, `ordina_per`,
        # `límite`, `oder`...).
        if kw_tok.type == "FILTRE_KW":
            field_tok, comparator_tok, val = rest
            return ("filter", QueryFilter(field=str(field_tok), op=str(comparator_tok), value=val))
        if kw_tok.type == "OU_KW":
            # `rest` est la liste des QueryFilter déjà construits par
            # `or_filter` (un ou plusieurs, "+" dans la grammaire).
            return ("or_group", list(rest))
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
            elif key == "or_group":
                q.filter_groups.append(QueryFilterGroup(filters=val))
            elif key == "order":
                q.order_by, q.order_dir = val
            elif key == "limit":
                q.limit = val
        return q

    # ---- chart -----------------------------------------------------------
    def chart_value(self, *toks):
        # Non-terminal dédié (STRING | NAME ("," NAME)*) plutôt que le
        # `value` générique (voir le commentaire dans grammar/nova.lark
        # juste au-dessus de `chart_prop` : réutiliser `value` ici cassait
        # le parsing ailleurs dans la grammaire à cause d'un conflit LALR).
        # Un seul token (cas usuel : `type`, `axe_x`, `titre`, ou `axe_y`
        # à une seule série) -> chaîne. Plusieurs NAME séparés par des
        # virgules (`axe_y: ventes, couts, marge`, multi-séries) -> liste.
        if len(toks) == 1:
            text = str(toks[0])
            return kw.strip_quotes(text) if text.startswith('"') else text
        return [str(t) for t in toks]

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
                if isinstance(val, list):
                    chart.y_fields = [str(v) for v in val]
                    chart.y_field = chart.y_fields[0] if chart.y_fields else None
                else:
                    chart.y_field = str(val)
                    chart.y_fields = [str(val)]
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

    # ---- validation ----------------------------------------------------------
    def validation_rule(self, _regle_tok, field_a_tok, comparator_tok, field_b_tok, _message_tok, message_str):
        return ValidationRule(
            field_a=str(field_a_tok),
            op=str(comparator_tok),
            field_b=str(field_b_tok),
            message=kw.strip_quotes(str(message_str)),
        )

    def validation_decl(self, _kw_tok, name_tok, _sur_tok, entity_tok, *rules):
        return Validation(name=str(name_tok), entity=str(entity_tok), rules=list(rules))

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
            elif isinstance(s, Validation):
                program.validations.append(s)
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
    _validate_app_languages(program)
    _validate_app_database(program)
    _validate_translations(program)
    _validate_relations(program)
    _validate_validations(program)
    _validate_mongo_unsupported_features(program)
    return program


def _validate_charts(program: NovaProgram) -> None:
    """`chart <Nom> sur <X>` : X doit être une entité ou une requête déjà
    déclarée. Contrairement à `query_decl` (pas de vérification équivalente
    aujourd'hui), on valide ici explicitement : une faute de frappe dans
    `sur` ne doit pas produire un projet généré qui échoue silencieusement
    au runtime — leçon tirée du bug auth_prop/query_prop plus haut.

    Valide aussi les séries multiples (`axe_y: a, b, c`) : seuls les types
    bar/line/area (kw.CHART_MULTI_SERIES_TYPES) ont un rendu multi-séries
    simple dans rx.recharts — pie (un seul anneau) et radar/scatter (un seul
    jeu de points par rapport à axe_x) n'en ont pas, donc plusieurs champs
    sur `axe_y` pour ces types-là est une erreur de compilation plutôt qu'un
    projet généré qui ignorerait silencieusement les séries en trop."""
    known_entities = {e.name for e in program.entities}
    known_queries = {q.name for q in program.queries}
    for chart in program.charts:
        if chart.source not in known_entities and chart.source not in known_queries:
            raise NovaSyntaxError(
                f"chart '{chart.name}': la source '{chart.source}' (après 'sur') "
                f"ne correspond à aucune entité ni requête déclarée."
            )
        if len(chart.y_fields) > 1 and chart.type not in kw.CHART_MULTI_SERIES_TYPES:
            raise NovaSyntaxError(
                f"chart '{chart.name}': plusieurs séries sur 'axe_y' "
                f"({', '.join(chart.y_fields)}) ne sont supportées que pour "
                f"les types {sorted(kw.CHART_MULTI_SERIES_TYPES)} — "
                f"le type '{chart.type}' n'accepte qu'un seul champ."
            )


def _validate_notifiers(program: NovaProgram) -> None:
    """`api <Entité> { ... notifier: creer, ... }` nécessite un bloc `email
    { ... }` déclaré quelque part dans le fichier : sans lui, il n'y a
    aucune configuration SMTP à utiliser au moment d'envoyer la
    notification. Comme pour `_validate_charts`, on le détecte à la
    compilation (`nova check`/`nova compile`) plutôt que de générer un
    projet dont la notification échouerait silencieusement (ou lèverait une
    NameError à l'import faute de module `emailer` généré).

    Valide aussi `destinataire:`/`piece_jointe:` (voir grammar/nova.lark sur
    `notify_recipient_stmt`/`notify_attachment_stmt`) : le champ référencé
    doit exister sur l'entité de cette `api`, et `piece_jointe:` doit
    pointer un champ `file`/`image` (une pièce jointe n'a de sens que pour
    un champ qui contient effectivement un fichier stocké)."""
    if any(api.notify_actions for api in program.apis) and program.email is None:
        offending = next(api for api in program.apis if api.notify_actions)
        raise NovaSyntaxError(
            f"api '{offending.entity}': 'notifier:' nécessite un bloc "
            f"'email {{ ... }}' déclaré dans le projet (configuration SMTP)."
        )
    known_entities = {e.name: e for e in program.entities}
    for api in program.apis:
        entity = known_entities.get(api.entity)
        if api.notify_recipient_field is not None:
            field_obj = entity and next((f for f in entity.fields if f.name == api.notify_recipient_field), None)
            if field_obj is None:
                raise NovaSyntaxError(
                    f"api '{api.entity}': 'destinataire: {api.notify_recipient_field}' "
                    f"ne correspond à aucun champ de l'entité '{api.entity}'."
                )
        if api.notify_attachment_field is not None:
            field_obj = entity and next((f for f in entity.fields if f.name == api.notify_attachment_field), None)
            if field_obj is None:
                raise NovaSyntaxError(
                    f"api '{api.entity}': 'piece_jointe: {api.notify_attachment_field}' "
                    f"ne correspond à aucun champ de l'entité '{api.entity}'."
                )
            if field_obj.type not in ("file", "image"):
                raise NovaSyntaxError(
                    f"api '{api.entity}': 'piece_jointe: {api.notify_attachment_field}' "
                    f"doit référencer un champ 'file'/'image' (type actuel : '{field_obj.type}')."
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


def _validate_app_languages(program: NovaProgram) -> None:
    """`application { langues: fr, en }` : chaque code doit être l'une des 6
    langues du DSL (`keywords.LANG_CODES`) — une faute de frappe ('fre' au
    lieu de 'fr') ne doit jamais silencieusement désactiver TOUTES les
    langues actives (une liste vide serait interprétée comme "pas de
    restriction", voir `NovaProgram.active_languages` — donc une entrée
    invalide DOIT être rejetée, jamais simplement ignorée). Si `lang:`
    (langue par défaut de l'UI, une seule) est aussi déclaré, elle doit
    figurer dans `langues:` — une langue par défaut absente des langues
    actives ne pourrait jamais s'afficher."""
    if program.app is None or not program.app.languages:
        return
    unknown = [code for code in program.app.languages if code not in kw.LANG_CODES]
    if unknown:
        raise NovaSyntaxError(
            f"application '{program.app.name}': langue(s) inconnue(s) dans 'langues:' : "
            f"{', '.join(unknown)} (langues valides : {', '.join(kw.LANG_CODES)})."
        )
    default_lang = program.app.props.get("lang")
    if default_lang is not None and default_lang not in program.app.languages:
        raise NovaSyntaxError(
            f"application '{program.app.name}': la langue par défaut ('lang: {default_lang}') "
            f"doit figurer dans 'langues: {', '.join(program.app.languages)}'."
        )


def _validate_app_database(program: NovaProgram) -> None:
    """`application { database: postgresql }` (alias `base_donnees`/
    `base_datos`/`datenbank`/`banco_dados`, tâche #28) : la valeur doit être
    l'un des moteurs supportés (`keywords.DATABASE_ENGINES`) — une faute de
    frappe ne doit jamais se traduire par un projet généré qui se rabat
    silencieusement sur SQLite (le moteur par défaut) sans que l'auteur du
    fichier .nova s'en aperçoive. La valeur canonique (ex. 'postgres' ->
    'postgresql') est réécrite dans `program.app.props['database']` pour
    que tout le codegen en aval lise directement une valeur normalisée via
    `NovaProgram.database_engine()` — jamais la chaîne brute saisie par
    l'auteur."""
    if program.app is None or "database" not in program.app.props:
        return
    raw = str(program.app.props["database"]).lower()
    canonical = kw.DATABASE_ENGINES.get(raw)
    if canonical is None:
        valid = ", ".join(sorted(set(kw.DATABASE_ENGINES.values())))
        raise NovaSyntaxError(
            f"application '{program.app.name}': moteur de base de données inconnu "
            f"('database: {program.app.props['database']}') — valeurs valides : {valid}."
        )
    program.app.props["database"] = canonical


def _validate_mongo_unsupported_features(program: NovaProgram) -> None:
    """`application { database: mongodb }` (tâche #29, voir
    codegen/api_mongo.py) : le backend NoSQL généré (Beanie/Motor) ne
    couvre, dans ce MVP, ni les requêtes déclaratives (`requete`/`query` —
    filtres/tris/jointures construits directement en SQLAlchemy côté SQL),
    ni les blocs `calendar`/`calendrier` (idem), ni les relations
    `has_many`/`possede_plusieurs` matérialisées (résumé texte construit via
    une requête SQL, voir `api_fastapi._has_many_relation_info`) — plutôt
    que générer silencieusement un projet dont ces blocs seraient ignorés
    ou casseraient à l'exécution, une erreur de compilation explicite est
    levée ici. `chart` (sur une entité), `validation`, `email`/`notifier:`,
    `auth`, les champs `fichier`/`image`/`multilingue`, `belongs_to` et
    `application { langues: ... }` restent supportés (voir la docstring de
    codegen/api_mongo.py pour le détail)."""
    if program.database_engine() != "mongodb":
        return
    problems = []
    if program.queries:
        problems.append("le bloc 'requete'/'query'")
    if program.calendars:
        problems.append("le bloc 'calendar'/'calendrier'")
    if any(rel.kind == "has_many" for e in program.entities for rel in e.relations):
        problems.append("les relations 'has_many'/'possede_plusieurs' matérialisées")
    if problems:
        app_name = program.app.name if program.app else "?"
        raise NovaSyntaxError(
            f"application '{app_name}': backend NoSQL ('database: mongodb') incompatible "
            f"avec : {', '.join(problems)} dans ce MVP (voir la documentation des limites connues)."
        )


def _validate_translations(program: NovaProgram) -> None:
    """Chaque entrée du bloc `traductions { ... }` doit fournir toutes les
    langues ACTIVES du projet (`NovaProgram.active_languages` : les 6
    langues du DSL par défaut, ou le sous-ensemble choisi via `application {
    langues: ... }`) — pas de traduction manquante à découvrir au runtime
    (page affichant une clé au lieu d'un texte). Chaque `titre <cle>`
    référencé par un `page_stmt` (voir `title_value`/`page_stmt`) doit
    correspondre à une entrée déclarée quelque part dans le fichier — même
    philosophie que `_validate_charts`/`_validate_calendars` : une faute de
    frappe dans la clé doit être détectée à `nova check`/`nova compile`,
    jamais au premier chargement de la page."""
    active = program.active_languages()
    for key, texts in program.translations.items():
        missing = [lang for lang in active if lang not in texts]
        if missing:
            raise NovaSyntaxError(
                f"traductions '{key}': langue(s) manquante(s) : {', '.join(missing)} "
                f"(les langues actives {', '.join(active)} sont requises pour chaque clé)."
            )
    for page in program.pages:
        for show in page.shows:
            if show.title_key is not None and show.title_key not in program.translations:
                raise NovaSyntaxError(
                    f"page '{page.name}': titre '{show.title_key}' ne correspond à "
                    f"aucune entrée déclarée dans un bloc 'traductions'/'translations'."
                )


def _validate_relations(program: NovaProgram) -> None:
    """`entity <Parent> { has_many: <Enfant> }` : `<Enfant>` doit être une
    entité déclarée, ET cette entité doit porter en retour un `belongs_to:
    <Parent>` — sans lui, aucune colonne de clé étrangère n'existe côté
    enfant (voir `_generate_models` : seul `belongs_to` crée une colonne
    `<parent>_id`) et le compilateur n'aurait aucun moyen de retrouver les
    enregistrements liés pour les matérialiser côté UI (voir
    `_generate_router`/`ui_reflex._generate_show_state_and_inner`). Même
    philosophie que les autres `_validate_*` : une relation mal déclarée
    doit être rejetée à la compilation, jamais silencieusement ignorée."""
    known_entities = {e.name: e for e in program.entities}
    for entity in program.entities:
        for rel in entity.relations:
            if rel.kind != "has_many":
                continue
            child = known_entities.get(rel.target)
            if child is None:
                raise NovaSyntaxError(
                    f"entity '{entity.name}': 'has_many: {rel.target}' ne correspond "
                    f"à aucune entité déclarée."
                )
            has_reciprocal = any(
                r.kind == "belongs_to" and r.target == entity.name for r in child.relations
            )
            if not has_reciprocal:
                raise NovaSyntaxError(
                    f"entity '{entity.name}': 'has_many: {rel.target}' nécessite que "
                    f"l'entité '{rel.target}' déclare en retour 'belongs_to: {entity.name}' "
                    f"(sinon aucune clé étrangère ne permet de retrouver les enregistrements liés)."
                )


_ORDERABLE_FIELD_TYPES = {"int", "float", "date", "datetime"}


def _validate_validations(program: NovaProgram) -> None:
    """`validation <Nom> sur <Entite> { regle: <champA> <op> <champB>
    message: "..." }` : l'entité doit exister, `<champA>`/`<champB>`
    doivent être deux champs simples (ni référence, ni multilingue — un
    champ multilingue n'a pas de valeur unique à comparer) déclarés sur
    cette entité, et un opérateur d'ordre (`>`/`<`/`>=`/`<=`) ne peut
    comparer que des champs dont le type l'autorise (`_ORDERABLE_FIELD_
    TYPES` : int/float/date/date_heure — comparer deux chaînes avec `>`
    n'a normalement aucun sens métier). Même philosophie que les autres
    `_validate_*` : une règle mal déclarée doit être rejetée à la
    compilation plutôt que de lever une TypeError silencieuse au runtime
    (voir codegen/api_fastapi.py::_validation_check_lines)."""
    known_entities = {e.name: e for e in program.entities}
    for validation in program.validations:
        entity = known_entities.get(validation.entity)
        if entity is None:
            raise NovaSyntaxError(
                f"validation '{validation.name}': l'entité '{validation.entity}' "
                f"(après 'sur') ne correspond à aucune entité déclarée."
            )
        fields_by_name = {f.name: f for f in entity.fields}
        for rule in validation.rules:
            for champ in (rule.field_a, rule.field_b):
                f = fields_by_name.get(champ)
                if f is None:
                    raise NovaSyntaxError(
                        f"validation '{validation.name}': le champ '{champ}' ne "
                        f"correspond à aucun champ de l'entité '{validation.entity}'."
                    )
                if f.is_reference or f.multilingual:
                    raise NovaSyntaxError(
                        f"validation '{validation.name}': le champ '{champ}' "
                        f"(référence ou multilingue) ne peut pas être comparé "
                        f"dans une règle de validation."
                    )
            if rule.op in (">", "<", ">=", "<="):
                type_a = fields_by_name[rule.field_a].type
                type_b = fields_by_name[rule.field_b].type
                if type_a not in _ORDERABLE_FIELD_TYPES or type_b not in _ORDERABLE_FIELD_TYPES:
                    raise NovaSyntaxError(
                        f"validation '{validation.name}': l'opérateur '{rule.op}' "
                        f"nécessite des champs numériques ou date/date_heure "
                        f"('{rule.field_a}': {type_a}, '{rule.field_b}': {type_b})."
                    )


def parse_file(path: str | Path) -> NovaProgram:
    text = Path(path).read_text(encoding="utf-8")
    return parse_source(text)
