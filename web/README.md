# Marquise — meubleconfort.com, rebuilt

A working bilingual storefront for **Meuble Confort & Style**, generated from the
store's own live catalogue. 362 pages, real products, real photography, real prices.

## Run it

```bash
python3 -m http.server 4173 --directory web/dist
```

Then open <http://localhost:4173/fr/>. (Or use the `marquise` config in
`.claude/launch.json`.)

## Rebuild it

```bash
cd web
curl -s "https://meubleconfort.com/products.json?limit=250" -o raw1.json
curl -s "https://meubleconfort.com/products.json?limit=250&page=2" -o raw2.json
python3 normalize.py     # raw feed  -> catalogue.json
python3 build.py         # catalogue -> dist/
```

### Which origin the build claims

Canonicals, hreflang, `og:` tags and the sitemap are absolute, so the build has
to be told where it lives:

```bash
python3 build.py                                          # production
SITE_URL=https://confort-demo.vercel.app python3 build.py # the demo
```

The committed `dist/` is built for the **demo** origin. Rebuild without
`SITE_URL` before pointing the real domain at it, or every canonical will send
crawlers to the demo.

| File | What it does |
|---|---|
| `normalize.py` | Parses the live feed: human names for the 24 SKU-titled products, one canonical category per item, dimensions pulled out of the description prose, colours/materials/features, variant options split back into Colour + Size, and the break-down model the fit check runs on. |
| `build.py` | Emits every page in both languages, plus `sitemap.xml`, `robots.txt` and `redirects.txt`. |
| `dist/assets/marquise.css` | The design system. Light and dark, both themes explicit. |
| `dist/assets/marquise.js` | Delivery dates, facets, gallery, variant pricing, fit check. |

## Brand

Colour is sampled from the store's own logo, not invented:

Black and red, at the client's request.

| Token | Light | Dark | Role |
|---|---|---|---|
| `--brand` | `#C62828` | `#E85A5F` | the red — the store's own theme primary |
| `--ink` | `#0D0D0D` | `#F2F1F0` | true black |
| `--paper` | `#F4F4F3` | `#0E0E0E` | neutral ground |

The red is not invented: `#C62828` is already the `--color-primary` in the
store's live Shopify theme. The `#B30000` announcement-bar red is retired so the
identity reads as a single red.

**Red is the only chroma in the system.** Stock, fit and warning states are
carried by weight and neutral value rather than by hue — the green "in stock"
chip and the amber "tight, but it goes" state are gone. That restraint is what
stops a red-and-black furniture site reading as a clearance flyer, which is
exactly the trap the current site fell into. If the semantic green is wanted
back for scannability, it is one token (`--signal`) in each theme block.

Every text pair clears WCAG AA in both themes; the numbers are checked, not
assumed.

Type: **Fraunces** for headlines, product names and reviews; **Familjen Grotesk**
for navigation, prices, buttons and body; **IBM Plex Mono** for labels, specs, SKUs
and dates. The serif carries what a person feels, the sans carries what they have
to read in order to buy.

The rust appears roughly three times on any page — a hairline before a section
label, one italic word in a headline, the underline on a link. That restraint is
what reads as high end; the photography does the selling.

## What's in it

- **`/fr/` and `/en/`** — both fully built and indexed, reciprocal `hreflang`, no
  translation widget. 10,668 internal links, zero broken.
- **Stock status on every card** — *En stock à Montréal* / *In stock in Montréal*,
  or *Sur commande — 2 à 3 semaines* when a product has no available variant.
  (Right now every product has at least one available variant, so the back-order
  chip never renders — the path is there for when stock runs out.)

  **Date-certain delivery is switched off.** `SHOW_DELIVERY_DATES = False` in
  `build.py`. The mechanic is still wired end to end — the weekday calculation,
  the 2pm cutoff, the cached-page guard — but nothing on the site claims a day.
  It needs two things the business does not have yet: inventory that is true at
  the SKU level, and a delivery calendar the site can read. Flip the flag when
  both exist and the chips go back to naming a weekday, with no other change.
- **Monthly price everywhere** — price ÷ 36, on cards and product pages.
- **The fit check** — on all 83 products whose dimensions could be parsed. It models
  how a piece actually comes apart: beds, tables and desks break into flat panels and
  clear almost anything; sectionals break into modules that keep their depth. When
  nothing fits it says so and gives the phone number rather than inventing options,
  and any alternatives it does offer stay in the same product family.
- **Real facets** — type, colour, material, price band, in stock, on sale. Filter
  state lives in the URL, so a filtered listing is a shareable link.
- **Schema** — `FurnitureStore` with hours and rating on the homepage, `Product` +
  `Offer` + `AggregateRating` on all 342 product pages, `BreadcrumbList` on listings.
- **`redirects.txt`** — 177 rules mapping every retired URL (`/collections/chanbre`,
  the emoji handle, all the `/products/if-XXXX` slugs) to its replacement.

## The hero

Three rooms pinned for the length of the section, cross-fading as you scroll,
with a rail on the right that is also navigation. Each panel names a room, gives
its live piece count and links to that category — the hero does work, it isn't
just atmosphere.

**The room photographs are AI-generated** (Higgsfield `soul_location`, three
scenes chosen from six variants, in `web/gen/`). They are art direction, not
inventory: no piece in them is a product the store actually sells. They are fine
as a hero — a hero sells a feeling, and every product image on the site is the
store's own — but **they must be replaced by a real shoot of the Saint-Hubert
showroom before launch**, and they must never migrate onto a product page.

Optimised to WebP at three widths, 242 KB for all nine files.

Progressive enhancement, in that order:

1. **No JavaScript** — an ordinary full-bleed hero showing room one. The section
   is a normal height; nothing is hidden waiting to be revealed.
2. **JavaScript** — the section becomes 280vh, the stage pins, the rooms
   cross-fade, the rail tracks.
3. **`prefers-reduced-motion`** — back to the static hero, and the scroll cue
   is hidden.

Two things worth knowing if you touch this code:

- The paint is driven by **both** a visibility-gated rAF loop and a scroll
  listener. Scroll events silently stopped reaching `window` once `html` had
  `overflow-x: hidden`, because that makes the root its own scroll container —
  it is now `overflow-x: clip`, which clips without creating one.
- Captions **do not cross-fade**; the outgoing one leaves before the incoming
  one arrives. Fading text over text turns two room names into mush.

## Buy now, pay later

Klarna, Afterpay and Affirm appear on product pages, in the footer payment row,
and as a comparison table on the financing page — in both languages.

Eligibility is computed from the price, and recomputed when the shopper changes
variant, because pay-in-4 caps out well below the price of a sectional:

| Price | What shows |
|---|---|
| $1,258 | `314,50 $` — Klarna · Afterpay, plus Affirm monthly |
| $1,688 | `422,00 $` — Afterpay only (past Klarna's cap), plus Affirm |
| $2,080 | Affirm monthly only — pay-in-4 disappears entirely |

Thresholds live in one `BNPL` list at the top of `build.py`. **They are
placeholders.** They decide which option appears on which product and must be
replaced with the real caps from your Canadian merchant agreements.

Three things have to happen before this is switched on:

1. **The merchant accounts do not exist.** Each of the three needs its own
   application and approval. Until then this is display, not a payment method,
   and the checkout would not honour it.
2. **Québec regulates BNPL as consumer credit.** Unlike the rest of Canada, the
   *Consumer Protection Act* treats many buy-now-pay-later offers as credit,
   which brings disclosure obligations, in French. A Québec lawyer should review
   both this page and the product-page messaging before it goes live. The
   financing page says so on its face, in both languages.
3. **Merchant fees run roughly 3–7% of the transaction.** Against furniture
   margins that is a real number, not a rounding error.

Provider names are set as **type, not logos**. Klarna, Afterpay and Affirm each
publish a brand kit with mandatory logo, clear-space and colour rules; drop the
official assets into `.bnpl-marks` and `.paymark` rather than approximating
their trademarks.

## Known gaps — deliberate, not oversights

1. **88 of 171 products have no parsed dimensions**, so they get no fit check. The
   numbers are buried in inconsistent prose in the live descriptions. This is the
   Phase 2 data task: move dimensions into structured fields at the source.
2. **English product descriptions are generated from the parsed attributes**, not
   translated. The French copy is genuinely good and stays; the English needs a
   writer, not a machine.
3. **The cart is a counter.** There is no checkout — this is a front end. The real
   build runs on the existing Shopify store, where checkout, inventory, tax and
   payments already work.
4. **The returns policy is a template.** The store has never written one down. The
   page says so, in both languages, and needs the owner's sign-off.
5. **Financing rates and the lender's name are blank.** Legally required in Québec
   and the first thing customers look for. The page flags it.
6. **Photography.** Product imagery is the store's own, from the Shopify CDN. The
   hero rooms are AI-generated stand-ins (see above) and the 23 single-image
   products still need a real shoot.

## The IFDC catalogue

`ifdc_fetch.py` harvests International Furniture Distribution Centre's dealer
catalogue from their sitemap into `ifdc-raw.json` — **976 products, 948 of which
are not on the site today.**

Their product pages are a Wix store and carry a JSON-LD block with a code and a
photograph **and nothing else**. Descriptions, dimensions, categories and prices
load client-side and are not in the HTML. So these deliberately do *not* become
product pages: with no dimensions there is no fit check, with no attributes there
are no filters, and with no margins there is no price. 948 hollow product pages
would bury the 171 real ones.

They live at `/fr/catalogue/` and `/en/catalogue/` instead — one browsable index,
filterable by SKU family and searchable by code, every tile marked *prix sur
demande*. It shows the range honestly without pretending to be a shop.

Families are derived from the SKU prefix (`IF` upholstery, `T` tables, `C`
chairs, `B` bunk beds, `ST`, plus named collections), because IFDC's own room
categories are not in the page source.

**When the margins arrive**, these graduate into the main catalogue: add price
and the parsed attributes to the importer and they become ordinary products,
fit check and all.
