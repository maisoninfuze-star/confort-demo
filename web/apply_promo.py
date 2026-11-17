# -*- coding: utf-8 -*-
"""Merge the IFDC Black Friday 2026 line-up into catalogue.json.

The flyer's "Reg" column is the dealer cost x2 — the store's own retail
formula, checked against supplier-cost.json on 15 items that matched exactly.
So "Special" is a RETAIL price, not a cost, and it goes on the page as-is:
`price` is the sale, `compare` is the regular. build.py folds TPS+TVQ into
both, and drops the sale the day the flyer expires.

Idempotent: every product it writes carries a `promo` block, and the ones it
wrote last time are removed before it writes again. Run it after the rest of
the pipeline, then build.
"""
import json, io, os, re, sys, urllib.request, concurrent.futures as cf
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROMO = 'bf2026'
ENDS = '2026-12-12'          # last day of the sale, inclusive
UA = {'User-Agent': 'Mozilla/5.0 (compatible; MCS-build/1.0)'}

SUB_LABEL = {
    'ensemble-manger': ('Ensembles de salle à manger', 'Dining sets'),
    'table-manger':    ('Tables de salle à manger', 'Dining tables'),
    'chaise':          ('Chaises', 'Chairs'),
    'lit':             ('Lits', 'Beds'),
    'lit-superpose':   ('Lits superposés', 'Bunk beds'),
    'ensemble-chambre':('Ensembles de chambre', 'Bedroom sets'),
    'decor':           ('Bancs', 'Benches'),
    'canape':          ('Canapés', 'Sofas'),
    'fauteuil':        ('Fauteuils', 'Armchairs'),
    'table-salon':     ('Tables de salon', 'Coffee tables'),
}
COLOUR = {'argent': ('Argent', 'Silver'), 'beige': ('Beige', 'Beige'),
          'blanc': ('Blanc', 'White'), 'bleu': ('Bleu', 'Blue'),
          'brun': ('Brun', 'Brown'), 'gris': ('Gris', 'Grey'),
          'noir': ('Noir', 'Black'), 'vert': ('Vert', 'Green')}
MATERIAL = {'bois': ('Bois', 'Wood'), 'boucle': ('Bouclé', 'Bouclé'),
            'cuir': ('Cuir', 'Leather'), 'marbre': ('Marbre', 'Marble'),
            'metal': ('Métal', 'Metal'), 'tissu': ('Tissu', 'Fabric'),
            'velours': ('Velours', 'Velvet'), 'verre': ('Verre', 'Glass')}
FEAT = {'convertible': ('Se convertit en lit', 'Converts to a bed'),
        'inclinable': ('Inclinable', 'Reclining'), 'led': ('Éclairage LED', 'LED lighting'),
        'rangement': ('Rangement', 'Storage'), 'usb': ('Prises USB', 'USB outlets')}

def ratio(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
            im = Image.open(io.BytesIO(r.read()))
        return round(im.width / im.height, 3)
    except Exception as e:
        return None

def facets(keys, table, field):
    out = []
    for k in keys:
        assert k in table, 'unknown %s key %r' % (field, k)
        out.append({'key': k, 'fr': table[k][0], 'en': table[k][1]})
    return out

def main():
    cat = json.load(io.open(os.path.join(HERE, 'catalogue.json'), encoding='utf-8'))
    defs = json.load(io.open(os.path.join(HERE, 'promo-bf2026.json'), encoding='utf-8'))

    before = len(cat)
    cat = [p for p in cat if (p.get('promo') or {}).get('id') != PROMO]
    dropped = before - len(cat)

    taken = {p['slug'] for p in cat} | {p['slug_en'] for p in cat}
    built = []
    for d in defs:
        assert d['slug'] not in taken and d['slug_en'] not in taken, \
            'slug collision: %s / %s' % (d['slug'], d['slug_en'])
        assert d['sub'] in SUB_LABEL, 'unmapped sub %r' % d['sub']
        assert d['price'] < d['was'], '%s: sale %.2f is not below reg %.2f' % (d['code'], d['price'], d['was'])

        sizes = d.get('sizes')
        if sizes:
            lead = min(s['price'] for s in sizes)
            assert abs(lead - d['price']) < 0.005, \
                '%s: product price %.2f is not the cheapest size %.2f' % (d['code'], d['price'], lead)
            variants = [{'id': '%s-%s-%d' % (PROMO, d['code'].replace(' ', ''), i),
                         'label': s['size'], 'price': s['price'], 'accessory': False,
                         'compare': None, 'available': False,
                         'colour': None, 'colour_en': None,
                         'size': s['size'], 'size_en': s['size_en']} for i, s in enumerate(sizes)]
            vsizes = [s['size'] for s in sizes]
            regular = {s['size']: s['was'] for s in sizes}
        else:
            variants = [{'id': '%s-%s-0' % (PROMO, d['code'].replace(' ', '')),
                         'label': d['name_fr'], 'price': d['price'], 'accessory': False,
                         'compare': None, 'available': False,
                         'colour': None, 'colour_en': None, 'size': None, 'size_en': None}]
            vsizes = []
            regular = {}

        p = {
            'id': 'bf-' + re.sub(r'[^a-z0-9]+', '-', d['code'].lower()).strip('-'),
            'sku': d['code'],
            'handle_old': None,
            'slug': d['slug'], 'slug_en': d['slug_en'],
            'name_fr': d['name_fr'], 'name_en': d['name_en'],
            'cat': d['cat'], 'sub': d['sub'],
            'sub_fr': SUB_LABEL[d['sub']][0], 'sub_en': SUB_LABEL[d['sub']][1],
            'price': d['price'], 'price_max': max([d['price']] + [s['price'] for s in (sizes or [])]),
            'compare': d['was'],
            'monthly': 0,
            # Nothing from this flyer is in the Montréal warehouse: it is a
            # supplier promotion, so every piece is ordered in.
            'available': False,
            'images': [d['image']],
            'body_fr': d['body_fr'], 'body_en': d['body_en'],
            'dims': d.get('dims'), 'seat_h': None,
            'colours': facets(d['colours'], COLOUR, 'colour'),
            'materials': facets(d['materials'], MATERIAL, 'material'),
            'feats': facets(d['feats'], FEAT, 'feat'),
            'variant_colours': [], 'variant_sizes': vsizes,
            'variants': variants,
            'fit': None, 'img_ar': None,
            'set_photo': bool(d.get('set_photo')),
            'promo': {'id': PROMO, 'ends': ENDS,
                      'regular': d['was'], 'sale': d['price'],
                      'regular_by_size': regular},
        }
        built.append(p)

    print('measuring %d supplier photos' % len(built))
    with cf.ThreadPoolExecutor(8) as ex:
        for p, ar in zip(built, ex.map(lambda x: ratio(x['images'][0]), built)):
            p['img_ar'] = ar
    bad = [p['sku'] for p in built if not p['img_ar']]
    assert not bad, 'photo would not load for: %s' % ', '.join(bad)

    cat.extend(built)

    # IF-9027 is already on the site as "Drift". The flyer prices it too, so it
    # gets the sale rather than a duplicate page.
    drift = next((p for p in cat if p['slug'] == 'drift'), None)
    assert drift, 'Drift (IF-9027) is gone from the catalogue — check before pricing it'
    drift['price'] = 1799.00
    drift['compare'] = 2000.00
    for v in drift['variants']:
        v['price'] = 1799.00
        v['compare'] = None
    drift['price_max'] = 1799.00
    drift['promo'] = {'id': PROMO, 'ends': ENDS, 'regular': 2000.00,
                      'sale': 1799.00, 'regular_by_size': {}}

    json.dump(cat, io.open(os.path.join(HERE, 'catalogue.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('removed %d previous %s products, added %d, repriced Drift (IF-9027)'
          % (dropped, PROMO, len(built)))
    print('catalogue is now %d products' % len(cat))
    for p in sorted(built, key=lambda x: (x['cat'], x['sub'], x['sku'])):
        print('  %-16s %-46s %8.2f  was %8.2f   ar %.2f'
              % (p['sku'], p['name_fr'][:46], p['price'], p['compare'], p['img_ar']))

if __name__ == '__main__':
    main()
