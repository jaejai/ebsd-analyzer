# Distributing EBSD Analyzer (tiny hosting, zero-knowledge user)

This packages the app so a non-technical Windows user installs it by
double-clicking **`EBSD_Analyzer_Setup.exe`** → Next → Next → Finish, with a
Start-Menu / Desktop shortcut. No Python, conda, or admin rights required.

## How it stays small to host

Instead of freezing the whole environment (~450 MB) and hosting that, the
installer ships only **your code + a lockfile** (a few MB). At install time it
fetches a private, self-contained environment from **conda-forge** (via `pixi`)
onto the user's machine. So **you host only a few MB**; the ~hundreds of MB of
libraries come from conda-forge's CDN, once, on the user's side.

This is the same method that will scale to matsam (PyTorch/SAM), where the
frozen bundle would be multiple GB and impossible to host.

### Licensing (safe for commercial/enterprise users)
- **pixi** — BSD-3-Clause (prefix.dev), free for any use.
- **conda-forge only** — `pixi.toml` declares `channels = ["conda-forge"]` and
  never Anaconda's `defaults` channel, so **no Anaconda commercial licence / ToS
  acceptance is ever required**. Do not add `defaults`/`anaconda` channels.
- App itself is **GPL v3** (because orix is GPL v3) — free to distribute as
  open source.

## Files (all in `standalone_ebsd/`)

| File | Role |
|------|------|
| `pixi.toml` | environment spec (conda-forge, pinned versions) |
| `pixi.lock` | exact resolved versions — commit this; guarantees reproducibility |
| `get_pixi.ps1` | downloads the pixi binary into a local `.pixi-bin/` |
| `install.bat` | one-time setup: fetch pixi → `pixi install` (builds the env) |
| `launch.bat` | run the app inside the pixi env (`pixi run app`) — the shortcut target |
| `packaging/ebsd_analyzer.iss` | Inno Setup script → builds `Setup.exe` |

The app also sets `NUMBA_CACHE_DIR` to a writable temp dir at startup
(`app.py`), so orix/numba's first-run compile cache never fails on a fresh
install.

## Build the installer (you, once per release)

1. Install **Inno Setup 6** (free): https://jrsoftware.org/isdl.php
2. Regenerate the lockfile if deps changed:
   ```
   pixi install        # run in standalone_ebsd/ ; commit the updated pixi.lock
   ```
3. Compile the installer:
   ```
   "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" packaging\ebsd_analyzer.iss
   ```
   Output: `packaging\Output\EBSD_Analyzer_Setup.exe` (small — a few MB).

## Host on GitHub (tiny footprint)

- **Repo (public):** commit the source + `pixi.toml` + `pixi.lock` + the `.bat`/
  `.ps1` scripts + `LICENSE` (GPL v3). A few MB total.
- **Release:** attach `EBSD_Analyzer_Setup.exe` as a Release asset (even this is
  only a few MB, since it doesn't bundle the libraries).
- **GitHub Pages:** a one-page site explaining the app with a "Download for
  Windows" button linking to the Release asset.

## What the user experiences

1. Download `EBSD_Analyzer_Setup.exe` (small).
2. Double-click → Windows SmartScreen may warn ("More info → Run anyway" — normal
   for unsigned apps). Optional fix: code-sign the exe (e.g. free OSS signing).
3. The wizard copies files, then shows *"Downloading analysis components…"* while
   it fetches the conda-forge environment (one-time, needs internet).
4. Finish → launch from the Start Menu / Desktop icon. Done.

Uninstall removes the app **and** the fetched `.pixi` environment cleanly.

## Ubuntu (the minority)

`pixi` is cross-platform and `pixi.toml` already lists `linux-64`. A small
`install.sh` / `launch.sh` mirroring the `.bat` files covers Ubuntu users (they
tolerate a terminal fine). Not built yet — add when needed.
