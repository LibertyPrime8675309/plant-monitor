"""1.58.0 (the dyslexia audit): the app's own words keep to short sentences. dev/tools/wording.py lists every sentence of more than
25 words that the front end writes. A file may not have more of them than its number below. The numbers only go down: when a stage of
the help-text rewrite shortens a file's sentences, lower its number here. A file not listed may have none. (The tool reads code, so a
few of the counted "sentences" are run-together labels rather than prose: rewriting them is not needed, only not adding more.)"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
import wording

LIMITS = {
    "browse.js": 5,
    "care.js": 3,
    "events.js": 1,
    "guide.js": 5,
    "library.js": 1,
    "lights.js": 1,
    "mushrooms.js": 1,
    "notify.js": 1,
    "offline.js": 6,
    "plant.js": 2,
    "propagation.js": 1,
    "releases.js": 2,
    "review.js": 1,
    "sensors.js": 4,
    "shopping.js": 2,
    "ui.js": 6,
    "weather.js": 4,
}


def test_no_new_long_sentences():
    over = []
    for f in sorted(os.listdir(wording.ROOT)):
        if not f.endswith('.js'): continue
        L = wording.long_ones(f)
        if len(L) > LIMITS.get(f, 0):
            over.append(f'{f}: {len(L)} (at most {LIMITS.get(f, 0)}): ' + ' | '.join(f'line {ln}: {s[:90]}' for ln, n, s in L))
    assert not over, 'Sentences over 25 words: split them into two or three short ones. ' + '; '.join(over)
