# -*- coding: utf-8 -*-
"""Build the Marquise storefront from catalogue.json into dist/.

Two fully-indexed languages, one canonical URL per product, real facets,
delivery dates, the fit check, and schema.org on every page.
"""
import json, os, re, html, shutil, datetime, collections

HERE = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(HERE, 'dist')
# Where this build believes it lives. The demo must build with its own origin,
# or every canonical, hreflang and share-preview points at a meubleconfort.com
# path that does not exist yet — a canonical aimed at a 404, and a broken image
# in every link someone pastes into Messenger.
#   production : python3 build.py
#   demo       : SITE_URL=https://confort-demo.vercel.app python3 build.py
SITE = os.environ.get('SITE_URL', 'https://meubleconfort.com').rstrip('/')
PHONE = '514-279-4600'
PHONE2 = '438-879-8019'
ADDR = '7566 rue Saint-Hubert'
CITY = 'Montréal, QC H2R 2N6'
TERM = 36  # financing term in months, shown as "or $x/month"

E = lambda s: html.escape(str(s), quote=True)

def asset(path):
    """Stamp CSS/JS with a content hash. vercel.json caches these for an hour,
    so without it a returning visitor keeps the old stylesheet after a deploy —
    which is exactly how a half-updated page happens."""
    import hashlib
    f = os.path.join(HERE, 'assets', os.path.basename(path))
    if not os.path.exists(f):
        return path
    h = hashlib.sha1(open(f, 'rb').read()).hexdigest()[:8]
    return f'{path}?v={h}'

# ── language furniture ──────────────────────────────────────────────────────
CATS = ['salon', 'chambre', 'salle-a-manger', 'bureau']
CAT = {
 'salon':          {'fr': ('Salon', 'salon'),               'en': ('Living room', 'living-room')},
 'chambre':        {'fr': ('Chambre', 'chambre'),           'en': ('Bedroom', 'bedroom')},
 'salle-a-manger': {'fr': ('Salle à manger', 'salle-a-manger'), 'en': ('Dining room', 'dining-room')},
 'bureau':         {'fr': ('Bureau', 'bureau'),             'en': ('Home office', 'home-office')},
}
# The supplier's full dealer catalogue. Those product pages carry a code and a photo
# and nothing else — no description, dimensions, category or price — so these
# cannot become full product pages without gutting what a product page means
# here (no fit check, no filters, no price). They live in one browsable index
# instead, clearly marked price-on-request, until the margins land.
SUPPLIER_FAMILIES = [
    ('IF', {'fr': 'Salon — sofas, sectionnels, fauteuils', 'en': 'Living — sofas, sectionals, chairs'}),
    ('T',  {'fr': 'Tables de salle à manger',              'en': 'Dining tables'}),
    ('C',  {'fr': 'Chaises',                               'en': 'Chairs'}),
    ('B',  {'fr': 'Lits superposés',                       'en': 'Bunk beds'}),
    ('ST', {'fr': 'Série ST',                              'en': 'ST series'}),
    ('*',  {'fr': 'Ensembles nommés',                      'en': 'Named collections'}),
]

PAGES = {
 'livraison':      {'fr': ('Livraison', 'livraison'),       'en': ('Delivery', 'delivery')},
 'financement':    {'fr': ('Financement', 'financement'),   'en': ('Financing', 'financing')},
 'salle-de-montre':{'fr': ('La salle de montre', 'salle-de-montre'), 'en': ('The showroom', 'showroom')},
 'retours':        {'fr': ('Retours et garantie', 'retours'),'en': ('Returns & warranty', 'returns')},
 'a-propos':       {'fr': ('À propos', 'a-propos'),         'en': ('About us', 'about')},
 'catalogue':      {'fr': ('Catalogue complet', 'catalogue'), 'en': ('Full catalogue', 'catalogue')},
}
CAT_BLURB = {
 'salon': {
  'fr': "Sectionnels, canapés, causeuses et tables de salon — en stock à Montréal, livrés montés et à l’étage.",
  'en': "Sectionals, sofas, loveseats and coffee tables — in stock in Montréal, delivered assembled and up your stairs."},
 'chambre': {
  'fr': "Lits, ensembles de chambre, matelas et commodes. Vérifiez que ça rentre avant de commander.",
  'en': "Beds, bedroom sets, mattresses and dressers. Check it fits before you order."},
 'salle-a-manger': {
  'fr': "Tables, chaises, ensembles complets et buffets pour toutes les tailles de cuisine montréalaise.",
  'en': "Tables, chairs, complete sets and sideboards for every size of Montréal kitchen."},
 'bureau': {
  'fr': "Bureaux, bureaux de coin et bibliothèques pour le travail à la maison.",
  'en': "Desks, corner desks and bookcases for working from home."},
}
COPY = {
 'fr': dict(
   tagline='Meubles · Matelas · Montréal',
   nav_more='Tout voir', ship='Livraison gratuite · montée · à l’étage',
   stock='En stock à Montréal', fin='Financement — approbation en 3 minutes',
   hero_h='Votre salon fini.<br>Livré et <em>monté</em>.',
   hero_p='Des meubles qui sont déjà dans notre entrepôt à Montréal. Livraison gratuite, montés, à l’étage — Montréal, Laval et Longueuil.',
   hero_cta='Voir ce qui est en stock', hero_cta2='Visiter la salle de montre',
   rooms_h='Magasinez par pièce', rooms_p='Chaque pièce, meublée au complet, sans louer de camion.',
   week_h='En stock à Montréal', week_p='Déjà dans notre entrepôt, prêt à livrer. On vous appelle pour fixer la livraison dès la commande passée.',
   deals_h='Vraies aubaines', deals_p='Seulement ce qui est réellement réduit — pas une liquidation permanente.',
   revs_h='79 familles montréalaises nous ont donné 5 sur 5',
   store_h='Venez vous asseoir dessus', 
   store_p='La salle de montre est sur la Plaza Saint-Hubert, sous la marquise. On vous laisse essayer, on ne vous suit pas dans les allées.',
   store_cta='Réservez un essai — 20 min', dir='Itinéraire',
   fin_h='Ou payez-le par mois', 
   fin_p='Approbation en 3 minutes, en ligne ou en magasin. Paiements mensuels simples, sans mauvaise surprise.',
   fin_cta='Voir le financement',
   add='Ajouter au panier', call='Appeler', mo='ou %s $/mois', was='Prix régulier',
   filters='Filtres', sort='Trier', clear='Tout effacer', cart='Panier',
   cart_soon='Le panier et le paiement arrivent avec la mise en ligne.',
   sort_pop='Les plus populaires', sort_soon='En stock d’abord',
   sort_asc='Prix croissant', sort_desc='Prix décroissant',
   f_sub='Type', f_colour='Couleur', f_material='Matériau', f_price='Prix', f_stock='Disponibilité',
   in_stock='En stock à Montréal', on_sale='En rabais',
   in_stock_mtl='En stock à Montréal', back_order='Sur commande — 2 à 3 semaines',
   fit_h='Ça rentre-tu chez vous ?', fit_entry='Votre entrée', fit_floor='Étage',
   entries=[('porte','Porte simple'),('colimacon','Escalier en colimaçon'),('exterieur','Escalier extérieur'),('ascenseur','Ascenseur')],
   floors=[('1','RDC'),('2','2ᵉ'),('3','3ᵉ'),('4','4ᵉ+')],
   specs='Fiche technique', desc_h='Description', sku='Code produit', dims='Dimensions',
   colour='Couleur', material='Matériau', seat='Hauteur d’assise', cat_l='Catégorie',
   also_h='Complétez la pièce', also_p='Ce qui va avec, du même arrivage.',
   crumb_home='Accueil', size='Taille', config='Configuration',
   no_dims='Dimensions sur demande — appelez-nous au ' + PHONE + ', on les a en magasin.',
   ret='14 jours pour changer d’avis. On vient le rechercher.',
   foot_shop='Magasiner', foot_help='Aide', foot_store='Le magasin', foot_hours='Ouvert 7 jours',
   bnpl_pay4='× 4 sans intérêts, aux 2 semaines',
   bnpl_mo='× %s mois, à partir de 0 %%',
   bnpl_more='Comment payer en versements →',
   pay_h='Modes de paiement',
   set_photo='Photo de l’ensemble',
   set_photo_note='La photo montre l’ensemble complet. Cette fiche ne vend que la pièce nommée ci-contre — appelez-nous au 514-279-4600 pour une photo de la pièce seule.',
   cat_eyebrow='Distributeur autorisé',
   cat_intro='Toute la gamme que nous pouvons commander — au-delà de ce qui est en stock au magasin. Repérez un code, appelez-nous, on vous donne le prix et le délai.',
   cat_search='Chercher un code (ex. IF-6401)',
   cat_ask='Prix sur demande',
   cat_none='Aucun modèle ne correspond. Appelez-nous au 514-279-4600.',
   cat_note='Ces modèles se commandent : ils ne sont pas au magasin aujourd’hui. Les prix, les dimensions et les descriptions complètes arrivent avec la mise à jour du catalogue — d’ici là, un appel donne la réponse en une minute.',
 ),
 'en': dict(
   tagline='Furniture · Mattresses · Montréal',
   nav_more='See all', ship='Free delivery · assembled · up your stairs',
   stock='In stock in Montréal', fin='Financing — approved in 3 minutes',
   hero_h='Your living room,<br>delivered and <em>assembled</em>.',
   hero_p='Furniture that is already in our Montréal warehouse. Free delivery, assembled, up your stairs — Montréal, Laval and Longueuil.',
   hero_cta='See what\u2019s in stock', hero_cta2='Visit the showroom',
   rooms_h='Shop by room', rooms_p='A whole room, furnished, without renting a truck.',
   week_h='In stock in Montréal', week_p='Already in our warehouse, ready to go out. We call you to book the delivery as soon as you order.',
   deals_h='Real markdowns', deals_p='Only what is genuinely reduced — not a permanent liquidation.',
   revs_h='79 Montréal families have given us 5 out of 5',
   store_h='Come sit on it',
   store_p='The showroom is on Plaza Saint-Hubert, under the marquee. You get to try things without being followed down the aisle.',
   store_cta='Book a 20-minute visit', dir='Directions',
   fin_h='Or pay monthly',
   fin_p='Approved in 3 minutes, online or in store. Simple monthly payments, no surprises.',
   fin_cta='See financing',
   add='Add to cart', call='Call us', mo='or $%s/month', was='Regular price',
   filters='Filters', sort='Sort', clear='Clear all', cart='Cart',
   cart_soon='Cart and checkout arrive at launch.',
   sort_pop='Most popular', sort_soon='In stock first',
   sort_asc='Price, low to high', sort_desc='Price, high to low',
   f_sub='Type', f_colour='Colour', f_material='Material', f_price='Price', f_stock='Availability',
   in_stock='In stock in Montréal', on_sale='On sale',
   in_stock_mtl='In stock in Montréal', back_order='Made to order — 2 to 3 weeks',
   fit_h='Will it fit through your door?', fit_entry='Your entrance', fit_floor='Floor',
   entries=[('porte','Standard door'),('colimacon','Spiral staircase'),('exterieur','Outdoor stairs'),('ascenseur','Elevator')],
   floors=[('1','Ground'),('2','2nd'),('3','3rd'),('4','4th+')],
   specs='Specifications', desc_h='Description', sku='Product code', dims='Dimensions',
   colour='Colour', material='Material', seat='Seat height', cat_l='Category',
   also_h='Finish the room', also_p='What goes with it, from the same shipment.',
   crumb_home='Home', size='Size', config='Configuration',
   no_dims='Dimensions on request — call ' + PHONE + ', we have them in store.',
   ret='14 days to change your mind. We come and pick it up.',
   foot_shop='Shop', foot_help='Help', foot_store='The store', foot_hours='Open 7 days',
   bnpl_pay4='× 4 interest-free, every 2 weeks',
   bnpl_mo='× %s months, from 0%%',
   bnpl_more='How instalments work →',
   pay_h='Ways to pay',
   set_photo='Photo of the full set',
   set_photo_note='The photograph shows the complete set. This page sells only the piece named opposite — call 514-279-4600 for a photo of the piece on its own.',
   cat_eyebrow='Authorised dealer',
   cat_intro='The full range we can order — beyond what is in stock at the store. Spot a code, call us, and we’ll give you the price and the lead time.',
   cat_search='Search a code (e.g. IF-6401)',
   cat_ask='Price on request',
   cat_none='Nothing matches. Call us at 514-279-4600.',
   cat_note='These are made to order — they are not in the store today. Prices, dimensions and full descriptions arrive with the catalogue update; until then a phone call answers it in a minute.',
 ),
}
# ── Buy now, pay later ──────────────────────────────────────────────────────
# Thresholds are the merchant-side caps that decide which option is even
# offered on a given price. THESE ARE PLACEHOLDERS: every one of them has to be
# confirmed against each provider's Canadian merchant agreement before launch,
# because they differ by market, by merchant and by the shopper's own limit.
BNPL = [
    dict(id='klarna',   name='Klarna',   kind='pay4',
         lo=35,  hi=1500,
         fr='4 versements égaux, sans intérêts, aux 2 semaines',
         en='4 equal payments, interest-free, every 2 weeks'),
    dict(id='afterpay', name='Afterpay', kind='pay4',
         lo=35,  hi=2000,
         fr='4 versements égaux, sans intérêts, aux 2 semaines',
         en='4 equal payments, interest-free, every 2 weeks'),
    dict(id='affirm',   name='Affirm',   kind='monthly',
         lo=50,  hi=30000,
         fr='Versements mensuels — taux de 0 % à 36 % selon le dossier',
         en='Monthly payments — 0% to 36% APR depending on approval'),
]
BNPL_TERM = 12   # months used for the Affirm monthly illustration

# supplier supply the dealer COST, not retail. Retail = cost × margin, and the
# margin is the store's to set — so nothing derived from that file is published
# until this is a number. Observed across the 33 products already priced against
# a known cost: median ×2.00, quartiles ×1.76–×2.00.
#   supplier_MARGIN = None -> catalogue stays "prix sur demande" (current)
#   supplier_MARGIN = 2.0  -> catalogue prices itself at keystone
supplier_MARGIN = None

# Date-certain delivery ("At your place Wednesday 26 August") is switched off.
# It needs two things the business does not have yet: inventory that is true at
# the SKU level, and a delivery calendar the site can read. Promising a weekday
# without those is a promise the truck breaks. Flip this back on once both
# exist — the whole mechanic is still wired, front and back.
SHOW_DELIVERY_DATES = False

SCENES = [
    ('salon',          'salon'),
    ('chambre',        'chambre'),
    ('salle-a-manger', 'manger'),
]
# French needs the article; "Voir salon" is not a sentence.
ROOM_LINK = {
 'salon':          {'fr': 'Voir le salon',            'en': 'View living room'},
 'chambre':        {'fr': 'Voir la chambre',          'en': 'View bedroom'},
 'salle-a-manger': {'fr': 'Voir la salle à manger',   'en': 'View dining room'},
 'bureau':         {'fr': 'Voir le bureau',           'en': 'View home office'},
}
SCENE_ALT = {
 'salon':   {'fr': "Salon d'appartement montréalais, sectionnel en bouclé clair, lumière d'hiver",
             'en': "Montréal apartment living room, light bouclé sectional, winter daylight"},
 'chambre': {'fr': "Chambre en lin, lit plateforme bas, lumière du matin",
             'en': "Linen bedroom, low platform bed, morning light"},
 'manger':  {'fr': "Salle à manger, mur de brique, table en chêne et chaises en velours",
             'en': "Dining room, brick wall, oak table and velvet chairs"},
}

SWATCH = {'Gris':'#8A8D88','Beige':'#CDBFA6','Blanc':'#F2F1EC','Noir':'#23241F',
          'Brun':'#7A5638','Bleu':'#3C5A76','Vert':'#4C6A50','Argent':'#B9BDBE'}
BANDS = [('a','< 500 $','< $500',0,500),('b','500 – 999 $','$500 – $999',500,1000),
         ('c','1 000 – 1 999 $','$1,000 – $1,999',1000,2000),('d','2 000 $ +','$2,000 +',2000,10**9)]
REVIEWS = [
 {'fr':"J’ai acheté un lit king et une table de salon. Très beaux meubles, livrés le jour promis. Je recommande.",
  'en':"I bought a king bed and a coffee table. Beautiful pieces, delivered on the day they promised. I recommend them.",
  'who':'Google · ★★★★★'},
 {'fr':"Matelas très confortable, grand choix dans le catalogue, prix raisonnables et propriétaire accueillant.",
  'en':"Very comfortable mattress, a big choice in the catalogue, fair prices and a welcoming owner.",
  'who':'Google · ★★★★★'},
 {'fr':"Matelas acheté à bon prix avec la garantie du fabricant. Livraison le jour prévu, bonne communication.",
  'en':"Mattress bought at a good price with the manufacturer’s warranty. Delivered on the scheduled day, good communication.",
  'who':'Google · ★★★★★'},
]

def money(v, lang):
    v = round(v)
    if lang == 'fr':
        return f'{v:,}'.replace(',', ' ') + ' $'
    return '$' + f'{v:,}'
def deliver_mode(p):
    """What the chip is allowed to claim."""
    if not p['available']:
        return 'order'
    return 'stock' if SHOW_DELIVERY_DATES else 'instock'

def deliver_text(p, lang):
    """Server-rendered text. With dates on, the script overwrites it with a real
    weekday; with dates off this is the final copy and no script touches it."""
    c = COPY[lang]
    if not p['available']:
        return c['back_order']
    return '…' if SHOW_DELIVERY_DATES else c['in_stock_mtl']

def money4(v, lang):
    if lang == 'fr':
        return f'{v:,.2f}'.replace(',', ' ').replace('.', ',') + ' $'
    return '$' + f'{v:,.2f}'

def img(src, w):
    if not src: return ''
    return src + ('&' if '?' in src else '?') + f'width={w}'
def url(lang, *parts):
    p = '/'.join([x for x in parts if x])
    return f'/{lang}/' + (p + '/' if p else '')
def cat_slug(cat, lang):  return CAT[cat][lang][1]
def cat_name(cat, lang):  return CAT[cat][lang][0]
def p_url(p, lang):       return url(lang, cat_slug(p['cat'], lang), p['slug'] if lang=='fr' else p['slug_en'])
def p_name(p, lang):      return p['name_fr'] if lang=='fr' else p['name_en']
def band_of(price):
    for k, fr, en, lo, hi in BANDS:
        if lo <= price < hi: return k
    return 'd'

def en_description(p):
    """The live store's copy is French only. Until the English copy is written,
    build an honest spec-led paragraph from the parsed attributes."""
    bits = []
    m = ', '.join(x['en'].lower() for x in p['materials'][:2])
    c = ', '.join(x['en'].lower() for x in p['colours'][:2])
    lead = p['sub_en'].rstrip('s')
    s = f"{p['name_en']} — a {lead.lower()}"
    if m: s += f" in {m}"
    if c: s += f", finished in {c}"
    s += "."
    bits.append(s)
    if p['feats']:
        bits.append("Features: " + ', '.join(f['en'].lower() for f in p['feats']) + ".")
    if p['dims']:
        d = p['dims']
        bits.append(f"Measures {d['w']:g}\" W × {d['d']:g}\" D × {d['h']:g}\" H"
                    + (f", seat height {p['seat_h']:g}\"." if p['seat_h'] else "."))
    bits.append("In our Montréal showroom on Plaza Saint-Hubert. Free delivery, assembled, "
                "to Montréal, Laval and Longueuil.")
    return '\n'.join('<p>' + E(b) + '</p>' for b in bits)

def fr_description(p):
    out, buf = [], []
    for line in p['body_fr'].split('\n'):
        line = line.strip()
        if not line: continue
        if len(line) < 60 and (line.isupper() or line.rstrip(':').lower() in
              ('description','dimensions','caractéristiques','caractéristiques principales',
               'features and benefits','matériaux','entretien')):
            if buf: out.append('<p>' + E(' '.join(buf)) + '</p>'); buf = []
            out.append('<h3>' + E(line.rstrip(':').capitalize()) + '</h3>')
        elif line.startswith(('•', '-', '·', '–')):
            if buf: out.append('<p>' + E(' '.join(buf)) + '</p>'); buf = []
            out.append('<li>' + E(line.lstrip('•-·– ').strip()) + '</li>')
        else:
            buf.append(line)
    if buf: out.append('<p>' + E(' '.join(buf)) + '</p>')
    # wrap runs of <li> in <ul>
    txt, inul = [], False
    for chunk in out:
        if chunk.startswith('<li>') and not inul: txt.append('<ul>'); inul = True
        elif not chunk.startswith('<li>') and inul: txt.append('</ul>'); inul = False
        txt.append(chunk)
    if inul: txt.append('</ul>')
    return '\n'.join(txt)

# ── shell ───────────────────────────────────────────────────────────────────
def shell(lang, title, desc, path, alt_path, body, jsonld=None, og_img=None, head_extra=''):
    c = COPY[lang]
    other = 'en' if lang == 'fr' else 'fr'
    ld = json.dumps(jsonld, ensure_ascii=False) if jsonld else None
    return f'''<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{SITE}{path}">
<link rel="alternate" hreflang="fr-CA" href="{SITE}{path if lang=='fr' else alt_path}">
<link rel="alternate" hreflang="en-CA" href="{SITE}{alt_path if lang=='fr' else path}">
<link rel="alternate" hreflang="x-default" href="{SITE}{path if lang=='fr' else alt_path}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Meuble Confort &amp; Style">
<meta property="og:locale" content="{'fr_CA' if lang=='fr' else 'en_CA'}">
<meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(desc)}">
<meta property="og:url" content="{SITE}{path}">
{f'<meta property="og:image" content="{E(og_img)}">' if og_img else ''}
<meta name="twitter:card" content="summary_large_image">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="preconnect" href="https://cdn.shopify.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..600;1,9..144,300..600&family=Familjen+Grotesk:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="{asset('/assets/marquise.css')}">
{f'<script type="application/ld+json">{ld}</script>' if ld else ''}
{head_extra}
</head>
<body>
<a class="skip" href="#main">{'Aller au contenu' if lang=='fr' else 'Skip to content'}</a>
{header(lang, path, alt_path)}
<main id="main">
{body}
</main>
{footer(lang)}
<script>window.MQ_CART_NOTE={json.dumps(COPY[lang]['cart_soon'], ensure_ascii=False)};</script>
<script src="{asset('/assets/marquise.js')}" defer></script>
</body>
</html>'''

def header(lang, path, alt_path):
    c = COPY[lang]
    other = 'en' if lang == 'fr' else 'fr'
    CUR = ' aria-current="page"'
    nav = ''.join(
        f'<a href="{url(lang, cat_slug(k, lang))}"'
        f'{CUR if path.startswith(url(lang, cat_slug(k, lang))) else ""}>'
        f'{E(cat_name(k, lang))}</a>' for k in CATS)
    # the nav label stays short; the page keeps its full name in the <h1>
    nav += f'<a href="{url(lang, PAGES["catalogue"][lang][1])}">{"Catalogue" if lang == "fr" else "Catalogue"}</a>'
    nav += f'<a href="{url(lang, PAGES["salle-de-montre"][lang][1])}">{E(PAGES["salle-de-montre"][lang][0])}</a>'
    nav += f'<a href="{url(lang, PAGES["financement"][lang][1])}">{E(PAGES["financement"][lang][0])}</a>'
    return f'''<div class="topbar"><div class="wrap">
  <span><b>{PHONE}</b> · {PHONE2}</span><span class="sep">|</span>
  <span>{ADDR}, Montréal</span><span class="sep">|</span>
  <span>{E(c['foot_hours'])} · 10 h – 18 h</span>
</div></div>
<header class="site"><div class="wrap">
  <a class="brand" href="{url(lang)}">
      <img class="on-light" src="/assets/img/logo-dark-450.png" width="450" height="134"
           alt="Meuble Confort &amp; Style">
      <img class="on-dark" src="/assets/img/logo-light-450.png" width="450" height="134" alt="">
    </a>
  <nav class="main">{nav}</nav>
  <div class="utils">
    <a class="tel" href="tel:+1{PHONE.replace('-','')}">{PHONE}</a>
    <span class="lang">
      <a href="{path if lang=='fr' else alt_path}"{' aria-current="true"' if lang=='fr' else ''}>FR</a>
      <a href="{alt_path if lang=='fr' else path}"{' aria-current="true"' if lang=='en' else ''}>EN</a>
    </span>
    <button class="cart" type="button" data-cart-note>{E(c['cart'])} <span data-cart-count>0</span></button>
  </div>
</div></header>
<div class="promise"><div class="wrap">
  <span><span class="dot"></span>{E(c['ship'])}</span>
  <span><span class="dot"></span>{E(c['stock'])}</span>
  <span><span class="dot"></span>{E(c['fin'])}</span>
</div></div>'''

def footer(lang):
    c = COPY[lang]
    shop = ''.join(f'<a href="{url(lang, cat_slug(k, lang))}">{E(cat_name(k, lang))}</a>' for k in CATS)
    help_ = ''.join(f'<a href="{url(lang, PAGES[k][lang][1])}">{E(PAGES[k][lang][0])}</a>'
                    for k in ('catalogue', 'livraison', 'financement', 'retours', 'a-propos'))
    return f'''<footer class="site"><div class="wrap">
 <div class="cols">
  <div><h2 class="fh">{E(c['foot_shop'])}</h2>{shop}</div>
  <div><h2 class="fh">{E(c['foot_help'])}</h2>{help_}</div>
  <div><h2 class="fh">{E(c['foot_store'])}</h2>
    <a href="{url(lang, PAGES['salle-de-montre'][lang][1])}">{ADDR}<br>{CITY}</a>
    <a href="tel:+1{PHONE.replace('-','')}">{PHONE}</a>
    <a href="tel:+1{PHONE2.replace('-','')}">{PHONE2}</a>
    <a href="https://www.facebook.com/p/Meuble-Confort-Style-61554149881969/" rel="noopener">Facebook</a>
  </div>
  <div><h2 class="fh">{E(c['foot_hours'])}</h2>
    <a href="{url(lang, PAGES['salle-de-montre'][lang][1])}">{'Lundi au samedi 10 h – 18 h' if lang=='fr' else 'Monday to Saturday 10am – 6pm'}</a>
    <a href="{url(lang, PAGES['salle-de-montre'][lang][1])}">{'Dimanche 11 h – 17 h' if lang=='fr' else 'Sunday 11am – 5pm'}</a>
  </div>
 </div>
 <div class="paybar">
   <span class="paybar-h">{E(c['pay_h'])}</span>
   <span class="paymark">Visa</span><span class="paymark">Mastercard</span>
   <span class="paymark">Interac</span><span class="paymark">Klarna</span>
   <span class="paymark">Afterpay</span><span class="paymark">Affirm</span>
   <span class="paymark">{'Financement en magasin' if lang=='fr' else 'In-store financing'}</span>
 </div>
 <div class="fine">
   <span>© 2026 Meuble Confort &amp; Style</span>
   <span>{ADDR}, {CITY}</span>
   <span>{'Prototype — les prix et les stocks proviennent du catalogue en ligne actuel.' if lang=='fr' else 'Prototype — prices and stock come from the current live catalogue.'}</span>
 </div>
</div></footer>'''

# ── product card ────────────────────────────────────────────────────────────
# The catalogue is shot landscape at a median of 1.4, so the tile is 7:5. The
# 9% of pieces shot portrait or panoramic are shown whole on a neutral tile
# rather than being cropped to fit a ratio they were never shot for.
FIT_LO, FIT_HI = 1.15, 1.75

def fit_class(p):
    ar = p.get('img_ar')
    return '' if ar is None or FIT_LO <= ar <= FIT_HI else ' is-contain'

def card(p, lang, rank=0, lazy=True):
    c = COPY[lang]
    sale = p['compare'] and p['compare'] > p['price']
    sw = ''.join(f'<i style="background:{SWATCH.get(x,"#999")}" title="{E(x)}"></i>'
                 for x in p['variant_colours'][:5])
    flags = ''
    if sale:
        pct = round((1 - p['price'] / p['compare']) * 100)
        flags += f'<span class="chip sale">-{pct}%</span>'
    return f'''<a class="pc" href="{p_url(p, lang)}"
   data-sub="{E(p['sub'])}" data-price="{p['price']:.0f}" data-band="{band_of(p['price'])}"
   data-colour="{E(' '.join(x['key'] for x in p['colours']))}"
   data-material="{E(' '.join(x['key'] for x in p['materials']))}"
   data-instock="{1 if p['available'] else 0}" data-sale="{1 if sale else 0}"
   data-setshot="{1 if p.get('set_photo') else 0}" data-rank="{rank}">
 <div class="pc-shot{fit_class(p)}">{f'<div class="pc-flags">{flags}</div>' if flags else ''}
   <img {'loading="lazy" ' if lazy else ''}src="{E(img(p['images'][0], 700))}" alt="{E(p_name(p, lang))}" width="700" height="500">
   {f'<span class="setshot">{E(c["set_photo"])}</span>' if p.get('set_photo') else ''}
 </div>
 <div class="pc-body">
   <div class="pc-sub">{E(p['sub_fr'] if lang=='fr' else p['sub_en'])}</div>
   <div class="pc-name">{E(p_name(p, lang))}</div>
   {f'<div class="pc-sw">{sw}</div>' if sw else ''}
   <div class="pc-price">
     <span class="now">{money(p['price'], lang)}</span>
     {f'<span class="was">{money(p["compare"], lang)}</span>' if sale else ''}
   </div>
   <div class="pc-mo">{c['mo'] % p['monthly']}</div>
   <span class="chip boxed {'go' if p['available'] else 'plain'}" style="align-self:flex-start">
     <span class="dot"></span><span data-deliver="{deliver_mode(p)}">{E(deliver_text(p, lang))}</span></span>
 </div></a>'''

# ── opening splash ──────────────────────────────────────────────────────────
# Same shape as the BMS opener: a pre-paint script decides whether the splash
# runs at all, so there is never a flash of it on a repeat view; the mark draws
# itself; the whole panel lifts away. Home page only — nobody wants an overture
# on their fourth product page.
SPLASH_PREPAINT = """<script>
/* Runs before first paint. Skips the opener on repeat views in the same
   session and whenever the visitor asks for reduced motion.
   #intro replays it, #introhold freezes it for review. */
try {
  var r = location.hash === '#intro' || location.hash === '#introhold';
  if (!r && (sessionStorage.getItem('mcsIntro') ||
             matchMedia('(prefers-reduced-motion: reduce)').matches)) {
    document.documentElement.classList.add('intro-skip');
  }
} catch (e) {}
</script>"""

def splash(lang):
    """The mark opens out of its own circle, the wordmark wipes in beside it,
    a red rule draws under both. Two halves of the supplied logo, animated
    separately — a single raster can only fade."""
    tag = 'Meubles · Matelas · Montréal' if lang == 'fr' else 'Furniture · Mattresses · Montréal'
    return f"""<div class="splash" id="splash" aria-hidden="true">
  <div class="splash-badge">
    <div class="splash-lockup">
      <img class="splash-mark" src="/assets/img/logo-mark-light.png" width="311" height="263" alt="">
      <img class="splash-word" src="/assets/img/logo-word-light.png" width="570" height="184" alt="">
    </div>
    <span class="splash-rule"></span>
    <span class="splash-sub">{E(tag.upper())}</span>
  </div>
</div>"""

# ── home ────────────────────────────────────────────────────────────────────
def build_home(cat, lang):
    c = COPY[lang]
    instock = [p for p in cat if p['available']][:10]
    deals = sorted([p for p in cat if p['compare'] and p['compare'] > p['price']],
                   key=lambda p: -(1 - p['price'] / p['compare']))[:5]
    hero = next((p for p in cat if p['sub'] == 'sectionnel' and p['images']), cat[0])
    rooms = ''
    for k in CATS:
        sample = next((p for p in cat if p['cat'] == k and p['images']), None)
        n = sum(1 for p in cat if p['cat'] == k)
        rooms += f'''<a class="room" href="{url(lang, cat_slug(k, lang))}">
      <img loading="lazy" src="{E(img(sample['images'][0], 660))}" alt="{E(cat_name(k, lang))}" width="660" height="880">
      <div class="room-t"><b>{E(cat_name(k, lang))}</b><span>{n} {'pièces' if lang=='fr' else 'pieces'}</span></div></a>'''
    revs = ''.join(f'<blockquote class="rev"><div class="stars">★★★★★</div>'
                   f'<p>“{E(r[lang])}”</p><cite>{E(r["who"])}</cite></blockquote>' for r in REVIEWS)

    slides, caps, rails = '', '', ''
    for i, (catkey, scene) in enumerate(SCENES):
        cnt = sum(1 for p in cat if p['cat'] == catkey)
        alt = SCENE_ALT[scene][lang]
        slides += f"""
      <figure class="shero-slide">
        <img {'fetchpriority="high"' if i == 0 else 'loading="lazy"'}
             src="/assets/img/{scene}-1400.webp"
             srcset="/assets/img/{scene}-800.webp 800w, /assets/img/{scene}-1400.webp 1400w, /assets/img/{scene}-2200.webp 2200w"
             sizes="100vw" alt="{E(alt)}" width="2200" height="921">
      </figure>"""
        caps += f"""
        <div class="shero-cap">
          <span class="rn">{E(cat_name(catkey, lang))}</span>
          <span class="rc">{cnt} {'pièces en stock' if lang == 'fr' else 'pieces in stock'}</span>
          <a class="rl" href="{url(lang, cat_slug(catkey, lang))}">{E(ROOM_LINK[catkey][lang])} →</a>
        </div>"""
        cur = ' aria-current="true"' if i == 0 else ''
        rails += (f'<a href="{url(lang, cat_slug(catkey, lang))}"{cur}>'
                  f'{E(cat_name(catkey, lang))}<span class="bar"></span></a>')

    body = f'''{splash(lang)}
<section class="shero" id="shero" aria-label="{'Nos pièces' if lang == 'fr' else 'Our rooms'}">
  <div class="shero-stage">
    <div class="shero-slides">{slides}
    </div>
    <div class="shero-veil"></div>
    <div class="shero-inner">
      <p class="eyebrow">{E(c['stock'])}</p>
      <h1>{c['hero_h']}</h1>
      <p class="shero-lede">{E(c['hero_p'])}</p>
      <div class="hero-cta">
        <a class="btn btn-primary" href="{url(lang, cat_slug('salon', lang))}?stock=instock">{E(c['hero_cta'])}</a>
        <a class="btn btn-ghost" href="{url(lang, PAGES['salle-de-montre'][lang][1])}">{E(c['hero_cta2'])}</a>
      </div>
      <div class="shero-caps">{caps}
      </div>
    </div>
    <nav class="shero-rail" aria-label="{'Pièces' if lang == 'fr' else 'Rooms'}">{rails}</nav>
    <div class="shero-scrollcue"><span class="ln"></span>{'Faites défiler' if lang == 'fr' else 'Scroll'}</div>
  </div>
</section>

<section class="band"><div class="wrap">
  <div class="band-head"><div><p class="eyebrow">{E(c['rooms_h'])}</p>
    <h2>{E(c['rooms_p'])}</h2></div></div>
  <div class="rooms">{rooms}</div>
</div></section>

<section class="band"><div class="wrap">
  <div class="band-head">
    <div><h2>{E(c['week_h'])}</h2><p>{E(c['week_p'])}</p></div>
    <a class="more" href="{url(lang, cat_slug('salon', lang))}?stock=instock">{E(c['nav_more'])}</a>
  </div>
  <div class="grid">{''.join(card(p, lang, i) for i, p in enumerate(instock))}</div>
</div></section>

{'' if not deals else f"""<section class="band"><div class="wrap">
  <div class="band-head"><div><h2>{E(c['deals_h'])}</h2><p>{E(c['deals_p'])}</p></div></div>
  <div class="grid">{''.join(card(p, lang, i) for i, p in enumerate(deals))}</div>
</div></section>"""}

<section class="band"><div class="wrap">
  <div class="store">
    <div class="store-shot"><img loading="lazy" src="{E(img(cat[3]['images'][0], 900))}" alt="{'Salle de montre' if lang=='fr' else 'Showroom'}" width="900" height="675"></div>
    <div>
      <p class="eyebrow">Plaza Saint-Hubert</p>
      <h2>{E(c['store_h'])}</h2>
      <p style="color:var(--ink-2);max-width:48ch">{E(c['store_p'])}</p>
      <table class="hours">
        <tr><td>{'Lundi – vendredi' if lang=='fr' else 'Monday – Friday'}</td><td>10 h – 18 h</td></tr>
        <tr><td>{'Samedi' if lang=='fr' else 'Saturday'}</td><td>10 h – 18 h</td></tr>
        <tr><td>{'Dimanche' if lang=='fr' else 'Sunday'}</td><td>11 h – 17 h</td></tr>
      </table>
      <div class="hero-cta">
        <a class="btn btn-primary" href="{url(lang, PAGES['salle-de-montre'][lang][1])}">{E(c['store_cta'])}</a>
        <a class="btn btn-ghost" href="https://maps.google.com/?q={E(ADDR + ', ' + CITY)}" rel="noopener">{E(c['dir'])}</a>
      </div>
    </div>
  </div>
</div></section>

<section class="band"><div class="wrap">
  <div class="band-head"><div><p class="eyebrow">Google · ★★★★★ 5,0</p><h2>{E(c['revs_h'])}</h2></div></div>
  <div class="revs">{revs}</div>
</div></section>

<section class="band" style="border-bottom:0"><div class="wrap">
  <div class="store">
    <div><p class="eyebrow">{E(c['fin'])}</p><h2>{E(c['fin_h'])}</h2>
      <p style="color:var(--ink-2);max-width:46ch">{E(c['fin_p'])}</p>
      <a class="btn btn-primary" href="{url(lang, PAGES['financement'][lang][1])}">{E(c['fin_cta'])}</a></div>
    <div class="box" style="padding:26px">
      <p class="eyebrow">{'Exemple' if lang=='fr' else 'Example'}</p>
      <div style="font-family:var(--f-display);font-size:38px;font-weight:600;letter-spacing:-.04em">{c['mo'] % 61}</div>
      <p style="margin-top:8px">{'Sur un sectionnel de 2 200 $, sur ' if lang=='fr' else 'On a $2,200 sectional, over '}{TERM}{' mois.' if lang=='fr' else ' months.'}</p>
    </div>
  </div>
</div></section>'''

    ld = {"@context":"https://schema.org","@type":"FurnitureStore",
          "name":"Meuble Confort & Style","url":SITE,
          "telephone":"+1-514-279-4600","priceRange":"$$",
          "address":{"@type":"PostalAddress","streetAddress":ADDR,"addressLocality":"Montréal",
                     "addressRegion":"QC","postalCode":"H2R 2N6","addressCountry":"CA"},
          "aggregateRating":{"@type":"AggregateRating","ratingValue":"5.0","reviewCount":"79"},
          "areaServed":["Montréal","Laval","Longueuil"],
          "openingHoursSpecification":[
            {"@type":"OpeningHoursSpecification","dayOfWeek":["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"],"opens":"10:00","closes":"18:00"},
            {"@type":"OpeningHoursSpecification","dayOfWeek":"Sunday","opens":"11:00","closes":"17:00"}]}
    title = ('Meubles à Montréal — livrés, montés, à l’étage'
             if lang == 'fr' else
             'Furniture in Montréal — delivered, assembled, up your stairs')
    return shell(lang, title, c['hero_p'], url(lang), url('en' if lang=='fr' else 'fr'),
                 body, ld, SITE + '/assets/img/salon-1400.webp',
                 head_extra=SPLASH_PREPAINT)

# ── listing ─────────────────────────────────────────────────────────────────
def build_listing(cat, k, lang):
    c = COPY[lang]
    ps = [p for p in cat if p['cat'] == k]
    # pieces that can only show the set photo sink below products that show
    # themselves — a "Nightstands" filter should open on nightstands
    ps.sort(key=lambda p: (not p['available'], bool(p.get('set_photo')), p['price']))
    subs, cols, mats = {}, {}, {}
    for p in ps:
        subs.setdefault(p['sub'], [p['sub_fr'] if lang=='fr' else p['sub_en'], 0])[1] += 1
        for x in p['colours']: cols.setdefault(x['key'], [x[lang], 0])[1] += 1
        for x in p['materials']: mats.setdefault(x['key'], [x[lang], 0])[1] += 1

    def box(name, title, items, swatch=False):
        rows = ''
        for key, (label, n) in sorted(items.items(), key=lambda kv: -kv[1][1]):
            dot = f'<span class="sw" style="background:{SWATCH.get(label,"#999")}"></span>' if swatch else ''
            rows += (f'<label><input type="checkbox" name="{name}" value="{E(key)}">'
                     f'{dot}<span>{E(label)}</span><span class="n">{n}</span></label>')
        return (f'<fieldset class="facet"><legend>{E(title)}</legend>{rows}</fieldset>'
                if rows else '')

    bandbox = ''.join(
        f'<label><input type="checkbox" name="price" value="{b}">'
        f'<span>{E(fr if lang=="fr" else en)}</span>'
        f'<span class="n">{sum(1 for p in ps if band_of(p["price"])==b)}</span></label>'
        for b, fr, en, lo, hi in BANDS if any(band_of(p['price']) == b for p in ps))

    # a checkbox that can only empty the grid is worse than no checkbox:
    # "En rabais · 0" reads as a broken filter
    inst = sum(1 for p in ps if p['available'])
    sale = sum(1 for p in ps if p['compare'] and p['compare'] > p['price'])
    stock_rows = ''
    if 0 < inst < len(ps):
        stock_rows += (f'<label><input type="checkbox" name="stock" value="instock">'
                       f'<span>{E(c["in_stock"])}</span><span class="n">{inst}</span></label>')
    if sale:
        stock_rows += (f'<label><input type="checkbox" name="stock" value="sale">'
                       f'<span>{E(c["on_sale"])}</span><span class="n">{sale}</span></label>')
    stockbox = (f'<fieldset class="facet"><legend>{E(c["f_stock"])}</legend>{stock_rows}</fieldset>'
                if stock_rows else '')

    facets = f'''<form class="facets" id="facets">
  {box('sub', c['f_sub'], subs)}
  {box('colour', c['f_colour'], cols, True)}
  {box('material', c['f_material'], mats)}
  <fieldset class="facet"><legend>{E(c['f_price'])}</legend>{bandbox}</fieldset>
  {stockbox}
  <button type="button" class="btn btn-primary facet-apply" id="facet-apply">{E(c['filters'])}</button>
</form>'''

    body = f'''<div class="wrap">
 <nav class="crumbs"><a href="{url(lang)}">{E(c['crumb_home'])}</a> · {E(cat_name(k, lang))}</nav>
 <div style="padding-bottom:6px"><h1 style="font-size:clamp(28px,4vw,40px);font-weight:700;letter-spacing:-.04em">{E(cat_name(k, lang))}</h1>
 <p style="color:var(--ink-2);max-width:62ch;margin-top:10px">{E(CAT_BLURB[k][lang])}</p></div>
 <div class="listing">
  {facets}
  <div>
    <div class="facet-bar">
      <button class="btn btn-ghost facet-toggle" id="facet-toggle" type="button" style="padding:8px 14px;font-size:14px">{E(c['filters'])}</button>
      <span class="count" id="count">{c['results'] if False else ''}{len(ps)}</span>
      <button class="clearf" id="clearf" type="button">{E(c['clear'])}</button>
      <select class="sort" id="sort" aria-label="{E(c['sort'])}">
        <option value="pop">{E(c['sort_pop'])}</option>
        <option value="soon">{E(c['sort_soon'])}</option>
        <option value="price-asc">{E(c['sort_asc'])}</option>
        <option value="price-desc">{E(c['sort_desc'])}</option>
      </select>
    </div>
    <div class="grid" id="results">{''.join(card(p, lang, i, i > 7) for i, p in enumerate(ps))}</div>
    <p id="empty" hidden style="padding:40px 0;color:var(--ink-2)">
      {'Aucun produit ne correspond. Retirez un filtre, ou appelez-nous au ' + PHONE + '.' if lang=='fr' else 'Nothing matches. Drop a filter, or call ' + PHONE + '.'}</p>
  </div>
 </div>
</div>'''
    ld = {"@context":"https://schema.org","@type":"BreadcrumbList","itemListElement":[
      {"@type":"ListItem","position":1,"name":c['crumb_home'],"item":SITE+url(lang)},
      {"@type":"ListItem","position":2,"name":cat_name(k, lang),"item":SITE+url(lang, cat_slug(k, lang))}]}
    other = 'en' if lang == 'fr' else 'fr'
    title = (f'{cat_name(k, lang)} à Montréal — {len(ps)} modèles en stock'
             if lang=='fr' else
             f'{cat_name(k, lang)} furniture in Montréal — {len(ps)} in stock')
    return shell(lang, title, CAT_BLURB[k][lang], url(lang, cat_slug(k, lang)),
                 url(other, cat_slug(k, other)), body, ld,
                 img(ps[0]['images'][0], 1200) if ps else None)

def bnpl_block(price, lang):
    """Only offer what the price is actually eligible for: pay-in-4 caps out
    well below the price of a sectional, and showing it anyway is a promise the
    checkout would break."""
    c = COPY[lang]
    pay4 = [b for b in BNPL if b['kind'] == 'pay4' and b['lo'] <= price <= b['hi']]
    monthly = [b for b in BNPL if b['kind'] == 'monthly' and b['lo'] <= price <= b['hi']]
    if not pay4 and not monthly:
        return ''
    rows = ''
    if pay4:
        per = price / 4
        names = ' · '.join(b['name'] for b in pay4)
        rows += f"""<div class="bnpl-row">
        <span class="bnpl-amt" data-bnpl-pay4>{money4(per, lang)}</span>
        <span class="bnpl-txt">{E(c['bnpl_pay4'])}</span>
        <span class="bnpl-marks">{E(names)}</span>
      </div>"""
    if monthly:
        per = price / BNPL_TERM
        rows += f"""<div class="bnpl-row">
        <span class="bnpl-amt" data-bnpl-mo>{money4(per, lang)}</span>
        <span class="bnpl-txt">{E(c['bnpl_mo'] % BNPL_TERM)}</span>
        <span class="bnpl-marks">Affirm</span>
      </div>"""
    return f"""<div class="bnpl" data-bnpl>
      {rows}
      <a class="bnpl-more" href="{url(lang, PAGES['financement'][lang][1])}">{E(c['bnpl_more'])}</a>
    </div>"""

# ── product page ────────────────────────────────────────────────────────────
# An alternative is only useful if it is the same kind of thing. Someone who
# cannot get a sectional up a spiral staircase wants a smaller sofa, not a
# coffee table.
FAMILY = [
    {'sectionnel', 'canape', 'canape-lit', 'causeuse', 'fauteuil'},
    {'lit', 'ensemble-chambre'},
    {'commode', 'chevet'},
    {'table-manger', 'ensemble-manger'},
    {'bureau', 'bibliotheque'},
    {'meuble-tv', 'table-salon'},
]
def family_of(sub):
    for f in FAMILY:
        if sub in f: return f
    return {sub}

def fit_payload(p, cat, lang):
    """Ship the piece's own clearance plus a pool of same-family candidates
    with theirs; the page filters that pool against the chosen entrance."""
    f = p['fit']
    if not f: return None
    fam = family_of(p['sub'])
    pool = []
    for q in cat:
        if q is p or not q['fit'] or q['sub'] not in fam: continue
        qf = q['fit']
        qp = min(qf['passage'], qf['split']) if qf['dismantles'] else qf['passage']
        pool.append((1 if q['sub'] == p['sub'] else 0, qp, q))
    pool.sort(key=lambda t: (t[1], -t[0]))
    return dict(passage=f['passage'], split=f['split'], pieces=f['pieces'],
                kind=f['kind'], dismantles=f['dismantles'],
                alts=[dict(name=p_name(q, lang), url=p_url(q, lang),
                           img=img(q['images'][0], 240), passage=qp, same=s)
                      for s, qp, q in pool[:12]])

def build_pdp(p, cat, lang):
    c = COPY[lang]
    sale = p['compare'] and p['compare'] > p['price']
    imgs = p['images'][:8]
    CUR = ' aria-current="true"'
    thumbs = ''.join(
        f'<button type="button" data-full="{E(img(s, 1000))}"{CUR if i==0 else ""}>'
        f'<img loading="lazy" src="{E(img(s, 170))}" alt="{E(p_name(p, lang))} — {i+1}" width="170" height="170"></button>'
        for i, s in enumerate(imgs))

    # variant options, split back into the attributes they should always have been
    colours = [v for v in dict.fromkeys(x['colour'] if lang=='fr' else x['colour_en']
                                        for x in p['variants'] if x['colour'])]
    sizes = [v for v in dict.fromkeys(x['size'] if lang=='fr' else x['size_en']
                                      for x in p['variants'] if x['size'])]
    optblocks = ''
    if colours:
        row = ''.join(f'<button class="opt" data-fit-opt aria-pressed="{str(i==0).lower()}">{E(v)}</button>'
                      for i, v in enumerate(colours))
        optblocks += f'<div class="opts" data-optgroup><span class="lbl">{E(c["colour"])}</span><div class="row">{row}</div></div>'
    if sizes:
        row = ''
        for i, v in enumerate(sizes):
            pr = next((x['price'] for x in p['variants']
                       if (x['size'] if lang=='fr' else x['size_en']) == v), p['price'])
            row += (f'<button class="opt" data-price="{pr}" aria-pressed="{str(i==0).lower()}">'
                    f'{E(v)} · {money(pr, lang)}</button>')
        optblocks += f'<div class="opts" data-optgroup><span class="lbl">{E(c["size"])}</span><div class="row">{row}</div></div>'
    # an add-on must never sit in the price picker: choosing "Option de
    # rangement" would drop a $780 bed to $180 on screen
    sellable = [v for v in p['variants'] if not v.get('accessory')]
    if not colours and not sizes and len(sellable) > 1:
        row = ''.join(f'<button class="opt" data-price="{v["price"]}" aria-pressed="{str(i==0).lower()}">'
                      f'{E(v["label"])}</button>' for i, v in enumerate(sellable[:6]))
        optblocks += f'<div class="opts" data-optgroup><span class="lbl">{E(c["config"])}</span><div class="row">{row}</div></div>'

    fit = fit_payload(p, cat, lang)
    fitblock = ''
    if fit:
        ents = ''.join(f'<button class="opt" data-fit="{k}" aria-pressed="{str(i==0).lower()}">{E(lbl)}</button>'
                       for i, (k, lbl) in enumerate(c['entries']))
        flrs = ''.join(f'<button class="opt" data-fit="{k}" aria-pressed="{str(i==0).lower()}">{E(lbl)}</button>'
                       for i, (k, lbl) in enumerate(c['floors']))
        fitblock = f'''<div class="box fitrow" id="fitcheck">
  <h2>{E(c['fit_h'])}</h2>
  <div class="opts" data-fitgroup="entry"><span class="lbl">{E(c['fit_entry'])}</span><div class="row">{ents}</div></div>
  <div class="opts" data-fitgroup="floor"><span class="lbl">{E(c['fit_floor'])}</span><div class="row">{flrs}</div></div>
  <div class="fitout"></div>
</div>
<script type="application/json" id="fitdata">{json.dumps(fit, ensure_ascii=False)}</script>'''

    rows = ''
    if p['sku']: rows += f'<tr><td>{E(c["sku"])}</td><td>{E(p["sku"])}</td></tr>'
    rows += f'<tr><td>{E(c["cat_l"])}</td><td>{E(p["sub_fr"] if lang=="fr" else p["sub_en"])}</td></tr>'
    if p['dims']:
        d = p['dims']
        rows += (f'<tr><td>{E(c["dims"])}</td><td>{d["w"]:g} × {d["d"]:g} × {d["h"]:g} '
                 f'{"po (L × P × H)" if lang=="fr" else "in (W × D × H)"}</td></tr>')
    else:
        rows += f'<tr><td>{E(c["dims"])}</td><td>{E(c["no_dims"])}</td></tr>'
    if p['seat_h']: rows += f'<tr><td>{E(c["seat"])}</td><td>{p["seat_h"]:g} po</td></tr>'
    if p['colours']:
        rows += f'<tr><td>{E(c["colour"])}</td><td>{E(", ".join(x[lang] for x in p["colours"]))}</td></tr>'
    if p['materials']:
        rows += f'<tr><td>{E(c["material"])}</td><td>{E(", ".join(x[lang] for x in p["materials"]))}</td></tr>'

    related = [q for q in cat if q['cat'] == p['cat'] and q is not p and q['sub'] != p['sub']][:5]
    desc_html = fr_description(p) if lang == 'fr' else en_description(p)

    body = f'''<div class="wrap">
 <nav class="crumbs"><a href="{url(lang)}">{E(c['crumb_home'])}</a> ·
   <a href="{url(lang, cat_slug(p['cat'], lang))}">{E(cat_name(p['cat'], lang))}</a> ·
   {E(p_name(p, lang))}</nav>
 <div class="pdp">
  <div class="buy">
   <div>
     <div class="sub">{E(p['sub_fr'] if lang=='fr' else p['sub_en'])}</div>
     <h1>{E(p_name(p, lang))}</h1>
   </div>
   <div class="priceline">
     <span class="now" data-price-now>{money(p['price'], lang)}</span>
     {f'<span class="was">{money(p["compare"], lang)}</span>' if sale else ''}
   </div>
   <div class="fin">{('ou ' if lang=='fr' else 'or $')}<span data-price-mo>{p['monthly']}</span>{(' $/mois · ' if lang=='fr' else '/month · ')}<a href="{url(lang, PAGES['financement'][lang][1])}">{'approbation en 3 min' if lang=='fr' else 'approved in 3 min'}</a></div>
   {bnpl_block(p['price'], lang)}
   <span class="chip boxed {'go' if p['available'] else 'plain'}" style="align-self:flex-start">
     <span class="dot"></span><span data-deliver="{deliver_mode(p)}">{E(deliver_text(p, lang))}</span></span>
   {optblocks}
   <button class="btn btn-primary btn-block" data-add type="button">{E(c['add'])}</button>
   <a class="btn btn-ghost btn-block" href="tel:+1{PHONE.replace('-','')}">{E(c['call'])} · {PHONE}</a>
   {fitblock}
   <script type="application/json" id="bnpldata">{json.dumps({'options': BNPL, 'term': BNPL_TERM}, ensure_ascii=False)}</script>
   <div class="box">
     <p><strong>{E(c['ship'])}</strong><br>{E(c['ret'])}</p>
   </div>
  </div>
  <div class="media">
   <div class="gal">
     <div class="gal-main{fit_class(p)}"><img src="{E(img(imgs[0], 1200))}" alt="{E(p_name(p, lang))}" width="1200" height="857" fetchpriority="high"></div>
     <div class="gal-thumbs">{thumbs}</div>
     {f'<p class="setshot-note">{E(c["set_photo_note"])}</p>' if p.get('set_photo') else ''}
   </div>
   <div class="desc" style="margin-top:30px">
     <h2 style="margin-top:0">{E(c['desc_h'])}</h2>
     {desc_html}
     <h2>{E(c['specs'])}</h2>
     <table class="specs">{rows}</table>
   </div>
  </div>
 </div>

 {'' if not related else f"""<section class="band" style="border-bottom:0">
   <div class="band-head"><div><h2>{E(c['also_h'])}</h2><p>{E(c['also_p'])}</p></div></div>
   <div class="grid">{''.join(card(q, lang, i) for i, q in enumerate(related))}</div>
 </section>"""}
</div>'''

    other = 'en' if lang == 'fr' else 'fr'
    ld = {"@context":"https://schema.org","@type":"Product",
          "name":p_name(p, lang),
          "image":[img(s, 1000) for s in imgs[:4]],
          "description":re.sub(r'\s+', ' ', re.sub('<[^>]+>', ' ', desc_html))[:400].strip(),
          "sku":p['sku'] or str(p['id']),
          "brand":{"@type":"Brand","name":"Meuble Confort & Style"},
          "aggregateRating":{"@type":"AggregateRating","ratingValue":"5.0","reviewCount":"79"},
          "offers":{"@type":"Offer","url":SITE+p_url(p, lang),"priceCurrency":"CAD",
                    "price":f"{p['price']:.2f}",
                    "availability":"https://schema.org/InStock" if p['available'] else "https://schema.org/PreOrder",
                    "itemCondition":"https://schema.org/NewCondition",
                    "seller":{"@type":"Organization","name":"Meuble Confort & Style"}}}
    desc = (f"{p_name(p, lang)} — {money(p['price'], lang)}. "
            + ("En stock à Montréal, livré gratuitement, monté et à l’étage. Ou "
               f"{p['monthly']} $/mois." if lang == 'fr' else
               "In stock in Montréal, delivered free, assembled and up your stairs. Or "
               f"${p['monthly']}/month."))
    # Trim the brand, never the product name: two pieces can differ only by the
    # finish at the end of the name, and cutting it makes their <title>s
    # identical.
    base = p_name(p, lang)
    suffix = " | Meuble Confort & Style"
    title = base if len(base) + len(suffix) > 60 else base + suffix
    return shell(lang, title, desc, p_url(p, lang), p_url(p, other), body, ld, img(imgs[0], 1200))

# ── prose pages ─────────────────────────────────────────────────────────────
PROSE = {
 'livraison': {'fr': """
<h1>Livraison</h1>
<p><strong>Gratuite à Montréal, Laval et Longueuil</strong> sur toute commande de 400 $ et plus. Montée, et montée jusqu’à votre étage — pas déposée sur le trottoir.</p>
<h2>Quand</h2>
<p>Ce qui est <strong>en stock</strong> est déjà dans notre entrepôt à Montréal. Dès que votre commande est passée, on vous appelle pour fixer la livraison ensemble — on ne vous impose pas une date, on s’entend sur une qui vous convient.</p>
<p>Ce qui n’est pas en stock est indiqué <em>sur commande</em> : comptez 2 à 3 semaines. On vous appelle dès que c’est arrivé à l’entrepôt.</p>
<h2>Le jour même</h2>
<ul>
<li>On vous appelle la veille avec une fenêtre de deux heures.</li>
<li>Deux livreurs. Ils montent les escaliers, y compris les colimaçons.</li>
<li>Le meuble est assemblé chez vous, et l’emballage repart avec nous.</li>
<li>Vous inspectez avant qu’on parte. Si quelque chose cloche, on le remporte.</li>
</ul>
<h2>Les escaliers de Montréal</h2>
<p>Un sectionnel qui ne monte pas au 3ᵉ, ça arrive — et ça coûte cher à tout le monde. C’est pourquoi chaque gros meuble a un <strong>vérificateur « Ça rentre-tu ? »</strong> sur sa page : vous entrez votre type d’entrée et votre étage, et on vous dit avant de commander.</p>
<div class="callout"><p>Un doute ? Appelez-nous au """ + PHONE + """ avec la largeur de votre porte. On vérifie avec vous en deux minutes.</p></div>
<h2>Hors zone</h2>
<p>On livre aussi à Terrebonne, Brossard, Repentigny et sur la Rive-Sud, avec des frais selon la distance. Appelez-nous pour un prix.</p>""",
 'en': """
<h1>Delivery</h1>
<p><strong>Free to Montréal, Laval and Longueuil</strong> on any order of $400 or more. Assembled, and carried up to your floor — not left on the sidewalk.</p>
<h2>When</h2>
<p>Anything marked <strong>in stock</strong> is already in our Montréal warehouse. As soon as you order we call you to arrange the delivery together — we don’t hand you a date, we agree on one that works.</p>
<p>Anything not in stock is marked <em>made to order</em>: allow 2 to 3 weeks. We call you the moment it reaches the warehouse.</p>
<h2>On the day</h2>
<ul>
<li>We call the day before with a two-hour window.</li>
<li>Two delivery people. They do stairs, spiral staircases included.</li>
<li>The furniture is assembled in your home, and the packaging leaves with us.</li>
<li>You inspect it before we go. If something is wrong, it goes back on the truck.</li>
</ul>
<h2>Montréal staircases</h2>
<p>A sectional that won’t go up to the third floor happens — and it costs everyone. That’s why every large piece has a <strong>“Will it fit?” check</strong> on its page: enter your entrance type and your floor, and you’ll know before you order.</p>
<div class="callout"><p>Not sure? Call """ + PHONE + """ with your door width. We’ll check it with you in two minutes.</p></div>
<h2>Outside the zone</h2>
<p>We also deliver to Terrebonne, Brossard, Repentigny and the South Shore, with a fee based on distance. Call us for a price.</p>"""},

 'financement': {'fr': """
<h1>Financement</h1>
<p>Un sectionnel à 2 200 $, c’est <strong>61 $ par mois</strong>. C’est comme ça que la plupart de nos clients meublent une pièce au complet d’un coup plutôt qu’une pièce à la fois.</p>
<h2>Comment ça marche</h2>
<ul>
<li><strong>Approbation en 3 minutes</strong>, en ligne ou au comptoir.</li>
<li>Paiements mensuels fixes sur 12, 24 ou 36 mois.</li>
<li>Pas de pénalité si vous remboursez d’avance.</li>
<li>Le montant mensuel est affiché sur chaque produit du site.</li>
</ul>
<h2>Ce qu’il vous faut</h2>
<ul>
<li>Une pièce d’identité avec photo</li>
<li>Une preuve de revenu (talon de paie ou relevé bancaire)</li>
<li>Une adresse au Québec</li>
</ul>
<div class="callout"><p><strong>À confirmer avant la mise en ligne :</strong> le nom du prêteur, le taux annuel, les durées offertes et les frais éventuels doivent être écrits ici noir sur blanc. C’est une exigence légale au Québec, et c’est aussi ce que les clients cherchent en premier.</p></div>

<h2>Payer en versements</h2>
<p>Quatre façons d’étaler un achat. Le montant applicable est affiché directement sur chaque produit, avant que vous ajoutiez quoi que ce soit au panier.</p>
<table class="paytable">
<thead><tr><th>Option</th><th>Comment ça marche</th><th>Coût</th></tr></thead>
<tbody>
<tr><td><strong>Klarna</strong></td><td>4 versements égaux, aux 2 semaines</td><td>Sans intérêts si payé à temps</td></tr>
<tr><td><strong>Afterpay</strong></td><td>4 versements égaux, aux 2 semaines</td><td>Sans intérêts si payé à temps</td></tr>
<tr><td><strong>Affirm</strong></td><td>Versements mensuels, 3 à 36 mois</td><td>De 0 % à 36 % selon le dossier</td></tr>
<tr><td><strong>Financement en magasin</strong></td><td>12, 24 ou 36 mois, approuvé au comptoir</td><td>À confirmer</td></tr>
</tbody></table>
<p>Klarna et Afterpay conviennent aux achats plus petits — une table, un matelas, un ensemble de chaises. Pour un sectionnel ou un ensemble de chambre complet, c’est Affirm ou le financement en magasin qui s’appliquent, parce que les paiements en 4 versements ont un plafond.</p>
<div class="callout"><p><strong>À régler avant la mise en ligne.</strong> Trois choses, et aucune n’est facultative :</p></div>
<ul>
<li><strong>Les comptes marchands n’existent pas encore.</strong> Klarna, Afterpay et Affirm demandent chacun une demande distincte, avec approbation. Tant que ce n’est pas fait, ces options sont de l’affichage, pas un moyen de paiement.</li>
<li><strong>Les plafonds affichés sur le site sont des valeurs par défaut.</strong> Ils décident quelle option apparaît sur quel produit et doivent être remplacés par les vôtres, tirés de vos ententes marchandes canadiennes.</li>
<li><strong>Le Québec encadre ces produits comme du crédit à la consommation.</strong> Contrairement au reste du Canada, la <em>Loi sur la protection du consommateur</em> traite plusieurs offres « achetez maintenant, payez plus tard » comme du crédit — ce qui entraîne des obligations de divulgation, en français. Faites valider la page et l’affichage sur les fiches produits par un conseiller juridique québécois avant de les activer.</li>
</ul>
<p class="fineprint">Les frais marchands pour ce type de service se situent généralement entre 3 % et 7 % de la transaction. Sur une marge de meuble, ce n’est pas négligeable : à valider avant de tout activer.</p>
<h2>Exemples</h2>
<ul>
<li>Ensemble de chambre 1 400 $ → <strong>39 $/mois</strong> sur 36 mois</li>
<li>Sectionnel 2 200 $ → <strong>61 $/mois</strong> sur 36 mois</li>
<li>Ensemble de salle à manger 900 $ → <strong>25 $/mois</strong> sur 36 mois</li>
</ul>""",
 'en': """
<h1>Financing</h1>
<p>A $2,200 sectional is <strong>$61 a month</strong>. It’s how most of our customers furnish a whole room at once instead of a piece at a time.</p>
<h2>How it works</h2>
<ul>
<li><strong>Approved in 3 minutes</strong>, online or at the counter.</li>
<li>Fixed monthly payments over 12, 24 or 36 months.</li>
<li>No penalty for paying it off early.</li>
<li>The monthly figure is shown on every product on this site.</li>
</ul>
<h2>What you need</h2>
<ul>
<li>Photo ID</li>
<li>Proof of income (pay stub or bank statement)</li>
<li>A Québec address</li>
</ul>
<div class="callout"><p><strong>To confirm before launch:</strong> the lender’s name, the annual rate, the terms offered and any fees have to be written here in plain sight. It’s a legal requirement in Québec, and it’s also the first thing customers look for.</p></div>

<h2>Paying in instalments</h2>
<p>Four ways to spread a purchase. The applicable amount is shown on each product, before you put anything in the cart.</p>
<table class="paytable">
<thead><tr><th>Option</th><th>How it works</th><th>Cost</th></tr></thead>
<tbody>
<tr><td><strong>Klarna</strong></td><td>4 equal payments, every 2 weeks</td><td>Interest-free when paid on time</td></tr>
<tr><td><strong>Afterpay</strong></td><td>4 equal payments, every 2 weeks</td><td>Interest-free when paid on time</td></tr>
<tr><td><strong>Affirm</strong></td><td>Monthly payments, 3 to 36 months</td><td>0% to 36% APR depending on approval</td></tr>
<tr><td><strong>In-store financing</strong></td><td>12, 24 or 36 months, approved at the counter</td><td>To be confirmed</td></tr>
</tbody></table>
<p>Klarna and Afterpay suit smaller purchases — a table, a mattress, a set of chairs. For a sectional or a full bedroom set it is Affirm or in-store financing that apply, because pay-in-4 has a ceiling.</p>
<div class="callout"><p><strong>To settle before launch.</strong> Three things, none of them optional:</p></div>
<ul>
<li><strong>The merchant accounts do not exist yet.</strong> Klarna, Afterpay and Affirm each require a separate application and approval. Until that is done these are display, not a payment method.</li>
<li><strong>The thresholds on this site are defaults.</strong> They decide which option appears on which product and must be replaced with yours, from your Canadian merchant agreements.</li>
<li><strong>Québec regulates these as consumer credit.</strong> Unlike the rest of Canada, the <em>Consumer Protection Act</em> treats many buy-now-pay-later offers as credit — which brings disclosure obligations, in French. Have a Québec lawyer review this page and the product-page messaging before switching it on.</li>
</ul>
<p class="fineprint">Merchant fees for these services generally run 3% to 7% of the transaction. Against furniture margins that is not a rounding error — worth confirming before you enable everything.</p>
<h2>Examples</h2>
<ul>
<li>$1,400 bedroom set → <strong>$39/month</strong> over 36 months</li>
<li>$2,200 sectional → <strong>$61/month</strong> over 36 months</li>
<li>$900 dining set → <strong>$25/month</strong> over 36 months</li>
</ul>"""},

 'salle-de-montre': {'fr': """
<h1>La salle de montre</h1>
<p>7566 rue Saint-Hubert, sur la Plaza — sous la marquise, entre Saint-Zotique et Bélanger. Le 99 et le 30 s’arrêtent devant, et il y a du stationnement sur Saint-Hubert et dans les rues transversales.</p>
<h2>Heures</h2>
<ul><li>Lundi au vendredi — 10 h à 18 h</li><li>Samedi — 10 h à 18 h</li><li>Dimanche — 11 h à 17 h</li></ul>
<h2>Réservez un essai — 20 minutes</h2>
<p>Dites-nous ce que vous avez vu sur le site et à quelle heure vous passez. On sort les modèles, on prépare les tissus, et vous avez la place pour vous asseoir dessus sans qu’on vous suive dans les allées.</p>
<p><a class="btn btn-primary" href="tel:+1""" + PHONE.replace('-','') + """" style="margin-top:8px">Appeler le """ + PHONE + """</a></p>
<h2>Ce qui est en magasin</h2>
<p>Le site montre ce qui est en stock à l’entrepôt. La salle de montre en a plus — surtout en matelas et en tissus. Si vous ne trouvez pas une couleur ici, appelez : on l’a peut-être sur le plancher.</p>""",
 'en': """
<h1>The showroom</h1>
<p>7566 rue Saint-Hubert, on the Plaza — under the marquee, between Saint-Zotique and Bélanger. The 99 and the 30 stop out front, and there’s parking on Saint-Hubert and the side streets.</p>
<h2>Hours</h2>
<ul><li>Monday to Friday — 10am to 6pm</li><li>Saturday — 10am to 6pm</li><li>Sunday — 11am to 5pm</li></ul>
<h2>Book a 20-minute visit</h2>
<p>Tell us what you saw on the site and when you’re coming. We’ll pull the models out, have the fabrics ready, and give you room to sit on them without being followed down the aisle.</p>
<p><a class="btn btn-primary" href="tel:+1""" + PHONE.replace('-','') + """" style="margin-top:8px">Call """ + PHONE + """</a></p>
<h2>What’s in the store</h2>
<p>The site shows what’s in stock at the warehouse. The showroom holds more — especially mattresses and fabrics. If you can’t find a colour here, call: it may be on the floor.</p>"""},

 'retours': {'fr': """
<h1>Retours et garantie</h1>
<div class="callout"><p><strong>Cette page est un gabarit.</strong> La politique réelle du magasin n’a jamais été écrite nulle part — ni sur le site actuel, ni ailleurs. Les termes ci-dessous sont une proposition raisonnable pour un détaillant de meubles au Québec ; ils doivent être confirmés par le propriétaire avant la mise en ligne.</p></div>
<h2>14 jours pour changer d’avis</h2>
<p>Si le meuble ne vous convient pas, appelez-nous dans les 14 jours suivant la livraison. On vient le rechercher. Il doit être dans son état d’origine, sans taches ni dommages.</p>
<h2>Ce qui n’est pas repris</h2>
<ul><li>Les matelas déballés, pour des raisons d’hygiène — sauf défaut de fabrication</li>
<li>Les commandes spéciales et les tissus sur mesure</li>
<li>Les articles de liquidation vendus « tel quel », indiqués comme tels sur la facture</li></ul>
<h2>Si c’est brisé</h2>
<p>Inspectez avant que les livreurs repartent. Un dommage constaté à la livraison, c’est notre problème, pas le vôtre : on remporte la pièce et on la remplace.</p>
<h2>Garantie</h2>
<p>Un an sur la structure et les mécanismes, contre les défauts de fabrication. Les garanties du fabricant, plus longues sur certains matelas, s’appliquent en plus.</p>""",
 'en': """
<h1>Returns &amp; warranty</h1>
<div class="callout"><p><strong>This page is a template.</strong> The store’s actual policy has never been written down anywhere — not on the current site, not elsewhere. The terms below are a reasonable proposal for a Québec furniture retailer; they need the owner’s confirmation before launch.</p></div>
<h2>14 days to change your mind</h2>
<p>If the furniture isn’t right, call us within 14 days of delivery. We come and pick it up. It has to be in its original condition, unstained and undamaged.</p>
<h2>What we can’t take back</h2>
<ul><li>Unwrapped mattresses, for hygiene reasons — unless there’s a manufacturing defect</li>
<li>Special orders and custom fabrics</li>
<li>Clearance items sold “as is”, marked as such on the invoice</li></ul>
<h2>If it arrives damaged</h2>
<p>Inspect it before the delivery team leaves. Damage found at delivery is our problem, not yours: the piece goes back on the truck and we replace it.</p>
<h2>Warranty</h2>
<p>One year on frames and mechanisms against manufacturing defects. Manufacturers’ warranties, longer on some mattresses, apply on top.</p>"""},

 'a-propos': {'fr': """
<h1>À propos</h1>
<p>Meuble Confort &amp; Style est un magasin de meubles familial sur la Plaza Saint-Hubert, à Montréal. On vend des sectionnels, des matelas, des ensembles de chambre et de salle à manger — et on les livre nous-mêmes.</p>
<h2>Pourquoi acheter ici plutôt qu’en ligne</h2>
<p>Un grand détaillant en ligne vous vendra le même sofa avec un délai de trois à cinq semaines et une livraison au trottoir. Nous, le sofa est à quinze minutes de chez vous, dans notre entrepôt, et il peut être dans votre salon en quelques jours — monté, à l’étage, par deux personnes que vous pourrez rappeler s’il y a un problème.</p>
<h2>79 avis, 5 sur 5</h2>
<p>C’est notre note Google. On la met sur le site parce que c’est la chose la plus vraie qu’on peut dire sur nous, et elle a été écrite par nos clients, pas par nous.</p>
<h2>Nous joindre</h2>
<p>""" + ADDR + """, """ + CITY + """<br>""" + PHONE + """ · """ + PHONE2 + """</p>""",
 'en': """
<h1>About us</h1>
<p>Meuble Confort &amp; Style is a family furniture store on Plaza Saint-Hubert in Montréal. We sell sectionals, mattresses, bedroom sets and dining sets — and we deliver them ourselves.</p>
<h2>Why buy here instead of online</h2>
<p>A large online retailer will sell you the same sofa with a three-to-five-week wait and a curbside drop. Ours is fifteen minutes away, in our warehouse, and it can be in your living room within days — assembled, up your stairs, by two people you can call back if something is wrong.</p>
<h2>79 reviews, 5 out of 5</h2>
<p>That’s our Google rating. We put it on the site because it’s the truest thing we can say about ourselves, and our customers wrote it, not us.</p>
<h2>Reach us</h2>
<p>""" + ADDR + """, """ + CITY + """<br>""" + PHONE + """ · """ + PHONE2 + """</p>"""},
}

def load_supplier_catalogue():
    p = os.path.join(HERE, 'supplier-raw.json')
    if not os.path.exists(p):
        return []
    pf = os.path.join(HERE, 'supplier-prices.json')
    prices = json.load(open(pf, encoding='utf-8')) if os.path.exists(pf) else {}
    rows = [r for r in json.load(open(p, encoding='utf-8'))
            if not r.get('error') and r.get('image')]
    for r in rows:
        code = (r.get('name') or r['slug']).strip()
        r['code'] = code
        m = re.match(r'^([A-Za-z]+)', code)
        fam = (m.group(1).upper() if m else '')
        r['fam'] = fam if fam in ('IF', 'T', 'C', 'B', 'ST') else '*'
        r['price'] = prices.get(re.sub(r'[^A-Z0-9]', '', code.upper()))
    rows.sort(key=lambda r: (r['fam'] == '*', r['fam'], r['code']))
    return rows

def build_catalogue(lang):
    c = COPY[lang]
    rows = load_supplier_catalogue()
    other = 'en' if lang == 'fr' else 'fr'
    counts = collections.Counter(r['fam'] for r in rows)
    chips = ''.join(
        f'<button class="opt" data-fam="{k}" aria-pressed="false">{E(lab[lang])}'
        f' <span class="n">{counts.get(k,0)}</span></button>'
        for k, lab in SUPPLIER_FAMILIES if counts.get(k))
    cards = ''.join(
        f'<article class="ic" data-fam="{r["fam"]}" data-code="{E(r["code"].lower())}">'
        f'<div class="ic-shot"><img loading="lazy" src="{E(r["image"])}" '
        f'alt="{E(r["code"])}" width="600" height="600"></div>'
        f'<div class="ic-code">{E(r["code"])}</div>'
        + (f'<div class="ic-price">{money(r["price"], lang)}</div>'
           if r.get('price') else f'<div class="ic-ask">{E(c["cat_ask"])}</div>')
        + '</article>'
        for r in rows)

    body = f'''<div class="wrap">
 <nav class="crumbs"><a href="{url(lang)}">{E(c['crumb_home'])}</a> · {E(PAGES['catalogue'][lang][0])}</nav>
 <div style="padding-bottom:8px">
   <p class="eyebrow">{E(c['cat_eyebrow'])}</p>
   <h1 style="font-size:clamp(30px,4.4vw,46px)">{E(PAGES['catalogue'][lang][0])}</h1>
   <p style="color:var(--ink-2);max-width:62ch;margin-top:12px">{E(c['cat_intro'])}</p>
 </div>
 <div class="cat-bar">
   <div class="opts"><div class="row">{chips}</div></div>
   <input class="cat-search" id="cat-search" type="search" placeholder="{E(c['cat_search'])}"
          aria-label="{E(c['cat_search'])}">
   <span class="count" id="cat-count">{len(rows)}</span>
 </div>
 <div class="cat-grid" id="cat-grid">{cards}</div>
 <p id="cat-empty" hidden style="padding:40px 0;color:var(--ink-2)">{E(c['cat_none'])}</p>
 <div class="box" style="margin:36px 0 8px;max-width:62ch">
   <p>{E(c['cat_note'])}</p>
 </div>
</div>'''
    ld = {"@context": "https://schema.org", "@type": "CollectionPage",
          "name": PAGES['catalogue'][lang][0],
          "inLanguage": 'fr-CA' if lang == 'fr' else 'en-CA',
          "url": SITE + url(lang, PAGES['catalogue'][lang][1]),
          "numberOfItems": len(rows)}
    return shell(lang, f"{PAGES['catalogue'][lang][0]} — {len(rows)} modèles" if lang == 'fr'
                 else f"{PAGES['catalogue'][lang][0]} — {len(rows)} models",
                 c['cat_intro'], url(lang, PAGES['catalogue'][lang][1]),
                 url(other, PAGES['catalogue'][other][1]), body, ld)

def build_prose(key, lang):
    other = 'en' if lang == 'fr' else 'fr'
    name = PAGES[key][lang][0]
    body = f'<div class="wrap"><article class="prose">{PROSE[key][lang]}</article></div>'
    txt = re.sub(r'\s+', ' ', re.sub('<[^>]+>', ' ', PROSE[key][lang])).strip()
    ld = {"@context": "https://schema.org", "@type": "WebPage",
          "name": name, "inLanguage": 'fr-CA' if lang == 'fr' else 'en-CA',
          "url": SITE + url(lang, PAGES[key][lang][1]),
          "isPartOf": {"@type": "WebSite", "name": "Meuble Confort & Style", "url": SITE},
          "about": {"@type": "FurnitureStore", "name": "Meuble Confort & Style",
                    "telephone": "+1-514-279-4600",
                    "address": {"@type": "PostalAddress", "streetAddress": ADDR,
                                "addressLocality": "Montréal", "addressRegion": "QC",
                                "postalCode": "H2R 2N6", "addressCountry": "CA"}},
          "breadcrumb": {"@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": COPY[lang]['crumb_home'],
               "item": SITE + url(lang)},
              {"@type": "ListItem", "position": 2, "name": name,
               "item": SITE + url(lang, PAGES[key][lang][1])}]}}
    return shell(lang, f'{name} | Meuble Confort & Style', txt[:180],
                 url(lang, PAGES[key][lang][1]), url(other, PAGES[key][other][1]), body, ld)

# ── write ───────────────────────────────────────────────────────────────────
def write(path, content):
    full = os.path.join(DIST, path.strip('/'), 'index.html') if not path.endswith('.xml') \
           and not path.endswith('.txt') else os.path.join(DIST, path.strip('/'))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as f:
        f.write(content)
    return full

def main():
    # dist/ is generated. Wipe it first, or renaming a product silently leaves
    # its old page behind as an orphan that is still crawlable and still linked
    # from nothing.
    if os.path.isdir(DIST):
        shutil.rmtree(DIST)
    os.makedirs(DIST)
    shutil.copytree(os.path.join(HERE, 'assets'), os.path.join(DIST, 'assets'))

    cat = json.load(open(os.path.join(HERE, 'catalogue.json'), encoding='utf-8'))
    cat = [p for p in cat if p['images']]
    urls, n = [], 0

    for lang in ('fr', 'en'):
        write(url(lang), build_home(cat, lang)); urls.append(url(lang)); n += 1
        for k in CATS:
            write(url(lang, cat_slug(k, lang)), build_listing(cat, k, lang))
            urls.append(url(lang, cat_slug(k, lang))); n += 1
        for key in PAGES:
            if key == 'catalogue':
                write(url(lang, PAGES[key][lang][1]), build_catalogue(lang))
            else:
                write(url(lang, PAGES[key][lang][1]), build_prose(key, lang))
            urls.append(url(lang, PAGES[key][lang][1])); n += 1
        for p in cat:
            write(p_url(p, lang), build_pdp(p, cat, lang))
            urls.append(p_url(p, lang)); n += 1

    # root: send people to French, the store's primary language
    write('/', '<!doctype html><html lang="fr"><head><meta charset="utf-8">'
               '<title>Meuble Confort &amp; Style</title>'
               '<meta http-equiv="refresh" content="0; url=/fr/">'
               '<link rel="canonical" href="' + SITE + '/fr/">'
               '</head><body><p><a href="/fr/">Français</a> · <a href="/en/">English</a></p></body></html>')

    today = datetime.date(2026, 8, 23).isoformat()
    sm = ['<?xml version="1.0" encoding="UTF-8"?>',
          '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
          'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for u in urls:
        sm.append(f'<url><loc>{SITE}{u}</loc><lastmod>{today}</lastmod></url>')
    sm.append('</urlset>')
    write('sitemap.xml', '\n'.join(sm))
    write('robots.txt', f'User-agent: *\nAllow: /\nSitemap: {SITE}/sitemap.xml\n')

    # redirect map for the URLs the current store retires at launch
    redirects = ['# old path -> new path (301)']
    redirects.append('/collections/chanbre\t/fr/chambre/')
    redirects.append('/collections/%F0%9F%94%A5-promotions\t/fr/salon/?stock=sale')
    for k in CATS:
        redirects.append(f'/collections/{k}\t{url("fr", cat_slug(k, "fr"))}')
    for p in cat:
        redirects.append(f'/products/{p["handle_old"]}\t{p_url(p, "fr")}')
    write('redirects.txt', '\n'.join(redirects))

    built = sum(1 for r, _, fs in os.walk(DIST) for f in fs if f == 'index.html')
    assert built == n + 1, f'wrote {n}+1 pages but dist/ holds {built} — orphans left behind'
    print(f'{n} pages written to dist/ (no orphans)')
    print(f'  {len(cat)} products × 2 languages')
    print(f'  sitemap: {len(urls)} URLs')
    print(f'  redirects: {len(redirects)-1} rules')

if __name__ == '__main__':
    main()
