# -*- coding: utf-8 -*-
"""Split multi-piece products so a set is priced as a set and a piece as a piece.

The store's Shopify variants mix two different ideas. On Nexus they are the
*components* of a 3-piece suite — "Set pcs $4200", "Sofa $2000", "Love $1500",
"Fauteuil $900" — not options of one product. The grid showed the cheapest
variant, so a $4,200 suite advertised itself at $900 and the product page then
said $4,200.

So: the parent keeps the set lines and is priced as the set; every component
becomes its own product in its own category, with its own price. Components of
the same kind in different sizes stay one product with size variants.
"""
import json, os, re, collections, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))

SET_RX = re.compile(r'(\bset\b|\bensemble\b|\d+\s*pcs?\b|\bpcs\b|\bpi[eè]ces?\b)', re.I)

# label pattern -> (sub key, FR label, EN label)
PIECES = [
    (r'\bsectionn?el|\bsectional',      ('sectionnel', 'Sectionnels', 'Sectionals')),
    (r'\bsofa.?bed|canap[eé].?lit',     ('canape-lit', 'Canapés-lits', 'Sofa beds')),
    (r'\bsofa\b|\bcanap[eé]\b',         ('canape', 'Canapés', 'Sofas')),
    (r'\blove\b|\bloveseat\b|causeuse', ('causeuse', 'Causeuses', 'Loveseats')),
    (r'fauteuil|\brecliner\b|\barmchair\b', ('fauteuil', 'Fauteuils', 'Armchairs')),
    (r'\bottomane?\b|\bpouf\b|\brepose.?pieds?\b', ('decor', 'Poufs et ottomanes', 'Ottomans')),
    (r'table de nuit|chevet|night.?stand', ('chevet', 'Tables de chevet', 'Nightstands')),
    (r'commode|dresser|\bchest\b',      ('commode', 'Commodes', 'Dressers')),
    (r'miroir|mirror',                  ('decor', 'Miroirs', 'Mirrors')),
    (r'\bbanc\b|\bbench\b',             ('decor', 'Bancs', 'Benches')),
    (r't[eê]te de lit|headboard',       ('lit', 'Lits', 'Beds')),
    (r'\blit\b|\bbed\b|plateforme',     ('lit', 'Lits', 'Beds')),
    (r'\bchaise\b|\bchair\b',           ('chaise', 'Chaises', 'Chairs')),
    (r'\btable\b',                      ('table-manger', 'Tables de salle à manger', 'Dining tables')),
    (r'\bmatelas\b|mattress',           ('matelas', 'Matelas', 'Mattresses')),
]
SET_SUB = {
    'salon':          ('ensemble-salon',  'Ensembles de salon',        'Living room sets'),
    'chambre':        ('ensemble-chambre','Ensembles de chambre',      'Bedroom sets'),
    'salle-a-manger': ('ensemble-manger', 'Ensembles de salle à manger','Dining sets'),
    'bureau':         ('ensemble-bureau', 'Ensembles de bureau',       'Office sets'),
}
SIZE_RX = re.compile(r'\b(simple|twin|double|full|queen|king)\b', re.I)
ACCESSORY_RX = re.compile(r'vendu\s+s[ée]par[ée]ment|\boption\b|\btiroirs?\b', re.I)
# a set's pieces read better without the word "Ensemble" dragged along
BASE_RX = re.compile(r'^\s*ensembles?\s+(?:de\s+)?(?:chambre|salle\s+[àa]\s+manger|salon)\s*', re.I)

def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'-{2,}', '-', re.sub(r'[^a-zA-Z0-9]+', '-', s).strip('-').lower())

# supplier codes name the piece on their own: T-1449 is a table, C-1712 a chair.
# Without this a set whose variants are bare codes prices itself off a single
# chair — "7 pc ensemble $699 / T-1449 $300 / C-1712 $70" showed $70.
CODE_PIECES = [
    (r'^\s*T[\s-]?\d{3,4}\b', ('table-manger', 'Tables de salle à manger', 'Dining tables')),
    (r'^\s*C[\s-]?\d{3,4}\b', ('chaise', 'Chaises', 'Chairs')),
    (r'^\s*B[\s-]?\d{3,4}\b', ('lit', 'Lits', 'Beds')),
]

def piece_of(label):
    for rx, meta in PIECES:
        if re.search(rx, label or '', re.I):
            return meta
    for rx, meta in CODE_PIECES:
        if re.search(rx, label or '', re.I):
            return meta
    return None

def main():
    p = os.path.join(HERE, 'catalogue.json')
    cat = json.load(open(p, encoding='utf-8'))
    out, split_report = [], []

    for prod in cat:
        vs = prod.get('variants') or []
        if len(vs) < 2 or len({v['price'] for v in vs}) < 2:
            out.append(prod); continue
        sets = [v for v in vs if SET_RX.search(v['label'] or '')
                and not ACCESSORY_RX.search(v['label'] or '')]
        pieces = [v for v in vs if v not in sets and piece_of(v['label'])]
        # a variant that is nothing but the product's own code — "IF-8030"
        # beside "Fauteuil IF-8030" — is the main piece of its category
        BARE = re.compile(r'^\s*(?:IF|I|T|C|B|ST)[\s-]?\d{3,4}[A-Z]?\s*$', re.I)
        if pieces:
            for v in vs:
                if v not in sets and v not in pieces and BARE.match(v['label'] or ''):
                    pieces.append(v)
        # "Ensemble de 2 tiroirs de rangement" is an add-on, not a suite. A set
        # is never cheaper than the pieces it contains, so anything that says
        # "ensemble" but undercuts a component is treated as a component.
        if sets and pieces:
            top = max(v['price'] for v in pieces)
            demoted = [v for v in sets if v['price'] < top]
            if demoted:
                sets = [v for v in sets if v['price'] >= top]
                pieces = pieces + [v for v in demoted if piece_of(v['label'])]
        if len(pieces) < 2 and not (sets and pieces) and not (sets and len(sets) < len(vs)):
            # every variant is a set line: it is a set, whatever it was filed as
            if sets and len(sets) == len(vs) and not prod['sub'].startswith('ensemble'):
                key, fr, en = SET_SUB.get(prod['cat'],
                                          (prod['sub'], prod['sub_fr'], prod['sub_en']))
                prod = dict(prod)
                prod['sub'], prod['sub_fr'], prod['sub_en'] = key, fr, en
            out.append(prod); continue

        # group components of the same kind (a bed in two sizes is one product)
        DEFAULT_META = {'salon': ('canape', 'Canapés', 'Sofas'),
                        'chambre': ('lit', 'Lits', 'Beds'),
                        'salle-a-manger': ('table-manger', 'Tables de salle à manger', 'Dining tables')}
        groups, group_meta = collections.OrderedDict(), {}
        for v in pieces:
            meta = piece_of(v['label']) or DEFAULT_META.get(prod['cat'])
            if meta is None:
                continue
            groups.setdefault(meta[0], []).append(v)
            group_meta[meta[0]] = meta

        # Variants that are neither a set line nor a recognised piece still
        # belong to something: under a bedroom set, a bare "Queen" is the bed.
        # Without this, "Logan – Silver" priced itself at 880 (bed only) while
        # its Set King line said 3480.
        DEFAULT_PIECE = {'chambre': ('lit', 'Lits', 'Beds'),
                         'salon': ('canape', 'Canapés', 'Sofas'),
                         'salle-a-manger': ('table-manger', 'Tables de salle à manger',
                                            'Dining tables')}
        if sets and not pieces:
            leftover = [v for v in vs if v not in sets]
            meta = DEFAULT_PIECE.get(prod['cat'])
            if leftover and meta:
                groups_extra = meta
            else:
                groups_extra = None
        else:
            groups_extra = None

        made = []
        if sets:
            parent = dict(prod)
            parent['variants'] = sets
            parent['price'] = min(v['price'] for v in sets)
            parent['price_max'] = max(v['price'] for v in sets)
            parent['monthly'] = round(parent['price'] / 36) if parent['price'] else 0
            key, fr, en = SET_SUB.get(prod['cat'], (prod['sub'], prod['sub_fr'], prod['sub_en']))
            parent['sub'], parent['sub_fr'], parent['sub_en'] = key, fr, en
            out.append(parent)
            made.append(('set', parent['name_fr'], parent['price']))

        if groups_extra:
            groups[groups_extra[0]] = [v for v in vs if v not in sets]
            group_meta[groups_extra[0]] = groups_extra

        for key, vlist in groups.items():
            meta = group_meta.get(key) or piece_of(vlist[0]['label'])
            child = dict(prod)
            child['variants'] = vlist
            child['price'] = min(v['price'] for v in vlist)
            child['price_max'] = max(v['price'] for v in vlist)
            child['monthly'] = round(child['price'] / 36) if child['price'] else 0
            # an accent chair in a living-room set is a fauteuil, not a
            # dining chair
            if meta[0] == 'chaise' and prod['cat'] == 'salon':
                meta = ('fauteuil', 'Fauteuils', 'Armchairs')
            child['sub'], child['sub_fr'], child['sub_en'] = meta
            base = BASE_RX.sub('', prod['name_fr']).strip() or prod['name_fr']
            base = re.sub(r'\s*[—-]\s*$', '', base)
            piece_word = meta[1].rstrip('s')
            # "Canapé Ahuntsic — Canapé" says it twice; the base already names it
            if base.split()[0].lower() == piece_word.lower():
                child['name_fr'] = base
            else:
                child['name_fr'] = f"{base} — {piece_word}"
            child['name_en'] = f"{prod['name_en']} — {meta[2].rstrip('s')}"
            child['slug'] = slugify(child['name_fr'])
            child['slug_en'] = slugify(child['name_en'])
            child['compare'] = None
            child['variant_sizes'] = [m.group(1).title() for v in vlist
                                      if (m := SIZE_RX.search(v['label'] or ''))]
            out.append(child)
            made.append(('piece', child['name_fr'], child['price']))

        if made:
            split_report.append((prod['name_fr'], min(v['price'] for v in vs), made))

    # slugs must stay unique now that products have been added
    for field in ('slug', 'slug_en'):
        seen = collections.Counter()
        for x in out:
            seen[x[field]] += 1
            if seen[x[field]] > 1:
                x[field] = f"{x[field]}-{seen[x[field]]}"

    # Reclassification runs over everything, not just the products that split:
    # a set whose variants are all one price never reaches the split logic at
    # all, so "Table A Manger" stayed filed under dining tables.
    for x in out:
        vs = x.get('variants') or []
        if not vs or x['sub'].startswith('ensemble'):
            continue
        if all(SET_RX.search(v['label'] or '') and not ACCESSORY_RX.search(v['label'] or '')
               for v in vs):
            key, fr, en = SET_SUB.get(x['cat'], (x['sub'], x['sub_fr'], x['sub_en']))
            x['sub'], x['sub_fr'], x['sub_en'] = key, fr, en

    # a set named after its old single-piece title reads absurdly —
    # "Chaise Christophe" selling a whole dining set
    for x in out:
        if x['sub'].startswith('ensemble') and re.match(r'^(Chaise|Canapé|Table basse)\b', x['name_fr']):
            x['name_fr'] = re.sub(r'^(Chaise|Canapé|Table basse)\b', 'Ensemble', x['name_fr'])
            x['name_en'] = 'Set ' + x['name_en'] if not x['name_en'].lower().startswith('set') else x['name_en']

    # a "was" price only means something if it belongs to the variants this
    # product actually keeps — inherited ones produce 699 marked down from 90
    for x in out:
        cmps = [v['compare'] for v in (x.get('variants') or []) if v.get('compare')]
        best = max(cmps) if cmps else None
        x['compare'] = best if (best and best > x['price']) else None

    json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(f'{len(cat)} products in, {len(out)} out  (+{len(out)-len(cat)})')
    print(f'{len(split_report)} sets split\n')
    for name, oldcard, made in split_report[:6]:
        print(f'  {name[:34]:34} card was {oldcard:8.2f}')
        for kind, n, pr in made:
            print(f'      {kind:5} {n[:44]:44} {pr:9.2f}')

if __name__ == '__main__':
    main()
