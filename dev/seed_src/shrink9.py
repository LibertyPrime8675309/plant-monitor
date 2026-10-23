import os as _os
REPO = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))  # repository root
import os, re, sys, time
from PIL import Image, ImageOps
SRC = '/mnt/user-data/uploads/Plants/Plant Database New Pics'; DST = REPO + '/dev/photos-raw/raw9'
done = 0
for f in sorted(os.listdir(SRC)):
    m = re.match(r'(P-\d{3})(?: \((\d+)\))?\.jpg$', f)
    if not m: continue
    out = f"{DST}/{m[1]}_{m[2] or '1'}.jpg"
    try:
        im = ImageOps.exif_transpose(Image.open(f'{SRC}/{f}')).convert('RGB')
    except Exception as e:
        print('not ready', f, e); continue
    im.thumbnail((1600, 1600)); im.save(out, 'JPEG', quality=85)
    os.remove(f'{SRC}/{f}'); done += 1
print(done, 'shrunk;', len(os.listdir(DST)), 'total')
