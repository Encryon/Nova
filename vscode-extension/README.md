# NOVA Language pour VS Code / NOVA Language for VS Code

Coloration syntaxique, snippets bilingues et intégration de la CLI `nova`
pour écrire des fichiers `.nova` dans Visual Studio Code.

Syntax highlighting, bilingual snippets and `nova` CLI integration for
writing `.nova` files in Visual Studio Code.

## Installation (mode développement / dev mode)

1. Installez le framework NOVA (voir le README à la racine du repo) afin que
   la commande `nova` soit disponible dans un terminal.
   Install the NOVA framework first (see the repo root README) so the
   `nova` command is available in a terminal.
2. Ouvrez le dossier `vscode-extension/` dans VS Code, puis appuyez sur
   `F5` (ou "Run > Start Debugging") : une nouvelle fenêtre VS Code
   ("Extension Development Host") s'ouvre avec l'extension chargée.
   Open the `vscode-extension/` folder in VS Code and press `F5` (or
   "Run > Start Debugging"): a new "Extension Development Host" window
   opens with the extension loaded.
3. Ouvrez un fichier `.nova` (par ex. `examples/blog.fr.nova` du repo) dans
   cette fenêtre : la coloration syntaxique et les snippets sont actifs.
   Open a `.nova` file (e.g. `examples/blog.fr.nova` from the repo) in
   that window: syntax highlighting and snippets are active.

## Installation permanente (paquet .vsix)

```bash
npm install -g @vscode/vsce
cd vscode-extension
vsce package
code --install-extension nova-lang-0.1.0.vsix
```

## Commandes / Commands

Palette de commandes (`Ctrl+Shift+P` / `Cmd+Shift+P`) :

- **NOVA: Vérifier la syntaxe / Check syntax** — équivalent à `nova check`.
- **NOVA: Compiler ce fichier / Compile this file** — équivalent à
  `nova compile <fichier> -o <outputDir>`.
- **NOVA: Nouveau projet... / New project...** — équivalent à `nova new`.

Ces commandes sont aussi accessibles via clic droit dans l'éditeur sur un
fichier `.nova`.
These commands are also available via right-click in the editor on a
`.nova` file.

## Paramètres / Settings

| Paramètre / Setting | Défaut / Default | Description |
|---|---|---|
| `nova.cliPath` | `nova` | Chemin vers l'exécutable `nova` / Path to the `nova` executable |
| `nova.outputDir` | `build` | Dossier de sortie du compilateur / Compiler output directory |

## Snippets

| Préfixe / Prefix | Résultat |
|---|---|
| `entity` | Bloc `entity { field ... }` (EN) |
| `entite` | Bloc `entité { champ ... }` (FR) |
| `api` / `api-fr` | Bloc API CRUD (EN / FR) |
| `page-table` / `page-tableau` | Page tableau (EN / FR) |
| `page-form` / `page-formulaire` | Page formulaire (EN / FR) |
| `app` / `application` | Bloc application (EN / FR) |
| `belongs-to` / `appartient-a` | Relation N-1 (EN / FR) |
