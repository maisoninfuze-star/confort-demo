# -*- coding: utf-8 -*-
"""Turn the supplier's cost list into retail prices.

The spreadsheet's column is headed "Cost" — dealer prices — and the client
confirms the markup is x2. That matches what the store already charges: across
the 33 products with both a live price and a listed cost, the median multiple
was x2.00. Retail = cost x MARGIN, applied to the catalogue and to the full
catalogue index.

Every change is reported before it ships — a price list applied to the wrong
column silently halves a catalogue, and that is not something to discover from
a customer.
"""
import json, os, re, openpyxl, collections

HERE = os.path.dirname(os.path.abspath(__file__))

# Dealer cost -> shelf price. One number, one place.
MARGIN = 2.0
# Located by pattern rather than by name: the supplier is not named anywhere in
# this repository. Override with PRICE_LIST=/path/to/file.xlsx
def _find_price_list():
    import glob
    if os.environ.get('PRICE_LIST'):
        return os.environ['PRICE_LIST']
    hits = glob.glob(os.path.expanduser('~/Downloads/*Price List*.xlsx'))
    if not hits:
        raise SystemExit('No price list found in ~/Downloads (expected "*Price List*.xlsx"). '
                         'Set PRICE_LIST=/path/to/file.xlsx')
    return max(hits, key=os.path.getmtime)

XLSX = _find_price_list()

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
                     'cost': p, 'price': round(p * MARGIN, 2), 'size': size_of(desc)})
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

    # a split piece must reach its own line: a nightstand product takes the
    # Nightstand line, not the cheapest line of the whole collection
    PIECE_LINE = [('chevet', r'night\s*stand'), ('commode', r'dresser|chest'),
                  ('lit', r'\bbed\b'), ('chaise', r'\bchair\b'),
                  ('table-manger', r'\btable\b'), ('canape', r'\bsofa\b'),
                  ('causeuse', r'\blove'), ('fauteuil', r'\bchair\b|recliner'),
                  ('sectionnel', r'section')]
    for sub, rx in PIECE_LINE:
        if is_set:
            break          # a set prices from its set line; the guard below is for lone pieces
        if product.get('sub') == sub:
            hit = [e for e in pool if re.search(rx, e['desc'], re.I)]
            if hit:
                pool = hit
            elif any(re.search(r2, e['desc'], re.I) for _, r2 in PIECE_LINE for e in pool):
                # the lines name pieces, just not THIS piece (it is DISC) —
                # a causeuse must not borrow the chair's line
                return None
            break

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
        # "Nexus" carries no code in its title — the codes are in its variant
        # labels ("IF-8140 Sofa") and body. Try the SKU, then any code found
        # in the variants or copy that the list actually knows.
        k = None
        if p.get('sku') and norm(p['sku']) in by:
            k = norm(p['sku'])
        else:
            hay = ' '.join([v.get('label') or '' for v in p.get('variants', [])]) \
                  + ' ' + p.get('name_fr', '') + ' ' + p.get('body_fr', '')[:400]
            for m in re.finditer(r'\b([A-Za-z]{1,3})[\s-]?(\d{3,4})\b', hay):
                cand = norm(m.group(1) + m.group(2))
                if cand in by:
                    k = cand; break
        if k is None:
            unmatched += 1; continue
        row = pick(by[k], p)
        if row is None:
            unmatched += 1; continue     # piece discontinued on the list
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
            # A variant often names its own code — "Table-1274" beside
            # "Chaise-1263". Look that up rather than the product's key, or the
            # chair is priced off the table and both read $1,319.98.
            own = None
            for m in re.finditer(r'\b([A-Za-z]{1,2})[\s-]?(\d{3,4})\b', lbl):
                cand = norm(m.group(1) + m.group(2))
                if cand in by:
                    own = by[cand]; break
            if own is None:
                # "Chaise -1263" gives the number without its letter. Infer the
                # prefix from the word: a chair is a C, a table a T.
                pref = ('C' if re.search(r'chaise|chair', lbl, re.I) else
                        'T' if re.search(r'\btable\b', lbl, re.I) else None)
                if pref:
                    for m in re.finditer(r'(\d{3,4})', lbl):
                        cand = norm(pref + m.group(1))
                        if cand in by:
                            own = by[cand]; break
                    if own is None:
                        # Some variants are just "Table" and "Chaise". The codes
                        # are in the product's own copy — "T-1274 + C-1261".
                        hay = f"{p.get('name_fr','')} {p.get('body_fr','')[:600]}"
                        for m in re.finditer(rf'\b{pref}[\s-]?(\d{{3,4}})\b', hay, re.I):
                            cand = norm(pref + m.group(1))
                            if cand in by:
                                own = by[cand]; break
            src = own if own else by[k]
            # a set variant takes a set line, a single takes a single line —
            # otherwise a "Set 7pcs" is priced off the table-only row
            want_set = bool(SET_RX.search(lbl))
            pool = [e for e in src if bool(SET_RX.search(e['desc'])) == want_set] or src
            vs = size_of(lbl) or v.get('size')
            line = next((e for e in pool if vs and e['size'] == vs), None)
            if line is None:
                # match the piece the variant names to the piece the line names
                KIND = [(r'fauteuil|recliner\b(?!.*sofa)', r'\bchair\b'),
                        (r'love|causeuse', r'\blove'),
                        (r'sofa|canap[eé]', r'\bsofa\b'),
                        (r'sectionn', r'section'),
                        (r'\btable\b', r'\btable\b'),
                        (r'\bchaise\b|\bchair\b', r'\bchair\b')]
                for vrx, drx in KIND:
                    if re.search(vrx, lbl, re.I):
                        line = next((e for e in pool if re.search(drx, e['desc'], re.I)), None)
                        break
                else:
                    line = min(pool, key=lambda e: e['price']) if pool else None
            # A variant with no line of its own keeps the store's price. The
            # supplier marks discontinued pieces DISC — stamping the sofa's
            # line onto a $1,000 armchair doubled it.
            if line is not None:
                v['price'] = round(line['price'], 2)
            v['compare'] = None
    json.dump(cat, open(os.path.join(HERE, 'catalogue.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    # prices for the supplier index — the cheapest line per code
    idx = {k: round(min(e['price'] for e in v), 2) for k, v in by.items()}
    json.dump(idx, open(os.path.join(HERE, 'supplier-prices.json'), 'w'), indent=0)

    print(f'price list: {len(by)} codes, cost x {MARGIN:g}')
    print(f'catalogue : {len(cat)-unmatched} matched, {unmatched} left on their existing price')
    print(f'changed   : {len(changes)}\n')
    ups = [c for c in changes if c[3] > c[2]]
    downs = [c for c in changes if c[3] < c[2]]
    print(f'  {len(downs)} go DOWN, {len(ups)} go UP\n')
    for s, n, o, w, d in sorted(changes, key=lambda c: (c[3]-c[2])/c[2])[:14]:
        print(f'  {(s or chr(8212)):12} {n:36} {o:8.2f} -> {w:8.2f}  {(w-o)/o*100:+6.0f}%  {d}')
    if len(changes) > 14:
        print(f'  … and {len(changes)-14} more')

if __name__ == '__main__':
    main()
