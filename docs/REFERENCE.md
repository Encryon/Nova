# NOVA — Référence complète des mots-clés / Full keyword reference

Ce document liste **tous** les mots-clés du DSL NOVA dans les **6 langues**
supportées (français, anglais, espagnol, allemand, italien, portugais).
Le [README](../README.md) donne une vue FR/EN plus courte pour démarrer
rapidement ; cette page est la référence exhaustive — générée à partir de
`nova_compiler/keywords.py` et `nova_compiler/grammar/nova.lark`, les deux
seuls fichiers à modifier pour ajouter une langue ou un synonyme.

Une entrée vide (`—`) signifie que ce mot-clé n'a pas de synonyme dédié
dans cette langue : NOVA retombe alors sur l'un des autres mots listés sur
la même ligne (souvent l'anglais ou l'espagnol/portugais, orthographes
identiques dans plusieurs langues).

## Blocs et structure / Blocks and structure

| Bloc | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| Application | `application` | `app` | `aplicacion` / `aplicación` | `anwendung` | `applicazione` | `aplicacao` / `aplicação` |
| Entité / Entity | `entité` / `entite` | `entity` | `entidad` | `entitaet` / `entität` | `entita` / `entità` | `entidade` |
| Champ / Field | `champ` | `field` | `campo` | `feld` | `campo` | `campo` |
| API | `api` | `api` | `api` | `api` | `api` | `api` |
| Page | `page` | `page` | `pagina` / `página` | `seite` | `pagina` | `pagina` / `página` |

## Modificateurs de champ / Field modifiers

| Modificateur | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| Requis / Required | `requis` | `required` | `requerido` / `obligatorio` | `erforderlich` | `richiesto` / `obbligatorio` | `obrigatorio` / `obrigatório` |
| Unique | `unique` | `unique` | `unico` / `único` | `eindeutig` | `unico` | `unico` / `único` |
| Défaut / Default | `defaut` / `défaut` / `par_defaut` | `default` | `predeterminado` / `por_defecto` | `standard` | `predefinito` | `padrao` / `padrão` |
| Regex / Pattern | `motif` / `regex` | `pattern` / `regex` | `patron` / `patrón` | `muster` | `modello` | `formato` |

## Relations

| Relation | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| 1-N | `possede_plusieurs` / `possède_plusieurs` | `has_many` | `tiene_muchos` | `hat_viele` | `ha_molti` | `tem_muitos` |
| N-1 | `appartient_a` / `appartient_à` | `belongs_to` | `pertenece_a` | `gehoert_zu` / `gehört_zu` | `appartiene_a` | `pertence_a` |

## Types de champ / Field types

| Type | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| Texte court / Short text | `chaine` / `chaîne` | `string` | `cadena` | `zeichenkette` | `stringa` | `cadeia` |
| Texte long / Long text | `texte` | `text` | `texto` | — (`text`) | `testo` | `texto` |
| Entier / Integer | `entier` | `int` / `integer` | `entero` | `ganzzahl` | `intero` | `inteiro` |
| Décimal / Float | `decimal` / `décimal` | `float` | `flotante` | `gleitkomma` | `decimale` | — (`decimal`) |
| Booléen / Boolean | `booleen` / `booléen` | `bool` / `boolean` | `booleano` | `boolesch` | `booleano` | `booleano` |
| Date | `date` | `date` | `fecha` | `datum` | `data` | `data` |
| Date + heure / Datetime | `date_heure` | `datetime` | `fecha_hora` | `datum_zeit` | `data_ora` | `data_hora` |
| Fichier / File | `fichier` | `file` | `archivo` | `datei` | — (`file`) | `arquivo` |
| Image | `image` | `image` | `imagen` | `bild` | `immagine` | `imagem` |
| Couleur / Color | `couleur` | `color` | `color` | `farbe` | `colore` | `cor` |

## Actions CRUD

| Action | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| Lister / List | `liste` | `list` | `listar` / `lista` | `auflisten` | `elenco` | `lista` |
| Créer / Create | `creer` / `créer` | `create` | `crear` | `erstellen` | `creare` | `criar` |
| Modifier / Update | `modifier` / `mettre_a_jour` | `update` | `actualizar` | `aktualisieren` | `aggiornare` | `atualizar` |
| Supprimer / Delete | `supprimer` | `delete` | `eliminar` / `borrar` | `loeschen` / `löschen` | `eliminare` | `excluir` |
| Obtenir / Get | `obtenir` / `lire` | `get` | `obtener` | `erhalten` / `holen` | `ottenere` | `obter` |

## Pages et affichage / Pages and display

| Mot-clé | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| Afficher / Show | `afficher` | `show` | `mostrar` | `zeigen` / `anzeigen` | `mostrare` | `exibir` |
| Comme / As | `comme` | `as` | `como` | `als` | `come` | `como` |
| Titre / Title | `titre` | `title` | `titulo` / `título` | `titel` | `titolo` | `titulo` / `título` |
| Mode tableau / Table mode | `table` | `table` | `tabla` | `tabelle` | `tabella` | `tabela` |
| Mode formulaire / Form mode | `formulaire` | `form` | `formulario` | `formular` | `modulo` | `formulario` / `formulário` |
| Mode fiche / Card mode | `carte` | `card` | `tarjeta` | `karte` | `scheda` | `cartao` / `cartão` |

## Style et CSS (bloc `style { ... }`, prop `css:`)

| Mot-clé | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| Bloc style | `style` | `style` / `css` | `estilo` | `stil` | `stile` | `estilo` |
| Prop. feuille externe / External stylesheet prop | `feuille_style` | `css` / `stylesheet` | `hoja_estilo` | `stildatei` | `foglio_stile` | `folha_estilo` |

Voir le README (section "Style et CSS") pour la liste des clés reconnues
à l'intérieur du bloc `style { ... }` (`couleur_fond`/`background`,
`arrondi`/`border_radius`...) — ces clés ne sont pas des mots-clés de la
grammaire, ce sont des alias déclarés dans `keywords.STYLE_ALIASES` et
traduits en propriété CSS ; toute clé absente de cette table est passée
telle quelle.

## Authentification (bloc `auth { ... }`)

| Mot-clé | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| Bloc auth | `authentification` | `auth` / `authentication` | `autenticacion` / `autenticación` | `authentifizierung` | `autenticazione` | `autenticacao` / `autenticação` |
| Rôles / Roles | `rôles` / `roles` | `roles` | `roles` | `rollen` | `ruoli` | `papeis` / `papéis` |
| Rôle par défaut / Default role | `role_par_defaut` / `role_par_défaut` | `default_role` | `rol_por_defecto` | `standardrolle` | `ruolo_predefinito` | `papel_padrao` / `papel_padrão` |
| Protéger (sur `api`) / Protect | `proteger` / `protéger` | `protect` | `proteger` | `schuetzen` / `schützen` | `proteggere` | `proteger` |

## Requêtes déclaratives (bloc `requete`/`query { ... }`)

| Mot-clé | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| Bloc requête / Query block | `requete` / `requête` | `query` | `consulta` | `abfrage` | `interrogazione` | `consulta` |
| Sur (entité) / On (entity) | `sur` | `on` / `from` | `en` | `von` | `su` | `em` |
| Filtre / Filter | `filtre` | `filter` | `filtro` | `filter` | `filtro` | `filtro` |
| Trier par / Sort by | `trier_par` | `sort_by` / `order_by` | `ordenar_por` | `sortieren_nach` | `ordina_per` | `ordenar_por` |
| Croissant / Ascending | `croissant` / `asc` | `asc` | `ascendente` | `aufsteigend` | `crescente` | `ascendente` |
| Décroissant / Descending | `décroissant` / `decroissant` | `desc` | `descendente` | `absteigend` | `decrescente` | `descendente` |
| Limite / Limit | `limite` | `limit` | `límite` | `limit` | `limite` | `limite` |

Comparateurs disponibles (identiques dans toutes les langues, ce sont des
symboles) : `>`, `<`, `>=`, `<=`, `==`, `!=`.

## Graphiques (bloc `chart <Nom> sur <Entité|Requête> { ... }`)

| Mot-clé | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| Bloc chart / Chart block | `graphique` | `chart` | `grafico` | `diagramm` | `grafico` | `gráfico` |
| Sur (source) / On (source) | `sur` | `on` / `from` | `en` | `von` | `su` | `em` |

Contrairement aux blocs `auth`/`query` ci-dessus, les propriétés à
l'intérieur de `chart { ... }` (`type`, `axe_x`/`x`, `axe_y`/`y`,
`titre`/`title`) ne sont **pas** des mots-clés de la grammaire mais des
alias déclarés dans `keywords.CHART_PROP_ALIASES` (même mécanisme que
`STYLE_ALIASES` pour le bloc `style`) :

| Propriété | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| Type de graphique / Chart type | `type` | `type` | `tipo` | `typ` | `tipo` | `tipo` |
| Axe X / X axis | `axe_x` | `x` / `x_axis` | `eje_x` | `x_achse` | `asse_x` | `eixo_x` |
| Axe Y / Y axis | `axe_y` | `y` / `y_axis` | `eje_y` | `y_achse` | `asse_y` | `eixo_y` |
| Titre / Title | `titre` | `title` | `titulo` / `título` | `titel` | `titolo` | `titulo` / `título` |

Valeurs possibles pour `type:` (alias déclarés dans `keywords.CHART_TYPES`) :

| Type | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| Barres / Bar | `barres` / `barre` | `bar` | `barra` / `barras` | `balken` | `barra` | `barra` / `barras` |
| Ligne / Line | `ligne` | `line` | `linea` / `línea` | `linie` | `linea` | `linha` |
| Camembert / Pie | `camembert` | `pie` | `tarta` / `circular` | `kreis` | `torta` / `pizza` | `torta` |
| Aires / Area | `aire` | `area` | `área` | `flaeche` / `fläche` | `area` | `area` |

`sur`/`on` référence soit une **entité** déclarée (données = son API
liste, protection JWT héritée de `api <Entité> { proteger: <rôle> }` si
présent), soit une **requête** (`requete`/`query`) déjà déclarée plus
haut dans le fichier (données déjà filtrées/triées, route toujours
publique). Une référence inconnue lève une erreur à la compilation
(`chart X sur Y` où `Y` n'est ni une entité ni une requête déclarée),
pas une page qui échoue silencieusement au premier chargement.

## Exemple : le même programme en 4 langues / Example: the same program in 4 languages

```
// Espagnol / Spanish
entidad Producto {
  campo nombre: cadena requerido
  campo precio: decimal
}
autenticacion {
  roles: admin, usuario
}
api Producto {
  listar
  crear
  proteger: admin
}
consulta ProductosCaros en Producto {
  filtro: precio > 100
  ordenar_por: precio descendente
  limite: 10
}
page Productos {
  show Producto as table style {
    couleur_fond: "#445566"
  }
}
```

```
// Allemand / German
entität Produkt {
  feld name: zeichenkette erforderlich
  feld preis: gleitkomma
}
authentifizierung {
  rollen: admin, benutzer
}
api Produkt {
  liste
  erstellen
  schützen: admin
}
query TeureProdukte von Produkt {
  filter: preis > 100
  sortieren_nach: preis absteigend
  limit: 10
}
```

```
// Italien / Italian
entità Prodotto {
  campo nome: stringa richiesto
  campo prezzo: decimale
}
auth {
  ruoli: admin, utente
}
api Prodotto {
  elenco
  creare
  proteggere: admin
}
query ProdottiCari su Prodotto {
  filter: prezzo > 100
  ordina_per: prezzo decrescente
  limit: 10
}
```

```
// Portugais / Portuguese
entidade Produto {
  campo nome: cadeia obrigatorio
  campo preco: decimal
}
auth {
  papeis: admin, usuario
}
api Produto {
  elenco
  criar
  proteger: admin
}
query ProdutosCaros em Produto {
  filter: preco > 100
  ordenar_por: preco descendente
  limite: 10
}
```

Ces 4 exemples, plus un cinquième mélangeant volontairement plusieurs
langues dans le même fichier, sont couverts par
`tests/test_parser.py::test_auth_and_query_blocks_recognize_all_six_languages`
et `test_style_and_css_prop_keywords_recognize_all_six_languages` — ils
sont exécutés à chaque `pytest tests/ -v`, pas seulement documentés ici.

Le bloc `chart` (mot-clé, types, alias de propriétés dans les 6 langues)
est couvert par `test_chart_type_keyword_recognizes_all_six_languages`
et `test_chart_keyword_and_prop_aliases_recognize_all_six_languages`
dans le même fichier, ainsi que par un test qui **importe réellement**
le frontend Reflex généré et construit l'arbre de composants de chaque
page de graphique (`test_chart_frontend_module_actually_imports_and_builds_all_pages`
dans `tests/test_codegen.py`).

---

[⬅ Retour au README / Back to README](../README.md)
