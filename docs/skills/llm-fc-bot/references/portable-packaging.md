# Portable Windows build — stdlib-only Python app the Boss can carry to another machine

> Standing context: the Boss's main machine holds the valuable account — bot testing
> happens on OTHER machines. Deliver a standalone folder (no agent, no LLM, no
> installed Python) zipped to USB size. See also: SKILL.md invariant 5 (runnable
> entrypoint, FC optional).

## Recipe (works; verified end-to-end on fila-bot)

1. **Embedded interpreter** — download the embeddable zip (~11MB):
   `https://www.python.org/ftp/python/<VER>/python-<VER>-embed-amd64.zip`
   Extract to `<pkg>/python/`.
2. **EDIT the bundled `python/python<XY>._pth`** — the default isolates the
   interpreter and your package imports will fail. Replace its content with:
   ```
   python<XY>.zip
   .
   ../src
   ```
   (one path per line, relative to the python/ dir). This is the step that
   silently breaks everything if skipped.
3. **Copy source + native DLLs** into the package (`src/fila_bot/`, built
   `.dll` files next to src/). Keep code stdlib-only: ctypes, json,
   http.server, tkinter all work; nothing that needs pip.
4. **One `.bat` launcher per mode** — Boss double-clicks, no terminal knowledge:
   ```bat
   @echo off
   cd /d "%~dp0"
   python\python.exe -c "import sys; sys.path.insert(0,'src'); from fila_bot.main import main; sys.exit(main())" --mode sim
   pause
   ```
   The trailing `pause` keeps the window open so errors are readable. Ship
   separate safe-mode (sim/dry) and diagnostic launchers; never a launcher
   that sends real input by default.
5. **Verify BEFORE zipping, with the embedded interpreter** (not the dev
   machine's python):
   - import sweep: `python\python.exe -c "import sys; sys.path.insert(0,'src'); import pkg.main, ..."`
   - run EVERY test file directly (`python\python.exe tests/test_x.py`) —
     `unittest discover` finds nothing because the tests are assert-scripts,
     not unittest classes.
6. `rm -rf __pycache__`, then `Compress-Archive -Path pkg -DestinationPath pkg.zip -Force`.
   Typical size ~21MB unpacked / ~11MB zipped.

## Pitfalls

- **Repo-relative paths break in the portable layout.** Any test/doc check like
  `ROOT/'vendor/...dll'` must accept candidate paths (`src/<dll>` in portable).
  One failing path check turns a green suite red on the target machine.
- **`python src/pkg/main.py` fails on relative imports.** Launch through the
  `python -c "...sys.path.insert(0,'src'); from pkg.main import main"` pattern
  (or `python -m pkg.main` with the `._pth` path set), and guard `__main__` for
  both package and direct execution.
- **Memory readers need the target process on the SAME machine.** A UI-tree
  dump fails with "Process not found" if the game client runs elsewhere — even
  if the user just sent screenshots of it from another box. The dump launcher
  must run on the machine that has the client; screenshots are still useful
  for visual comparison, but not for the DLL.
- **When the project is published to a git repo, the tests folder ships WITH
  it — rerun every assert-script test file against the embedded interpreter
  after packaging, not just the import sweep.** A test that passes on the dev
  tree can fail in the package because a path check (e.g. `vendor/...dll` vs
  `src/<dll>`) assumed the repo layout; patch such checks to accept candidate
  paths. Boss does not want a generated README in his repos — push code,
  tests, docs only (no README unless he asks).
- **Client UI redesigns invalidate community attr names.** A radial HUD replacing
  legacy gauges breaks health-extractor attr names even though list-type windows
  (overview, inventory) survive. Ground every extractor against a real UI-tree
  JSON dump on the target client before trusting it — schema docs lag redesigns.
