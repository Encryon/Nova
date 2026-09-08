"""Tests du parser NOVA : le français et l'anglais doivent produire le même AST."""

from pathlib import Path

import pytest

from nova_compiler.parser import NovaSyntaxError, parse_file, parse_source

EXAMPLES = Path(__file__).parent.parent / "examples"


def test_english_and_french_blog_are_structurally_equivalent():
    en = parse_file(EXAMPLES / "blog.en.nova")
    fr = parse_file(EXAMPLES / "blog.fr.nova")

    assert len(en.entities) == len(fr.entities) == 3
    assert len(en.apis) == len(fr.apis) == 3
    assert len(en.pages) == len(fr.pages) == 3

    for e_en, e_fr in zip(en.entities, fr.entities):
        assert len(e_en.fields) == len(e_fr.fields)
        assert [f.type for f in e_en.fields] == [f.type for f in e_fr.fields]
        assert [f.required for f in e_en.fields] == [f.required for f in e_fr.fields]

    for a_en, a_fr in zip(en.apis, fr.apis):
        assert sorted(a_en.actions) == sorted(a_fr.actions)

    for p_en, p_fr in zip(en.pages, fr.pages):
        assert [s.mode for s in p_en.shows] == [s.mode for s in p_fr.shows]


def test_mixed_fr_en_file_parses():
    program = parse_file(EXAMPLES / "mixed.nova")
    assert {e.name for e in program.entities} == {"Product", "Commande"}
    assert program.get_entity("Commande").relations[0].kind == "belongs_to"
    assert program.get_entity("Commande").relations[0].target == "Product"


def test_field_modifiers():
    src = """
    entity Item {
      field sku: string required unique
      field qty: int default = 0
    }
    """
    program = parse_source(src)
    item = program.get_entity("Item")
    sku, qty = item.fields
    assert sku.required and sku.unique
    assert qty.default == 0


def test_french_synonyms_for_types_and_actions():
    src = """
    entité Truc {
      champ label: chaîne requis
      champ actif: booléen
      champ montant: décimal
    }
    api Truc {
      liste
      obtenir
      mettre_à_jour
    }
    """
    program = parse_source(src)
    truc = program.get_entity("Truc")
    assert [f.type for f in truc.fields] == ["string", "bool", "float"]
    assert program.apis[0].actions == ["list", "get", "update"]


def test_invalid_syntax_raises_nova_syntax_error():
    with pytest.raises(NovaSyntaxError):
        parse_source("entity {{{ not valid")


def test_pattern_modifier_in_english_and_french():
    src_en = """
    entity Contact {
      field email: string required pattern = "^[^@]+@[^@]+$"
    }
    """
    src_fr = """
    entité Contact {
      champ email: chaine requis motif = "^[^@]+@[^@]+$"
    }
    """
    for src in (src_en, src_fr):
        program = parse_source(src)
        email = program.get_entity("Contact").fields[0]
        assert email.pattern == "^[^@]+@[^@]+$"


def test_field_without_pattern_has_none():
    program = parse_source('entity X { field name: string }')
    assert program.get_entity("X").fields[0].pattern is None


def test_spanish_german_italian_portuguese_type_synonyms():
    """Les 4 langues ajoutées dans cette version (ES/DE/IT/PT) doivent
    normaliser vers les mêmes types canoniques que FR/EN."""
    sources = {
        "es": """
        entidad Cliente {
          campo nombre: cadena requerido
          campo activo: booleano
          campo saldo: flotante
          campo edad: entero
        }
        """,
        "de": """
        entität Kunde {
          feld name: zeichenkette erforderlich
          feld aktiv: boolesch
          feld betrag: gleitkomma
          feld alter: ganzzahl
        }
        """,
        "it": """
        entità Cliente {
          campo nome: stringa richiesto
          campo attivo: booleano
          campo saldo: decimale
          campo eta: intero
        }
        """,
        "pt": """
        entidade Cliente {
          campo nome: cadeia obrigatorio
          campo ativo: booleano
          campo saldo: decimal
          campo idade: inteiro
        }
        """,
    }
    for lang, src in sources.items():
        program = parse_source(src)
        entity = program.entities[0]
        assert [f.type for f in entity.fields] == ["string", "bool", "float", "int"], lang
        assert entity.fields[0].required, lang


def test_auth_block_parses_roles_and_default_role():
    src = """
    auth {
      roles: admin, user, editeur
    }
    """
    program = parse_source(src)
    assert program.auth is not None
    assert program.auth.enabled
    assert program.auth.roles == ["admin", "user", "editeur"]


def test_protect_stmt_sets_protected_role_on_api():
    src = """
    entity Secret {
      field label: string
    }
    api Secret {
      list
      create
      proteger: admin
    }
    """
    program = parse_source(src)
    api = program.apis[0]
    assert sorted(api.actions) == ["create", "list"]
    assert api.protected_role == "admin"


def test_api_without_protect_stmt_is_unprotected():
    program = parse_source("entity X { field n: string }\napi X { list }")
    assert program.apis[0].protected_role is None


def test_query_block_parses_filters_sort_and_limit():
    src = """
    entity Produit {
      field prix: float
    }
    requete ProduitsChers sur Produit {
      filtre: prix > 100
      trier_par: prix desc
      limite: 10
    }
    """
    program = parse_source(src)
    assert len(program.queries) == 1
    q = program.queries[0]
    assert q.name == "ProduitsChers"
    assert q.entity == "Produit"
    assert len(q.filters) == 1
    assert q.filters[0].field == "prix"
    assert q.filters[0].op == ">"
    assert q.filters[0].value == 100
    assert q.order_by == "prix"
    assert q.order_dir == "desc"
    assert q.limit == 10


def test_query_block_defaults_sort_direction_to_asc():
    src = """
    entity Produit {
      field nom: string
    }
    query CheapFirst on Produit {
      sort_by: nom
    }
    """
    program = parse_source(src)
    q = program.queries[0]
    assert q.order_by == "nom"
    assert q.order_dir == "asc"


def test_style_block_parses_props_on_page_show():
    src = """
    entity Produit {
      field nom: string
    }
    page Produits {
      show Produit as table style {
        couleur_fond: "#445566"
        classe: "carte-produit"
      }
    }
    """
    program = parse_source(src)
    show = program.pages[0].shows[0]
    assert show.style["couleur_fond"] == "#445566"
    assert show.style["classe"] == "carte-produit"


def test_page_show_without_style_block_has_empty_style_dict():
    program = parse_source(
        "entity X { field n: string }\npage P { show X as table }"
    )
    assert program.pages[0].shows[0].style == {}


def test_auth_and_query_blocks_recognize_all_six_languages():
    """Régression : `auth_prop`/`query_prop` comparaient le *texte* du
    token (`str(kw_tok) in ("roles", "rôles")`, etc.) plutôt que son type
    Lark (`ROLES_KW`). La grammaire reconnaissait bien `rollen`/`ruoli`/
    `papeis` (DE/IT/PT) comme un mot-clé `ROLES_KW` valide, mais le
    parser les traitait silencieusement comme `default_role` faute de
    correspondre au texte français/anglais codé en dur — sans erreur,
    juste un AST incorrect (`auth.roles` pollué, `filtre`/`trier_par`/
    `limite` de la requête ignorés). Un seul test en français/anglais ne
    pouvait pas détecter ce genre de bug ; il faut vérifier chaque langue."""
    sources = {
        "es": """
        entidad Producto { campo precio: decimal }
        autenticacion { roles: admin, user }
        api Producto { listar proteger: admin }
        consulta CarosProductos en Producto {
          filtro: precio > 100
          ordenar_por: precio descendente
          limite: 5
        }
        """,
        "de": """
        entität Produkt { feld preis: gleitkomma }
        authentifizierung { rollen: admin, user }
        api Produkt { liste schützen: admin }
        query TeureProdukte von Produkt {
          filter: preis > 100
          sortieren_nach: preis absteigend
          limit: 5
        }
        """,
        "it": """
        entità Prodotto { campo prezzo: decimale }
        auth { ruoli: admin, user }
        api Prodotto { elenco proteggere: admin }
        query ProdottiCari su Prodotto {
          filter: prezzo > 100
          ordina_per: prezzo decrescente
          limit: 5
        }
        """,
        "pt": """
        entidade Produto { campo preco: decimal }
        auth { papeis: admin, user }
        api Produto { elenco proteger: admin }
        query ProdutosCaros em Produto {
          filter: preco > 100
          ordenar_por: preco descendente
          limite: 5
        }
        """,
    }
    for lang, src in sources.items():
        program = parse_source(src)
        assert program.auth.roles == ["admin", "user"], lang
        assert program.apis[0].protected_role == "admin", lang
        q = program.queries[0]
        assert q.order_dir == "desc", lang
        assert q.limit == 5, lang
        assert len(q.filters) == 1 and q.filters[0].value == 100, lang


def test_style_and_css_prop_keywords_recognize_all_six_languages():
    sources = {
        "es": 'aplicacion T { nombre: "T" css: "tema.css" }\nentidad P { campo n: cadena }\npage Pg { show P as table estilo { color: "red" } }',
        "de": 'anwendung T { name: "T" css: "thema.css" }\nentität P { feld n: zeichenkette }\npage Pg { show P as table stil { color: "red" } }',
        "it": 'applicazione T { nome: "T" css: "tema.css" }\nentità P { campo n: stringa }\npage Pg { show P as table stile { color: "red" } }',
        "pt": 'aplicacao T { nome: "T" css: "tema.css" }\nentidade P { campo n: cadeia }\npage Pg { show P as table estilo { color: "red" } }',
    }
    for lang, src in sources.items():
        program = parse_source(src)
        assert program.app.props.get("css") == ("tema.css" if lang != "de" else "thema.css"), lang
        assert program.pages[0].shows[0].style == {"color": "red"}, lang


def test_chart_block_on_entity_source_all_types_and_props():
    src = """
    entity Produit {
        field nom: string required
        field prix: float required
    }

    chart RepartitionPrix sur Produit {
        type: barres
        axe_x: nom
        axe_y: prix
        titre: "Prix par produit"
    }
    """
    program = parse_source(src)
    assert len(program.charts) == 1
    chart = program.charts[0]
    assert chart.name == "RepartitionPrix"
    assert chart.source == "Produit"
    assert chart.type == "bar"          # "barres" (FR) -> canonique "bar"
    assert chart.x_field == "nom"
    assert chart.y_field == "prix"
    assert chart.title == "Prix par produit"


def test_chart_block_on_query_source():
    src = """
    entity Produit {
        field nom: string required
        field prix: float required
        field stock: int required
    }

    requete StockFaible sur Produit {
        filtre: stock < 10
        trier_par: stock asc
    }

    chart Alerte sur StockFaible {
        type: line
        axe_x: nom
        axe_y: stock
    }
    """
    program = parse_source(src)
    chart = program.charts[0]
    assert chart.source == "StockFaible"
    assert chart.type == "line"
    assert chart.title is None


def test_chart_type_keyword_recognizes_all_six_languages():
    types = {
        "bar": "bar", "barres": "bar", "barra": "bar", "balken": "bar",
        "line": "line", "ligne": "line", "linea": "line", "linie": "line",
        "pie": "pie", "camembert": "pie", "torta": "pie", "kreis": "pie",
        "area": "area", "aire": "area", "área": "area", "fläche": "area",
    }
    for word, canonical in types.items():
        src = f"""
        entity P {{ field n: string }}
        chart C sur P {{ type: {word} }}
        """
        program = parse_source(src)
        assert program.charts[0].type == canonical, word


def test_chart_keyword_and_prop_aliases_recognize_all_six_languages():
    # Le mot-clé du bloc (`chart`/`graphique`/`grafico`/`gráfico`/`diagramm`)
    # et les alias de propriétés (`axe_x`/`x`/`eje_x`/`x_achse`/`asse_x`/
    # `eixo_x`, etc. -> "x") dans les 6 langues.
    sources = {
        "en": "entity P { field n: string field v: int }\nchart C sur P { x_axis: n y_axis: v }",
        "fr": "entity P { field n: string field v: int }\ngraphique C sur P { axe_x: n axe_y: v }",
        "es": "entity P { field n: string field v: int }\ngrafico C sur P { eje_x: n eje_y: v }",
        "de": "entity P { field n: string field v: int }\ndiagramm C sur P { x_achse: n y_achse: v }",
        "it": "entity P { field n: string field v: int }\ngrafico C sur P { asse_x: n asse_y: v }",
        "pt": "entity P { field n: string field v: int }\ngrafico C sur P { eixo_x: n eixo_y: v }",
    }
    for lang, src in sources.items():
        program = parse_source(src)
        chart = program.charts[0]
        assert chart.x_field == "n", lang
        assert chart.y_field == "v", lang


def test_chart_sur_unknown_source_raises_syntax_error():
    src = """
    entity Produit { field nom: string }
    chart Bad sur Inconnu { type: pie }
    """
    with pytest.raises(NovaSyntaxError):
        parse_source(src)


def test_rich_field_types_file_image_color_recognize_all_six_languages():
    # file/fichier/archivo/datei/(file)/arquivo, image/imagen/bild/immagine/
    # imagem, color/couleur/farbe/colore/cor — voir keywords.TYPES.
    words = {
        "file": {"en": "file", "fr": "fichier", "es": "archivo", "de": "datei", "it": "file", "pt": "arquivo"},
        "image": {"en": "image", "fr": "image", "es": "imagen", "de": "bild", "it": "immagine", "pt": "imagem"},
        "color": {"en": "color", "fr": "couleur", "es": "color", "de": "farbe", "it": "colore", "pt": "cor"},
    }
    for canonical, per_lang in words.items():
        for lang, word in per_lang.items():
            program = parse_source(f"entity P {{ field x: {word} }}")
            assert program.entities[0].fields[0].type == canonical, (canonical, lang, word)


def test_email_block_parses_all_props_and_notify_stmt_on_api():
    src = """
    entity Produit { field nom: string required }
    email {
      host: "smtp.example.com"
      port: 2525
      user: "nova"
      from: "noreply@example.com"
      to: "admin@example.com"
      tls: false
    }
    api Produit {
      create
      update
      delete
      notifier: create, update, delete
    }
    """
    program = parse_source(src)
    assert program.email.host == "smtp.example.com"
    assert program.email.port == 2525
    assert program.email.user == "nova"
    assert program.email.from_addr == "noreply@example.com"
    assert program.email.to_addr == "admin@example.com"
    assert program.email.tls is False
    assert program.apis[0].notify_actions == ["create", "update", "delete"]


def test_email_block_defaults_when_props_omitted():
    program = parse_source("email { }")
    assert program.email.host == "localhost"
    assert program.email.port == 587
    assert program.email.tls is True
    assert program.email.to_addr == ""


def test_email_keyword_and_prop_aliases_recognize_all_six_languages():
    # Mot-clé du bloc (email/courriel/correo/correio) et alias de propriétés
    # (hote/host/servidor, expediteur/from/remitente/absender/mittente/
    # remetente, destinataire/to/destinatario/empfaenger) dans les 6 langues,
    # plus le mot-clé `notifier`/`notify`/`notificar`/`benachrichtigen`/
    # `notificare` sur `api`.
    sources = {
        "fr": 'courriel { hote: "s" expediteur: "a@a" destinataire: "b@b" }\n'
        "entity P { field n: string }\napi P { create notifier: creer }",
        "en": 'email { host: "s" from: "a@a" to: "b@b" }\n'
        "entity P { field n: string }\napi P { create notify: create }",
        "es": 'correo { servidor: "s" remitente: "a@a" destinatario: "b@b" }\n'
        "entity P { field n: string }\napi P { create notificar: crear }",
        "de": 'email { host: "s" absender: "a@a" empfaenger: "b@b" }\n'
        "entity P { field n: string }\napi P { create benachrichtigen: erstellen }",
        "it": 'email { host: "s" mittente: "a@a" destinatario: "b@b" }\n'
        "entity P { field n: string }\napi P { create notificare: creare }",
        "pt": 'correio { host: "s" remetente: "a@a" destinatario: "b@b" }\n'
        "entity P { field n: string }\napi P { create notificar: criar }",
    }
    for lang, src in sources.items():
        program = parse_source(src)
        assert program.email is not None, lang
        assert program.email.from_addr == "a@a", lang
        assert program.email.to_addr == "b@b", lang
        assert program.apis[0].notify_actions == ["create"], lang


def test_notifier_without_email_block_raises_syntax_error():
    src = """
    entity Produit { field nom: string }
    api Produit { create notifier: create }
    """
    with pytest.raises(NovaSyntaxError):
        parse_source(src)


def test_calendar_block_parses_explicit_date_and_title_fields():
    src = """
    entity Event {
        field title: string required
        field starts_at: datetime required
        field location: string
    }
    calendar EventCal sur Event {
      champ_date: starts_at
      champ_titre: title
    }
    """
    program = parse_source(src)
    cal = program.calendars[0]
    assert cal.name == "EventCal"
    assert cal.entity == "Event"
    assert cal.date_field == "starts_at"
    assert cal.title_field == "title"


def test_calendar_block_defaults_date_field_to_first_date_or_datetime_field():
    src = """
    entity Event {
        field title: string required
        field starts_at: datetime required
    }
    calendar EventCal sur Event { }
    """
    program = parse_source(src)
    cal = program.calendars[0]
    assert cal.date_field == "starts_at"
    assert cal.title_field is None


def test_calendar_keyword_and_prop_aliases_recognize_all_six_languages():
    # Mot-clé du bloc (calendar/calendrier/calendario/calendário/kalender)
    # et alias de propriétés (champ_date/date_field/campo_fecha/datumsfeld/
    # campo_data, champ_titre/title_field/campo_titulo/titelfeld/
    # campo_titolo) dans les 6 langues.
    entity_src = "entity Event { field title: string field starts_at: datetime }\n"
    sources = {
        "en": entity_src + "calendar C sur Event { date_field: starts_at title_field: title }",
        "fr": entity_src + "calendrier C sur Event { champ_date: starts_at champ_titre: title }",
        "es": entity_src + "calendario C sur Event { campo_fecha: starts_at campo_titulo: title }",
        "de": entity_src + "kalender C sur Event { datumsfeld: starts_at titelfeld: title }",
        "it": entity_src + "calendario C sur Event { campo_data: starts_at campo_titolo: title }",
        "pt": entity_src + "calendário C sur Event { campo_data: starts_at campo_titulo: title }",
    }
    for lang, src in sources.items():
        program = parse_source(src)
        assert len(program.calendars) == 1, lang
        cal = program.calendars[0]
        assert cal.date_field == "starts_at", lang
        assert cal.title_field == "title", lang


def test_calendar_sur_unknown_entity_raises_syntax_error():
    src = """
    entity Event { field starts_at: date }
    calendar Bad sur Inconnu { }
    """
    with pytest.raises(NovaSyntaxError):
        parse_source(src)


def test_calendar_entity_without_any_date_field_raises_syntax_error():
    src = """
    entity Event { field title: string }
    calendar Bad sur Event { }
    """
    with pytest.raises(NovaSyntaxError):
        parse_source(src)


def test_calendar_explicit_date_field_not_a_date_type_raises_syntax_error():
    src = """
    entity Event { field title: string field starts_at: datetime }
    calendar Bad sur Event { champ_date: title }
    """
    with pytest.raises(NovaSyntaxError):
        parse_source(src)


def test_calendar_explicit_title_field_unknown_raises_syntax_error():
    src = """
    entity Event { field starts_at: datetime }
    calendar Bad sur Event { champ_titre: inconnu }
    """
    with pytest.raises(NovaSyntaxError):
        parse_source(src)


# --------------------------------------------------------- multilingual ---

def test_multilingual_field_modifier_sets_flag_and_leaves_others_unset():
    src = """
    entity Produit {
        field nom: string required
        field titre: string multilingual
        field prix: float
    }
    """
    program = parse_source(src)
    fields = {f.name: f for f in program.entities[0].fields}
    assert fields["titre"].multilingual is True
    assert fields["nom"].multilingual is False
    assert fields["prix"].multilingual is False


def test_multilingual_keyword_recognizes_all_six_languages():
    field_src = {
        "en": "entity P { field titre: string multilingual }",
        "fr": "entité P { champ titre: chaine multilingue }",
        "es": "entidad P { campo titre: cadena multilingüe }",
        "de": "entität P { feld titre: zeichenkette mehrsprachig }",
        "it": "entità P { campo titre: stringa multilingua }",
        "pt": "entidade P { campo titre: cadeia multilíngue }",
    }
    for lang, src in field_src.items():
        program = parse_source(src)
        assert program.entities[0].fields[0].multilingual is True, lang


def test_translations_block_parses_all_six_languages_per_entry():
    src = """
    translations {
        accueil {
            fr: "Bienvenue"
            en: "Welcome"
            es: "Bienvenido"
            de: "Willkommen"
            it: "Benvenuto"
            pt: "Bem-vindo"
        }
    }
    entity P { field n: string }
    """
    program = parse_source(src)
    assert program.translations == {
        "accueil": {
            "fr": "Bienvenue",
            "en": "Welcome",
            "es": "Bienvenido",
            "de": "Willkommen",
            "it": "Benvenuto",
            "pt": "Bem-vindo",
        }
    }


def test_translations_keyword_recognizes_all_six_languages():
    body = '{ cle { fr: "a" en: "b" es: "c" de: "d" it: "e" pt: "f" } }'
    sources = {
        "en": f"translations {body}\nentity P {{ field n: string }}",
        "fr": f"traductions {body}\nentity P {{ field n: string }}",
        "es": f"traducciones {body}\nentity P {{ field n: string }}",
        "de": f"übersetzungen {body}\nentity P {{ field n: string }}",
        "it": f"traduzioni {body}\nentity P {{ field n: string }}",
        "pt": f"traduções {body}\nentity P {{ field n: string }}",
    }
    for lang, src in sources.items():
        program = parse_source(src)
        assert "cle" in program.translations, lang


def test_page_title_literal_string_vs_translation_key():
    src = """
    entity P { field n: string }
    translations {
        titre_page { fr: "a" en: "b" es: "c" de: "d" it: "e" pt: "f" }
    }
    page Un { show P as table title "Texte litteral" }
    page Deux { show P as table title titre_page }
    """
    program = parse_source(src)
    show_un = program.pages[0].shows[0]
    show_deux = program.pages[1].shows[0]
    assert show_un.title == "Texte litteral"
    assert show_un.title_key is None
    assert show_deux.title is None
    assert show_deux.title_key == "titre_page"


def test_multilingual_field_on_non_string_type_raises_syntax_error():
    src = """
    entity Produit { field prix: float multilingual }
    """
    with pytest.raises(NovaSyntaxError):
        parse_source(src)


def test_multilingual_field_combined_with_required_raises_syntax_error():
    src = """
    entity Produit { field titre: string required multilingual }
    """
    with pytest.raises(NovaSyntaxError):
        parse_source(src)


def test_translations_entry_missing_language_raises_syntax_error():
    src = """
    entity P { field n: string }
    translations {
        incomplete { fr: "a" en: "b" es: "c" de: "d" it: "e" }
    }
    """
    with pytest.raises(NovaSyntaxError):
        parse_source(src)


def test_page_title_unknown_translation_key_raises_syntax_error():
    src = """
    entity P { field n: string }
    page Un { show P as table title cle_inconnue }
    """
    with pytest.raises(NovaSyntaxError):
        parse_source(src)
