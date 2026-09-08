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
