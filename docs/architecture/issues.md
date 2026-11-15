# The Issue tracker and Check for updates (1.58.0)

Asked for by Ethan on November 15, 2026, after two things he noticed away from the PC: High contrast in the Light theme looked as if it did nothing (it is as built: the light theme's text was already at 14.9 to 1, so only the lines had far to go), and his iPad mini showed 1.55.0 while the PC ran 1.57.0 (the page had been open since 1.55.0, which had nothing to notice a newer server; that came in 1.56.5). His answers: people who can only view may send reports; naming each device once is fine; only the owner sees the Issue tracker; and "Check for updates" beside the version on Settings and at the foot of Navigation.

## Files
- `app/plantdb/issues.py`: tables, `POST /api/report`, `/api/issues...`, the photo guard.
- `app/static/js/issues.js`, `app/static/css/issues.css`: the report window, the Issue tracker page, Today's line, the Settings card.
- `app/plantdb/releases.py` (`POST /api/whatsnew/check`), `app/static/js/releases.js` (`rlCheck()`), `app/static/css/releases.css`: Check for updates.
- Shared lines: `core.py` (`ISSUES_SCHEMA` in `init_db()`, `/api/issues` in `OWNER_ONLY_PATHS`, `/api/report` in `VIEWER_POSTS`), `index.html` (`#sn-more` with `#report-btn` and `#upcheck-btn` in `#sn-foot`; `#report-top` in `.top-acts`; `#page-foot` after `main`), `ui.js` (`pinLayout()` moves `#sn-more`), `core.js` (the version line on Settings; `toast()` tells `issNoteError()` about an error), `offline.js` (`/api/report` in `OFF_OK`, `offWords()`, viewers may queue it).
- Tests: `dev/test/unit/test_issues.py`, `dev/test/issues_check.py` (in `run_checks.py` before `names`).

## A report
`POST /api/report`, a form (or JSON without pictures): `notes`, `page` (the hash), `page_title` (the page's h1), `section` (the section marked in Navigation), `page_version` (`PAGE_VERSION`, the meta tag the page was served with), `device`, `made_at`, `info` and `settings` (each a JSON object as text), `files` (up to 4 pictures). Words or a picture are required.
- The server adds: `at`, the account (`login`, `name`, `role`, `via`), `addr` (through Tailscale the first address in `X-Forwarded-For`, read on the Tailscale port only; else the request's own), `server_version`.
- `info` and `settings` are written by the page, so they are kept as words to show and nothing else: `issue_json()` keeps a JSON object of plain values, at most 80 keys, 600 characters a value, 12,000 characters in all.
- At most `ISSUE_PER_HOUR` (30) reports an hour for each account (429).
- `made_at` comes from `X-Offline-Made` when the report waited in the outbox, so it is when it was written.
- It is in `VIEWER_POSTS`: a report changes nothing of the plants. On the mirror it is refused like every change (a mirror's record is replaced by the next backup).

**What the page gathers** (`issInfo()`, `issSettings()`, `issWhere()` in issues.js, when the window opens, so it describes the page behind it): kind of device (`offGuessDevice()`), user agent, system, Home Screen app or tab, how it is connected and the host, screen and window, text size, layout (narrow, touch, no sections), colours and contrast, language and time zone, the home in use, online state (`OFF.reach`, `OFF.saved`), changes waiting, the version `/api/meta` last gave, network type, the shell caches the service worker holds (`plantdb-shell-<version>`), whether a service worker controls the page, storage used, the last three page timings, and `ISS_ERRS`: the last eight errors (`toast(msg, true)`, `window.onerror`, unhandled rejections). Settings are every Display setting (marked "(changed)" when not the default) and every `plantdb.*` key in localStorage except `ISS_SKIP` (the editor's name, saved answers, timings, the shopping list), each cut to 300 characters.

**The device's name** is `OFFDEV` (IndexedDB `kv.device`), the name the Offline page has kept since 1.24.0. The window's box writes it there. A browser cannot read a device's own name; the mock's and Tailscale Serve's headers do not carry the node name either.

## Pictures
Saved by `issue_save_image()` into the photos folder as `issue_<32 hex>.jpg` (written again as JPEG, at most 2000 px, so a screenshot's small text stays readable), so every backup with photos carries them and a restore brings them back. They are served by `/api/issues/<id>/photo/<n>` (the owner's). `issue_photo_guard()` (a `before_request`, after core's `guard()`) answers 404 to `/photos/issue_*` and `/thumbs/issue_*` for anyone but the owner. The front end never builds those addresses.

## The Issue tracker
Everything under `/api/issues` is in `OWNER_ONLY_PATHS`: `GET /api/issues` (all reports with what they carry; `?brief=1` only `counts` and `fresh`), `POST /api/issues/seen`, `PUT /api/issues/<id>` (`status` open, looking, fixed, closed; `fixed_in` three numbers; `owner_notes`), `DELETE /api/issues/<id>` (its pictures go too), the photo route. Changes are in the audit log (`field` issue).
- `fresh` counts reports from accounts that are not the owner and that the owner has not seen (`seen_at`). Today's line (`iss-today`, order 7) shows while it is above zero; opening the page posts `seen`.
- The page (`#/issues`, Settings row, after Audit log; `css/issues.css` hides its link from everyone but the owner, as `updates.css` does) keeps the list in `ISS.data` and draws cards itself: `issRedraw()` after Show, Search or a status change. Status, fixed-in and notes save on `change` (`changeActs`), so notes save on leaving the box. `issText()` is the text Copy for Claude copies.
- The page has no h2 sections, so on a wide screen it has no Navigation.

## Where the buttons are
`#sn-more` holds Report a problem and Check for updates. `pinLayout()` (ui.js) puts it:
- in `#sn-foot`, above Display, held at the bottom of Navigation;
- after the list of sections (not held) where the window is under 40 lines of text tall (the largest text on a phone), where the pair would leave the list three lines;
- in `#page-foot` (after `main`, in the space `main` keeps empty at its end) on a wide page with no sections, where there is no Navigation.

`#report-top` ("Report", read out as "Report a problem") is a second button in the top bar, on a wide page with no sections. `topFit()` (core.js) fits the bar without it first (`data-toprep="0"`, which hides it), then tries it (`data-toprep="1"`), and keeps it only if the bar comes out exactly the same: links folded or not, one line or two, compact or not, and its height. So the bar is never changed by it (the `layout` check caught the first version, which let it fold the page links at 1920 wide). Display moved to the top bar on these pages in 1.57.0; a third button in the corner was not an option because the corner hid the ends of tables.

## Check for updates
`rlCheck()` in releases.js, from `data-act="rlcheck"`:
1. `rlServerVersion()`: `GET /api/version?nosave=1` with `cache: 'no-store'` and `X-Probe` (the service worker then asks the server itself, for up to 8 seconds, and saves nothing). An answer marked `X-Offline-Saved` counts as no answer.
2. `registration.update()`, so the service worker fetches its own newer copy.
3. The owner only: `POST /api/whatsnew/check` runs `check_latest()` now (not with `PLANTDB_UPDATES=0` or on the mirror: `off`) and gives `{version, asked, off, newer, latest}`.
The window compares the server's version with `PAGE_VERSION`. "Reload the app" is `location.reload()` (`reloadnow`, from 1.56.5): the service worker asks the server first for the app's own files since 1.56.5, so a reload with the server in reach is the new app. A check replaces `rlServerVersion` to try a newer server and a silent one.

**Why the iPad said 1.55.0 and not "offline":** `#app-ver` is filled once in a page's life from `/api/meta` (`META`), and the page's requests were live. A page from before 1.56.5 has no `PAGE_VERSION` and no `newerApp()`; nothing can reach into it. 1.55.0's service worker also served the saved app for 30 seconds after any failed request, so a reload just after Tailscale woke gave 1.55.0 again.

## Not built
- Telling the owner's phone about a new report (a push kind). `push.py` calls a fixed list of senders; the open prototypes 86 and 118 plan `PUSH_EXTRA_KINDS` in core for this.
- The sender seeing their own reports and what became of them.
- Reports in the JSON download.
