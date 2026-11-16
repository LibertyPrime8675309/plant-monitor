"""1.58.0 (the dyslexia audit): the app's own words keep to short sentences. dev/tools/wording.py lists every sentence of more than
25 words that the front end writes. A file may not have more of them than its number below. The numbers only go down: when a stage of
the help-text rewrite shortens a file's sentences, lower its number here. A file not listed may have none. (The tool reads code, so a
few of the counted "sentences" are run-together labels rather than prose: rewriting them is not needed, only not adding more.)"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
import wording

LIMITS = {
    "care.js": 3,
    "lights.js": 1,
    "mushrooms.js": 1,
    "plant.js": 2,
    "propagation.js": 1,
    "review.js": 1,
    "sensors.js": 2,
    "shopping.js": 2,
    "ui.js": 4,
    "weather.js": 3,
}


def test_no_new_long_sentences():
    over = []
    for f in sorted(os.listdir(wording.ROOT)):
        if not f.endswith('.js'): continue
        L = wording.long_ones(f)
        if len(L) > LIMITS.get(f, 0):
            over.append(f'{f}: {len(L)} (at most {LIMITS.get(f, 0)}): ' + ' | '.join(f'line {ln}: {s[:90]}' for ln, n, s in L))
    assert not over, 'Sentences over 25 words: split them into two or three short ones. ' + '; '.join(over)


# The manual and the README (stage 5): no sentence over 50 words (the longest left are lists of sections),
# and no more sentences over 25 words than now. Split the new ones.
MANUAL_LIMIT = 292  # 271, then the Layouts page came from main


def test_manual_keeps_short_sentences():
    found = [(os.path.relpath(f, wording.MANUAL), ln, n, s)
             for f in wording.manual_files() for ln, n, s in wording.manual_long(f)]
    huge = [x for x in found if x[2] > 50]
    assert not huge, 'Sentences over 50 words in the manual: ' + '; '.join(
        f'{f}:{ln} ({n}) {s[:80]}' for f, ln, n, s in huge)
    assert len(found) <= MANUAL_LIMIT, (
        f'{len(found)} sentences over 25 words in the manual (at most {MANUAL_LIMIT}): split the new ones')
