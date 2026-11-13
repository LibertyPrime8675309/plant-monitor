"""Pictures of the layout options on proto/first-screen (November 12 review, items 9 and 10), each beside the page as it is now, as one
gallery page. Start the mock server first (never a real record: preview_spots.py moves plants onto made-up spots), then:
    python3 dev/test/shots_preview.py OUTDIR
Writes OUTDIR/gallery/index.html and OUTDIR/gallery/data/*.json (see build_gallery.py). The options are switched on from
localStorage "plantdb.preview" (app/static/js/preview.js); the app is as it was without it."""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[1]); os.makedirs(OUT, exist_ok=True)
ALL = 'pc1080,pc1440,ipad6p,s21u'
# key, title, the page it is a picture of, the option (plantdb.preview), where the picture starts, devices, what to look at
OPTIONS = [
    ('today-a', 'Watering list by place: rows', 'today', {'water': 'rows'}, '#today-water', ALL,
     'Item 9, option A. The plants to water are grouped by room and spot, in the order of Rooms and spots, with one "Watered all here" button for each spot. Each plant is one line: how late it is and what it last had. The long reason is behind "Why".'),
    ('today-b', 'Watering list by place: cards', 'today', {'water': 'cards'}, '#today-water', ALL,
     'Item 9, option B. The same groups and buttons, with each plant as a card with a larger picture, so you can know a plant by sight. It takes more room than the rows.'),
    ('plants-a', 'All plants: one row of tools', 'plants', {'plants': 'tools'}, '', ALL,
     'Item 10, option A. The count sits beside the title, the winter plans are a list in the row of tools, the buttons share one row, and the cold warning is one line. On a phone only the search box stays out; the lists and the buttons fold.'),
    ('plants-b', 'All plants: tools and winter-plan counts', 'plants', {'plants': 'chips'}, '', 'pc1080,pc1440',
     'Item 10, option B. As option A, but the five winter-plan counts stay in view as a row of small buttons. On a phone it is the same as option A.'),
    ('plant-a', "A plant's page: care buttons under its name", 'plant', {'plant': 'top'}, '', ALL,
     'Item 10. Watered today and the other care buttons come straight after the name, with a short line on watering. Previous and Next, their filters and the layout switch share one row, so the two halves are taller. Repotting, turning and pest lines stay in the details.'),
    ('bar-a', 'Phone: the top bar in one row', 'today', {'bar': 'one'}, '', 'ipad6p,s21u',
     'Item 10. The page menu, search and More share one row; "Plant record" and the version move into More. At the largest text search and More take a second row.'),
    ('phone-all', 'Phone: all of it together on All plants', 'plants', {'plants': 'tools', 'bar': 'one'}, '', 'ipad6p,s21u',
     'The one-row top bar, the one-line cold warning and the row of tools at once, to show how far down the first plant now is.'),
]
TEXT = {
    'title': 'Plant record: layout options for watering by place and the first screen',
    'intro': 'Options for items 9 and 10 of the November 12 review, each beside the page as it is now (1.57.0 with the changes merged for December). Nothing here is in the app yet: say which you want, or what to change, and that is what gets built. Choose an option, a device and the settings below. Press a picture to see it large.',
    'notes': ['A pink dashed line marks where each screenful ends, so you can see how much fits before you scroll.',
              'The pictures use the test record (101 plants) with made-up spots such as "Black bench". On your PC the groups are your own rooms and spots; plants with no spot yet come last in their room.',
              'The watering pictures start at the Water part of Today, not at the top of the page.',
              'Long pages stop after three screens in the pictures.'],
    'new': 'Option', 'old': 'As it is now', 'beside': 'Show the page as it is now beside it', 'page_word': 'Option', 'every': 'Every option', 'first': '*',
    'count_note': '. The page as it is now is shown beside each option.',
    'about': {o[0]: o[6] for o in OPTIONS}, 'order': [o[0] for o in OPTIONS],
}
def shots(out, key, title, page, devices, pv, frm):
    env = dict(os.environ, SHOTS_AS=f'{key}={title}', SHOTS_SCREENS=os.environ.get('SHOTS_SCREENS', '3'), SHOTS_FROM=frm, SHOTS_PREVIEW=json.dumps(pv) if pv else '')
    subprocess.run([sys.executable, os.path.join(HERE, 'shots_all.py'), out, devices, 'usual,largest', page], check=True, env=env)
subprocess.run([sys.executable, os.path.join(HERE, 'preview_spots.py')], check=True)
only = sys.argv[2].split(',') if len(sys.argv) > 2 else None
for key, title, page, pv, frm, devices, _ in OPTIONS:
    if only and key not in only: continue
    shots(os.path.join(OUT, 'after'), key, title, page, devices, pv, frm)
    shots(os.path.join(OUT, 'before'), key, title, page, devices, None, frm)
json.dump(TEXT, open(os.path.join(OUT, 'text.json'), 'w'), indent=1)
subprocess.run([sys.executable, os.path.join(HERE, 'build_gallery.py'), os.path.join(OUT, 'gallery'), os.path.join(OUT, 'after'), os.path.join(OUT, 'before')],
               check=True, env=dict(os.environ, GALLERY_TEXT=os.path.join(OUT, 'text.json')))
