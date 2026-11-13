"""Pictures of the options on proto/import-and-cards (November 13, 2026), as one gallery page:
  item 12 of the November 12 review: plant updates that arrive as a file Ethan brings in (three layouts, and the page before and after);
  the watering cards on Today using less of the screen (four ways), each beside the cards as they are now.
Start the mock server first (never a real record: preview_spots.py moves plants onto made-up spots), then:
    python3 dev/test/shots_preview.py OUTDIR [keys]
Writes OUTDIR/gallery/index.html and OUTDIR/gallery/data/*.json (see build_gallery.py). The options are switched on from
localStorage "plantdb.preview" (app/static/js/preview.js); the app is as it was without it. Run again with a key to retake one option."""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[1]); os.makedirs(OUT, exist_ok=True)
ALL = 'pc1440,pc1080,ipad6p,s21u'
# key, title, the page it is a picture of, the option (plantdb.preview), where the picture starts, devices, is there a page as it is now, what to look at
OPTIONS = [
    ('upd-a', 'Updates from a file, A: every plant on one page', 'updates', {'updates': 'plant'}, '', ALL, False,
     'Each plant in the file has its picture and its changes. A change says what the page says now, what it would say, and why. Everything is ticked to begin with, so if you agree you press one button, and you untick what you do not want. A change that needs your decision is marked, and stays as it is unless you choose Claude\'s.'),
    ('upd-b', 'Updates from a file, B: one plant at a time', 'updates', {'updates': 'walk', 'updstep': 3}, '', ALL, False,
     'Like the health walk-through: one plant at a time with a large picture, and "Accept and go on" or "Skip this plant". It takes more presses, but nothing is passed over, and it suits a phone. The picture is the third plant of eleven.'),
    ('upd-c', 'Updates from a file, C: a short list by kind of change', 'updates', {'updates': 'kind'}, '', ALL, False,
     'The shortest: one line for each change, grouped by kind (corrections, new pages, plants to archive, questions for you), with what needs your decision first. The reason is behind "Why".'),
    ('upd-start', 'Updates from a file: choosing the file (the same in A, B and C)', 'updates', {'updates': 'plant', 'updstate': 'start'}, '', ALL, False,
     'Before a file is chosen. Claude saves one small file on your computer and tells you its name; you choose it here. Nothing about your plants goes into the public code, and the files you brought in before are listed.'),
    ('upd-done', 'Updates from a file: after the changes are made (the same in A, B and C)', 'updates', {'updates': 'plant', 'updstate': 'done'}, '', ALL, False,
     'After you press the button: what was changed, where it is recorded, and how to take a change back.'),
    ('water-1', 'Watering cards, 1: one run of cards, a tile for each spot', 'today', {'water': 'flow'}, '#today-water', ALL, True,
     'The same buttons as now on every card, in one run in place of a box for each spot. A tile marks where a spot starts and holds its "Watered all here" button. The code sits beside the name, and pressing how late a plant is opens the reason, so the separate "Why" line is gone. On a wide screen the cards are wider, so the two buttons sit side by side and the picture is larger. On a phone a spot\'s tile is a full row, and one list goes to a spot in place of a button for each.'),
    ('water-2', 'Watering cards, 2: each spot in its box, small spots side by side', 'today', {'water': 'boxes'}, '#today-water', ALL, True,
     'The same cards as option 1, with each spot still in a box of its own. Spots with few plants share a row on a wide screen. It saves less than option 1.'),
    ('water-3', 'Watering cards, 3: tick the pictures, one bar of buttons', 'today', {'water': 'tick', 'ticked': 3}, '#today-water', ALL, True,
     'One run with tiles, as in option 1, but a card has no buttons of its own: press a picture to tick it, and "Watered" and "Still moist" for everything ticked stay at the bottom of the screen. Three are ticked in the picture. Each spot keeps "Watered all here".'),
    ('water-4', 'Watering cards, 4: a strip of pictures for each spot', 'today', {'water': 'spots'}, '#today-water', ALL, True,
     'Each spot is one row: its name, how late its plants are, its one button and a strip of pictures without names. The plants open into cards with their names and buttons on request, and a picture opens that plant\'s page. The shortest, but you read a name only after opening a spot.'),
]
TEXT = {
    'title': 'Plant record: options for updates from a file, and for tighter watering cards',
    'intro': 'Two sets of options. First, how updates from Claude would arrive as a file you bring in (item 12 of the November 12 review): three layouts for the page that shows the changes, and the page before and after. Second, four ways for the watering cards on Today to take less of the screen while keeping the pictures, each beside the cards as they are now. Nothing here is in the app yet: say which you want, or what to change, and that is what gets built. Choose an option, a device and the settings below. Press a picture to see it larger.',
    'notes': ['A pink dashed line marks where each screenful ends, so you can see how much fits before you scroll.',
              'The changes in the update pictures are made up to show every kind of change. They are not corrections I am proposing.',
              os.environ.get('GALLERY_SPOTS_NOTE') or 'The pictures use the test record (101 plants) with made-up spots such as "Black bench". On your PC the spots are your own, and several hold more plants than these.',
              'The watering pictures start at the Water part of Today. Their first screenful is the screen as it would be there.',
              'Long pages stop after three screens in the pictures.'],
    'new': 'Option', 'old': 'As it is now', 'beside': 'Show the page as it is now beside it', 'page_word': 'Option', 'every': 'Every option', 'first': '*',
    'count_note': '. The watering options have the page as it is now beside them.',
    'about': {o[0]: o[7] for o in OPTIONS}, 'order': [o[0] for o in OPTIONS],
}
# The watering pictures can come from a second mock server (SHOTS_URL_WATER), one whose plants sit on spots laid out like the owner's own.
URL = os.environ.get('SHOTS_URL', 'http://127.0.0.1:8080'); URL_WATER = os.environ.get('SHOTS_URL_WATER', URL)
def shots(out, key, title, page, devices, pv, frm):
    env = dict(os.environ, SHOTS_URL=URL_WATER if page == 'today' else URL, SHOTS_AS=f'{key}={title}', SHOTS_SCREENS=os.environ.get('SHOTS_SCREENS', '3'), SHOTS_FROM=frm, SHOTS_PREVIEW=json.dumps(pv) if pv else '')
    subprocess.run([sys.executable, os.path.join(HERE, 'shots_all.py'), out, devices, 'usual,largest', page], check=True, env=env)
def same(out, key0, key, title):         # the page as it is now is one picture for every option of that page: taken once, then copied
    import shutil
    ix = json.load(open(os.path.join(out, 'index.json')))
    for name, v in list(ix['shots'].items()):
        if v['page'] != key0: continue
        new = name.replace(key0 + '__', key + '__', 1); shutil.copyfile(os.path.join(out, name), os.path.join(out, new)); ix['shots'][new] = dict(v, page=key)
    ix['pages'][key] = title; json.dump(ix, open(os.path.join(out, 'index.json'), 'w'), indent=0)
only = sys.argv[2].split(',') if len(sys.argv) > 2 else None
if not only and URL_WATER == URL: subprocess.run([sys.executable, os.path.join(HERE, 'preview_spots.py'), URL], check=True)
taken = {}
for key, title, page, pv, frm, devices, now, _ in OPTIONS:
    if only and key not in only: continue
    shots(os.path.join(OUT, 'after'), key, title, page, devices, pv, frm)
    if now:
        if (page, frm, devices) in taken: same(os.path.join(OUT, 'before'), taken[(page, frm, devices)], key, title)
        else: shots(os.path.join(OUT, 'before'), key, title, page, devices, None, frm); taken[(page, frm, devices)] = key
    print('done', key, flush=True)
json.dump(TEXT, open(os.path.join(OUT, 'text.json'), 'w'), indent=1)
before = os.path.join(OUT, 'before')
subprocess.run([sys.executable, os.path.join(HERE, 'build_gallery.py'), os.path.join(OUT, 'gallery'), os.path.join(OUT, 'after')] + ([before] if os.path.isdir(before) else []),
               check=True, env=dict(os.environ, GALLERY_TEXT=os.path.join(OUT, 'text.json')))
