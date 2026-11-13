"""Pictures of finished pages, each beside the page as it was, as one gallery page (November 13, 2026: pull requests 125 and 126).
Two mock servers, never a real record: one from this folder, one from a copy of the code as it was
(`git worktree add /tmp/wt-before <commit>`, started there with PORT=8180 PLANTDB_TS_PORT=8181 PLANTDB_SENSOR_PORT=8182
MOCK_VISION_PORT=8190 and its own DATA_DIR). Put the test plants on spots in both first (preview_spots.py URL).
    python3 dev/test/shots_finished.py OUTDIR AFTER_URL BEFORE_URL [keys]
Writes OUTDIR/gallery/index.html and OUTDIR/gallery/data/*.json (see build_gallery.py). PAGES and TEXT below are that day's: change
them for the next one. A part of Today that only shows in warm weather (the feeding question) needs servers started with
MOCK_BASE_F=65; the cold warning needs MOCK_BASE_F=40. Run again with a key to retake one page: the gallery is rebuilt from all of them."""
import json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.abspath(sys.argv[1]); os.makedirs(OUT, exist_ok=True)
AFTER, BEFORE = sys.argv[2], sys.argv[3]
ALL = 'pc1440,pc1080,ipad6p,s21u'
# key, title, the page it is a picture of, where the picture starts, devices, what to look at
PAGES = [
    ('today-water', 'Today: watering by room and spot', 'today', '#today-water', ALL,
     'Your choice 9B. The plants to water are grouped by room and spot, as cards with a larger picture, the name and how late each one is. Each spot has one "Watered all here" button, and with three spots or more a row of buttons at the top goes straight to each one. The long reason is behind "Why". "Most overdue first" is the list as it was.'),
    ('today-ask', 'Today: the question about feeding reminders', 'today', '#today-unfed', ALL,
     'Today asks once whether you want reminders for plants with no feeding in the log. "Yes, remind me" starts counting that day; "No reminders for these" keeps Today quiet about them. Flushes and root checks have the same question. Before, these were folded parts that stayed every day.'),
    ('plants', 'All plants: one row of tools', 'plants', '', ALL,
     'Your choice 10A. The count sits beside the title, the winter plans are a list in the row of tools, the buttons share one row, and the cold warning is one line. On a phone only the search box stays out; the lists are in "More filters" and the buttons in "More to do here".'),
    ('plant', "A plant's page: care buttons under its name", 'plant', '', ALL,
     'Watered today and the other care buttons come straight after the name, with a short line on watering. All plants, Previous Plant, Next Plant, their filters and the layout switch share one row. Repotting, turning and pest lines have a box of their own at the top of the details.'),
    ('where', 'Rooms and spots: the order you walk', 'where', '', ALL,
     '"Move up" and "Move down" put rooms and spots in your own order. Today lists the spots in that order.'),
]
TEXT = {
    'title': 'Plant record: the finished pages for watering by place and the first screen',
    'intro': 'The pages as built from your choices on November 13, 2026 (9B, 10A, the plant page, the phone top bar and the feeding question), each beside the page as it was. They go out with the December 1 release. Choose a page, a device and the settings below. Press a picture to see it larger.',
    'notes': ['A pink dashed line marks where each screenful ends, so you can see how much fits before you scroll.',
              'The pictures use the test record (101 plants) with made-up spots such as "Black bench". On your PC the groups are your own rooms and spots; plants with no spot yet come last in their room.',
              'The watering picture starts at the Water part of Today, and the feeding picture at the question, not at the top of the page.',
              'The phone pictures show the top bar in one row.',
              'Long pages stop after three screens in the pictures.'],
    'new': 'Now', 'old': 'Before', 'beside': 'Show the page as it was beside it', 'page_word': 'Page', 'every': 'Every page', 'first': '*',
    'count_note': '. The page as it was is shown beside each one.',
    'about': {o[0]: o[5] for o in PAGES}, 'order': [o[0] for o in PAGES],
}
def shots(out, url, key, title, page, devices, frm):
    env = dict(os.environ, SHOTS_URL=url, SHOTS_AS=f'{key}={title}', SHOTS_SCREENS=os.environ.get('SHOTS_SCREENS', '3'), SHOTS_FROM=frm, SHOTS_PREVIEW='')
    subprocess.run([sys.executable, os.path.join(HERE, 'shots_all.py'), out, devices, 'usual,largest', page], check=True, env=env)
only = sys.argv[4].split(',') if len(sys.argv) > 4 else None
for key, title, page, frm, devices, _ in PAGES:
    if only and key not in only: continue
    shots(os.path.join(OUT, 'after'), AFTER, key, title, page, devices, frm)
    shots(os.path.join(OUT, 'before'), BEFORE, key, title, page, devices, frm)
    print('done', key, flush=True)
json.dump(TEXT, open(os.path.join(OUT, 'text.json'), 'w'), indent=1)
subprocess.run([sys.executable, os.path.join(HERE, 'build_gallery.py'), os.path.join(OUT, 'gallery'), os.path.join(OUT, 'after'), os.path.join(OUT, 'before')],
               check=True, env=dict(os.environ, GALLERY_TEXT=os.path.join(OUT, 'text.json')))
