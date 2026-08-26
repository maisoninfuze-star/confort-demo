# -*- coding: utf-8 -*-
"""Give each split piece the photograph of that piece.

Splitting a set gave every piece the parent's whole gallery, so each one opened
on whichever image happened to be first — a $210 nightstand showing a dresser.
image-map.json records which image actually shows which piece, read off contact
sheets by eye, because the galleries are not in a consistent order.

Pieces with no entry have no photo of their own anywhere in the gallery. They
are marked so the page can say the picture is of the whole set rather than
implying it is the piece.
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
            if x is ps[0]:
                continue                       # the parent keeps the set shot
            idx = m.get(x['sub'])
            imgs = x.get('images') or []
            if idx is not None and idx < len(imgs):
                x['images'] = [imgs[idx]] + [u for i, u in enumerate(imgs) if i != idx]
                x['set_photo'] = False
                fixed += 1
            else:
                # no photograph of this piece exists in the gallery
                x['set_photo'] = True
                flagged += 1

    json.dump(cat, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{fixed} pieces given their own photo, {flagged} still showing the set shot')

if __name__ == '__main__':
    main()
