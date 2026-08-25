# -*- coding: utf-8 -*-
"""Apply manual price corrections, last in the pipeline.

Two jobs: carry the client's returned "Prix corrigé" column into the build, and
correct defects in the store's own data. Runs after the split so it can target a
piece that only exists once a set has been broken up.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))

def main():
    src = os.path.join(HERE, 'price-overrides.json')
    if not os.path.exists(src):
        print('no price-overrides.json — nothing to apply'); return
    spec = json.load(open(src, encoding='utf-8')).get('overrides', [])
    cat = json.load(open(os.path.join(HERE, 'catalogue.json'), encoding='utf-8'))

    applied, missed = [], []
    for o in spec:
        hits = [p for p in cat
                if (o.get('name') and p['name_fr'] == o['name'])
                or (o.get('sku') and p.get('sku') == o['sku'])]
        if not hits:
            missed.append(o); continue
        for p in hits:
            was = p['price']
            new = round(float(o['price']), 2)
            p['price'] = new
            p['price_max'] = max(new, p.get('price_max') or new)
            p['monthly'] = round(new / 36) if new else 0
            if p.get('compare') and p['compare'] <= new:
                p['compare'] = None
            for v in p.get('variants', []):
                if not v.get('accessory'):
                    v['price'] = new
            applied.append((p['name_fr'], was, new, o.get('reason', '')))

    json.dump(cat, open(os.path.join(HERE, 'catalogue.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(f'{len(applied)} override(s) applied, {len(missed)} unmatched')
    for n, was, new, why in applied:
        print(f'  {n[:34]:34} {was:9.2f} -> {new:9.2f}')
        print(f'      {why[:110]}')
    for o in missed:
        print(f'  UNMATCHED: {o.get("name") or o.get("sku")} — check the name still exists after the split')

if __name__ == '__main__':
    main()
