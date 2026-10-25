"""Build app/seed/batches/batchA3.json and app/static/lights/*.jpg: Ethan's grow lights (1.13.0).

Read from the product photos and spec screenshots Ethan saved in Plants\\Grow Lights on October 24, 2026 (one folder per
light, with the count in the folder name or his message). PPFD figures are the makers' own, at the centre under the light;
'estimated' marks figures Claude worked out because the maker gives none.
Run: python3 dev/seed_src/build_batchA3.py <folder with the Grow Lights subfolders>"""
import json, os, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT_IMG = os.path.join(ROOT, 'app', 'static', 'lights')
SPEC = lambda b, g, r, fr: {'blue': b, 'green': g, 'red': r, 'far_red': fr}

LIGHTS = [
    dict(key='sansi-80w', name='SANSI 80 W folding bulb', count=1, kind='Bulb (E26 screw-in, 4 folding wings)', brand='SANSI', watts=80,
         lumens=8000, kelvin=4000, cri='97+', spectrum=SPEC(18.0, 33.1, 40.42, 8.48), direction='down',
         ppfd=[[12, 720.9, 3.0], [24, 331.3, 8.7], [36, 163.3, 17.0], [48, 94.6, 29.1]],
         power='Screws into an E26 socket (120 V); the cord or fixture is not included', needs_socket=True,
         timer='Remote: 4, 8 or 12 hours. Settings are lost after a power cut.', timer_hours=[4, 8, 12], timer_repeats=True,
         dimming=[25, 50, 75, 100], size='17 in across with the wings open', url='https://www.amazon.com/dp/B0FHQ953HT',
         photo=('SANSI 80 W bulb', '71BqTp8hlqL', 'The SANSI 80 W bulb seen from below: four wings of three round LED pods each, 17 inches across'),
         chart=('SANSI 80 W bulb', '81ybtMy6pUL', "Maker's chart: PPFD 720.9 at 1 ft, 331.3 at 2 ft, 163.3 at 3 ft and 94.6 at 4 ft")),
    dict(key='sansi-tripod', name='SANSI tripod floor light (88 LEDs)', count=1, kind='Floor stand with a gooseneck head', brand='SANSI', watts=45,
         lumens=4283, kelvin=4000, cri='95', spectrum=SPEC(19, 35.23, 39.25, 6.47), direction='down',
         ppfd=[[12, 719.41, 0.54], [24, 233.57, 1.51], [36, 106.4, 2.26], [48, 52.39, 5.06]],
         power='Plugs into an outlet; 58 in cord', timer='Remote: 4, 8 or 12 hours. Reset the timer after a power cut.', timer_hours=[4, 8, 12],
         timer_repeats=True, dimming=[25, 50, 75, 100], size='Stand 33 to 58 in tall; head 4 by 5 in, turns 330°', url='https://www.amazon.com/dp/B0FHW28D6L',
         photo=('SANSI tripod', '71SXhis+IJL', 'The SANSI tripod light: a black telescopic tripod stand with a gooseneck and a small square LED panel on top'),
         chart=('SANSI tripod', '71xJ2ipY36L', "Maker's chart: PPFD 719.41 at 1 ft, 233.57 at 2 ft, 106.4 at 3 ft and 52.39 at 4 ft")),
    dict(key='sansi-gooseneck', name='SANSI 4-head gooseneck clamp light', count=1, kind='Clamp light with four gooseneck heads', brand='SANSI', watts=40,
         kelvin=4000, cri='95', spectrum=SPEC(18.0, 33.1, 40.42, 8.48), direction='down',
         ppfd=[[6, 2496, 0.3], [12, 804, 0.8], [18, 480, 1.6]], area_estimated=True,
         power='Plugs into an outlet; 6 ft cord. Each head holds a replaceable 10 W PAR20 bulb (E26, 10 W at most).',
         timer='On/off switch only, no timer', timer_hours=[], timer_repeats=False, dimming=[100],
         size='Goosenecks 15.8 in; clamp opens about 2 in', url='https://www.amazon.com/dp/B09NVGNYNH',
         ppfd_note="The maker's figures are with all four heads aimed at one spot, and look generous next to SANSI's own 10 W bulb figures. Aim the heads apart to light more plants, less brightly.",
         photo=('SANSI 4-head gooseneck clamp', '71z+BpdYyDL', 'The SANSI gooseneck light: a black clamp with four long goosenecks, each ending in a white bulb'),
         chart=('SANSI 4-head gooseneck clamp', '71xIVwYVdNL', "Maker's chart: PPFD 2496 at 6 in, 804 at 12 in and 480 at 18 in")),
    dict(key='sansi-30w', name='SANSI 30 W bulb (PAR25)', count=2, kind='Bulb (E26 screw-in)', brand='SANSI', watts=30, lumens=3000, kelvin=5000,
         cri='over 80', spectrum=SPEC(17.65, 35.55, 40.07, 6.73), direction='down', beam='60°',
         ppfd=[[12, 336, 0.75], [24, 99, 2.9], [36, 44, 6.6], [48, 24, 11.6]],
         power='Screws into an E26 socket (120 V). Not dimmable.', needs_socket=True, timer='None of its own', timer_hours=[], timer_repeats=False,
         dimming=[100], size='3.1 in across, 4.5 in long', url='https://www.amazon.com/dp/B0D2HK8756',
         ppfd_note='40 white and 10 deep red (660 nm) LEDs. One line of the listing says 220 PPFD at 1 ft; its chart and text say 336.',
         photo=('SANSI 30W Bulb', '71-jQNZgE1L', 'The SANSI 30 W bulb: a white finned PAR25 bulb with a screw base'),
         chart=('SANSI 30W Bulb', '71uPc4wSYDL', "Maker's chart: PPFD 336 at 1 ft, 99 at 2 ft, 44 at 3 ft and 24 at 4 ft, in a 60 degree beam")),
    dict(key='barrina-standing', name='Barrina 2 ft standing light', count=1, kind='Upright tube on a base (lights sideways)', brand='Barrina', watts=20,
         cri='89', direction='side', ppfd=[[7.87, 129.14, 1.0], [11.81, 80.19, 1.5], [15.75, 39.38, 2.0]], area_estimated=True,
         power='Plugs into an outlet; 4.9 ft cord with an on/off switch', timer='None', timer_hours=[], timer_repeats=False, dimming=[100],
         size='24 in tall tube on a 5 in base; can also hang (2 clips)', url='https://www.amazon.com/dp/B0CKXMCB6J',
         ppfd_note='Measured sideways from the tube. Warm white with deep red (660 nm) LEDs, up to 75 LEDs.',
         photo=('Barrina standing light, 2 ft', '61cocdxO0kL', 'The Barrina standing light: a 24 inch clear tube of LEDs standing upright on a round black base'),
         chart=('Barrina standing light, 2 ft', '71W5IW3nqFL', "Maker's chart: PPFD 129.14 at 7.87 in, 80.19 at 11.81 in and 39.38 at 15.75 in to the side")),
    dict(key='gooingtop-clip', name='GooingTop 2-bar clip light', count=2, kind='Clamp light with two LED bars', brand='GooingTop', watts=10,
         kelvin=6000, cri='95', direction='down', ppfd=[[6, 60, 1.0], [12, 25, 2.0]], estimated=True,
         power='USB or plug-in adapter', timer='Repeats every day: 4, 8 or 12 hours on', timer_hours=[4, 8, 12], timer_repeats=True, dimming=[50, 100],
         url='https://www.amazon.com/dp/B085CDPSMR', ppfd_note='The maker gives no PPFD. These are Claude\'s estimates for about 10 W of LEDs (74 white, 10 red).',
         photo=('GooingTop clip', '818mUZwqTTL', 'The GooingTop light: two black LED bars on goosenecks from one clamp, with its timer controller')),
    dict(key='sansi-10w', name='SANSI 10 W bulb (PAR20)', count=6, kind='Bulb (E26 screw-in)', brand='SANSI', watts=10, kelvin=4000, cri='about 98',
         spectrum=SPEC(15.45, 34.15, 41.96, 8.44), direction='down', beam='60°',
         ppfd=[[12, 97.91, 1.1], [24, 24.48, 4.4], [36, 10.88, 9.9], [48, 6.12, 17.5]],
         power='Screws into an E26 socket (90 to 132 V)', needs_socket=True, timer='None of its own', timer_hours=[], timer_repeats=False, dimming=[100],
         url='https://www.amazon.com/dp/B0BZNJC3Z4', ppfd_note='PPF 16.8 µmol/s per bulb.',
         photo=('SANSI 10 W bulbs (6)', '71lE11Xg-fL', 'The SANSI 10 W bulb taken apart: lens, a ring of LED chips, ceramic board, finned body and screw base'),
         chart=('SANSI 10 W bulbs (6)', '61g0exPGkAL', "Maker's chart: PPFD 97.91 at 1 ft, 24.48 at 2 ft, 10.88 at 3 ft and 6.12 at 4 ft, in a 60 degree beam")),
    dict(key='barrina-t5', name='Barrina 1 ft T5 strips, bank of 4', count=2, kind='Strip lights: 8 strips, used as 2 banks of 4', brand='Barrina',
         watts=20, lumens=1600, kelvin=5000, cri='98', direction='down', ppfd=[[6, 170, 1.0], [12, 90, 2.0], [18, 48, 3.2]], estimated=True,
         power='Plugs into an outlet; 4 cords with switches and 7 linking cables for the 8 strips (5 W each)', timer='On/off switch on each strip, no timer',
         timer_hours=[], timer_repeats=False, dimming=[100], size='Each strip 1 ft long, black; magnets, clips or cable ties',
         url='https://www.amazon.com/dp/B0CHRMZC3F', ppfd_note="The maker gives no PPFD, only heights: 12 to 14 in for leafy growth, 8 to 12 in for flowering, strips about 4 in apart. These are Claude's estimates for a bank of four strips 4 in apart under a shelf; one strip alone gives roughly a third as much.",
         photo=('Barrina T5 strips, 1 ft (8)', '71atFgoIKnL', 'Two black Barrina T5 strips mounted under a shelf, each with its own on/off switch, over a begonia'),
         chart=('Barrina T5 strips, 1 ft (8)', '71zaGQ7M1AL', "Maker's height guide: 11.8 to 13.8 in for seedlings and leafy growth, 7.9 to 11.8 in for flowering, strips 3.93 in apart")),
    dict(key='sansi-t8', name='SANSI 2 ft T8 strip set', count=1, kind='Strip lights', brand='SANSI', kelvin=4000, cri='96',
         spectrum=SPEC(16.65, 33.84, 42.33, 7.17), direction='down', ppfd=[[12, 37.9, 5.49], [24, 12.1, 10.87], [36, 5.7, 16.68], [48, 3.3, 21.74]],
         power='Plugs into an outlet; 6 ft cord. Splash-proof (IP54).', timer='Repeats every day: 4, 8 or 12 hours on', timer_hours=[4, 8, 12],
         timer_repeats=True, dimming=[25, 50, 75, 100], url='https://www.amazon.com/dp/B0DGGD81DQ',
         ppfd_note="The maker's figures. Claude does not know yet how many strips the set has or their watts.",
         photo=('SANSI T8 strips, 2 ft', '81-YVshOgUL', 'A SANSI T8 strip lit up under a shelf, with water spraying on it to show it is splash-proof'),
         chart=('SANSI T8 strips, 2 ft', '71VvuBmSGkL', "Maker's chart: PPFD 37.9 at 1 ft, 12.1 at 2 ft, 5.7 at 3 ft and 3.3 at 4 ft")),
    dict(key='sansi-pot-clip', name='SANSI pot clip light', count=3, kind='Small light that clips to a pot', brand='SANSI', watts=5, kelvin=4000,
         cri='95', spectrum=SPEC(16.65, 33.84, 42.33, 7.17), direction='down', ppfd=[[6, 35.78, 1.0]], area_estimated=True,
         power='USB (5 V): a phone charger, power bank or computer; 78.7 in cord', timer='Repeats every day: 3, 6 or 12 hours on',
         timer_hours=[3, 6, 12], timer_repeats=True, dimming=[25, 50, 75, 100], size='12.8 in gooseneck; clips onto a rim up to 0.8 in thick',
         url='https://www.amazon.com/dp/B0C2CQ2ZB6', ppfd_note='The maker gives one figure, 35.78 at 6 in.',
         photo=('SANSI pot clips (3)', '71VjNxHOjVL', 'The SANSI pot clip light: a small round white head on a white gooseneck, clipped to a square pot')),
    dict(key='disk-light', name='Commercial Electric disk light', count=1, kind='Ceiling disk light (a room light, not a grow light)', brand='Commercial Electric',
         watts=9.7, lumens=800, kelvin=3000, cri='90', direction='down', ppfd=[[12, 28, 3.0], [24, 8, 10.0], [36, 4, 20.0]], estimated=True,
         power='Wired in or on a lamp cord (120 V)', timer='None', timer_hours=[], timer_repeats=False, dimming=[10, 25, 50, 75, 100],
         ppfd_note="A room light, so there is no PPFD from the maker. Claude's estimate from its 800 lumens, warm white and wide beam: fine for plants that need little light, close up.",
         notes=''),
]

def photo_for(src, folder, stem, out, width):
    path = next((os.path.join(src, folder, f) for f in os.listdir(os.path.join(src, folder)) if f.startswith(stem)), None)
    if not path: raise SystemExit('missing photo %s/%s' % (folder, stem))
    im = Image.open(path).convert('RGB')
    if im.width > width: im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.save(os.path.join(OUT_IMG, out), 'JPEG', quality=80, optimize=True, progressive=True)
    return out

def main(src):
    os.makedirs(OUT_IMG, exist_ok=True)
    out = []
    for L in LIGHTS:
        L = dict(L)
        if 'photo' in L:
            folder, stem, alt = L.pop('photo'); L['photo'] = 'lights/' + photo_for(src, folder, stem, L['key'] + '.jpg', 640); L['photo_alt'] = alt
        if 'chart' in L:
            folder, stem, alt = L.pop('chart'); L['chart'] = 'lights/' + photo_for(src, folder, stem, L['key'] + '-chart.jpg', 1100); L['chart_alt'] = alt
        out.append(L)
    batch = {
        'id': 'batchA3', 'author': 'Claude (grow lights, Oct 24, 2026)',
        'lights_add': out,
        'requests_add': [
            {'key': 'lights-sockets', 'kind': 'question', 'text': 'Grow lights: which lamps or clamp sockets do the six SANSI 10 W bulbs, the two 30 W bulbs and the 80 W bulb screw into, and are any of the 10 W bulbs the ones in the 4-head gooseneck? Put it under "Where it is" on the Grow lights page, or tell Claude.'},
            {'key': 'lights-t8-set', 'kind': 'question', 'text': 'Grow lights: how many strips are in the SANSI 2 ft T8 set, and how many watts is each (on the strip or its box)?'},
            {'key': 'lights-disk', 'kind': 'question', 'text': 'Grow lights: where is the Commercial Electric disk light: in a ceiling, a lamp or under a shelf, and about how far above the plants?'},
            {'key': 'lights-spots', 'kind': 'question', 'text': 'Grow lights: where inside will the plants go (rooms, shelves, windows), and which of your lights are already set up there? The Grow lights page suggests a layout you can set up with one press each.'},
        ],
    }
    p = os.path.join(ROOT, 'app', 'seed', 'batches', 'batchA3.json')
    json.dump(batch, open(p, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
    print('wrote', p, len(out), 'lights;', len(os.listdir(OUT_IMG)), 'images,', sum(os.path.getsize(os.path.join(OUT_IMG, f)) for f in os.listdir(OUT_IMG)) // 1024, 'KB')

if __name__ == '__main__':
    main(sys.argv[1])
