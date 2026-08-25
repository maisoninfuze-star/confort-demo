# -*- coding: utf-8 -*-
"""Turn the live meubleconfort.com product feed into the structured catalogue
the new site needs: real names, one canonical category, parsed dimensions,
colours, materials, and the fit-check data.  Writes catalogue.json."""
import json, re, html, unicodedata, sys, collections

RAW = ['raw1.json', 'raw2.json']

def plain(h):
    t = re.sub(r'<(br|/p|/div|/li)[^>]*>', '\n', h or '', flags=re.I)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = html.unescape(t)
    t = re.sub(r'[ \t\xa0]+', ' ', t)
    return re.sub(r'\n\s*\n+', '\n', t).strip()

def slugify(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    s = re.sub(r'[^a-zA-Z0-9]+', '-', s).strip('-').lower()
    return re.sub(r'-{2,}', '-', s)

# ── taxonomy ────────────────────────────────────────────────────────────────
# (subcategory key, FR label, EN label, regex over title+body+tags)
SUBS = [
    ('sectionnel',    'Sectionnels',        'Sectionals',        r'sectionn|sectional|chaise longue|lhf|rhf'),
    ('lit-superpose', 'Lits superposés',    'Bunk beds',         r'lit\s*superpos|bunk\s*bed|\bB-\d{3}'),
    # "convertible" alone is not a sofa bed: a bunk bed is "convertible en
    # 2 lits séparés". Require an actual sofa word.
    ('canape-lit',    'Canapés-lits',       'Sofa beds',         r'canap[eé].?lit|sofa.?bed|(?:canap[eé]|sofa)[^.]{0,30}convertible'),
    ('canape',        'Canapés',            'Sofas',             r'\bcanap[eé]|\bsofa\b'),
    ('causeuse',      'Causeuses',          'Loveseats',         r'causeuse|loveseat'),
    ('fauteuil',      'Fauteuils',          'Armchairs',         r'fauteuil|inclinable|recliner|accent chair'),
    ('table-salon',   'Tables de salon',    'Coffee tables',     r'table basse|table de salon|coffee table|table d.appoint|tables? gigogne'),
    ('meuble-tv',     'Meubles TV',         'TV units',          r'meuble t[eé]l[eé]|meuble tv|tv stand|console'),
    ('ensemble-chambre','Ensembles de chambre','Bedroom sets',   r'ensemble.{0,12}chambre|bedroom set|set de chambre'),
    ('lit',           'Lits',               'Beds',              r'\blit\b|\bbed\b|t[eê]te de lit|platform'),
    ('matelas',       'Matelas',            'Mattresses',        r'matelas|mattress'),
    ('commode',       'Commodes',           'Dressers',          r'commode|dresser|chiffonnier'),
    ('chevet',        'Tables de chevet',   'Nightstands',       r'table de (nuit|chevet)|nightstand'),
    ('ensemble-manger','Ensembles de salle à manger','Dining sets', r'ensemble.{0,16}(salle [aà] manger|dinette)|dining set'),
    ('table-manger',  'Tables de salle à manger','Dining tables', r'table de (salle [aà] manger|cuisine)|dining table'),
    ('chaise',        'Chaises',            'Chairs',            r'\bchaise\b|\bchair\b|tabouret|stool'),
    ('buffet',        'Buffets',            'Sideboards',        r'buffet|sideboard|vaisselier'),
    ('bureau',        'Bureaux',            'Desks',             r'bureau|desk'),
    ('bibliotheque',  'Bibliothèques',      'Bookcases',         r'biblioth[eè]que|bookcase|[eé]tag[eè]re'),
    ('decor',         'Décoration',         'Decor',             r'coussin|pillow|miroir|mirror|vase|tapis|lampe|horloge'),
]
SUB_PARENT = {
    'sectionnel':'salon','canape-lit':'salon','lit-superpose':'chambre','canape':'salon','causeuse':'salon','fauteuil':'salon',
    'table-salon':'salon','meuble-tv':'salon',
    'ensemble-chambre':'chambre','lit':'chambre','matelas':'chambre','commode':'chambre','chevet':'chambre',
    'ensemble-manger':'salle-a-manger','table-manger':'salle-a-manger','chaise':'salle-a-manger','buffet':'salle-a-manger',
    'bureau':'bureau','bibliotheque':'bureau',
    'decor':'salon',
}
CATS = {
  'salon':          dict(fr='Salon',              en='Living room',  en_slug='living-room'),
  'chambre':        dict(fr='Chambre',            en='Bedroom',      en_slug='bedroom'),
  'salle-a-manger': dict(fr='Salle à manger',     en='Dining room',  en_slug='dining-room'),
  'bureau':         dict(fr='Bureau',             en='Home office',  en_slug='home-office'),
}
TAG_CAT = {'salon':'salon','chambre':'chambre','matelas':'chambre',
           'salle a manger':'salle-a-manger','bureau':'bureau'}

COLOURS = [
    ('gris',   'Gris',    'Grey',   r'\bgris\b|\bgrey\b|\bgray\b|anthracite|charcoal'),
    ('beige',  'Beige',   'Beige',  r'\bbeige\b|\bsable\b|\btaupe\b|\bcr[eè]me\b|\bivoire\b|\bcream\b'),
    ('blanc',  'Blanc',   'White',  r'\bblanc\w*\b|\bwhite\b'),
    ('noir',   'Noir',    'Black',  r'\bnoir\w*\b|\bblack\b|\bespresso\b'),
    ('brun',   'Brun',    'Brown',  r'\bbrun\w*\b|\bbrown\b|\bch[eê]ne\b|\bnoyer\b|\bwalnut\b|\boak\b|\bmoka\b'),
    ('bleu',   'Bleu',    'Blue',   r'\bbleu\w*\b|\bblue\b|\bmarine\b|\bnavy\b'),
    ('vert',   'Vert',    'Green',  r'\bvert\w*\b|\bgreen\b'),
    ('argent', 'Argent',  'Silver', r'\bargent\w*\b|\bsilver\b|\bchrom\w*\b|\bdor[eé]\b|\bgold\b'),
]
MATERIALS = [
    ('boucle',  'Bouclé',       'Bouclé',        r'boucl[eé]'),
    ('velours', 'Velours',      'Velvet',        r'velours|velvet'),
    ('cuir',    'Cuir',         'Leather',       r'\bcuir\b|leather'),
    ('lin',     'Lin',          'Linen',         r'\blin\b|linen'),
    ('tissu',   'Tissu',        'Fabric',        r'tissu|fabric|polyester|chenille'),
    ('bois',    'Bois',         'Wood',          r'\bbois\b|\bwood\b|ch[eê]ne|oak|noyer|walnut|pin\b|mdf|plaqu[eé]'),
    ('metal',   'Métal',        'Metal',         r'm[eé]tal|metal|acier|steel|fer forg'),
    ('verre',   'Verre',        'Glass',         r'\bverre\b|\bglass\b|tremp[eé]'),
    ('marbre',  'Marbre',       'Marble',        r'marbre|marble'),
]
FEATURES = [
    ('rangement',  'Rangement',        'Storage',           r'rangement|storage|coffre|tiroir|drawer'),
    ('convertible','Se convertit en lit','Converts to a bed', r'canap[eé].?lit|sofa.?bed|convertible|se transforme'),
    ('inclinable', 'Inclinable',       'Reclining',         r'inclinable|recliner|reclining|power'),
    ('led',        'Éclairage LED',    'LED lighting',      r'\bled\b'),
    ('usb',        'Prises USB',       'USB outlets',       r'\busb\b|prise de recharge|charging station'),
]

# ── dimension parsing ───────────────────────────────────────────────────────
NUM = r'(\d{1,3}(?:[.,]\d)?)'
DIM_PATTERNS = [
    # 101 po L × 62 po P × 37 po H   /   42,25 pouces L x 20 pouces L x 30 pouces H
    re.compile(NUM+r'\s*(?:po|pouces|")\s*L\s*[x×]\s*'+NUM+r'\s*(?:po|pouces|")\s*[LPW]\s*[x×]\s*'+NUM+r'\s*(?:po|pouces|")\s*H', re.I),
    # 84"L 57"W 45"H
    re.compile(NUM+r'\s*"?\s*L\s*[x×,]?\s*'+NUM+r'\s*"?\s*W\s*[x×,]?\s*'+NUM+r'\s*"?\s*H', re.I),
    # 84 x 57 x 45 po
    re.compile(NUM+r'\s*[x×]\s*'+NUM+r'\s*[x×]\s*'+NUM+r'\s*(?:po|"|pouces)', re.I),
]
# Longueur : 78,75 po  /  Largeur : 47,25 po  /  Hauteur : 30 po
LABELLED = {
    'w': re.compile(r'(?:longueur|largeur totale|width|length)\s*:?\s*'+NUM+r'\s*(?:po|pouces|")', re.I),
    'd': re.compile(r'(?:profondeur|largeur|depth)\s*:?\s*'+NUM+r'\s*(?:po|pouces|")', re.I),
    'h': re.compile(r'(?:hauteur|height)\s*:?\s*'+NUM+r'\s*(?:po|pouces|")', re.I),
}
# 32" diamètre x 18" hauteur
ROUND_RX = re.compile(NUM+r'\s*(?:po|pouces|")?\s*(?:de\s+)?diam[eè]tre\s*[x×]\s*'+NUM+r'\s*(?:po|pouces|")?\s*(?:de\s+)?hauteur', re.I)

def _f(g):
    return float(g.replace(',', '.'))

def parse_dims(body):
    for pat in DIM_PATTERNS:
        m = pat.search(body)
        if m:
            try:
                v = [_f(g) for g in m.groups()]
            except ValueError:
                continue
            if all(4 <= x <= 200 for x in v):
                return dict(w=v[0], d=v[1], h=v[2])
    m = ROUND_RX.search(body)
    if m:
        dia, hgt = _f(m.group(1)), _f(m.group(2))
        if 4 <= dia <= 200 and 4 <= hgt <= 200:
            return dict(w=dia, d=dia, h=hgt, round=True)
    got = {}
    for k, rx in LABELLED.items():
        m = rx.search(body)
        if m:
            v = _f(m.group(1))
            if 4 <= v <= 200:
                got[k] = v
    if len(got) == 3:
        return got
    return None

def parse_seat_height(body):
    m = re.search(r"hauteur d.assise\s*:?\s*"+NUM, body, re.I)
    return float(m.group(1).replace(',', '.')) if m else None

def find_all(defs, hay):
    out = []
    for key, fr, en, rx in defs:
        if re.search(rx, hay, re.I):
            out.append(dict(key=key, fr=fr, en=en))
    return out

# ── naming ──────────────────────────────────────────────────────────────────
# Monarch codes a title several ways: a bare pair ("T-1811 / C-1835"), a code
# with a real description after it ("C-1541 – Chaise moderne en PU gris"), a
# code buried at the end ("Table basse IF-2631"), and some carry a marketing
# emoji. A customer should never see any of it.
CODE = r'(?:IF|I|T|C|A|N|M)[\s\-]?\d{3,4}[A-Z]?'
CODE_RUN = re.compile(r'\b' + CODE + r'(?:\s*[/&,+]\s*' + CODE + r')*', re.I)
EMOJI = re.compile('[\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F\u2B00-\u2BFF]')
LEAD_JUNK = re.compile(r'^[\s\-–—:|/·.]+|[\s\-–—:|/·.]+$')

def strip_codes(title):
    """Return (clean title, the codes that were in it)."""
    codes = [m.group(0).strip() for m in CODE_RUN.finditer(title)]
    clean = EMOJI.sub('', title)
    clean = CODE_RUN.sub(' ', clean)
    clean = re.sub(r'\s{2,}', ' ', clean)
    clean = LEAD_JUNK.sub('', clean)
    return clean.strip(), (codes[0] if codes else None)

STREETS = ['Verdun','Rosemont','Villeray','Ahuntsic','Outremont','Lachine','Cartier',
           'Beaubien','Papineau','Fabre','Chabanel','Iberville','Boyer','Drolet','Christophe',
           'Marquette','Gaspé','Casgrain','Waverly','Clark','Jeanne-Mance','Esplanade',
           'Saint-Denis','Saint-Urbain','Saint-Zotique','Bélanger','Jarry','Everett','Dante']

# rstrip('s') does not singularise "Ensembles de salle à manger".
SINGULAR = {
 'Sectionnels':'Sectionnel','Canapés-lits':'Canapé-lit','Canapés':'Canapé','Causeuses':'Causeuse',
 'Fauteuils':'Fauteuil','Tables de salon':'Table de salon','Meubles TV':'Meuble TV',
 'Ensembles de chambre':'Ensemble de chambre','Lits':'Lit','Matelas':'Matelas','Commodes':'Commode',
 'Tables de chevet':'Table de chevet','Ensembles de salle à manger':'Ensemble de salle à manger',
 'Tables de salle à manger':'Table de salle à manger','Chaises':'Chaise','Buffets':'Buffet',
 'Bureaux':'Bureau','Bibliothèques':'Bibliothèque','Décoration':'Meuble',
}
def singular(label):
    return SINGULAR.get(label, label.rstrip('s') if label.endswith('s') else label)

def humanize(title, sub_fr, sub_en, colours, materials, idx):
    """Codes and emoji come out. Whatever real words remain become the name; if
    nothing remains, the piece is named after a Montréal street."""
    clean, sku = strip_codes(title)
    # Keep a leftover only if it reads like a product name: enough letters, but
    # not a marketing sentence lifted out of the description.
    letters = len(re.sub(r'[^A-Za-zÀ-ÿ]', '', clean))
    words = len(clean.split())
    sentence = bool(re.search(r"\b(est|sont|incarne|offre|apporte|combine|vous|votre|ce|cette)\b",
                              clean, re.I))
    meaningful = letters >= 4 and words <= 7 and not sentence
    if meaningful:
        if clean.isupper():
            clean = clean.title()
        clean = re.sub(r'\s*"\s*L\b', '" L', clean)
        return clean, clean, sku

    piece_fr = singular(sub_fr) if sub_fr else 'Meuble'
    piece_en = (sub_en.rstrip('s') if sub_en else 'Piece')
    name = STREETS[idx % len(STREETS)]
    qual_fr = qual_en = ''
    if materials:
        qual_fr, qual_en = materials[0]['fr'].lower(), materials[0]['en'].lower()
    if colours:
        cf, ce = colours[0]['fr'].lower(), colours[0]['en'].lower()
        qual_fr = f'{qual_fr} {cf}'.strip() if qual_fr else cf
        qual_en = f'{qual_en} {ce}'.strip() if qual_en else ce
    fr = f'{piece_fr} {name}' + (f' — {qual_fr}' if qual_fr else '')
    en = f'{name} {piece_en}' + (f' — {qual_en}' if qual_en else '')
    return fr, en, sku

# ── variant option repair ───────────────────────────────────────────────────
# An add-on is not the product. "Option de rangement (vendu séparément)" is the
# cheapest variant on a bunk bed, so min(prices) advertised a $780 bed at $180.
ACCESSORY_RX = re.compile(
    r'vendu\s+s[ée]par[ée]ment|\boption\b|\btiroirs?\b|\bcoussins?\b|\bhousse\b|'
    r'\bprotecteur\b|\bgarantie\b|\blivraison\b|\bsuppl[ée]ment', re.I)

SIZE_RX = re.compile(r'\b(simple|double|full|queen|king|grand lit|tr[eè]s grand)\b', re.I)
SIZE_MAP = {'simple':('Simple','Twin'),'double':('Double','Full'),'full':('Double','Full'),
            'queen':('Queen','Queen'),'king':('King','King'),
            'grand lit':('Queen','Queen'),'très grand':('King','King'),'tres grand':('King','King')}

def split_option(label):
    """'GRIS double' -> colour Gris + size Double.  The current store keeps
    both jammed into one option named 'chambre'."""
    colour = size = None
    low = label.lower()
    for key, fr, en, rx in COLOURS:
        if re.search(rx, low, re.I):
            colour = (fr, en); break
    m = SIZE_RX.search(low)
    if m:
        size = SIZE_MAP.get(m.group(1).lower())
    return colour, size

# ── fit check ───────────────────────────────────────────────────────────────
# How a piece actually comes apart, which decides what has to clear the doorway.
#   'flat'  — breaks into panels (headboard, rails, tabletop, shelves). Once
#             apart these go through anything; the binding dimension is small.
#   'module'— breaks into upholstered modules that keep their depth and height.
#   None    — arrives in one piece.
BREAKDOWN = {
    'lit':              ('flat', 3),
    'ensemble-chambre': ('flat', 5),
    'commode':          (None, 1),
    'table-manger':     ('flat', 2),
    'ensemble-manger':  ('flat', 2),
    'bureau':           ('flat', 3),
    'bibliotheque':     ('flat', 4),
    'buffet':           (None, 1),
    'sectionnel':       ('module', 3),
    'canape-lit':       ('module', 2),
    'canape':           ('module', 2),
    'meuble-tv':        ('flat', 2),
}
FLAT_CLEARANCE = 16      # a panel turned on edge clears any normal opening

def fit_profile(sub, dims, features):
    """The binding number is the smallest dimension of the piece, since it can
    be turned any way through an opening.  Breaking it down shrinks that."""
    if not dims:
        return None
    kind, pieces = BREAKDOWN.get(sub, (None, 1))
    whole = min(dims['w'], dims['d'], dims['h'])
    if kind == 'flat':
        split = FLAT_CLEARANCE
    elif kind == 'module':
        split = min(dims['w'] / pieces, dims['d'], dims['h'])
    else:
        split = whole
    return dict(pieces=pieces, kind=kind or 'whole',
                passage=round(whole), split=round(split),
                dismantles=kind is not None)

# ── main ────────────────────────────────────────────────────────────────────
def main():
    raw = []
    for f in RAW:
        raw += json.load(open(f, encoding='utf-8'))['products']

    out = []
    for idx, p in enumerate(raw):
        body = plain(p['body_html'])
        hay = ' '.join([p['title'], body, ' '.join(p['tags']), p.get('product_type') or ''])

        sub = None
        for key, fr, en, rx in SUBS:
            if re.search(rx, hay, re.I):
                sub = (key, fr, en); break
        if not sub:
            sub = ('decor', 'Décoration', 'Decor')
        cat = SUB_PARENT.get(sub[0], 'salon')
        for t in p['tags']:                      # an explicit tag wins
            if t.strip().lower() in TAG_CAT:
                cat = TAG_CAT[t.strip().lower()]
        if sub[0] == 'matelas':
            cat = 'chambre'
        if sub[0] in ('bureau', 'bibliotheque'):
            cat = 'bureau'

        colours   = find_all(COLOURS, hay)
        materials = find_all(MATERIALS, hay)
        features  = find_all(FEATURES, hay)
        dims      = parse_dims(body)

        name_fr, name_en, sku = humanize(p['title'], sub[1], sub[2], colours, materials, idx)

        variants = []
        vcolours, vsizes = [], []
        for v in p['variants']:
            # A product can carry several option dimensions. "Chambre Moderne
            # Blanche" keeps the real configuration in option3 ("Set Queen",
            # "Lit Double"); reading only option1 left every variant labelled
            # with its size and priced from the cheapest row.
            label = ' · '.join(x.strip() for x in
                               (v.get('option1'), v.get('option2'), v.get('option3'))
                               if x and str(x).strip()) or (v['title'] or '').strip()
            c, s = split_option(label)
            variants.append(dict(
                id=v['id'], label=label, price=float(v['price']),
                accessory=bool(ACCESSORY_RX.search(label)),
                compare=float(v['compare_at_price']) if v.get('compare_at_price') else None,
                available=bool(v['available']),
                colour=c[0] if c else None, colour_en=c[1] if c else None,
                size=s[0] if s else None, size_en=s[1] if s else None))
            if c and c[0] not in vcolours: vcolours.append(c[0])
            if s and s[0] not in vsizes:  vsizes.append(s[0])

        # price from the cheapest REAL variant, and take the "was" price from
        # that same variant — max() across variants invents discounts
        real = [v for v in variants if not ACCESSORY_RX.search(v['label'] or '')] or variants
        lead = min(real, key=lambda v: v['price'])
        prices  = [v['price'] for v in real] or [0]
        price   = lead['price']
        compare = [lead['compare']] if lead.get('compare') else []

        out.append(dict(
            id=p['id'], sku=sku, handle_old=p['handle'],
            slug=slugify(name_fr), slug_en=slugify(name_en),
            name_fr=name_fr, name_en=name_en,
            cat=cat, sub=sub[0], sub_fr=sub[1], sub_en=sub[2],
            price=price, price_max=max(prices),
            compare=max(compare) if compare else None,
            monthly=round(price / 36) if price else 0,
            available=any(v['available'] for v in variants),
            images=[i['src'] for i in p['images']],
            body_fr=body,
            dims=dims, seat_h=parse_seat_height(body),
            colours=colours, materials=materials, feats=features,
            variant_colours=vcolours, variant_sizes=vsizes,
            variants=variants,
            fit=fit_profile(sub[0], dims, features),
        ))

    # The live store ships duplicate titles ("Sofa Lit" four times). Distinguish
    # them by colour, then by SKU, so no two pages share a name or a <title>.
    for field, lang in (('name_fr', 'fr'), ('name_en', 'en')):
        counts = collections.Counter(x[field] for x in out)
        used = collections.Counter()
        for x in out:
            if counts[x[field]] < 2:
                continue
            mark = (x['colours'][0][lang] if x['colours'] else None) or x['sku'] or ''
            cand = f'{x[field]} — {mark}'.strip(' —') if mark else x[field]
            used[cand] += 1
            if used[cand] > 1:
                cand = f'{cand} ({used[cand]})'
            x[field] = cand
        # slugs are derived from the names, so refresh them
    for x in out:
        x['slug'] = slugify(x['name_fr'])
        x['slug_en'] = slugify(x['name_en'])

    # the live store ships duplicate titles ("Bureau" twice) — slugs must stay unique
    for field, other in (('slug', 'sku'), ('slug_en', 'sku')):
        seen = {}
        for x in out:
            base = x[field]
            if base in seen:
                suffix = slugify(x['sku']) if x['sku'] else str(seen[base])
                x[field] = f'{base}-{suffix}'
                seen[base] += 1
            else:
                seen[base] = 1
        # a second pass in case a suffix itself collided
        seen2 = {}
        for x in out:
            while x[field] in seen2:
                x[field] += '-2'
            seen2[x[field]] = 1

    json.dump(out, open('catalogue.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    # ── report ──
    from collections import Counter
    print(f'{len(out)} products')
    print('by category :', Counter(x['cat'] for x in out).most_common())
    print('renamed     :', sum(1 for x in out if x['sku'] and x['name_fr'] != x['handle_old']))
    print('with dims   :', sum(1 for x in out if x['dims']), '/', len(out))
    print('with fit    :', sum(1 for x in out if x['fit']))
    print('colours     :', Counter(c['key'] for x in out for c in x['colours']).most_common())
    print('materials   :', Counter(m['key'] for x in out for m in x['materials']).most_common())
    print('no image    :', sum(1 for x in out if not x['images']))
    print('sample      :')
    for x in out[:6]:
        print('   ', x['cat'], '|', x['sub'], '|', x['name_fr'], '|', x['price'],
              '| dims', x['dims'], '| fit', x['fit'])

if __name__ == '__main__':
    main()
