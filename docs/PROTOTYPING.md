# Prototyping new features

This repository is set up so any Claude session can pick up the project and try ideas. Ethan decides which ones become real releases.

## The workflow
1. **Branch.** Work on a branch named `proto/<short-name>`, for example `proto/watering-calendar`. Never commit prototypes straight to `main`.
2. **Build it as a real feature**, following `CLAUDE.md`: accessible, plain words, works on a phone, upgrades an existing database safely.
3. **Test it:**
   1. Run `dev/test/mock_server.py` with a throwaway `DATA_DIR` under `dev/tmp/`.
   2. Run `dev/test/smoke.py`.
   3. Look at the screenshots.
   4. Add a focused Playwright check for the new feature if it has interaction.
4. **Write it up** in `docs/prototypes/<short-name>.md`:
   - what it does and why
   - screenshots
   - how to try it
   - what it changes in the database
   - open questions for Ethan
5. **Open a pull request** to `main` titled `Prototype: <name>`, with the write-up as its description and the screenshots attached. Ethan reads it there.
6. **Trying it on his PC** before merging: only if Ethan asks. Build a zip from the branch with `tools/make-release.py` and put "PROTOTYPE" at the top of its CHANGELOG entry. The updater installs it like any release and makes a backup first. Remind him that going back means restoring that backup (Backups page) and installing the previous zip with `-Force`. Screenshots are usually enough.
7. **Merge** only when Ethan says so. The release (version bump, CHANGELOG, zip) is built from `main` after merging.

## Keeping prototypes mergeable
Several prototypes are usually open at once, and Ethan may merge them in any order. Each one should merge cleanly with `main` and with every other open `proto/` branch:
- **Register, don't wrap (1.46.0, PLAN.md step 2).** A prototype is its own files: `app/plantdb/<name>.py` (found by the package by itself; give it `ORDER = 60` if it imports from another feature module), `app/static/js/<name>.js` (one line in `app/static/js/manifest.json`, before `main`), `app/static/css/<name>.css` (joined into the stylesheet by the server) and `dev/test/<name>_check.py` (one line in `run_checks.py`'s ORDER). What it adds to existing pages is said once with `addFeature()` at the end of its script (see ARCHITECTURE, "The feature registry"): a page, a block on Today with its order number, an addition to a plant's or a group's page, a care kind. Never wrap `viewToday` or `loadCarePlant`, never watch `#app` with a MutationObserver, never add lines to `route()`, `SECTIONS`, `server.py`, `index.html` or `sw.js`: the registry and the manifest do those.
- The shared lines a prototype still touches are one line each in `manifest.json` and `run_checks.py`, and a CHANGELOG and README entry. Two prototypes that both add a line there merge with a one-line conflict at most; keep both sides.
- Before opening the pull request, merge every open `proto/` branch into a throwaway local branch, run all the focused checks and the smoke test there, then delete the throwaway branch.

## Ideas list
Add ideas to `docs/IDEAS.md` with a line each; a prototype session can take the top one.
