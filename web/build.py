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
# www is the primary host on Vercel — the apex 308s to it, so every canonical,
# hreflang and sitemap URL must carry www or Google is told about a redirect.
# The store moved to meublesconfortstyles.com on 7 Oct 2026; the old
# meubleconfort.com never had its DNS cut over and now resolves to Shopify.
SITE = os.environ.get('SITE_URL', 'https://www.meublesconfortstyles.com').rstrip('/')
# Meta dataset "Meuble Confort Style Event Data", in portfolio 1532830784423396.
# A pixel id is public by design: it ships in the source of every page.
META_PIXEL = os.environ.get('META_PIXEL_ID', '1164650748537760')
# Meta Business Settings → Domains → meublesconfortstyles.com (id 1296697739209238).
# Public by design, like the pixel id; it only proves who owns the domain.
META_DOMAIN_TAG = '<meta name="facebook-domain-verification" content="7p8b8i0hyil2s1qu4309z7w7exwon0">'
PHONE = '514-279-4600'
PHONE2 = '438-879-8019'
ADDR = '7566 rue Saint-Hubert'
CITY = 'Montréal, QC H2R 2N6'
# Québec Law 25: the person in charge of personal information, published on the
# site with a way to reach them. Confirmed by the owner's side on 14 Oct 2026.
PRIVACY_OFFICER = 'Zacharie Bien-Aimé'
PRIVACY_EMAIL = 'meubleconfortstyle@gmail.com'
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
 'financement':    {'fr': ('Paiement', 'financement'),       'en': ('Payment', 'financing')},
 'retours':        {'fr': ('Retours et garantie', 'retours'),'en': ('Returns & warranty', 'returns')},
 'a-propos':       {'fr': ('À propos', 'a-propos'),         'en': ('About us', 'about')},
 'catalogue':      {'fr': ('Catalogue complet', 'catalogue'), 'en': ('Full catalogue', 'catalogue')},
 'confidentialite':{'fr': ('Politique de confidentialité', 'confidentialite'), 'en': ('Privacy policy', 'privacy')},
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
   nav_more='Tout voir', ship='Livraison gratuite dès 400 $ · montée · à l’étage',
   stock='En stock à Montréal', fin='Paiement sécurisé',
   hero_h='Votre salon fini.<br>Livré et <em>monté</em>.',
   hero_p='Des meubles qui sont déjà dans notre entrepôt à Montréal. Livraison gratuite dès 400 $, montés, à l’étage — Montréal, Laval et Longueuil.',
   hero_cta='Voir ce qui est en stock', hero_cta2='Comment on livre',
   rooms_h='Magasinez par pièce', rooms_p='Chaque pièce, meublée au complet, sans louer de camion.',
   week_h='En stock à Montréal', week_p='Déjà dans notre entrepôt, prêt à livrer. On vous appelle pour fixer la livraison dès la commande passée.',
   deals_h='Vraies aubaines', deals_p='Seulement ce qui est réellement réduit — pas une liquidation permanente.',
   revs_h='79 familles montréalaises nous ont donné 5 sur 5',
   store_h='Une boutique en ligne, livrée chez vous', 
   store_p='Tout se passe en ligne : vous commandez, on livre et on monte chez vous. Une question sur un tissu ou une dimension ? Appelez-nous, on vérifie à l’entrepôt.',
   store_cta='Comment on livre', dir='Nous appeler',
   fin_h='Payez en toute confiance',
   fin_p='Visa, Mastercard, American Express et Apple Pay. Le paiement est traité par Stripe : votre numéro de carte ne passe jamais par notre site.',
   fin_cta='Modes de paiement',
   add='Ajouter au panier', call='Appeler', was='Prix régulier',
   filters='Filtres', sort='Trier', clear='Tout effacer', cart='Panier',
   cart_h='Votre panier', cart_empty='Votre panier est vide.',
   cart_browse='Découvrir les collections', cart_sub='Total',
   tax_incl='TPS et TVQ incluses',
   cart_pay='Passer au paiement', cart_close='Fermer',
   cart_demo='Paiement sécurisé par Stripe. Les prix incluent la TPS et la TVQ.',
   merci_h='Merci — votre commande est confirmée',
   merci_p='Votre paiement est accepté. On vous appelle pour fixer le jour de livraison — on monte le meuble à l’étage et on l’assemble chez vous. Une question ? ' + PHONE + '.',
   merci_badge='Paiement accepté', merci_cta='Retour à l’accueil',
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
   no_dims='Dimensions sur demande — appelez-nous au ' + PHONE + ', on les a à l’entrepôt.',
   ret='14 jours pour changer d’avis. On vient le rechercher.',
   foot_shop='Magasiner', foot_help='Aide', foot_store='Nous joindre', foot_hours='Service téléphonique',
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
   nav_more='See all', ship='Free delivery from $400 · assembled · up your stairs',
   stock='In stock in Montréal', fin='Secure payment',
   hero_h='Your living room,<br>delivered and <em>assembled</em>.',
   hero_p='Furniture that is already in our Montréal warehouse. Free delivery from $400, assembled, up your stairs — Montréal, Laval and Longueuil.',
   hero_cta='See what\u2019s in stock', hero_cta2='How delivery works',
   rooms_h='Shop by room', rooms_p='A whole room, furnished, without renting a truck.',
   week_h='In stock in Montréal', week_p='Already in our warehouse, ready to go out. We call you to book the delivery as soon as you order.',
   deals_h='Real markdowns', deals_p='Only what is genuinely reduced — not a permanent liquidation.',
   revs_h='79 Montréal families have given us 5 out of 5',
   store_h='An online store, delivered to you',
   store_p='It all happens online: you order, we deliver and assemble it in your home. Question about a fabric or a dimension? Call us and we check it at the warehouse.',
   store_cta='How delivery works', dir='Call us',
   fin_h='Pay with confidence',
   fin_p='Visa, Mastercard, American Express and Apple Pay. Payment is handled by Stripe: your card number never touches our site.',
   fin_cta='Ways to pay',
   add='Add to cart', call='Call us', was='Regular price',
   filters='Filters', sort='Sort', clear='Clear all', cart='Cart',
   cart_h='Your cart', cart_empty='Your cart is empty.',
   cart_browse='Browse the collections', cart_sub='Total',
   tax_incl='GST and QST included',
   cart_pay='Proceed to payment', cart_close='Close',
   cart_demo='Secure payment by Stripe. Prices include GST and QST.',
   merci_h='Thank you — your order is confirmed',
   merci_p='Your payment went through. We will call you to book your delivery day — we carry it up and assemble it in your home. Questions? ' + PHONE + '.',
   merci_badge='Payment accepted', merci_cta='Back to the home page',
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
   no_dims='Dimensions on request — call ' + PHONE + ', we have them at the warehouse.',
   ret='14 days to change your mind. We come and pick it up.',
   foot_shop='Shop', foot_help='Help', foot_store='Contact', foot_hours='Phone support',
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
# ── How the customer actually pays ──────────────────────────────────────────
# Klarna, Afterpay, Affirm and a 36-month lender plan used to be advertised
# here. None of them was ever connected: a live checkout session for a $644
# order offers card and Apple Pay, and nothing else. A payment method the
# customer cannot choose is not a payment method, so the site no longer names
# one. If a merchant account is approved later, add it here AND confirm it
# appears on a live session before any page mentions it again.

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

# Québec TPS 5% + TVQ 9,975%. The store shows one number: what you actually
# pay. Every catalogue price is converted once, here, before anything renders —
# the page, the JSON-LD, the cart and the amount sent to Stripe all read the
# same already-taxed figure, so the shelf price and the charge cannot drift.
# Rounded to the dollar so the displayed price IS the charged price to the cent.
TAX_RATE = 0.14975
# Must stay in step with the inclusive rates api/checkout.js puts on the
# Stripe line items, or the cart and the Stripe page would itemise differently.
TAX_PARTS = [
    dict(pct=0.05,     fr='TPS (5 % incluse)',      en='GST (5% included)'),
    dict(pct=0.09975,  fr='TVQ (9,975 % incluse)',  en='QST (9.975% included)'),
]

def with_tax(v):
    return float(round(v * (1 + TAX_RATE))) if v else v

def apply_tax_inclusive(cat):
    """Fold tax into every price the build will ever read. Run once, early."""
    for p in cat:
        p['price'] = with_tax(p['price'])
        if p.get('price_max'):
            p['price_max'] = with_tax(p['price_max'])
        if p.get('compare'):
            p['compare'] = with_tax(p['compare'])
            # a "was" that no longer beats the price is not a discount
            if p['compare'] <= p['price']:
                p['compare'] = None
        for v in p.get('variants', []):
            if v.get('price'):
                v['price'] = with_tax(v['price'])
            if v.get('compare'):
                v['compare'] = None
    return cat

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
    bits.append("In stock in our Montréal warehouse. Free delivery from $400, assembled, "
                "to Montréal, Laval and Longueuil.")
    return '\n'.join('<p>' + E(b) + '</p>' for b in bits)

# The supplier's own copy says things like "Disponible en magasin et en ligne".
# There is no magasin any more, so the claim is dropped wherever it appears —
# at build time, because a re-scrape would bring it straight back.
STORE_CLAIM_RX = re.compile(
    r'(disponible\s+(en\s+magasin|in\s+store)|en\s+magasin\s+et\s+en\s+ligne'
    r'|in\s+store\s+and\s+online|visitez\s+(notre|nos)\s+magasin'
    r'|salle\s+de\s+montre|showroom)', re.I)

def fr_description(p):
    out, buf = [], []
    for line in p['body_fr'].split('\n'):
        line = line.strip()
        if not line: continue
        if STORE_CLAIM_RX.search(line): continue
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
# Meta Pixel, consent first. Québec's Law 25 treats ad measurement as
# profiling, so it must be opt-in. This stub only QUEUES calls: fbevents.js —
# the part that talks to Meta — is injected by marquise.js after the visitor
# accepts, and it then sends the queued PageView/ViewContent in order. Refuse,
# and the queue never leaves the page.
# Vercel Web Analytics. The npm package and `@vercel/analytics/next` are the
# React/Next entry points; this site is static HTML with no bundler, so it uses
# the script Vercel serves from the deployment itself. Cookieless and without
# personal identifiers, so it sits outside the consent gate the Meta pixel needs.
VERCEL_ANALYTICS = '<script defer src="/_vercel/insights/script.js"></script>'

PIXEL_HEAD = ('<script>!function(w){if(w.fbq)return;var n=w.fbq=function(){n.callMethod?'
              'n.callMethod.apply(n,arguments):n.queue.push(arguments)};if(!w._fbq)w._fbq=n;'
              "n.push=n;n.loaded=!0;n.version='2.0';n.queue=[]}(window);"
              f"fbq('init','{META_PIXEL}');fbq('track','PageView');</script>")

def consent_banner(lang):
    fr = lang == 'fr'
    return f'''<div class="consent" id="consent" role="region" aria-label="{'Témoins' if fr else 'Cookies'}" hidden>
 <p>{'On utilise des témoins de Meta pour mesurer nos publicités. Vous pouvez refuser : le site fonctionne exactement pareil.' if fr else 'We use Meta cookies to measure our ads. You can decline — the site works exactly the same.'}
  <a href="{url(lang, PAGES['confidentialite'][lang][1])}">{'Politique de confidentialité' if fr else 'Privacy policy'}</a></p>
 <div class="consent-b">
  <button class="btn btn-ghost" type="button" data-consent="no">{'Refuser' if fr else 'Decline'}</button>
  <button class="btn btn-primary" type="button" data-consent="yes">{'Accepter' if fr else 'Accept'}</button>
 </div>
</div>'''

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
{META_DOMAIN_TAG}
{VERCEL_ANALYTICS}
{PIXEL_HEAD}
{head_extra}
</head>
<body>
<a class="skip" href="#main">{'Aller au contenu' if lang=='fr' else 'Skip to content'}</a>
{header(lang, path, alt_path)}
<main id="main">
{body}
</main>
{footer(lang)}
{cart_drawer(lang)}
{consent_banner(lang)}
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
    nav += f'<a href="{url(lang, PAGES["financement"][lang][1])}">{E(PAGES["financement"][lang][0])}</a>'
    return f'''<div class="topbar"><div class="wrap">
  <span><b>{PHONE}</b> · {PHONE2}</span><span class="sep">|</span>
  <span>{'Livraison Montréal · Laval · Longueuil' if lang=='fr' else 'Delivery Montréal · Laval · Longueuil'}</span><span class="sep">|</span>
  <span>{'Boutique en ligne' if lang=='fr' else 'Online store'}</span>
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
    <button class="cart" type="button" data-cart-open>{E(c['cart'])} <span data-cart-count>0</span></button>
  </div>
</div></header>
<div class="promise"><div class="wrap">
  <span><span class="dot"></span>{E(c['ship'])}</span>
  <span><span class="dot"></span>{E(c['stock'])}</span>
  <span><span class="dot"></span>{E(c['fin'])}</span>
</div></div>'''

def cart_drawer(lang):
    """The cart panel, on every page. All markup is static; the script fills
    the item list from localStorage and posts it to /api/checkout, where the
    real prices live."""
    c = COPY[lang]
    return f'''<div class="cart-veil" id="cartveil" hidden></div>
<aside class="cart-drawer" id="cartdrawer" aria-label="{E(c['cart'])}" aria-hidden="true">
 <div class="cart-head">
   <h2>{E(c['cart_h'])}</h2>
   <button class="cart-x" type="button" data-cart-close aria-label="{E(c['cart_close'])}">×</button>
 </div>
 <div class="cart-items" id="cartitems"></div>
 <div class="cart-empty" id="cartempty">
   <p>{E(c['cart_empty'])}</p>
   <a class="btn btn-ghost" href="{url(lang)}">{E(c['cart_browse'])}</a>
 </div>
 <div class="cart-foot" id="cartfoot" hidden>
   <div class="cart-sub"><span>{E(c['cart_sub'])}</span><b id="cartsum"></b></div>
   <div class="cart-tax" id="carttax"></div>
   <button class="btn btn-primary btn-block" id="cartpay" type="button">{E(c['cart_pay'])}</button>
   <p class="cart-note">{E(c['cart_demo'])}</p>
 </div>
 <script type="application/json" id="taxdata">{json.dumps({'rate': TAX_RATE, 'parts': [{'label': t[lang], 'pct': t['pct']} for t in TAX_PARTS]}, ensure_ascii=False)}</script>
</aside>'''

def footer(lang):
    c = COPY[lang]
    shop = ''.join(f'<a href="{url(lang, cat_slug(k, lang))}">{E(cat_name(k, lang))}</a>' for k in CATS)
    help_ = ''.join(f'<a href="{url(lang, PAGES[k][lang][1])}">{E(PAGES[k][lang][0])}</a>'
                    for k in ('catalogue', 'livraison', 'financement', 'retours', 'a-propos', 'confidentialite'))
    return f'''<footer class="site"><div class="wrap">
 <div class="cols">
  <div><h2 class="fh">{E(c['foot_shop'])}</h2>{shop}</div>
  <div><h2 class="fh">{E(c['foot_help'])}</h2>{help_}</div>
  <div><h2 class="fh">{E(c['foot_store'])}</h2>
    <a href="tel:+1{PHONE.replace('-','')}">{PHONE}</a>
    <a href="tel:+1{PHONE2.replace('-','')}">{PHONE2}</a>
    <a href="https://www.facebook.com/p/Meuble-Confort-Style-61554149881969/" rel="noopener">Facebook</a>
  </div>
  <div><h2 class="fh">{E(c['foot_hours'])}</h2>
    <span>{'Lundi au samedi 10 h – 18 h' if lang=='fr' else 'Monday to Saturday 10am – 6pm'}</span>
    <span>{'Dimanche 11 h – 17 h' if lang=='fr' else 'Sunday 11am – 5pm'}</span>
  </div>
 </div>
 <div class="paybar">
   <span class="paybar-h">{E(c['pay_h'])}</span>
   <span class="paymark">Visa</span><span class="paymark">Mastercard</span>
   <span class="paymark">American Express</span><span class="paymark">Apple Pay</span>
 </div>
 <div class="fine">
   <span>© 2026 Meuble Confort &amp; Style</span>
   <span>{ADDR}, {CITY}</span>
   <span>{'Tous les prix incluent la TPS et la TVQ.' if lang=='fr' else 'All prices include GST and QST.'}</span>
   <button class="linkish" type="button" data-consent-open>{'Témoins' if lang=='fr' else 'Cookies'}</button>
   <span>{'Propulsé par' if lang=='fr' else 'Powered by'} <a href="https://b12ventures.com" target="_blank" rel="noopener">B12 Ventures</a></span>
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
        <a class="btn btn-ghost" href="{url(lang, PAGES['livraison'][lang][1])}">{E(c['hero_cta2'])}</a>
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
    <div class="store-shot"><img loading="lazy" src="{E(img(cat[3]['images'][0], 900))}" alt="{'Salon livré et monté' if lang=='fr' else 'Living room delivered and assembled'}" width="900" height="675"></div>
    <div>
      <p class="eyebrow">{'Montréal · Laval · Longueuil' if lang=='fr' else 'Montréal · Laval · Longueuil'}</p>
      <h2>{E(c['store_h'])}</h2>
      <p style="color:var(--ink-2);max-width:48ch">{E(c['store_p'])}</p>
      <table class="hours">
        <tr><td colspan="2" style="padding-bottom:4px">{'On répond au téléphone' if lang=='fr' else 'We answer the phone'}</td></tr>
        <tr><td>{'Lundi – samedi' if lang=='fr' else 'Monday – Saturday'}</td><td>10 h – 18 h</td></tr>
        <tr><td>{'Dimanche' if lang=='fr' else 'Sunday'}</td><td>11 h – 17 h</td></tr>
      </table>
      <div class="hero-cta">
        <a class="btn btn-primary" href="{url(lang, PAGES['livraison'][lang][1])}">{E(c['store_cta'])}</a>
        <a class="btn btn-ghost" href="tel:+1{PHONE.replace('-','')}">{E(c['dir'])}</a>
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
      <p class="eyebrow">{'Taxes incluses' if lang=='fr' else 'Taxes included'}</p>
      <div style="font-family:var(--f-display);font-size:32px;font-weight:600;letter-spacing:-.03em;line-height:1.1">{'Le prix affiché est le prix payé' if lang=='fr' else 'The price shown is the price paid'}</div>
      <p style="margin-top:8px">{'La TPS et la TVQ sont déjà comprises dans chaque prix du site. Le total de votre panier est exactement celui porté à votre carte.' if lang=='fr' else 'GST and QST are already in every price on this site. Your cart total is exactly what is charged to your card.'}</p>
    </div>
  </div>
</div></section>'''

    # Online only: no premises to visit, so no street address and no opening
    # hours. Claiming either would put a closed door on Google Maps.
    ld = {"@context":"https://schema.org","@type":"OnlineStore",
          "name":"Meuble Confort & Style","url":SITE,
          "telephone":"+1-514-279-4600","priceRange":"$$",
          "address":{"@type":"PostalAddress","addressLocality":"Montréal",
                     "addressRegion":"QC","addressCountry":"CA"},
          "aggregateRating":{"@type":"AggregateRating","ratingValue":"5.0","reviewCount":"79"},
          "areaServed":["Montréal","Laval","Longueuil"]}
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

    colours, kind, opts = pdp_options(p, lang)
    optblocks = ''
    if colours:
        row = ''.join(f'<button class="opt" data-fit-opt data-vlabel="{E(v)}" aria-pressed="{str(i==0).lower()}">{E(v)}</button>'
                      for i, v in enumerate(colours))
        optblocks += f'<div class="opts" data-optgroup><span class="lbl">{E(c["colour"])}</span><div class="row">{row}</div></div>'
    if opts:
        row = ''.join(f'<button class="opt" data-price="{pr}" data-vlabel="{E(v)}" aria-pressed="{str(i==0).lower()}">'
                      f'{E(v)}{f" · {money(pr, lang)}" if kind == "size" else ""}</button>'
                      for i, (v, pr) in enumerate(opts))
        optblocks += (f'<div class="opts" data-optgroup><span class="lbl">'
                      f'{E(c["size"] if kind == "size" else c["config"])}</span><div class="row">{row}</div></div>')

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
     <span class="taxnote">{E(c['tax_incl'])}</span>
   </div>
   <span class="chip boxed {'go' if p['available'] else 'plain'}" style="align-self:flex-start">
     <span class="dot"></span><span data-deliver="{deliver_mode(p)}">{E(deliver_text(p, lang))}</span></span>
   {optblocks}
   <button class="btn btn-primary btn-block" data-add type="button"
     data-id="{E(p['slug'])}" data-name="{E(p_name(p, lang))}" data-img="{E(img(imgs[0], 170))}"
     data-url="{p_url(p, lang)}" data-price="{p['price']}">{E(c['add'])}</button>
   <a class="btn btn-ghost btn-block" href="tel:+1{PHONE.replace('-','')}">{E(c['call'])} · {PHONE}</a>
   {fitblock}
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
            + ("En stock à Montréal. Livraison gratuite dès 400 $, monté et à l’étage. Taxes incluses."
               if lang == 'fr' else
               "In stock in Montréal. Free delivery from $400, assembled and up your stairs. Taxes included."))
    # Trim the brand, never the product name: two pieces can differ only by the
    # finish at the end of the name, and cutting it makes their <title>s
    # identical.
    base = p_name(p, lang)
    suffix = " | Meuble Confort & Style"
    title = base if len(base) + len(suffix) > 60 else base + suffix
    # ViewContent payload. The id is the slug — the same key the add button,
    # api/prices.json and the server-side Purchase use — so Meta sees one
    # product across all four events. The replace keeps a stray "</script>" in
    # a product name from closing the tag early.
    view = json.dumps({'id': p['slug'], 'name': p_name(p, lang), 'cat': cat_name(p['cat'], lang),
                       'value': round(p['price'], 2)}, ensure_ascii=False).replace('</', '<\\/')
    body += f'\n<script type="application/json" id="mcsview">{view}</script>'
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
<h1>Modes de paiement</h1>
<p>Tout se règle en ligne, au moment de passer la commande. Le prix affiché est le prix payé : la TPS et la TVQ sont déjà comprises, et il n’y a aucuns frais cachés.</p>
<h2>Ce que nous acceptons</h2>
<ul>
<li><strong>Visa, Mastercard et American Express</strong> — crédit et débit</li>
<li><strong>Apple Pay</strong>, sur iPhone, iPad et Mac</li>
</ul>
<h2>Un paiement sécurisé</h2>
<p>Le paiement est traité par <strong>Stripe</strong>, le service utilisé par des milliers de commerces canadiens. Votre numéro de carte ne transite jamais par notre site et nous ne le voyons jamais. La connexion est chiffrée du début à la fin.</p>
<h2>Les taxes sont déjà incluses</h2>
<p>Chaque prix affiché sur le site comprend la TPS (5 %) et la TVQ (9,975 %). Le détail vous est présenté ligne par ligne à la caisse : <strong>le total de votre panier est exactement le montant porté à votre carte</strong>. Aucun supplément n’apparaît à la dernière étape.</p>
<h2>Un achat important</h2>
<p>Pour un ensemble complet ou une commande de plusieurs pièces, appelez-nous au """ + PHONE + """ avant de commander. On confirme avec vous la disponibilité, le délai et le total, et on répond à vos questions sur le tissu ou les dimensions.</p>
<h2>Après la commande</h2>
<p>Vous recevez une confirmation par courriel immédiatement, puis notre appel pour fixer la livraison. La livraison est gratuite à Montréal, Laval et Longueuil dès 400 $, montée et assemblée chez vous.</p>""",
 'en': """
<h1>Ways to pay</h1>
<p>Everything is settled online, at the moment you place the order. The price you see is the price you pay: GST and QST are already included, and there are no hidden fees.</p>
<h2>What we accept</h2>
<ul>
<li><strong>Visa, Mastercard and American Express</strong> — credit and debit</li>
<li><strong>Apple Pay</strong>, on iPhone, iPad and Mac</li>
</ul>
<h2>Secure payment</h2>
<p>Payment is handled by <strong>Stripe</strong>, the service used by thousands of Canadian businesses. Your card number never travels through our site and we never see it. The connection is encrypted end to end.</p>
<h2>Taxes are already included</h2>
<p>Every price on this site includes GST (5%) and QST (9.975%). The breakdown is shown line by line at checkout: <strong>your cart total is exactly the amount charged to your card</strong>. Nothing is added at the last step.</p>
<h2>A larger purchase</h2>
<p>For a full set or an order of several pieces, call us at """ + PHONE + """ before you order. We’ll confirm availability, the lead time and the total with you, and answer any question about fabric or dimensions.</p>
<h2>After you order</h2>
<p>You get an email confirmation right away, then our call to arrange delivery. Delivery is free in Montréal, Laval and Longueuil from $400, carried up and assembled in your home.</p>"""},

 'retours': {'fr': """
<h1>Retours et garantie</h1>
<p>Un meuble, ça s’achète pour des années. Si celui que vous recevez n’est pas le bon, voici exactement ce à quoi vous avez droit.</p>
<h2>14 jours pour changer d’avis</h2>
<p>Si le meuble ne vous convient pas, appelez-nous dans les 14 jours suivant la livraison. On vient le rechercher. Il doit être dans son état d’origine, sans taches ni dommages.</p>
<h2>Ce qui n’est pas repris</h2>
<ul><li>Les matelas déballés, pour des raisons d’hygiène — sauf défaut de fabrication</li>
<li>Les commandes spéciales et les tissus sur mesure</li>
<li>Les articles de liquidation vendus « tel quel », indiqués comme tels sur la facture</li></ul>
<h2>Si c’est brisé</h2>
<p>Inspectez avant que les livreurs repartent. Un dommage constaté à la livraison, c’est notre problème, pas le vôtre : on remporte la pièce et on la remplace.</p>
<h2>Garantie</h2>
<p>Un an sur la structure et les mécanismes, contre les défauts de fabrication. Les garanties du fabricant, plus longues sur certains matelas, s’appliquent en plus.</p>
<h2>Remboursements</h2>
<p>Un retour accepté est remboursé sur le mode de paiement utilisé lors de l’achat, taxes comprises. Comptez de 5 à 10 jours ouvrables pour que votre institution financière l’affiche.</p>
<h2>Nous joindre</h2>
<p>Un retour, un défaut, une question : appelez-nous au """ + PHONE + """ ou au """ + PHONE2 + """. On règle ça au téléphone.</p>""",

 'en': """
<h1>Returns &amp; warranty</h1>
<p>Furniture is bought for years. If the piece that arrives isn’t the right one, here is exactly what you’re entitled to.</p>
<h2>14 days to change your mind</h2>
<p>If the furniture isn’t right, call us within 14 days of delivery. We come and pick it up. It has to be in its original condition, unstained and undamaged.</p>
<h2>What we can’t take back</h2>
<ul><li>Unwrapped mattresses, for hygiene reasons — unless there’s a manufacturing defect</li>
<li>Special orders and custom fabrics</li>
<li>Clearance items sold “as is”, marked as such on the invoice</li></ul>
<h2>If it arrives damaged</h2>
<p>Inspect it before the delivery team leaves. Damage found at delivery is our problem, not yours: the piece goes back on the truck and we replace it.</p>
<h2>Warranty</h2>
<p>One year on frames and mechanisms against manufacturing defects. Manufacturers’ warranties, longer on some mattresses, apply on top.</p>
<h2>Refunds</h2>
<p>An accepted return is refunded to the payment method used for the purchase, taxes included. Allow 5 to 10 business days for your bank to show it.</p>
<h2>Reach us</h2>
<p>A return, a defect, a question: call us at """ + PHONE + """ or """ + PHONE2 + """. We sort it out on the phone.</p>"""},

 'a-propos': {'fr': """
<h1>À propos</h1>
<p>Meuble Confort &amp; Style est une entreprise de meubles familiale de Montréal. On vend en ligne des sectionnels, des matelas, des ensembles de chambre et de salle à manger — et on les livre nous-mêmes.</p>
<h2>Pourquoi acheter ici</h2>
<p>Un grand détaillant en ligne vous vendra le même sofa avec un délai de trois à cinq semaines et une livraison au trottoir. Nous, le sofa est à quinze minutes de chez vous, dans notre entrepôt, et il peut être dans votre salon en quelques jours — monté, à l’étage, par deux personnes que vous pourrez rappeler s’il y a un problème.</p>
<h2>79 avis, 5 sur 5</h2>
<p>C’est notre note Google. On la met sur le site parce que c’est la chose la plus vraie qu’on peut dire sur nous, et elle a été écrite par nos clients, pas par nous.</p>
<h2>Nous joindre</h2>
<p>""" + ADDR + """, """ + CITY + """<br>""" + PHONE + """ · """ + PHONE2 + """</p>""",
 'en': """
<h1>About us</h1>
<p>Meuble Confort &amp; Style is a family furniture business in Montréal. We sell sectionals, mattresses, bedroom sets and dining sets online — and we deliver them ourselves.</p>
<h2>Why buy here</h2>
<p>A large online retailer will sell you the same sofa with a three-to-five-week wait and a curbside drop. Ours is fifteen minutes away, in our warehouse, and it can be in your living room within days — assembled, up your stairs, by two people you can call back if something is wrong.</p>
<h2>79 reviews, 5 out of 5</h2>
<p>That’s our Google rating. We put it on the site because it’s the truest thing we can say about ourselves, and our customers wrote it, not us.</p>
<h2>Reach us</h2>
<p>""" + ADDR + """, """ + CITY + """<br>""" + PHONE + """ · """ + PHONE2 + """</p>"""},

 # Québec Law 25. Every statement here describes what the code actually does:
 # checkout (api/checkout.js → Stripe), the CRM bridge (api/stripe-webhook.js →
 # GoHighLevel), the opt-in pixel and server-side Purchase (marquise.js, webhook),
 # hosting on Vercel, fonts from Google, product photos from Shopify's CDN.
 # Change the code, change this page.
 'confidentialite': {'fr': """
<h1>Politique de confidentialité</h1>
<p class="fineprint">Dernière mise à jour : 14 octobre 2026</p>
<p>Meuble Confort &amp; Style vend des meubles en ligne et les livre à Montréal, Laval et Longueuil. Cette politique explique quels renseignements personnels nous recueillons, pourquoi, avec qui nous les partageons et comment exercer vos droits, conformément à la <em>Loi sur la protection des renseignements personnels dans le secteur privé</em> du Québec.</p>
<h2>Responsable de la protection des renseignements personnels</h2>
<p><strong>""" + PRIVACY_OFFICER + """</strong>, propriétaire<br>
Courriel : <a href="mailto:""" + PRIVACY_EMAIL + """">""" + PRIVACY_EMAIL + """</a><br>
Téléphone : """ + PHONE + """<br>
Adresse postale : """ + ADDR + """, """ + CITY + """</p>
<h2>Ce que nous recueillons</h2>
<ul>
<li><strong>Quand vous commandez</strong> : votre nom, votre courriel, votre téléphone, vos adresses de facturation et de livraison, et le détail de la commande. Le paiement est traité par Stripe : nous ne voyons ni ne conservons jamais votre numéro de carte.</li>
<li><strong>Quand vous nous écrivez ou nous appelez</strong> (téléphone, Messenger, Instagram) : votre nom, vos coordonnées et le contenu de vos messages.</li>
<li><strong>Quand vous naviguez sur le site</strong> : notre hébergeur conserve des journaux techniques (adresse IP, type de navigateur, pages demandées). Votre panier et votre choix concernant les témoins sont gardés dans votre propre navigateur, pas chez nous.</li>
<li><strong>Seulement si vous acceptez les témoins</strong> : le pixel Meta enregistre les pages vues, les produits consultés, les ajouts au panier, le début du paiement et les achats.</li>
</ul>
<h2>Pourquoi</h2>
<ul>
<li>Traiter et encaisser votre commande, vous appeler pour fixer la livraison, livrer, et assurer le service après-vente et la garantie.</li>
<li>Répondre à vos questions.</li>
<li>Respecter nos obligations légales, notamment fiscales.</li>
<li>Avec votre consentement seulement : mesurer l’efficacité de nos publicités sur Facebook et Instagram.</li>
</ul>
<p>Nous ne vendons pas vos renseignements personnels.</p>
<h2>Témoins et publicité</h2>
<p>Le pixel Meta est désactivé par défaut : il ne se charge que si vous cliquez sur « Accepter » dans le bandeau des témoins. Si vous acceptez puis passez une commande, notre serveur transmet aussi l’achat à Meta avec votre courriel, votre téléphone, votre nom et votre adresse sous forme hachée (SHA-256, illisible pour Meta comme pour nous), ainsi que l’adresse IP et le navigateur utilisés lors de la commande. Si vous refusez, rien de tout cela n’est envoyé.</p>
<p>Vous pouvez changer d’avis en tout temps avec le lien « Témoins » au bas de chaque page. Si vous retirez votre consentement, le pixel cesse de se charger et les témoins de Meta déposés sur notre site sont effacés.</p>
<h2>Avec qui nous les partageons</h2>
<p>Seulement avec les entreprises qui nous fournissent un service, et seulement ce dont elles ont besoin :</p>
<ul>
<li><strong>Stripe</strong> — le paiement des commandes.</li>
<li><strong>HighLevel (LeadConnector)</strong> — notre logiciel de gestion de la clientèle, où sont gardés vos coordonnées, vos commandes et vos messages.</li>
<li><strong>Meta Platforms</strong> — les messages que vous nous envoyez par Messenger ou Instagram, et la mesure publicitaire si vous l’avez acceptée.</li>
<li><strong>Vercel</strong> — l’hébergement du site.</li>
<li><strong>Google Fonts et Shopify</strong> — les polices et les photos des produits sont chargées depuis leurs serveurs, qui reçoivent donc votre adresse IP.</li>
</ul>
<p>Notre équipe de livraison reçoit votre nom, votre adresse et votre téléphone pour vous livrer.</p>
<p>Ces fournisseurs sont en grande partie situés à l’extérieur du Québec, notamment aux États-Unis : vos renseignements peuvent y être hébergés et traités. Nous ne leur communiquons que ce qui est nécessaire au service rendu.</p>
<h2>Combien de temps nous les gardons</h2>
<p>Seulement le temps nécessaire aux fins décrites ci-dessus ou exigé par la loi. Pour une commande, cela comprend la durée de la garantie et la période de conservation exigée par les lois fiscales, soit six ans. Les renseignements sont ensuite détruits ou rendus anonymes.</p>
<h2>Vos droits</h2>
<p>Vous pouvez :</p>
<ul>
<li>savoir quels renseignements nous détenons sur vous et en obtenir une copie, y compris dans un format technologique structuré et couramment utilisé ;</li>
<li>les faire corriger s’ils sont inexacts, incomplets ou équivoques ;</li>
<li>retirer votre consentement ;</li>
<li>demander que nous cessions de les diffuser ou de les utiliser à des fins publicitaires.</li>
</ul>
<p>Écrivez à """ + PRIVACY_OFFICER + """ à <a href="mailto:""" + PRIVACY_EMAIL + """">""" + PRIVACY_EMAIL + """</a>. Nous répondons dans les 30 jours. Si vous n’êtes pas satisfait de notre réponse, vous pouvez vous adresser à la <a href="https://www.cai.gouv.qc.ca/" rel="noopener">Commission d’accès à l’information du Québec</a>.</p>
<h2>Sécurité</h2>
<p>Le site est servi en connexion chiffrée (HTTPS) et l’accès à vos renseignements est limité aux personnes qui en ont besoin pour vous servir. Si un incident de confidentialité présente un risque de préjudice sérieux, nous en avisons les personnes concernées et la Commission d’accès à l’information.</p>
<h2>Mineurs</h2>
<p>Le site ne s’adresse pas aux personnes de moins de 14 ans et nous ne recueillons pas sciemment leurs renseignements.</p>
<h2>Modifications</h2>
<p>Toute modification de cette politique sera publiée sur cette page, avec sa date.</p>""",
 'en': """
<h1>Privacy policy</h1>
<p class="fineprint">Last updated: October 14, 2026</p>
<p>Meuble Confort &amp; Style sells furniture online and delivers it to Montréal, Laval and Longueuil. This policy explains what personal information we collect, why, who we share it with, and how to exercise your rights under Québec’s <em>Act respecting the protection of personal information in the private sector</em>.</p>
<h2>Person in charge of personal information</h2>
<p><strong>""" + PRIVACY_OFFICER + """</strong>, owner<br>
Email: <a href="mailto:""" + PRIVACY_EMAIL + """">""" + PRIVACY_EMAIL + """</a><br>
Phone: """ + PHONE + """<br>
Mailing address: """ + ADDR + """, """ + CITY + """</p>
<h2>What we collect</h2>
<ul>
<li><strong>When you order</strong>: your name, email, phone, billing and delivery addresses, and what you ordered. Payment is handled by Stripe: we never see or store your card number.</li>
<li><strong>When you write or call us</strong> (phone, Messenger, Instagram): your name, your contact details and what you tell us.</li>
<li><strong>When you browse the site</strong>: our host keeps technical logs (IP address, browser type, pages requested). Your cart and your cookie choice are kept in your own browser, not by us.</li>
<li><strong>Only if you accept cookies</strong>: the Meta pixel records pages viewed, products viewed, add-to-cart, checkout start and purchases.</li>
</ul>
<h2>Why</h2>
<ul>
<li>To process and charge your order, call you to book delivery, deliver it, and provide after-sales service and warranty.</li>
<li>To answer your questions.</li>
<li>To meet our legal obligations, including tax law.</li>
<li>Only with your consent: to measure how our Facebook and Instagram ads perform.</li>
</ul>
<p>We do not sell your personal information.</p>
<h2>Cookies and advertising</h2>
<p>The Meta pixel is off by default: it only loads if you click “Accept” in the cookie banner. If you accept and then order, our server also reports the purchase to Meta with your email, phone, name and address in hashed form (SHA-256, unreadable to Meta and to us), along with the IP address and browser used for the order. If you decline, none of this is sent.</p>
<p>You can change your mind at any time with the “Cookies” link at the bottom of every page. If you withdraw consent, the pixel stops loading and the Meta cookies set on our site are deleted.</p>
<h2>Who we share it with</h2>
<p>Only with companies that provide a service to us, and only what they need:</p>
<ul>
<li><strong>Stripe</strong> — order payments.</li>
<li><strong>HighLevel (LeadConnector)</strong> — our customer management software, which holds your contact details, orders and messages.</li>
<li><strong>Meta Platforms</strong> — messages you send us through Messenger or Instagram, and ad measurement if you accepted it.</li>
<li><strong>Vercel</strong> — website hosting.</li>
<li><strong>Google Fonts and Shopify</strong> — fonts and product photos load from their servers, which therefore receive your IP address.</li>
</ul>
<p>Our delivery team receives your name, address and phone number to deliver your order.</p>
<p>These providers are largely located outside Québec, notably in the United States, so your information may be stored and processed there. We only share what the service requires.</p>
<h2>How long we keep it</h2>
<p>Only as long as needed for the purposes above or as required by law. For an order, that includes the warranty period and the retention period required by tax law, which is six years. The information is then destroyed or anonymized.</p>
<h2>Your rights</h2>
<p>You can:</p>
<ul>
<li>find out what information we hold about you and get a copy, including in a structured, commonly used technological format;</li>
<li>have it corrected if it is inaccurate, incomplete or ambiguous;</li>
<li>withdraw your consent;</li>
<li>ask us to stop disseminating it or using it for advertising.</li>
</ul>
<p>Write to """ + PRIVACY_OFFICER + """ at <a href="mailto:""" + PRIVACY_EMAIL + """">""" + PRIVACY_EMAIL + """</a>. We reply within 30 days. If you are not satisfied with our answer, you can contact the <a href="https://www.cai.gouv.qc.ca/" rel="noopener">Commission d’accès à l’information du Québec</a>.</p>
<h2>Security</h2>
<p>The site is served over an encrypted connection (HTTPS), and access to your information is limited to the people who need it to serve you. If a confidentiality incident presents a risk of serious harm, we notify the people concerned and the Commission d’accès à l’information.</p>
<h2>Minors</h2>
<p>The site is not directed at people under 14, and we do not knowingly collect their information.</p>
<h2>Changes</h2>
<p>Any change to this policy will be published on this page, with its date.</p>"""},
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
          "about": {"@type": "OnlineStore", "name": "Meuble Confort & Style",
                    "telephone": "+1-514-279-4600",
                    "address": {"@type": "PostalAddress", "addressLocality": "Montréal",
                                "addressRegion": "QC", "addressCountry": "CA"}},
          "breadcrumb": {"@type": "BreadcrumbList", "itemListElement": [
              {"@type": "ListItem", "position": 1, "name": COPY[lang]['crumb_home'],
               "item": SITE + url(lang)},
              {"@type": "ListItem", "position": 2, "name": name,
               "item": SITE + url(lang, PAGES[key][lang][1])}]}}
    return shell(lang, f'{name} | Meuble Confort & Style', txt[:180],
                 url(lang, PAGES[key][lang][1]), url(other, PAGES[key][other][1]), body, ld)

def pdp_options(p, lang):
    """The priced option rows of a PDP — ONE source for both the page and the
    checkout price map, so what the customer sees and what Stripe charges can
    never disagree. Returns (colours, kind, opts) with opts as (label, price).

    The first option is pre-selected on the page, so it must carry the price
    the card and the headline lead with — the list is stably reordered to put
    that option first, and the build fails if no option carries it."""
    colours = [v for v in dict.fromkeys(x['colour'] if lang == 'fr' else x['colour_en']
                                        for x in p['variants'] if x['colour'])]
    sizes = [v for v in dict.fromkeys(x['size'] if lang == 'fr' else x['size_en']
                                      for x in p['variants'] if x['size'])]
    # an add-on must never sit in the price picker: choosing "Option de
    # rangement" would drop a $780 bed to $180 on screen
    sellable = [v for v in p['variants'] if not v.get('accessory')]
    kind, opts = None, []
    if sizes:
        kind = 'size'
        for s in sizes:
            pr = next((x['price'] for x in p['variants']
                       if (x['size'] if lang == 'fr' else x['size_en']) == s), p['price'])
            opts.append((s, pr))
    elif not colours and len(sellable) > 1:
        kind = 'config'
        opts = [(v['label'], v['price']) for v in sellable[:6]]
    opts.sort(key=lambda t: abs(t[1] - p['price']) > 0.005)   # stable: leading price first
    assert not opts or abs(opts[0][1] - p['price']) < 0.005, \
        f"{p['slug']} ({lang}): no option carries the leading price {p['price']}: {opts}"
    return colours, kind, opts

def build_merci(lang):
    """Where Stripe sends people after a successful payment. The inline
    script empties the cart before marquise.js paints the count."""
    c = COPY[lang]
    path = url(lang, 'merci' if lang == 'fr' else 'thank-you')
    alt = url('en' if lang == 'fr' else 'fr', 'thank-you' if lang == 'fr' else 'merci')
    body = f'''<div class="wrap merci" data-purchase>
 <span class="chip boxed go"><span class="dot"></span>{E(c['merci_badge'])}</span>
 <h1>{E(c['merci_h'])}</h1>
 <p>{E(c['merci_p'])}</p>
 <a class="btn btn-primary" href="{url(lang)}">{E(c['merci_cta'])}</a>
</div>
<script>try{{localStorage.removeItem('mqCart')}}catch(e){{}}</script>'''
    return shell(lang, f"{c['merci_h']} | Meuble Confort & Style", c['merci_p'][:180],
                 path, alt, body)

def write_price_map(cat):
    """api/prices.json — what the checkout function charges from. Keyed by
    slug (split-set pieces share their parent's Shopify id; the slug is the
    one key unique per product). The variant map holds EXACTLY the option
    labels pdp_options() renders, in both languages — the same code path that
    paints the button prices — so the label the browser reports resolves to
    the price the customer was shown, or to nothing at all."""
    nrm = lambda s: re.sub(r'[^a-z0-9]', '', (s or '').lower())
    pm = {}
    for p in cat:
        v = {}
        for lang in ('fr', 'en'):
            for lbl, pr in pdp_options(p, lang)[2]:
                k = nrm(lbl)
                if not k:
                    continue
                assert v.get(k, round(pr * 100)) == round(pr * 100), \
                    f"{p['slug']}: option '{lbl}' would map to two different prices"
                v[k] = round(pr * 100)
        pm[p['slug']] = {'fr': p['name_fr'], 'en': p['name_en'],
                            'img': img(p['images'][0], 400),
                            'p': round(p['price'] * 100), 'v': v}
    api_dir = os.path.join(HERE, '..', 'api')
    os.makedirs(api_dir, exist_ok=True)
    with open(os.path.join(api_dir, 'prices.json'), 'w', encoding='utf-8') as f:
        json.dump(pm, f, ensure_ascii=False, separators=(',', ':'))
    return len(pm)

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
    # before any page, any price map, any structured data
    cat = apply_tax_inclusive(cat)
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
        # the post-payment page — deliberately not in the sitemap
        write(url(lang, 'merci' if lang == 'fr' else 'thank-you'), build_merci(lang)); n += 1

    # root: send people to French, the store's primary language
    write('/', '<!doctype html><html lang="fr"><head><meta charset="utf-8">'
               '<title>Meuble Confort &amp; Style</title>' + META_DOMAIN_TAG +
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

    priced = write_price_map(cat)

    built = sum(1 for r, _, fs in os.walk(DIST) for f in fs if f == 'index.html')
    assert built == n + 1, f'wrote {n}+1 pages but dist/ holds {built} — orphans left behind'
    print(f'{n} pages written to dist/ (no orphans)')
    print(f'  api/prices.json: {priced} products for the checkout function')
    print(f'  {len(cat)} products × 2 languages')
    print(f'  sitemap: {len(urls)} URLs')
    print(f'  redirects: {len(redirects)-1} rules')

if __name__ == '__main__':
    main()
