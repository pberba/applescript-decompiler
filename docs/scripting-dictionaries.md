# Adding a scripting dictionary (.sdef)

Terms from an application's dictionary (`make`, `selection`, `POSIX path`,
…) are stored in the compiled script only as their four-character codes.
The printer turns them back into readable terms using the `.sdef` files
bundled in `applescript_decompiler/data/`. Each file is keyed by its
filename stem, which must match the application name in the script's `tell`
block: `Finder.sdef` resolves codes inside `tell application "Finder"`, and
`System Events.sdef` inside `tell application "System Events"`.

Codes from an application without a bundled `.sdef` are printed as the raw
four-character code instead of the term. Export the app's dictionary with
`sdef`, naming the file for the exact application name:

```shell
sdef /Applications/Spotify.app > Spotify.sdef
```

There are two places that file can go.

### Your own directory (no install)

Point the `APPLESCRIPT_DECOMPILER_SDEF_DIR` environment variable at a
directory of `.sdef` files. They are loaded in addition to the bundled ones,
so you can add dictionaries without touching the package:

```shell
mkdir -p ~/.applescript-sdef
sdef /Applications/Spotify.app > ~/.applescript-sdef/Spotify.sdef
APPLESCRIPT_DECOMPILER_SDEF_DIR=~/.applescript-sdef applescript_decompile script.scpt
```

The variable may list several directories, separated by `os.pathsep` (`:` on
macOS/Linux). Files there are loaded after the bundled dictionaries, so a
`.sdef` whose filename stem matches a bundled app overrides that app's terms.

### Bundled with the package

To ship a dictionary with the package (e.g. when contributing), drop it in
the data directory instead:

```shell
sdef /Applications/Spotify.app > applescript_decompiler/data/Spotify.sdef
```

Either way it is picked up automatically: `load_package_sdefs()`
(`utils.py`) parses every `*.sdef` in the data directory and in each
`APPLESCRIPT_DECOMPILER_SDEF_DIR` directory once at import, pulling out
command/parameter names and enumerators. `pyproject.toml` already ships
`data/*.sdef` as package data, so a bundled file installs with the package.
The Standard Additions and AppleScript's own terms are always available
(`StandardAdditions.sdef` and the built-in terminology table), so commands
with no `tell` block resolve without any extra dictionary.
