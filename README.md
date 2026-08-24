# Meuble Confort & Style — Marquise

A working bilingual storefront for [Meuble Confort & Style](https://meubleconfort.com),
7566 rue Saint-Hubert, Montréal — generated from the store's own live product feed.

**362 pages · FR + EN · 171 products · 0 broken links**

## Run it

```bash
python3 -m http.server 4173 --directory web/dist
```

Then open <http://localhost:4173/fr/>.

## Rebuild it

```bash
cd web
python3 normalize.py   # live Shopify feed -> catalogue.json
python3 build.py       # catalogue.json    -> dist/
```

`web/dist/` is generated output — never hand-edit it. Source lives in
`web/normalize.py`, `web/build.py` and `web/assets/`.

## What's here

| Path | What |
|---|---|
| `web/` | The site: build scripts, source assets, and generated `dist/` |
| `web/README.md` | Full documentation — brand, mechanics, known gaps |
| `marquise-concept.html` | The audit and concept document behind the build |

## Read this before launch

`web/README.md` lists the open items in full. The ones that need a decision from
the business rather than more code:

- The **returns policy** has never been written down. The page is a template.
- **Financing rates and the lender's name** are blank — legally required in Québec.
- **Buy-now-pay-later** (Klarna, Afterpay, Affirm) is displayed but not connected;
  no merchant accounts exist yet, and Québec regulates these as consumer credit.
- The **hero room photographs are AI-generated** stand-ins, not real inventory.
  They need replacing with a shoot of the actual showroom.

## Not in this repository

`catalog/` — a 837 MB product catalogue belonging to **Meubles Navcan**, a
different business that happens to share the working folder. It is git-ignored
deliberately.
