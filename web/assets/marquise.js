/* Marquise storefront behaviour: delivery dates, facets, gallery, fit check. */
(function () {
  'use strict';
  var L = document.documentElement.lang === 'en' ? 'en' : 'fr';
  var T = {
    fr: {
      days: ['dimanche','lundi','mardi','mercredi','jeudi','vendredi','samedi'],
      months: ['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre'],
      at: 'Chez vous ', order: 'Sur commande — 2 à 3 semaines',
      results: function (n) { return n + (n === 1 ? ' produit' : ' produits'); },
      none: 'Aucun produit ne correspond. Retirez un filtre, ou appelez-nous au 514-279-4600 — on l’a peut-être en entrepôt.',
      added: 'Ajouté au panier',
      remove: 'Retirer',
      qless: 'Diminuer la quantité', qmore: 'Augmenter la quantité',
      paywait: 'Redirection vers le paiement…',
      payerr: 'Le paiement n’a pas pu démarrer. Réessayez, ou appelez-nous au 514-279-4600.',
      fits: 'Ça rentre', tight: 'Serré — mais ça passe', nofit: 'Ne rentre pas par là',
      fitsB: 'Livré monté, rien à faire.',
      tightB: function (p, w, flat) { return flat
        ? 'On le démonte en ' + p + ' panneaux à plat — ils passent partout — et on le remonte chez vous, sans frais.'
        : 'On le démonte en ' + p + ' modules — le plus large fait ' + w + ' po — et on le remonte chez vous, sans frais.'; },
      nofitB: function (w) { return 'Il faut ' + w + ' po de dégagement au minimum.'; },
      alts: 'Ceux-ci rentrent chez vous :',
      noalts: 'On n’a rien d’assez étroit en ligne pour cette entrée. Appelez-nous au 514-279-4600 — la salle de montre en a plus que le site.',
      est: 'Estimation à partir des dimensions du fabricant. Un doute ? Appelez-nous, on vérifie avec vous.'
    },
    en: {
      days: ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'],
      months: ['January','February','March','April','May','June','July','August','September','October','November','December'],
      at: 'At your place ', order: 'Made to order — 2 to 3 weeks',
      results: function (n) { return n + (n === 1 ? ' product' : ' products'); },
      none: 'Nothing matches. Drop a filter, or call 514-279-4600 — we may have it in the warehouse.',
      added: 'Added to cart',
      remove: 'Remove',
      qless: 'Decrease quantity', qmore: 'Increase quantity',
      paywait: 'Opening secure checkout…',
      payerr: 'Checkout could not start. Try again, or call us at 514-279-4600.',
      fits: 'It fits', tight: 'Tight — but it goes', nofit: 'Won’t go that way',
      fitsB: 'Delivered assembled — nothing for you to do.',
      tightB: function (p, w, flat) { return flat
        ? 'We take it apart into ' + p + ' flat panels — they go anywhere — and rebuild it inside, free.'
        : 'We take it apart into ' + p + ' modules — the widest is ' + w + '" — and rebuild it inside, free.'; },
      nofitB: function (w) { return 'You need at least ' + w + '" of clearance.'; },
      alts: 'These will fit:',
      noalts: 'We have nothing narrow enough online for that entrance. Call 514-279-4600 — the showroom holds more than the site.',
      est: 'Estimated from the manufacturer’s dimensions. Not sure? Call us and we’ll check it with you.'
    }
  }[L];


  /* ── opening splash ─────────────────────────────────────────────
     The animation is entirely CSS; script only records that it has run and
     retires the node. A splash that fails to lift traps the whole page behind
     a scroll lock, so there are four independent ways out: the animation
     ending, a timeout, any input from the visitor, and a hash change out of
     the frozen review mode. */
  var splash = document.getElementById('splash');
  if (splash) {
    var isHold = function () { return location.hash === '#introhold'; };
    var retired = false;
    var retire = function () {
      if (retired || !splash.isConnected) return;
      retired = true;
      splash.classList.add('done');
      splash.remove();
    };
    var arm = function () {
      splash.addEventListener('animationend', function (e) {
        if (e.animationName === 'splash-leave') retire();
      });
      setTimeout(retire, 5000);
    };

    try { sessionStorage.setItem('mcsIntro', '1'); } catch (e) {}

    if (document.documentElement.classList.contains('intro-skip')) {
      retire();
    } else if (isHold()) {
      splash.classList.add('hold');
    } else {
      arm();
    }

    // let anyone out early, and never strand a visitor behind the overlay
    ['pointerdown', 'keydown', 'wheel', 'touchstart'].forEach(function (ev) {
      addEventListener(ev, retire, { once: true, passive: true });
    });
    // leaving #introhold releases the freeze without needing a reload
    addEventListener('hashchange', function () {
      if (!isHold() && !retired) { splash.classList.remove('hold'); arm(); }
    });
  }

  /* ── delivery date ──────────────────────────────────────────────
     Trucks run Wednesday and Saturday. Orders placed before 2pm make
     the next run. Recomputed in the browser so a cached page is never
     promising a date that has already passed. */
  function nextDelivery() {
    var now = new Date();
    var d = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    if (now.getHours() >= 14) d.setDate(d.getDate() + 1);
    for (var i = 0; i < 14; i++) {
      d.setDate(d.getDate() + 1);
      if (d.getDay() === 3 || d.getDay() === 6) return d;
    }
    return d;
  }
  function fmt(d) {
    return L === 'fr'
      ? T.days[d.getDay()] + ' ' + d.getDate() + ' ' + T.months[d.getMonth()]
      : T.days[d.getDay()] + ', ' + T.months[d.getMonth()].slice(0, 3) + ' ' + d.getDate();
  }
  // Only elements explicitly asking for a date get one. When date-certain
  // delivery is switched off server-side the chip ships its own final text and
  // nothing here overwrites it.
  var dated = document.querySelectorAll('[data-deliver="stock"]');
  if (dated.length) {
    var DATE = fmt(nextDelivery());
    [].forEach.call(dated, function (el) { el.textContent = T.at + DATE; });
  }

  function toast(msg) {
    var t = document.createElement('div');
    t.textContent = msg;
    t.style.cssText = 'position:fixed;left:50%;bottom:26px;transform:translateX(-50%);z-index:200;' +
      'background:var(--ink);color:var(--paper);padding:12px 20px;border-radius:3px;' +
      'font-family:var(--f-mono);font-size:12px;letter-spacing:.06em;box-shadow:var(--shadow)';
    document.body.appendChild(t);
    setTimeout(function () { t.remove(); }, 2200);
  }

  /* ── cart ───────────────────────────────────────────────────────
     Items live in localStorage; the drawer renders them, and checkout POSTs
     them to /api/checkout. The prices stored here are display only — the
     function reprices every line from its own map before charging. */
  var CART_KEY = 'mqCart';
  function cartLoad() {
    try {
      var c = JSON.parse(localStorage.getItem(CART_KEY));
      return Array.isArray(c) ? c : [];
    } catch (e) { return []; }
  }
  function cartSave(c) {
    try {
      localStorage.setItem(CART_KEY, JSON.stringify(c));
      localStorage.removeItem('mq-cart'); // the old prototype counter
    } catch (e) {}
  }
  var drawer = document.getElementById('cartdrawer');
  var veil = document.getElementById('cartveil');

  function renderCart() {
    var c = cartLoad();
    var nItems = c.reduce(function (s, i) { return s + i.q; }, 0);
    [].forEach.call(document.querySelectorAll('[data-cart-count]'), function (e) { e.textContent = nItems; });
    if (!drawer) return;
    var box = document.getElementById('cartitems');
    var sum = 0;
    box.innerHTML = '';
    c.forEach(function (i, idx) {
      sum += i.p * i.q;
      var row = document.createElement('div');
      row.className = 'cart-item';
      row.innerHTML =
        '<a class="ci-shot"><img alt="" width="64" height="64" loading="lazy"></a>' +
        '<div class="ci-body"><a class="ci-name"></a><div class="ci-opts"></div>' +
        '<div class="ci-row"><span class="ci-qty">' +
        '<button type="button" data-dq="-1">−</button><b></b>' +
        '<button type="button" data-dq="1">+</button></span>' +
        '<b class="ci-price"></b></div></div>' +
        '<button class="ci-x" type="button" data-rm>×</button>';
      // everything from storage goes in as text or a property, never as markup
      row.querySelector('.ci-shot').href = i.url;
      row.querySelector('.ci-shot img').src = i.img;
      var nameEl = row.querySelector('.ci-name');
      nameEl.href = i.url; nameEl.textContent = i.name;
      var optsEl = row.querySelector('.ci-opts');
      if (i.opts) { optsEl.textContent = i.opts; } else { optsEl.remove(); }
      row.querySelector('.ci-qty b').textContent = i.q;
      row.querySelector('.ci-price').textContent = money2(i.p * i.q);
      row.querySelector('[data-rm]').setAttribute('aria-label', T.remove);
      row.querySelector('[data-dq="-1"]').setAttribute('aria-label', T.qless);
      row.querySelector('[data-dq="1"]').setAttribute('aria-label', T.qmore);
      row.addEventListener('click', function (e) {
        var b = e.target.closest('button'); if (!b) return;
        // find the line by key, not by render-time index — another tab (or
        // the merci page) may have reshaped the cart since this row painted
        var cc = cartLoad(), pos = -1;
        cc.forEach(function (x, j) { if (pos < 0 && x.k === i.k) pos = j; });
        if (pos < 0) { renderCart(); return; }
        if (b.hasAttribute('data-rm')) { cc.splice(pos, 1); }
        else { cc[pos].q = Math.max(1, Math.min(9, cc[pos].q + parseInt(b.dataset.dq, 10))); }
        cartSave(cc); renderCart();
      });
      box.appendChild(row);
    });
    document.getElementById('cartempty').hidden = c.length > 0;
    document.getElementById('cartfoot').hidden = !c.length;
    var sumEl = document.getElementById('cartsum');
    if (sumEl) sumEl.textContent = money2(sum);
  }

  var cartOpener = null;
  function openCart() {
    if (!drawer) return;
    renderCart();
    cartOpener = document.activeElement;
    drawer.classList.add('open');
    drawer.setAttribute('aria-hidden', 'false');
    veil.hidden = false;
    document.documentElement.classList.add('cart-lock');
    var x = drawer.querySelector('.cart-x');
    if (x) x.focus();
  }
  function closeCart() {
    if (!drawer) return;
    drawer.classList.remove('open');
    drawer.setAttribute('aria-hidden', 'true');
    veil.hidden = true;
    document.documentElement.classList.remove('cart-lock');
    if (cartOpener && cartOpener.focus) { cartOpener.focus(); cartOpener = null; }
  }
  [].forEach.call(document.querySelectorAll('[data-cart-open]'), function (b) {
    b.addEventListener('click', openCart);
  });
  [].forEach.call(document.querySelectorAll('[data-cart-close]'), function (b) {
    b.addEventListener('click', closeCart);
  });
  if (veil) veil.addEventListener('click', closeCart);
  addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && drawer && drawer.classList.contains('open')) closeCart();
  });

  [].forEach.call(document.querySelectorAll('[data-add]'), function (b) {
    b.addEventListener('click', function () {
      var opts = [], pv = '';
      // the stored price comes from the pressed priced option itself — the
      // add button's dataset is only the fallback for one-price products
      var price = parseFloat(b.dataset.price) || 0;
      [].forEach.call(document.querySelectorAll('[data-optgroup]'), function (g) {
        var sel = g.querySelector('.opt[aria-pressed="true"]');
        if (!sel) return;
        var lbl = sel.dataset.vlabel || sel.textContent.trim();
        opts.push(lbl);
        if (sel.dataset.price) { pv = lbl; price = parseFloat(sel.dataset.price); }
      });
      var c = cartLoad();
      var key = b.dataset.id + '|' + opts.join(' · ');
      var hit = null;
      c.forEach(function (i) { if (i.k === key) hit = i; });
      if (hit) { hit.q = Math.min(9, hit.q + 1); }
      else {
        c.push({ k: key, id: b.dataset.id, name: b.dataset.name, img: b.dataset.img,
                 url: b.dataset.url, opts: opts.join(' · '), pv: pv,
                 p: price, q: 1 });
      }
      cartSave(c);
      openCart();
    });
  });

  var payBtn = document.getElementById('cartpay');
  var payBase = payBtn ? payBtn.textContent : '';
  if (payBtn) payBtn.addEventListener('click', function () {
    var c = cartLoad();
    if (!c.length) return;
    var base = payBtn.textContent;
    payBtn.disabled = true;
    payBtn.textContent = T.paywait;
    // the slashed path is the canonical one under trailingSlash — calling it
    // directly saves the 308 hop the unslashed POST provokes
    fetch('/api/checkout/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lang: L, items: c.map(function (i) {
        return { id: i.id, pv: i.pv, opts: i.opts, q: i.q };
      }) })
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (d && d.url) { location.href = d.url; }
      else { throw new Error('checkout'); }
    }).catch(function () {
      payBtn.disabled = false;
      payBtn.textContent = base;
      toast(T.payerr);
    });
  });

  renderCart();

  // Back from Stripe restores this page from bfcache with the pay button
  // still disabled and the old cart painted — reset both.
  addEventListener('pageshow', function (e) {
    if (!e.persisted) return;
    if (payBtn) { payBtn.disabled = false; payBtn.textContent = payBase; }
    renderCart();
  });
  // another tab edited the cart (or the merci page cleared it)
  addEventListener('storage', function (e) {
    if (e.key === CART_KEY || e.key === null) renderCart();
  });

  /* ── variant options ────────────────────────────────────────── */
  [].forEach.call(document.querySelectorAll('[data-optgroup]'), function (g) {
    g.addEventListener('click', function (e) {
      var b = e.target.closest('.opt'); if (!b) return;
      [].forEach.call(g.querySelectorAll('.opt'), function (o) { o.setAttribute('aria-pressed', o === b); });
      if (!b.dataset.price) return;
      var price = parseFloat(b.dataset.price);
      var p = document.querySelector('[data-price-now]');
      if (p) p.textContent = money(price);
      // The financing offer has a floor, so a variant can cross it in either
      // direction: show the line only while the chosen price clears it. No
      // amount is ever written — the page states that financing exists, not
      // what it would cost.
      var finBox = document.querySelector('[data-fin]');
      if (finBox) finBox.hidden = price < ((BNPL && BNPL.finMin) || 0);
      // the add button carries what the cart will store
      var add = document.querySelector('[data-add]');
      if (add) add.dataset.price = price;
      paintBnpl(price);
    });
  });
  /* Eligibility follows the chosen variant: switching from a Double to a King
     can push a price past a pay-in-4 cap, and that offer has to disappear when
     it does. Only eligibility is painted — never an instalment amount, which
     would be a credit quote the page is not allowed to make. */
  var BNPL = null;
  var bnplEl = document.getElementById('bnpldata');
  if (bnplEl) { try { BNPL = JSON.parse(bnplEl.textContent); } catch (e) { BNPL = null; } }

  function money2(v) {
    return L === 'fr'
      ? v.toLocaleString('fr-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' $'
      : '$' + v.toLocaleString('en-CA', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  function paintBnpl(price) {
    var box = document.querySelector('[data-bnpl]');
    if (!box || !BNPL) return;
    var fits = function (kind) {
      return BNPL.options.filter(function (o) {
        return o.kind === kind && price >= o.lo && price <= o.hi;
      });
    };
    var p4 = fits('pay4'), mo = fits('monthly');
    var row4 = box.querySelector('[data-bnpl-pay4]');
    var rowM = box.querySelector('[data-bnpl-mo]');
    if (row4) {
      var r = row4.closest('.bnpl-row');
      r.hidden = !p4.length;
      var marks = r.querySelector('.bnpl-marks');
      if (p4.length && marks) {
        marks.textContent = p4.map(function (o) { return o.name; }).join(' · ');
      }
    }
    if (rowM) rowM.closest('.bnpl-row').hidden = !mo.length;
    box.hidden = !p4.length && !mo.length;
  }

  function money(v) {
    return L === 'fr'
      ? v.toLocaleString('fr-CA', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) + ' $'
      : '$' + v.toLocaleString('en-CA', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  }

  /* ── gallery ────────────────────────────────────────────────── */
  var gal = document.querySelector('.gal');
  if (gal) {
    var main = gal.querySelector('.gal-main img');
    gal.addEventListener('click', function (e) {
      var b = e.target.closest('.gal-thumbs button'); if (!b) return;
      main.src = b.dataset.full; main.alt = b.querySelector('img').alt;
      [].forEach.call(gal.querySelectorAll('.gal-thumbs button'), function (t) {
        if (t === b) { t.setAttribute('aria-current', 'true'); } else { t.removeAttribute('aria-current'); }
      });
    });
  }

  /* ── fit check ──────────────────────────────────────────────── */
  var fitEl = document.getElementById('fitcheck');
  if (fitEl) {
    var FIT = JSON.parse(document.getElementById('fitdata').textContent);
    // usable clearance in inches for each way into a Montréal apartment
    var CLEAR = { porte: 34, colimacon: 28, exterieur: 31, ascenseur: 41 };
    var state = { entry: 'porte', floor: 1 };
    fitEl.addEventListener('click', function (e) {
      var b = e.target.closest('[data-fit]'); if (!b) return;
      var g = b.closest('[data-fitgroup]');
      [].forEach.call(g.querySelectorAll('[data-fit]'), function (o) { o.setAttribute('aria-pressed', o === b); });
      state[g.dataset.fitgroup] = g.dataset.fitgroup === 'floor' ? parseInt(b.dataset.fit, 10) : b.dataset.fit;
      render();
    });
    function render() {
      var clear = CLEAR[state.entry];
      // stairs get tighter the higher you go: turning a landing costs clearance
      if (state.entry !== 'ascenseur' && state.floor >= 3) clear -= 2;
      var whole = FIT.passage, split = FIT.split;
      var out = fitEl.querySelector('.fitout'), cls, title, body;
      if (whole <= clear) { cls = 'go'; title = T.fits; body = T.fitsB; }
      else if (FIT.dismantles && split <= clear) { cls = 'tight'; title = T.tight; body = T.tightB(FIT.pieces, split, FIT.kind === 'flat'); }
      else { cls = 'no'; title = T.nofit; body = T.nofitB(FIT.dismantles ? split : whole); }

      var extra = '';
      if (cls === 'no') {
        // only offer pieces that clear THIS entrance, not merely narrower ones
        var fits = (FIT.alts || [])
          .filter(function (a) { return a.passage <= clear; })
          .sort(function (a, b) { return (b.same - a.same) || (a.passage - b.passage); })
          .slice(0, 3);
        if (fits.length) {
          extra = '<p class="mono" style="margin:2px 0 0;font-size:10.5px;letter-spacing:.09em;' +
                  'text-transform:uppercase;color:var(--ink-3)">' + T.alts + '</p>' +
                  '<div class="grid" style="grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:9px">' +
            fits.map(function (a) {
              return '<a class="pc" href="' + a.url + '"><div class="pc-shot"><img loading="lazy" src="' + a.img +
                '" alt="' + a.name + '" width="240" height="300"></div><div class="pc-body" style="padding:9px 10px 11px">' +
                '<div class="pc-name" style="font-size:13px">' + a.name + '</div>' +
                '<div class="pc-mo">' + a.passage + (L === 'fr' ? ' po' : '"') + '</div></div></a>';
            }).join('') + '</div>';
        } else {
          extra = '<p style="margin:0;font-size:14.5px;line-height:1.5;color:var(--ink-2)">' + T.noalts + '</p>';
        }
      }
      out.innerHTML =
        '<span class="chip boxed ' + cls + '"><span class="dot"></span>' + title + '</span>' +
        '<p style="margin:0;font-size:14.5px;line-height:1.5;color:var(--ink-2)">' + body + '</p>' +
        extra +
        '<p class="mono" style="margin:2px 0 0;font-size:10.5px;color:var(--ink-3);line-height:1.5">' + T.est + '</p>';
    }
    render();
  }


  /* ── scroll hero ────────────────────────────────────────────────
     Progressive enhancement: the markup is a plain hero showing room one.
     Only if the browser can do this smoothly do we make the section tall,
     pin the stage and crossfade. Nothing is hidden that JS must reveal. */
  var shero = document.getElementById('shero');
  if (shero && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    var slides = [].slice.call(shero.querySelectorAll('.shero-slide'));
    var capBox = shero.querySelector('.shero-caps');
    var caps = [].slice.call(shero.querySelectorAll('.shero-cap'));
    var rails = [].slice.call(shero.querySelectorAll('.shero-rail a'));
    var n = slides.length;
    if (n > 1) {
      shero.setAttribute('data-scroll', '');
      if (capBox) capBox.setAttribute('data-js', '');
      var last = -1;
      var paint = function () {
        var box = shero.getBoundingClientRect();
        var span = shero.offsetHeight - window.innerHeight;
        var p = span > 0 ? Math.min(1, Math.max(0, -box.top / span)) : 0;
        var t = p * (n - 1);
        slides.forEach(function (s, i) {
          var w = Math.min(1, Math.max(0, 1 - Math.abs(t - i)));
          s.style.opacity = w;
          s.style.transform = 'scale(' + (1.05 - 0.05 * w).toFixed(4) + ')';
        });
        var active = Math.round(t);
        if (active !== last) {
          last = active;
          caps.forEach(function (c, i) {
            if (i === active) { c.setAttribute('data-on', ''); }
            else { c.removeAttribute('data-on'); }
          });
          rails.forEach(function (r, i) {
            if (i === active) { r.setAttribute('aria-current', 'true'); }
            else { r.removeAttribute('aria-current'); }
          });
        }
      };
      // Two drivers, because neither is reliable alone: scroll events don't
      // reach window when something upstream makes another element the scroll
      // container, and a bare rAF loop burns frames forever. The rAF loop runs
      // only while the hero is on screen; the scroll listener covers the case
      // where rAF is throttled.
      var running = false;
      var loop = function () {
        if (!running) return;
        paint();
        requestAnimationFrame(loop);
      };
      var start = function () {
        if (!running) { running = true; requestAnimationFrame(loop); }
      };
      if (window.IntersectionObserver) {
        new IntersectionObserver(function (es) {
          if (es[0].isIntersecting) { start(); }
          else { running = false; paint(); }
        }, { rootMargin: '120px' }).observe(shero);
      } else {
        start();
      }
      if (caps[0]) caps[0].setAttribute('data-on', '');
      addEventListener('scroll', paint, { passive: true });
      document.addEventListener('scroll', paint, { passive: true, capture: true });
      addEventListener('resize', paint);
      paint();
    }
  }


  /* ── supplier catalogue: family chips + code search ─────────────────── */
  var icGrid = document.getElementById('cat-grid');
  if (icGrid) {
    var icCards = [].slice.call(icGrid.querySelectorAll('.ic'));
    var icCount = document.getElementById('cat-count');
    var icEmpty = document.getElementById('cat-empty');
    var icSearch = document.getElementById('cat-search');
    // scope to the filter bar: the cards carry data-fam too, and selecting
    // them all wires a click handler onto every one of the 975 tiles
    var fams = [].slice.call(document.querySelectorAll('.cat-bar [data-fam]'));
    var active = null;

    var applyIc = function () {
      var q = (icSearch.value || '').trim().toLowerCase().replace(/[\s-]/g, '');
      var shown = 0;
      icCards.forEach(function (el) {
        var okFam = !active || el.dataset.fam === active;
        var okQ = !q || el.dataset.code.replace(/[\s-]/g, '').indexOf(q) > -1;
        el.hidden = !(okFam && okQ);
        if (!el.hidden) shown++;
      });
      icCount.textContent = shown;
      icEmpty.hidden = shown > 0;
    };
    fams.forEach(function (b) {
      b.addEventListener('click', function () {
        active = active === b.dataset.fam ? null : b.dataset.fam;
        fams.forEach(function (o) {
          o.setAttribute('aria-pressed', String(o.dataset.fam === active));
        });
        applyIc();
      });
    });
    icSearch.addEventListener('input', applyIc);
  }

  /* ── facets ─────────────────────────────────────────────────── */
  var list = document.getElementById('results');
  if (list) {
    var cards = [].slice.call(list.querySelectorAll('.pc'));
    var form = document.getElementById('facets');
    var countEl = document.getElementById('count');
    var sortEl = document.getElementById('sort');
    var empty = document.getElementById('empty');

    function checked(name) {
      return [].slice.call(form.querySelectorAll('input[name="' + name + '"]:checked')).map(function (i) { return i.value; });
    }
    function apply() {
      var f = { sub: checked('sub'), colour: checked('colour'), material: checked('material'), price: checked('price'), stock: checked('stock') };
      var shown = 0;
      cards.forEach(function (c) {
        var d = c.dataset;
        var ok =
          (!f.sub.length || f.sub.indexOf(d.sub) > -1) &&
          (!f.colour.length || f.colour.some(function (v) { return (d.colour || '').split(' ').indexOf(v) > -1; })) &&
          (!f.material.length || f.material.some(function (v) { return (d.material || '').split(' ').indexOf(v) > -1; })) &&
          (!f.price.length || f.price.indexOf(d.band) > -1) &&
          (!f.stock.length || f.stock.every(function (v) { return d[v] === '1'; }));
        c.hidden = !ok;
        if (ok) shown++;
      });
      countEl.textContent = T.results(shown);
      empty.hidden = shown > 0;
      var url = new URL(location.href);
      url.search = '';
      Object.keys(f).forEach(function (k) { if (f[k].length) url.searchParams.set(k, f[k].join(',')); });
      history.replaceState(null, '', url);
    }
    function sort() {
      var v = sortEl.value;
      var arr = cards.slice().sort(function (a, b) {
        // whatever the sort, a card that can only show the set photo yields
        // to one that shows the product itself
        var set = (a.dataset.setshot - b.dataset.setshot);
        if (v === 'price-asc') return (a.dataset.price - b.dataset.price) || set;
        if (v === 'price-desc') return (b.dataset.price - a.dataset.price) || set;
        if (v === 'soon') return (b.dataset.instock - a.dataset.instock) || set || (a.dataset.price - b.dataset.price);
        return a.dataset.rank - b.dataset.rank;
      });
      arr.forEach(function (c) { list.appendChild(c); });
    }
    // On a phone the grid updates out of sight below the open drawer, which
    // reads as "the filter does nothing". The button inside the drawer says
    // how many results the current choice gives, and jumps to them.
    var applyBtn = document.getElementById('facet-apply');
    var toggleBtn = document.getElementById('facet-toggle');
    function feedback() {
      var shown = cards.filter(function (c) { return !c.hidden; }).length;
      var active = form.querySelectorAll('input:checked').length;
      if (applyBtn) applyBtn.textContent = T.results(shown);
      if (toggleBtn) {
        toggleBtn.classList.toggle('is-active', active > 0);
        toggleBtn.textContent = active > 0 ? toggleBtn.dataset.base + ' · ' + active
                                           : toggleBtn.dataset.base;
      }
    }
    if (toggleBtn) toggleBtn.dataset.base = toggleBtn.textContent.trim();
    if (applyBtn) applyBtn.addEventListener('click', function () {
      form.classList.remove('open');
      document.getElementById('results').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

    form.addEventListener('change', function () { apply(); feedback(); });
    feedback();
    sortEl.addEventListener('change', function () { sort(); apply(); });
    var clear = document.getElementById('clearf');
    if (clear) clear.addEventListener('click', function () { form.reset(); apply(); feedback(); });
    var tog = document.getElementById('facet-toggle');
    if (tog) tog.addEventListener('click', function () { form.classList.toggle('open'); });

    // restore state from the URL so a filtered listing is a shareable link
    new URL(location.href).searchParams.forEach(function (val, key) {
      val.split(',').forEach(function (v) {
        var i = form.querySelector('input[name="' + key + '"][value="' + v + '"]');
        if (i) i.checked = true;
      });
    });
    sort(); apply();
  }
})();
