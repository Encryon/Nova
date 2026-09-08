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
| Multilingue / Multilingual | `multilingue` | `multilingual` | `multilingüe` | `mehrsprachig` | `multilingua` | `multilíngue` |

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

## Notifications email (bloc `email { ... }` + `notifier:` sur `api`)

| Mot-clé | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| Bloc email / Email block | `courriel` | `email` | `correo` | `email` | `email` | `correio` |
| Notifier (sur `api`) / Notify (on `api`) | `notifier` | `notify` | `notificar` | `benachrichtigen` | `notificare` | `notificar` |

Comme pour `chart` ci-dessus, les propriétés à l'intérieur de
`email { ... }` sont des alias déclarés dans `keywords.EMAIL_PROP_ALIASES`,
pas des mots-clés de grammaire dédiés :

| Propriété | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| Serveur / Host | `hote` / `serveur` | `host` | `servidor` / `host` | `host` | `host` | `host` |
| Port | `port` | `port` | `puerto` / `port` | `port` | `porta` / `port` | `port` |
| Utilisateur / User | `utilisateur` | `user` | `usuario` | `benutzer` / `user` | `utente` / `user` | `user` |
| Expéditeur / From | `expediteur` / `expéditeur` | `from` | `remitente` | `absender` | `mittente` | `remetente` |
| Destinataire / To | `destinataire` | `to` | `destinatario` | `empfaenger` / `empfänger` | `destinatario` | `destinatario` |
| TLS | `tls` / `ssl` | `tls` / `ssl` | `tls` / `ssl` | `tls` / `ssl` | `tls` / `ssl` | `tls` / `ssl` |

`notifier:`/`notify:` accepte une liste d'actions séparées par des
virgules, parmi les mêmes mots-clés que le bloc `api` (`creer`/`create`,
`modifier`/`update`, `supprimer`/`delete` — pas `liste`/`list` ni
`obtenir`/`get`, notifier sur une lecture n'ayant pas de sens) :

```
api Produit {
  creer
  supprimer
  notifier: creer, supprimer
}
```

**Volontairement absent de ce bloc : le mot de passe SMTP.** Aucune
propriété ne le porte — il n'existe aucun mot-clé pour lui dans aucune
langue. Il est fourni exclusivement au runtime via la variable
d'environnement `NOVA_SMTP_PASSWORD` (voir README, section
"Notifications par email"). `notifier:` sans bloc `email { ... }`
déclaré dans le même fichier lève une erreur à la compilation.

## Calendrier (bloc `calendar <Nom> sur <Entité> { ... }`)

| Mot-clé | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| Bloc calendar / Calendar block | `calendrier` | `calendar` | `calendario` | `kalender` | `calendario` | `calendário` |
| Sur (source) / On (source) | `sur` | `on` / `from` | `en` | `von` | `su` | `em` |

Comme pour `chart`/`email` ci-dessus, les propriétés à l'intérieur de
`calendar { ... }` (`champ_date`/`date_field`, `champ_titre`/
`title_field`) sont des alias déclarés dans
`keywords.CALENDAR_PROP_ALIASES`, pas des mots-clés de grammaire
dédiés :

| Propriété | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| Champ date / Date field | `champ_date` | `date_field` | `campo_fecha` | `datumsfeld` | `campo_data` | `campo_data` |
| Champ titre / Title field | `champ_titre` | `title_field` | `campo_titulo` | `titelfeld` | `campo_titolo` | `campo_titulo` |

`sur`/`on` référence toujours une **entité** déclarée (données = son
API liste, protection JWT héritée de `api <Entité> { proteger: <rôle>
}` si présent, comme pour `chart`) :

```
calendrier Ajouts sur Produit {
  champ_date: date_ajout
  champ_titre: nom
}
```

- `champ_date`/`date_field` : doit être un champ `date`/`date_heure`
  de l'entité — s'il est omis, résolu automatiquement au premier champ
  `date`/`date_heure` déclaré sur l'entité ; une erreur de compilation
  est levée si l'entité n'en a aucun, ou si la valeur fournie
  explicitement n'est pas un champ `date`/`date_heure` de l'entité.
- `champ_titre`/`title_field` : optionnel, doit exister sur l'entité
  s'il est fourni ; sans lui, un simple marqueur « • » signale un jour
  ayant des enregistrements.
- Une référence `sur` inconnue lève également une erreur à la
  compilation (`calendar X sur Y` où `Y` n'est pas une entité
  déclarée), pas une page qui échoue silencieusement au premier
  chargement.
- Génère une page Reflex dédiée (route `/calendriers/<nom>`) avec une
  grille mensuelle calculée côté serveur via la seule bibliothèque
  standard Python (`calendar`, `datetime`) — aucune dépendance JS
  supplémentaire, vue lecture seule dans ce MVP.

## Contenu multilingue (bloc `traductions { ... }` + champ `multilingue`)

| Mot-clé | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| Bloc traductions / Translations block | `traductions` | `translations` | `traducciones` | `übersetzungen` | `traduzioni` | `traduções` |
| Modificateur multilingue / Multilingual modifier | `multilingue` | `multilingual` | `multilingüe` | `mehrsprachig` | `multilingua` | `multilíngue` |

Les 6 codes de langue utilisés à la fois comme clés à l'intérieur d'un
bloc `traductions { <cle> { <code>: "<texte>" ... } }` et comme suffixes
des colonnes générées pour un champ `multilingue` sont toujours
`fr`/`en`/`es`/`de`/`it`/`pt` (`keywords.LANG_CODES`) — non
traduits/localisés eux-mêmes, contrairement aux autres mots-clés de ce
document :

```
traductions {
  titre_catalogue {
    fr: "Catalogue"
    en: "Catalog"
    es: "Catálogo"
    de: "Katalog"
    it: "Catalogo"
    pt: "Catálogo"
  }
}

entité Produit {
  champ nom: chaine requis
  champ description: texte multilingue
}

page Produits {
  afficher Produit comme table titre titre_catalogue
}
```

- Chaque entrée du bloc `traductions` doit fournir les 6 langues — une
  langue manquante lève une erreur à la compilation.
- `titre <cle>` (NAME nu, sans guillemets) référence une entrée du bloc
  `traductions` ; `titre "Texte"` (STRING) reste un texte littéral
  affiché tel quel quelle que soit la langue — les deux formes sont
  mutuellement exclusives sur un même `show`. Une clé `titre <cle>`
  inconnue lève une erreur à la compilation.
- Le modificateur `multilingue`/`multilingual` n'est valide que sur un
  champ `chaine`/`string` ou `texte`/`text`, et ne peut pas être combiné
  avec `requis`/`unique`/`motif` dans ce MVP.
- Génère une colonne par langue en base (`<champ>_fr` ...
  `<champ>_pt`, toutes optionnelles), un état Reflex `LangState` partagé
  (langue courante persistée en cookie navigateur), un sélecteur de
  langue dans la barre de navigation, et une fonction `t_<cle>()` par
  entrée de `traductions` — toutes deux réactives (`rx.match`), le texte/
  la valeur affichée change immédiatement au changement de langue, sans
  rechargement de page.

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
