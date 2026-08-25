# -*- coding: utf-8 -*-
"""Apply the supplier price list as RETAIL prices.

The spreadsheet's column is headed "Cost", but the client confirms these are
their selling prices, margin already included. So they are written straight to
the catalogue and to the supplier index as retail.

Every change is reported before it ships — a price list applied to the wrong
column silently halves a catalogue, and that is not something to discover from
a customer.
"""
import json, os, re, openpyxl, collections

HERE = os.path.dirname(os.path.abspath(__file__))
XLSX = os.path.expanduser(
    '~/Downloads/supplier 2026 Price List-New Items + New Additions (v3) 03.03.26 (R).xlsx')

def norm(s):
    return re.sub(r'[^A-Z0-9]', '', (s or '').upper())

SIZE = [('king', 'KING'), ('78"', 'KING'),
        ('queen', 'QUEEN'), ('60"', 'QUEEN'),
        ('double', 'DOUBLE'), ('full', 'DOUBLE'), ('54"', 'DOUBLE'),
        ('twin', 'SIMPLE'), ('single', 'SIMPLE'), ('39"', 'SIMPLE')]

def size_of(text):
    t = (text or '').lower()
    for needle, tag in SIZE:
        if needle in t:
            return tag
    return None

def read_list():
    ws = openpyxl.load_workbook(XLSX, data_only=True)['R']
    rows, item = [], None
    for r in ws.iter_rows(min_row=2, values_only=True):
        it, desc, _cat, _pcs, price = (list(r) + [None] * 5)[:5]
        if it and str(it).strip():
            item = str(it).strip()
        if price is None or not item:
            continue
        try:
            p = float(price)
        except (TypeError, ValueError):
            continue
        if p <= 0:
            continue
        m = re.match(r'^([A-Za-z]+[\s-]?[0-9]+[A-Za-z0-9\-/]*)', item)
        if not m:
            continue
        rows.append({'key': norm(m.group(1)), 'item': item,
                     'desc': str(desc).strip() if desc else '',
                     'price': p, 'size': size_of(desc)})
    by = collections.defaultdict(list)
    for r in rows:
        by[r['key']].append(r)
    return by

SET_RX = re.compile(r'\b(\d+\s*pc|piece|set|ensemble|dinette)\b', re.I)
# A dining set is often only identifiable from the French copy or from the two
# codes paired in the title — "T-1448 C-1263", "Table : … Chaises : …".
PAIR_RX = re.compile(r'\bT[\s-]?\d{3,4}\b\W{0,4}\bC[\s-]?\d{3,4}\b', re.I)

def looks_like_set(hay):
    if SET_RX.search(hay) or PAIR_RX.search(hay):
        return True
    return bool(re.search(r'\btables?\b', hay, re.I)
                and re.search(r'\bchaises?\b|\bchairs?\b', hay, re.I))

def pick(entries, product):
    """A code can carry several lines: Double / Queen / King, and "Table Only"
    beside "7pc Dining Set". Match what the product actually is — pricing a
    seven-piece set off the table-only line is how a $1,600 set becomes $170."""
    hay = ' '.join([product.get('name_fr', ''), product.get('sub_fr', ''),
                    product.get('body_fr', '')[:500]])
    is_set = looks_like_set(hay) or product.get('sub') in ('ensemble-manger',
                                                           'ensemble-chambre')
    pool = entries
    if is_set:
        sets = [e for e in entries if SET_RX.search(e['desc'])]
        if sets:
            pool = sets
    else:
        singles = [e for e in entries if not SET_RX.search(e['desc'])]
        if singles:
            pool = singles

    sizes = {s.upper() for s in (product.get('variant_sizes') or [])}
    want = size_of(hay) or (list(sizes)[0] if sizes else None)
    if want:
        hit = [e for e in pool if e['size'] == want]
        if hit:
            return min(hit, key=lambda e: e['price'])
    return min(pool, key=lambda e: e['price'])

def main():
    by = read_list()
    cat = json.load(open(os.path.join(HERE, 'catalogue.json'), encoding='utf-8'))
    changes, unmatched = [], 0
    for p in cat:
        if not p.get('sku'):
            unmatched += 1; continue
        k = norm(p['sku'])
        if k not in by:
            unmatched += 1; continue
        row = pick(by[k], p)
        old = p['price']
        new = round(row['price'], 2)
        if abs(new - old) > 0.005:
            changes.append((p['sku'], p['name_fr'][:36], old, new, row['desc'][:34]))
        p['price'] = new
        p['price_max'] = max(new, p.get('price_max') or new)
        p['monthly'] = round(new / 36) if new else 0
        # The old "was" belonged to the old pricing. Once the list moves a
        # price, keeping it invents a discount: Lit Verdun went to 149.99 and
        # kept a 600.00 "was", advertising -75%.
        if abs(new - old) > 0.005:
            p['compare'] = None
        elif p.get('compare') and p['compare'] <= new:
            p['compare'] = None
        # Give each variant its own line where the list has one for that size;
        # writing the single picked price onto every variant flattened
        # Simple / Double / Queen to one number.
        for v in p.get('variants', []):
            lbl = v.get('label') or ''
            # a set variant takes a set line, a single takes a single line —
            # otherwise a "Set 7pcs" is priced off the table-only row
            want_set = bool(SET_RX.search(lbl))
            pool = [e for e in by[k] if bool(SET_RX.search(e['desc'])) == want_set] or by[k]
            vs = size_of(lbl) or v.get('size')
            line = next((e for e in pool if vs and e['size'] == vs), None) \
                   or (min(pool, key=lambda e: e['price']) if pool else None)
            v['price'] = round(line['price'], 2) if line else new
            v['compare'] = None
    json.dump(cat, open(os.path.join(HERE, 'catalogue.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    # prices for the supplier index — the cheapest line per code
    idx = {k: round(min(e['price'] for e in v), 2) for k, v in by.items()}
    json.dump(idx, open(os.path.join(HERE, 'supplier-prices.json'), 'w'), indent=0)

    print(f'price list: {len(by)} codes')
    print(f'catalogue : {len(cat)-unmatched} matched, {unmatched} left on their existing price')
    print(f'changed   : {len(changes)}\n')
    ups = [c for c in changes if c[3] > c[2]]
    downs = [c for c in changes if c[3] < c[2]]
    print(f'  {len(downs)} go DOWN, {len(ups)} go UP\n')
    for s, n, o, w, d in sorted(changes, key=lambda c: (c[3]-c[2])/c[2])[:14]:
        print(f'  {s:12} {n:36} {o:8.2f} -> {w:8.2f}  {(w-o)/o*100:+6.0f}%  {d}')
    if len(changes) > 14:
        print(f'  … and {len(changes)-14} more')

if __name__ == '__main__':
    main()
