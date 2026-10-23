# Prototype: photo packs, so release zips stay small

## Why
A release zip carries every plant photo, so it is now 29.7 MB. That is just under the 30 MB limit for saving a file to your PC from a Claude chat, so the next photo round would not fit.

## What it does
- **The release zip no longer carries plant photos.** It drops from about 30 MB to about 0.4 MB.
- **Photos travel in photo packs,** one zip per plant update:

  | Pack | Photos | Size |
  |---|---|---|
  | `plant-database-photos-seed.zip` | 47 | 9.8 MB |
  | `plant-database-photos-batch2.zip` | 28 | 6.7 MB |
  | `plant-database-photos-batch6.zip` | 30 | 5.1 MB |
  | `plant-database-photos-batch8.zip` | 2 | 0.2 MB |
  | `plant-database-photos-batch9.zip` | 113 | 7.5 MB |

  A pack never changes once made, so each release only comes with the packs for its new plant updates. A very big photo round is split into `-part2`, `-part3` and so on, each under 30 MB.
- **The updater adds the photos.** It looks for packs next to the release zip and adds any photos your `plant-database` folder does not have yet.
  - **Your PC today:** your folder already has every photo from the old full zips, so nothing changes and no packs are needed.
  - **A missing pack:** the updater lists which packs are missing and stops before changing anything.
  - **A pack that arrives late:** if you updated with `-Force` and the packs come later, running the updater again adds their photos, even though the version is already up to date.
- **The app repairs photos itself.** When it starts, it copies any plant photo that arrived late in a pack into your photos folder, so a plant page never stays stuck with a missing picture.

This is what the updater shows when packs are missing, then when they are there:
```
This release needs plant photos that are not in the plant-database folder yet, and these photo packs are not in this folder:
  plant-database-photos-batch9.zip  (113 photos)
STOPPED: Save those photo packs next to the release zip and run the updater again. Nothing has been changed.
...
== Adding plant photos from plant-database-photos-batch9.zip
113 photos added.
Done. Plant record version 1.8.0 is running at http://localhost:8080
```

## What it changes in the database
Nothing. At start-up the app copies any missing plant photo from the app's seed folder into `data/photos`, if it has that photo now.

## How it works (for whoever merges it)
- `tools/make-release.py`:
  - writes the slim app zip with `app/seed/photo-packs.json` (which photos each pack holds, and the pack's file name), plus one `dist/plant-database-photos-<pack>.zip` per pack
  - assigns each photo to the first batch that uses it, in the order batches apply; photos no batch names go in `extra`
  - `--full` builds the old single zip
- `tools/update-plant-database.ps1`:
  - `Pending-Packs` compares the manifest with the photos already in the folder
  - a missing pack stops the update before copying, unless `-Force`
  - the photos-only run handles packs that arrive after the version is installed
- `app/server.py`: `repair_seed_photos()` runs at start-up.
- `CLAUDE.md` and the README explain photo packs.
- Test: `dev/test/updater_check.sh` runs five situations with PowerShell 7, a fake `docker` and a fake app: existing install, missing packs, packs present, packs arriving late, nothing to do. All pass.

## Questions for Ethan
1. Is it fine to save one or two extra zips (the photo packs) in your Plants folder when a release has new photos? The chat reply will always say which ones go with which release.
2. Once you have updated, the packs can be deleted. Should the updater offer to delete them, or move them into an `old-zips` folder?
