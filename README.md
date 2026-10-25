# pmp-to-txt

Turn a **PenguinMod** (`.pmp`) or **Scratch 3** (`.sb3`) project into a plain text file that shows every script as readable text.

It is handy for sharing your code in a chat or forum post, asking an AI or a friend to review it, searching a project for a block, comparing two versions with a diff tool, or keeping a text backup next to the project.

It is one Python file with **no dependencies**.

## Example

A project with a script like this in the editor:

```
when green flag clicked
forever
    move 10 steps
    if touching edge? then
        turn right 15 degrees
```

becomes:

```
======== Sprite: Cat ========
Variables: score
Lists: Roles

--- Script 1 ---
When green flag clicked
Forever
  Move 10 steps
  If <touching (edge)?> then
    Turn right 15 degrees
  End
End
```

## Requirements

- Python 3.7 or newer. Get it from [python.org](https://www.python.org/downloads/). On Windows, tick "Add Python to PATH" in the installer.
- That's it. There is nothing to `pip install`.

## Install

1. Go to the [**Releases**](../../releases/latest) page of this repo.
2. Under **Assets**, download **`pmp-to-txt.zip`**, which contains `convert.bat` and `pmp_to_txt.py`. **Don't pick "Source code"**, since that is the whole repo and has extra files you don't need.
3. Unzip it anywhere. Keep the two files together in the same folder.

You can keep the folder next to your projects or run it from any location.

## Usage

Open a terminal in the folder with the script and run:

```
python pmp_to_txt.py MyGame.pmp
```

This writes `MyGame.txt` next to the project.

On some systems the command is `python3` or `py` instead of `python`.

**File names with spaces** need quotes:

```
python pmp_to_txt.py "My Game v1.2.pmp"
```

**No terminal typing:** see [Double-click](#double-click-windows) below, or run `python pmp_to_txt.py` with no file name and a window opens where you pick the project.

**Tip:** type `python pmp_to_txt.py ` (with a trailing space), then drag your project file into the terminal window. It pastes the full path for you.

### Double-click (Windows)

Keep `convert.bat` in the same folder as `pmp_to_txt.py`.

- **Double-click `convert.bat`**, pick your project in the window that opens, and the `.txt` appears next to it.
- **Or drag your `.pmp` / `.sb3` onto `convert.bat`.** You can drop several at once.

The window stays open at the end so you can read any message. If it says Python wasn't found, install it from [python.org](https://www.python.org/downloads/) and tick "Add Python to PATH".

### Options

| Option | What it does |
|---|---|
| `file` | The `.pmp` or `.sb3` to convert. If you leave it out, a file picker opens. |
| `-o FILE`, `--output FILE` | Choose the output file name. Default: the project name with `.txt`, in the same folder. |
| `--stdout` | Print the result in the terminal instead of writing a file. |
| `--no-comments` | Leave out comments. By default they are included. |
| `--fetch` | Download extensions that are only saved as a web address, so their blocks get readable names. See [Extensions](#extensions). Needs an internet connection. |
| `-h`, `--help` | Show the built-in help. |

Options can be combined:

```
python pmp_to_txt.py "My Game.pmp" --fetch -o "My Game script.txt"
```

## How to read the output

| Notation | Meaning |
|---|---|
| `(something)` | A reporter or number slot, like `(x position)` or a variable like `(score)` |
| `<something>` | A true/false slot, like `<touching (edge)?>` |
| `[something]` | A dropdown, or a variable or list name, like `[my list]` |
| plain text | A typed-in value, like `Move 10 steps` |
| `// text` | A comment. Comments on a block appear right under that block's line. |
| `End` | Closes a block that holds other blocks (repeat, forever, if) |
| Indentation | Blocks inside another block |

The file starts with the extensions the project uses. Then each sprite (and the stage) gets a section with its variables and lists, followed by each script, in on-screen order (top to bottom, then left to right). Custom blocks appear as `Define name (argument)` followed by their body.

## What is supported

- Every sprite and the stage, all scripts, and custom blocks (definitions and calls, with their arguments).
- All the standard Scratch blocks: motion, looks, sound, events, control, sensing, operators, variables and lists.
- The pen extension.
- Comments, both ones attached to blocks and free-floating workspace comments (see below).
- PenguinMod's expandable `if / else if / else` block.
- A few PenguinMod blocks: `not equal`, `mouse clicked?`, `amount of ... in list`, and the Operators Expansion `if ... is truthy` / `or if falsey` blocks.

### Comments

A comment attached to a block is printed on lines starting with `//`, directly under that block:

```
When green flag clicked
// Start of the game
Repeat 3
// loops 3 times
  Move 10 steps
End
```

Free-floating workspace comments, and comments attached to a block nested inside another block's slot, are listed together at the end of that sprite's section under `--- Comments ---`. Use `--no-comments` to leave them all out.

### Extensions

Extension blocks keep the text they show in the editor, when the script can find it.

- **Extensions embedded in the project** (custom extensions loaded from a file or from code): the script reads the extension's code and uses its real block text. For example, `Print text hello with ID my-text`.
- **Extensions loaded from a web address:** these only store the address in the project, so by default their blocks print by their internal name, like `SPtempVars: some block [INPUT=value]`. Run with `--fetch` to download the extension code and get readable block text. The code is only read as text and is never run.
- **Blocks the script doesn't know** are still printed in the form `extension: block name [INPUT=value]`, so nothing is hidden.

## Limitations

- **Scratch 2 projects (`.sb2`) don't work.** Open them in Scratch 3 and save as `.sb3` first.
- Costumes, sounds and sprite positions are not included. Only scripts, variables, lists and comments are.
- Some blocks that Scratch or PenguinMod hide in the editor menus may print with their internal names instead of nicer text.
- Scratch's built-in extensions other than pen (music, video sensing, text to speech, translate) print in the generic form until they're added to the table.
- Blocks not in the built-in table show as `category: block name [INPUT=value]`. This is still readable, just not pretty.
- Tested on sample projects built to match the `.pmp` and `.sb3` formats. If a real project prints something odd, please open an issue and include the output (or the project).

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` is not recognized | Try `py` or `python3`, or reinstall Python and tick "Add Python to PATH". |
| `No project.json inside that file` | The file isn't a Scratch 3 or PenguinMod project (for example an `.sb2`, or a damaged file). |
| The file name has spaces and the script says it can't find it | Put the name in quotes. |
| Blocks print as `SPtempVars: some block [...]` | Add `--fetch`. |
| The picker window doesn't open | Your Python may not include tkinter. The script asks you to type the path instead. |
| Output has strange characters | Open the `.txt` as UTF-8. It's written as UTF-8. |

## Adding a block that prints badly

Block text lives in one table near the top of `pmp_to_txt.py`, named `T`. Each line is an opcode and its text, where `{NAME}` is replaced by the input or dropdown with that name:

```python
"motion_movesteps": "move {STEPS} steps",
"operator_add": "({NUM1} + {NUM2})",
```

Reporters carry their own `( )` and true/false blocks their own `< >`. Adding a line to the table is all you need for a new block.

## Contributing

Issues and pull requests are welcome, especially for blocks that print badly or extensions that need support. When reporting a problem, please include the output text and, if you can, the part of the project that causes it.

## License

MIT. See [LICENSE](LICENSE).
