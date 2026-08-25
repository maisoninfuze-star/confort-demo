# -*- coding: utf-8 -*-
"""Harvest the IFDC dealer catalogue into ifdc-raw.json.

IFDC is a Wix store: each product page carries one JSON-LD Product block with a
name and an image, and nothing else — descriptions, dimensions and categories
are loaded client-side and are not in the HTML. So this gets the code and the
photograph, which is what the site can honestly show until the dealer margins
arrive and real product data comes with them.
"""
import re, json, gzip, io, urllib.request, concurrent.futures as cf, sys, os

HERE = os.path.dirname(os.path.abspath(__file__))
SITEMAP = 'https://www.ifdc.ca/store-products-sitemap.xml'
UA = {'User-Agent': 'Mozilla/5.0 (compatible; MCS-dealer-import/1.0)',
      'Accept-Encoding': 'gzip'}

def get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
        if r.headers.get('Content-Encoding') == 'gzip':
            raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        return raw.decode('utf-8', 'ignore')

def first_image(img):
    if isinstance(img, list): img = img[0] if img else None
    if isinstance(img, dict): img = img.get('contentUrl')
    return img if isinstance(img, str) else None

def big(url):
    """Wix serves a fitted derivative; ask for a usable size instead of 500px."""
    return re.sub(r'/v1/fit/w_\d+,h_\d+', '/v1/fit/w_1200,h_1200', url or '')

def one(url):
    slug = url.rsplit('/', 1)[-1]
    try:
        h = get(url)
    except Exception as e:
        return {'slug': slug, 'error': str(e)[:60]}
    m = re.search(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', h, re.S)
    if not m:
        return {'slug': slug, 'error': 'no ld+json'}
    try:
        d = json.loads(m.group(1))
    except Exception:
        return {'slug': slug, 'error': 'bad ld+json'}
    for it in (d if isinstance(d, list) else [d]):
        if it.get('@type') == 'Product':
            off = it.get('offers') or {}
            if isinstance(off, list): off = off[0] if off else {}
            return {'slug': slug, 'name': it.get('name'),
                    'image': big(first_image(it.get('image'))),
                    'available': 'InStock' in str(off.get('availability', '')),
                    'url': url}
    return {'slug': slug, 'error': 'no Product'}

def main():
    urls = [u for u in re.findall(r'<loc>([^<]+)</loc>', get(SITEMAP))
            if '/product-page/' in u]
    print(f'{len(urls)} product pages', flush=True)
    out = []
    with cf.ThreadPoolExecutor(8) as ex:
        for i, r in enumerate(ex.map(one, urls), 1):
            out.append(r)
            if i % 100 == 0:
                print(f'  {i}/{len(urls)}', flush=True)
    json.dump(out, open(os.path.join(HERE, 'ifdc-raw.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    ok = [r for r in out if not r.get('error')]
    print(f'done: {len(ok)} products, {len(out)-len(ok)} failed', flush=True)

if __name__ == '__main__':
    main()
