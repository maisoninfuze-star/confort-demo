# -*- coding: utf-8 -*-
"""Record the aspect ratio of every product's primary photograph into
catalogue.json, so the grid can fit the photography instead of cropping it.

The catalogue is shot mostly landscape around 1.4, but a handful of pieces
(bookcases, floor lamps) are portrait. One fixed card ratio either crops the
landscape shots or guts the portrait ones — knowing each ratio lets the card
decide per product.
"""
import json, os, io, urllib.request, concurrent.futures as cf
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
UA = {'User-Agent': 'Mozilla/5.0 (compatible; MCS-build/1.0)'}

def ratio(url):
    try:
        u = url + ('&' if '?' in url else '?') + 'width=400'
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25) as r:
            im = Image.open(io.BytesIO(r.read()))
        return round(im.width / im.height, 3)
    except Exception:
        return None

def main():
    p = os.path.join(HERE, 'catalogue.json')
    cat = json.load(open(p, encoding='utf-8'))
    todo = [(i, x['images'][0]) for i, x in enumerate(cat) if x.get('images')]
    print(f'measuring {len(todo)} primary photos')
    with cf.ThreadPoolExecutor(10) as ex:
        for (i, _), ar in zip(todo, ex.map(lambda t: ratio(t[1]), todo)):
            cat[i]['img_ar'] = ar
    json.dump(cat, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    got = [x['img_ar'] for x in cat if x.get('img_ar')]
    got.sort()
    wide = sum(1 for a in got if a > 1.75)
    tall = sum(1 for a in got if a < 1.15)
    print(f'  measured {len(got)}/{len(cat)}   median {got[len(got)//2]}')
    print(f'  outside the 1.15–1.75 band: {tall} portrait, {wide} very wide '
          f'({(tall+wide)*100//max(len(got),1)}%) — these get contain, not cover')

if __name__ == '__main__':
    main()
