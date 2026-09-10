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
| Jointure / Join | `jointure` | `join` | `union` | `verknüpfung` | `unione` | `junção` |

Comparateurs disponibles (identiques dans toutes les langues, ce sont des
symboles) : `>`, `<`, `>=`, `<=`, `==`, `!=`.

`jointure: <Entité> sur <local> = <distant>` relie explicitement une autre
entité à la requête (indépendamment des relations `appartient_a`/
`possede_plusieurs` éventuellement déjà déclarées) : `<local>`/`<distant>`
sont chacun un champ, éventuellement qualifié `<Entité>.<champ>` (non
qualifié = entité principale de la requête). Les `filtre:`/`trier_par:`
suivants peuvent alors référencer un champ qualifié de l'entité jointe
(`filtre: <Entité>.<champ> ...`) — voir la section "Requêtes déclaratives"
du README pour un exemple complet et la forme de la réponse (l'entité
jointe apparaît sous une clé nommée d'après elle dans chaque enregistrement).

## Validation croisée (bloc `validation <Nom> sur <Entité> { ... }`)

| Mot-clé | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| Bloc validation | `validation` | `validation` | `validación` | `validierung` | `convalida` / `validazione` | `validação` |
| Règle / Rule | `regle` / `règle` | `rule` | `regla` | `regel` | `regola` | `regra` |
| Message | `message` | `message` | `mensaje` | `nachricht` | `messaggio` | `mensagem` |

Fonctions disponibles dans une expression `regle:` (mêmes noms dans les 6
langues — sauf `round`/`abs`, qui ont des alias) :

| Fonction | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| min / max | `min` / `max` | `min` / `max` | `min` / `max` | `min` / `max` | `min` / `max` | `min` / `max` |
| Arrondi / Round | `arrondi` / `arrondir` | `round` | `redondear` | `runden` | `arrotonda` / `arrotondare` | `arredondar` |
| Valeur absolue / Abs | `abs` / `valeur_absolue` | `abs` | `abs` / `valor_absoluto` | `abs` / `betrag` | `abs` | `abs` / `valor_absoluto` |

`regle: <expression> <comparateur> <expression> message: "..."` — chaque
`<expression>` est un champ, une constante, une combinaison `+`/`-`, ou un
appel de fonction (`min`/`max` : 2+ arguments ; `round` : 1 ou 2 ; `abs` :
1) — voir la section "Validation croisée entre champs" du README pour un
exemple complet et les règles de validation (champs numériques requis
sous une fonction/`+`/`-`, date/date_heure acceptée seulement pour un
champ nu seul de chaque côté d'un opérateur d'ordre).

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
| Agrégation / Aggregation (tâche #35) | `agregation` / `agrégation` | `aggregation` | `agregacion` / `agregación` | `aggregierung` | `aggregazione` | `agregacao` / `agregação` |

Valeurs possibles pour `type:` (alias déclarés dans `keywords.CHART_TYPES`) :

| Type | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| Barres / Bar | `barres` / `barre` | `bar` | `barra` / `barras` | `balken` | `barra` | `barra` / `barras` |
| Ligne / Line | `ligne` | `line` | `linea` / `línea` | `linie` | `linea` | `linha` |
| Camembert / Pie | `camembert` | `pie` | `tarta` / `circular` | `kreis` | `torta` / `pizza` | `torta` |
| Aires / Area | `aire` | `area` | `área` | `flaeche` / `fläche` | `area` | `area` |
| Radar | `radar` / `araignée` | `radar` | `radial` | `radar` | `radar` | `radar` |
| Nuage de points / Scatter | `nuage` / `dispersion` | `scatter` | `dispersion` | `streudiagramm` / `punktdiagramm` | `dispersion` | `dispersao` / `dispersão` |
| Anneau / Donut (tâche #35) | `anneau` / `beignet` | `donut` | `rosquilla` / `dona` | `donut` | `ciambella` | `rosca` |
| Entonnoir / Funnel (tâche #35) | `entonnoir` | `funnel` | `embudo` | `trichter` | `imbuto` | `funil` |

`sur`/`on` référence soit une **entité** déclarée (données = son API
liste, protection JWT héritée de `api <Entité> { proteger: <rôle> }` si
présent), soit une **requête** (`requete`/`query`) déjà déclarée plus
haut dans le fichier (données déjà filtrées/triées, route toujours
publique). Une référence inconnue lève une erreur à la compilation
(`chart X sur Y` où `Y` n'est ni une entité ni une requête déclarée),
pas une page qui échoue silencieusement au premier chargement.

`axe_y` accepte plusieurs champs séparés par des virgules pour un
graphique multi-séries (`axe_y: ventes, couts`), uniquement sur les
types qui s'y prêtent (`kw.CHART_MULTI_SERIES_TYPES` = `bar`/`line`/
`area`) — rejeté à la compilation sur `pie`/`radar`/`scatter`/`donut`/
`funnel`.

**Agrégation** (`agregation`/`aggregation`, tâche #35) : regroupe les
lignes par `axe_x` puis agrège `axe_y` avec une fonction déclarée dans
`keywords.CHART_AGGREGATIONS` :

| Fonction | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| Compte / Count | `compte` / `nombre` | `count` | `cantidad` | `anzahl` | `conteggio` | `contagem` |
| Somme / Sum | `somme` | `sum` | `suma` | `summe` | `somme` | `soma` |
| Moyenne / Average | `moyenne` | `avg` / `average` | `promedio` / `media` | `durchschnitt` | `media` | `media` |
| Min | `min` / `minimum` | `min` / `minimum` | `min` | `mindestens` | `min` | `min` |
| Max | `max` / `maximum` | `max` / `maximum` | `max` | `hoechstens` / `höchstens` | `max` | `max` |

`compte`/`count` n'a pas besoin de `axe_y` (compte les lignes de
chaque groupe) ; les autres fonctions l'exigent — validé à la
compilation par `_validate_charts` (`parser.py`), comme la référence
`sur` inconnue et le multi-séries sur un type qui ne le supporte pas.
Le calcul lui-même se fait côté frontend, dans le `load_rows()` de
l'état Reflex du graphique (`_nova_chart_aggregate`, voir
`codegen/ui_reflex.py::_CHART_AGGREGATE_HELPER`) — aucune modification
du backend ni de la route de données source.

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
| Template (tâche #37) | `modele` / `modèle` | `template` | `plantilla` | `vorlage` | `modello` | `modelo` |

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

**`template`/`modele` (tâche #37, optionnel)** — chemin d'un fichier
`.html` résolu relativement au fichier `.nova` source, copié tel quel
dans `backend/app/email_templates/notification.html` au moment de la
compilation (`codegen/__init__.py::generate_project`, même mécanisme
que `application { css: "..." }` — placeholder généré si le fichier
référencé est introuvable, jamais d'échec de compilation). Quand ce
bloc est présent, `backend/app/emailer.py` génère en plus une fonction
`render_email_template(values: dict) -> tuple[str, str, str]`
(sujet, corps HTML, repli texte brut) et `_generate_router` (voir
`api_fastapi.py::_template_field_names`) l'appelle à la place du
sujet/corps codés en dur, avec un dict portant `action`
(`created`/`updated`/`deleted`), `entity` (nom NOVA de l'entité), `id`,
et un champ par attribut substituable de l'entité (mêmes conventions de
nommage que `models.py` : `<champ>_<langue>` pour un champ multilingue,
`<cible>_id` pour une référence `belongs_to`). Le fichier HTML peut
utiliser ces clés sous forme de `{{cle}}` ; une balise
`<title>...</title>` (une fois les `{{...}}` substitués) devient le
sujet de l'email, sinon un sujet générique bilingue est utilisé.
Pour `delete`, l'enregistrement est capturé dans un dict
`deleted_values` **avant** `session.delete`/`commit` (l'objet SQLModel
expire après le commit) — voir les tests
`test_email_template_file_copied_and_used_for_render_real_execution`
et `test_email_template_placeholder_used_when_referenced_file_missing`
dans `tests/test_codegen.py`, et `test_email_template_prop_parses_and_
recognizes_all_six_languages` dans `tests/test_parser.py`.

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
  grille mois/semaine/jour calculée côté serveur via la seule
  bibliothèque standard Python (`calendar`, `datetime`) — aucune
  dépendance JS supplémentaire.
- **Glisser-déposer** (tâche #36) : chaque case-jour (mois/semaine) est
  à la fois draggable et cible de dépose (`NovaDnd`, sous-classe
  minimale de `rx.el.div` ajoutant `on_drag_start`/`on_drag_over`/
  `on_drop` — Reflex ne les expose pas nativement sur `Div`, voir
  `codegen/ui_reflex.py::_CALENDAR_DND_HELPER`). Déposer un jour sur un
  autre **déplace** le premier événement du jour source (`PUT` sur
  `champ_date` uniquement, heure préservée pour `date_heure`) —
  toujours généré. Un chip « + Nouvel évènement » dans la barre
  d'outils **crée** un enregistrement en étant déposé sur un jour
  (`POST` avec `champ_date` + `champ_titre` par défaut) — généré
  uniquement quand `_calendar_quick_create_safe` (`codegen/ui_reflex.py`)
  détermine que c'est sûr : aucun autre champ requis sans valeur par
  défaut, et aucune relation `appartient_a` sur l'entité (sinon le chip
  est omis, le déplacement restant toujours disponible). Les
  événements d'un même jour étant affichés en un seul texte joint
  (`champ_titre` de chaque enregistrement séparés par des virgules —
  `rx.foreach` imbriqué sur une liste dans un dict lève
  `ForeachVarError`, voir le commentaire sur ce point dans
  `_generate_calendar_state_and_view`), le glisser-déposer porte sur la
  case-jour entière, pas un événement individuel.

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

## Base de données (prop `database` sur `application`/`app`)

| Mot-clé | FR | EN | ES | DE | IT | PT |
|---|---|---|---|---|---|---|
| Prop. base de données / Database prop | `base_donnees` / `base_données` | `database` | `base_datos` | `datenbank` | — (`database`) | `banco_dados` |

Contrairement au reste du DSL, les **valeurs** de cette propriété
(`sqlite`, `postgresql`, `mysql`, `sqlserver`, `oracle`, `mongodb`) sont
des noms propres non traduits par langue — quelques alias usuels sont
néanmoins acceptés, déclarés dans `keywords.DATABASE_ENGINES` :

| Moteur | Valeur canonique | Alias acceptés |
|---|---|---|
| SQLite (défaut) | `sqlite` | — |
| PostgreSQL | `postgresql` | `postgres`, `postgre` |
| MySQL | `mysql` | `mariadb`, `maria` |
| SQL Server | `sqlserver` | `sql_server`, `mssql` |
| Oracle | `oracle` | — |
| MongoDB (NoSQL) | `mongodb` | `mongo` |

```
application MonApp {
  base_donnees: postgresql
}
```

- Absent de `application { ... }` = `sqlite` (comportement historique
  inchangé, aucune dépendance supplémentaire).
- Une valeur inconnue lève une erreur à la compilation listant les
  valeurs valides (`_validate_app_database` dans `parser.py`).
- `sqlite`/`postgresql`/`mysql`/`sqlserver`/`oracle` : backend SQLModel
  inchangé ; seuls la dépendance pilote (`requirements.txt`), l'URL de
  connexion par défaut et le service `db:` du `docker-compose.yml`/
  `values.yaml` Helm changent selon le moteur (voir README, section
  "Base de données").
- `mongodb`/`mongo` : chemin de génération entièrement différent
  (modèles [Beanie](https://beanie-odm.dev/), routes `async`). `requete`/
  `query` (sans jointure), `calendar`/`calendrier` et les relations
  `has_many`/`possede_plusieurs` sont pleinement supportés — seule la
  **jointure explicite** (`jointure:`/`join:` dans un bloc `requete`/
  `query`) est **rejetée à la compilation**
  (`_validate_mongo_unsupported_features` dans `parser.py`), MongoDB
  n'ayant pas de `JOIN` natif — voir README, section "Base de données",
  pour le détail des fonctionnalités supportées (auth JWT, email,
  upload, contenu multilingue, `belongs_to`, `chart` sur entité, requêtes,
  calendrier, `has_many`).

Couvert par `tests/test_parser.py` (section "base sql config" —
canonicalisation des alias, rejet d'un moteur inconnu, reconnaissance du
mot-clé `database` dans les 6 langues — et section "backend NoSQL Mongo"
pour le rejet à la compilation de la jointure explicite et l'acceptation
de `requete`/`calendar`/`has_many`) et `tests/test_codegen.py`
(génération du driver/service/`values.yaml` par moteur SQL, et exécution
réelle complète — auth JWT, CRUD, unicité, validation, requête, calendrier
`.ics`, `has_many` — du backend Mongo généré via `TestClient` avec
`mongomock-motor`).

## Migrations Alembic (commande CLI `nova migrate`, tâche #38)

Pas un bloc du DSL — une commande de la CLI `nova` (`nova_compiler/cli.py`),
disponible uniquement pour un moteur SQL (`program.database_engine() !=
"mongodb"`, sinon rejetée avec un message explicite avant toute
génération).

Structure générée dans `codegen/api_fastapi.py::generate_backend_scaffold`
(constante `_ALEMBIC_SCAFFOLD`) — **une seule fois**, comme
`routers_custom/` : jamais réécrite par une compilation suivante (voir
`codegen/__init__.py::generate_project`, boucle `scaffold_files` avec
`if target.exists(): continue`) :

| Fichier | Rôle |
|---|---|
| `backend/alembic.ini` | Config Alembic minimale ; `sqlalchemy.url` volontairement vide (lue dynamiquement depuis `app.database`, jamais codée en dur). |
| `backend/migrations/env.py` | Importe `app.models` (peuple `SQLModel.metadata`) et réutilise `DATABASE_URL`/`engine` de `app.database` — donc `NOVA_DATABASE_URL` au runtime, rien à configurer. |
| `backend/migrations/script.py.mako` | Template de révision Alembic standard, avec `import sqlmodel` ajouté (requis : les types SQLModel comme `AutoString` apparaissent dans le SQL autogénéré — sans cet import, `alembic upgrade` lève `NameError: name 'sqlmodel' is not defined`). |
| `backend/migrations/versions/.gitkeep` | Dossier vide au départ, gardé par git avant la première révision. |

`backend/requirements.txt` reçoit systématiquement `alembic>=1.13` pour un
backend SQL (jamais pour Mongo, voir `_generate_emailer`... plutôt
`generate_backend` dans `api_fastapi.py`).

`nova migrate <source.nova> -o <sortie> -m "<message>"` :
1. Compile le projet (`generate_project`, identique à `nova compile`) —
   régénère `models.py`, `database.py`, etc., mais jamais le scaffold
   Alembic ci-dessus.
2. `subprocess.run([sys.executable, "-m", "alembic", "revision",
   "--autogenerate", "-m", message], cwd=<sortie>/backend)`.
3. `subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"],
   cwd=<sortie>/backend)`.

Chaque étape échoue explicitement (`typer.Exit(code=1)`, stderr affiché)
plutôt que de continuer silencieusement. Aucun mock : `alembic` doit être
importable dans l'environnement Python qui exécute `nova` (même
hypothèse que `docker compose` pour `nova run`).

Couvert par `tests/test_codegen.py::test_alembic_scaffold_generated_once_
for_sql_backend` (présence/contenu du scaffold, non-écrasement à la
recompilation, absence côté Mongo — voir aussi l'assertion dédiée dans
`test_mongo_backend_generates_beanie_documents_and_nosql_requirements`) et
`tests/test_cli.py` (exécution réelle d'un VRAI processus `alembic` —
`revision --autogenerate` puis `upgrade head` contre une base SQLite
réelle, vérification directe des tables/colonnes créées ; rejet propre
pour `database: mongodb` ; non-écrasement du scaffold par un `nova
compile` ultérieur).

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
dans `tests/test_codegen.py`). Les types `donut`/`funnel` et
l'agrégation (tâche #35) ont leurs propres tests dans `test_parser.py`
(`test_chart_type_keyword_recognizes_donut_and_funnel_all_six_languages`,
`test_chart_donut_and_funnel_reject_multi_series`,
`test_chart_aggregation_function_recognizes_all_six_languages` et les
tests de validation associés) ; le helper Python généré
`_nova_chart_aggregate` est, lui aussi, appelé réellement (pas
seulement `ast.parse`) avec des données synthétiques dans
`test_chart_frontend_module_actually_imports_and_builds_all_pages`.

Le glisser-déposer du bloc `calendar` (tâche #36) a sa propre couverture :
`test_calendar_generates_state_route_and_navbar_link` vérifie le code
généré (`NovaDnd`, `on_drag_start`/`on_drag_over`/`on_drop`, chip de
création rapide) ; `test_calendar_quick_create_chip_omitted_when_entity_has_other_required_field`,
`..._has_belongs_to` et `..._chip_present_when_extra_field_has_default`
couvrent la décision de génération du chip (`_calendar_quick_create_safe`,
testée aussi directement par `test_calendar_quick_create_safe_helper_unit`) ;
et `test_chart_frontend_module_actually_imports_and_builds_all_pages`
appelle réellement `drop_on_day` (déplacement ET création rapide) sur le
state généré, réseau simulé par un faux client httpx qui enregistre les
appels — vérifiant la résolution du premier événement du jour source, la
préservation de l'heure pour `date_heure`, et la construction exacte du
payload envoyé au backend (`entité Rappel`, calendrier `Rappels`, non
protégée pour ce test précis : `get_state(AuthState)` a besoin d'un
contexte de requête Reflex actif, absent d'un state instancié
directement).

---

[⬅ Retour au README / Back to README](../README.md)
