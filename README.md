# catalog

A window that searches Diablo II Resurrected's Horadric Cube recipes and runewords. Written in Mara.

## Run

```
mara build catalog
catalog.exe
```

Type to search. The search covers both tabs: cube recipes and runewords. Every word typed has to appear in an entry. Click a tab or press Tab to switch. Up/Down, PageUp/PageDown, Home/End and the mouse wheel scroll the active tab. Escape clears the search.

`catalog.exe --find <words>` prints the matches as text, without a window.

Click the sort line under the tabs to order a tab by level: file order, lowest first, or highest first. A recipe's level is its result item's level requirement; 78 of the 157 recipes have one, and the rest sort last. A runeword's level is its highest rune's, since Runes.txt doesn't store one. The window opens without a console (`build.mara` sets `console = false`).

## Data

`data/` holds six of the game's tables, copied from the install (the game keeps them packed in CASC archives):

- `cubemain.txt`: the enabled cube recipes (157). The result is the title; the ingredients are listed under it.
- `Runes.txt`: the complete runewords (99). Runes and item types are named using `misc.txt` and `ItemTypes.txt`.
- `armor.txt` and `weapons.txt`: the level requirements of the cube results.

Bonus stats are shown by their game codes (`res-cold 30`, `ac% 50-60`) because the readable names live in the game's string tables, which are not extracted.

To refresh the tables after a game patch:

```
python -I tools\extract_tables.py
```

The default install folder is at the top of `tools/extract_tables.py`; pass another as the first argument.
