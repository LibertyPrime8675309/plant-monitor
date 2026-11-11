# Prototype: pests that eat plants (proto/browse-risk)

**What:** Ethan's plants are being eaten by rabbits, rats and mice (November 11, 2026). Each plant gets a rough browse risk, High, Some or Low, with the reason in words, worked out from its genus (a few species have their own entry). A page, `#/browse`, sorts every plant here by it and says what to do; a plant's own page has a line with its risk and a link to the page.

**Why from the genus and not a stored field:** it works for all ~98 plants and any added later, with no batch of per-plant values to keep in step with codes. Nothing is stored, so no database change and nothing to upgrade.

**Files:** `app/plantdb/browse.py` (table `BROWSE`, `browse_for()`, `GET /api/browse[?plant=CODE]`), `app/static/js/browse.js`, `css/browse.css`, one line in `manifest.json` and `run_checks.py`. Tests: `dev/test/unit/test_browse.py`, `dev/test/browse_check.py`.

**Where the data came from:** a photo review in a Claude chat on November 11, 2026 (about 40 photos), saved in Ethan's Plants project as `claude/garden-pest-resistance-plant-id-2026-11-11.md`, checked against general horticulture knowledge. Corrections made on the way: elephant bush (Portulacaria) and purple heart (Tradescantia) are not deterrents, and succulents get chewed by rats and mice in dry spells.

**Open questions for Ethan**
1. Should a risk be editable per plant (for example, once you see which plants really get eaten)? That would need a field and a batch.
2. A "Pests seen" log (who ate what, and when) would show whether it is rabbits or rodents. Wanted?
3. Should high-risk plants show up on Today in the evening, as a reminder to cover them?
4. Page link: it is not in the top bar (the row would wrap). Fine?
