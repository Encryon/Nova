// Extension VS Code pour le langage NOVA.
// VS Code extension for the NOVA language.
//
// Fournit : coloration syntaxique (via syntaxes/nova.tmLanguage.json),
// snippets bilingues (via snippets/nova.code-snippets), et des commandes
// pour appeler la CLI `nova` (check / compile / new) sans quitter l'éditeur.
//
// Provides: syntax highlighting, bilingual snippets, and commands wrapping
// the `nova` CLI (check / compile / new) without leaving the editor.

const vscode = require("vscode");
const path = require("path");

let novaTerminal = null;

function getTerminal() {
  if (!novaTerminal || novaTerminal.exitStatus !== undefined) {
    novaTerminal = vscode.window.createTerminal("NOVA");
  }
  return novaTerminal;
}

function runInFileDir(filePath, commandLine) {
  const dir = path.dirname(filePath);
  const terminal = getTerminal();
  terminal.show();
  terminal.sendText(`cd "${dir}"`);
  terminal.sendText(commandLine);
}

function requireActiveNovaFile() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showWarningMessage(
      "Ouvrez un fichier .nova / Open a .nova file first."
    );
    return null;
  }
  if (!editor.document.fileName.endsWith(".nova")) {
    vscode.window.showWarningMessage(
      "Ce fichier n'est pas un fichier .nova / This is not a .nova file."
    );
    return null;
  }
  return editor;
}

function activate(context) {
  const cli = () => vscode.workspace.getConfiguration("nova").get("cliPath", "nova");
  const outDir = () => vscode.workspace.getConfiguration("nova").get("outputDir", "build");

  context.subscriptions.push(
    vscode.commands.registerCommand("nova.compile", async () => {
      const editor = requireActiveNovaFile();
      if (!editor) return;
      await editor.document.save();
      const base = path.basename(editor.document.fileName);
      runInFileDir(editor.document.fileName, `${cli()} compile "${base}" -o "${outDir()}"`);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("nova.check", async () => {
      const editor = requireActiveNovaFile();
      if (!editor) return;
      await editor.document.save();
      const base = path.basename(editor.document.fileName);
      runInFileDir(editor.document.fileName, `${cli()} check "${base}"`);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("nova.newProject", async () => {
      const name = await vscode.window.showInputBox({
        prompt: "Nom du projet NOVA / NOVA project name",
        placeHolder: "mon_projet",
      });
      if (!name) return;
      const lang = await vscode.window.showQuickPick(["fr", "en"], {
        placeHolder: "Langue du fichier de départ / Starter file language",
      });
      const folders = vscode.workspace.workspaceFolders;
      const cwd = folders && folders.length ? folders[0].uri.fsPath : process.cwd();
      const terminal = getTerminal();
      terminal.show();
      terminal.sendText(`cd "${cwd}"`);
      terminal.sendText(`${cli()} new ${name} --lang ${lang || "fr"}`);
    })
  );
}

function deactivate() {}

module.exports = { activate, deactivate };
