# -*- coding: utf-8 -*-
"""Give each split piece the photograph of that piece.

image-map.json records which gallery image shows which piece, read by eye from
contact sheets of all 50 split sets — the galleries are in no consistent order,
and an automated backdrop test was wrong in both directions.

Two hard lessons encoded here:
- The mapping always reads from the ORIGINAL gallery order. This script once
  reordered galleries in place and was run twice, which shifted every mapping
  by one — nightstands became beds on 15 sets.
- The first product of a parentless group (a split with no set line) is a
  piece too, not a parent. It used to keep the set shot silently, with no
  label saying so.
"""
import json, os, collections

HERE = os.path.dirname(os.path.abspath(__file__))

def main():
    p = os.path.join(HERE, 'catalogue.json')
    cat = json.load(open(p, encoding='utf-8'))
    spec = json.load(open(os.path.join(HERE, 'image-map.json'), encoding='utf-8'))['map']

    byh = collections.defaultdict(list)
    for x in cat:
        byh[x.get('handle_old')].append(x)

    fixed = flagged = 0
    for h, ps in byh.items():
        if len(ps) < 2:
            continue
        m = spec.get(h, {})
        for x in ps:
            # idempotence: map from the gallery as it came from the store
            orig = x.get('orig_images') or list(x.get('images') or [])
            x['orig_images'] = orig
            if x['sub'].startswith('ensemble'):
                x['images'] = list(orig)          # the set keeps the set shot
                x['set_photo'] = False
                continue
            idx = m.get(x['sub'])
            if idx is not None and idx < len(orig):
                x['images'] = [orig[idx]] + [u for i, u in enumerate(orig) if i != idx]
                x['set_photo'] = False
                fixed += 1
            else:
                x['images'] = list(orig)
                x['set_photo'] = True
                flagged += 1

    json.dump(cat, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{fixed} pieces given their own photo, {flagged} labelled as showing the set')

if __name__ == '__main__':
    main()
