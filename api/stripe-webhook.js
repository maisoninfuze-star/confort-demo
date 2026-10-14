// Stripe -> GoHighLevel bridge. Stripe calls this after a checkout completes;
// the paid order becomes a GHL contact (guest or account, both land here) with
// the order logged as a note and tags that a GHL Workflow turns into a client
// portal invite.
//
// Trust model, without the raw-body dance a static Vercel function makes
// awkward: the POST only names a session id. Nothing in the request is
// believed. We gate spam with a shared secret in the URL, then RE-FETCH the
// session from Stripe with our own secret key — so the customer data and the
// "paid" status always come from Stripe, never from the caller.
const { stripeKey } = require('./_stripe');

// GoHighLevel v2 (LeadConnector). Auth is a Private Integration token
// (starts "pit-"); every call carries the Version header, and contacts calls
// carry the location id. The owner stored the token as GHL_API.
const GHL_BASE = 'https://services.leadconnectorhq.com';
const ghlToken = () => process.env.GHL_TOKEN || process.env.GHL_API || process.env.GHL_API_KEY || null;
const ghlLocation = () => process.env.GHL_LOCATION_ID || null;

const send = (res, status, obj) => { res.statusCode = status; res.end(JSON.stringify(obj)); };

// Meta Conversions API — the server half of Purchase. The thank-you page fires
// the browser half with the same event_id (the Stripe session id), so Meta
// counts the pair once. Sent only when the buyer accepted Meta cookies at
// checkout and META_CAPI_TOKEN is set, and only for live payments unless a
// test code routes it to Events Manager's Test events tab. A Meta failure is
// reported, never retried through Stripe: the order itself is what matters.
const crypto = require('crypto');
const META_DATASET = () => process.env.META_PIXEL_ID || '1164650748537760';
const META_GRAPH = () => process.env.META_GRAPH_VERSION || 'v23.0';
const sha = (v) => crypto.createHash('sha256').update(String(v).trim().toLowerCase()).digest('hex');
const hashed = (v) => (v ? [sha(v)] : undefined);

function capiEvent(s, site) {
  const md = s.metadata || {};
  const cd = s.customer_details || {};
  const ship = (s.shipping_details && s.shipping_details.address) || cd.address || {};
  const name = (cd.name || (s.shipping_details && s.shipping_details.name) || '').trim().split(/\s+/);
  let digits = String(cd.phone || '').replace(/\D/g, '');
  if (digits.length === 10) digits = '1' + digits;
  const items = (s.line_items && s.line_items.data) || [];
  return {
    event_name: 'Purchase',
    event_time: Math.floor(Date.now() / 1000),
    event_id: s.id,
    action_source: 'website',
    event_source_url: site + (md.lang === 'en' ? '/en/thank-you/' : '/fr/merci/'),
    user_data: {
      em: hashed(cd.email),
      ph: hashed(digits),
      fn: hashed(name[0]),
      ln: hashed(name.slice(1).join(' ')),
      ct: hashed(String(ship.city || '').replace(/\s+/g, '')),
      st: hashed(ship.state),
      zp: hashed(String(ship.postal_code || '').replace(/\s+/g, '')),
      country: hashed(ship.country || 'ca'),
      external_id: hashed(typeof s.customer === 'string' ? s.customer : ''),
      client_ip_address: md.meta_ip || undefined,
      client_user_agent: md.meta_ua || undefined,
      fbp: md.meta_fbp || undefined,
      fbc: md.meta_fbc || undefined,
    },
    custom_data: {
      currency: String(s.currency || 'cad').toUpperCase(),
      value: (s.amount_total || 0) / 100,
      content_type: 'product',
      content_ids: md.meta_ids ? md.meta_ids.split(',') : undefined,
      num_items: items.reduce((n, li) => n + (li.quantity || 0), 0) || undefined,
      order_id: s.id,
    },
  };
}

async function sendCapi(s, site, testCode) {
  const token = process.env.META_CAPI_TOKEN;
  if (!token) return { skipped: 'META_CAPI_TOKEN not set' };
  if ((s.metadata || {}).meta_consent !== 'yes') return { skipped: 'no consent' };
  const code = testCode || process.env.META_TEST_EVENT_CODE || '';
  if (!s.livemode && !code) return { skipped: 'test-mode payment without a test event code' };
  const r = await fetch(`https://graph.facebook.com/${META_GRAPH()}/${META_DATASET()}/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    // JSON.stringify drops the undefined fields, so absent data is simply not sent
    body: JSON.stringify({ data: [capiEvent(s, site)], test_event_code: code || undefined, access_token: token }),
  });
  const j = await r.json().catch(() => null);
  return r.ok
    ? { sent: true, events_received: j && j.events_received, fbtrace_id: j && j.fbtrace_id, test: !!code }
    : { error: 'meta', status: r.status, detail: j && j.error && j.error.message };
}

function money(cents, cur) {
  const v = (cents || 0) / 100;
  return v.toLocaleString('fr-CA', { minimumFractionDigits: 2 }) + ' ' + String(cur || 'cad').toUpperCase();
}

async function stripeGet(key, path) {
  const r = await fetch('https://api.stripe.com' + path, {
    headers: { Authorization: 'Basic ' + Buffer.from(key + ':').toString('base64') },
  });
  return r.ok ? r.json() : null;
}

async function ghl(method, path, body) {
  const r = await fetch(GHL_BASE + path, {
    method,
    headers: {
      Authorization: 'Bearer ' + ghlToken(),
      Version: '2021-07-28',
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await r.text();
  let json = null; try { json = text ? JSON.parse(text) : null; } catch (e) {}
  return { ok: r.ok, status: r.status, json };
}

async function pushToGHL(s) {
  const cd = s.customer_details || {};
  const ship = (s.shipping_details && s.shipping_details.address) || cd.address || {};
  const name = (cd.name || (s.shipping_details && s.shipping_details.name) || '').trim();
  const sp = name.split(/\s+/);
  const email = cd.email || '';
  const phone = cd.phone || '';
  if (!email && !phone) return { skipped: 'no email or phone' };

  // a self-test contact must not fire the real portal-invite workflow
  const tags = s._selftest
    ? ['selftest-site']
    : [process.env.GHL_ORDER_TAG || 'commande-site',
       process.env.GHL_PORTAL_TAG || 'portal-invite'];

  const up = await ghl('POST', '/contacts/upsert', {
    locationId: ghlLocation(),
    firstName: sp[0] || '', lastName: sp.slice(1).join(' '),
    email, phone,
    address1: ship.line1 || '', city: ship.city || '',
    state: ship.state || '', postalCode: ship.postal_code || '',
    country: ship.country || 'CA',
    source: 'Site web — Confort & Style',
    tags,
  });
  if (!up.ok) return { error: 'ghl upsert', status: up.status, detail: up.json };
  const contactId = up.json && up.json.contact && up.json.contact.id;
  if (!contactId) return { error: 'no contact id', detail: up.json };

  const items = (s.line_items && s.line_items.data) || [];
  const lines = items.map((li) => ` - ${li.description} × ${li.quantity} — ${money(li.amount_total, s.currency)}`).join('\n');
  const addr = [ship.line1, ship.city, ship.state, ship.postal_code].filter(Boolean).join(', ');
  const note = [
    'Commande — Meuble Confort & Style' + (s.livemode ? '' : ' (TEST)'),
    'Total : ' + money(s.amount_total, s.currency) + ' — ' + (s.payment_status || ''),
    items.length ? 'Articles :\n' + lines : '',
    addr ? 'Livraison : ' + addr : '',
    'Stripe : ' + s.id,
  ].filter(Boolean).join('\n');
  // best-effort: the contact + tags are what drive the CRM and the invite; a
  // note hiccup should not make Stripe retry a saved order
  const noteRes = await ghl('POST', '/contacts/' + contactId + '/notes', { body: note });

  return { contactId, isNew: !!(up.json && up.json.new), noteSaved: noteRes.ok };
}

// what the self-test writes into GHL: obviously fake, tagged selftest-site,
// safe to delete from the CRM afterwards
const SELFTEST_SESSION = {
  id: 'selftest', livemode: false, _selftest: true,
  currency: 'cad', amount_total: 0, payment_status: 'paid',
  customer_details: { email: 'verification.site@exemple.com', name: 'Vérification Site Web', phone: '' },
  shipping_details: {
    name: 'Vérification Site Web',
    address: { line1: '7566 rue Saint-Hubert', city: 'Montréal', state: 'QC', postal_code: 'H2R 2N6', country: 'CA' },
  },
  line_items: { data: [{ description: 'TEST — vérification de la connexion GoHighLevel', quantity: 1, amount_total: 0 }] },
};

module.exports = async (req, res) => {
  res.setHeader('Content-Type', 'application/json');
  res.setHeader('Cache-Control', 'no-store');
  try {
    if (req.method !== 'POST') return send(res, 405, { error: 'method' });

    const provided = (req.query && req.query.key)
      || (() => { try { return new URL(req.url, 'https://x').searchParams.get('key'); } catch (e) { return null; } })();
    if (!process.env.HOOK_SECRET || provided !== process.env.HOOK_SECRET) {
      return send(res, 401, { error: 'unauthorized' });
    }

    let evt = req.body;
    if (typeof evt === 'string') { try { evt = JSON.parse(evt); } catch (e) { evt = null; } }

    // {"type":"selftest"} exercises the exact GHL write path with fake data —
    // no Stripe involved, no charge, one deletable contact in the CRM
    if (evt && evt.type === 'selftest') {
      if (!ghlToken()) return send(res, 500, { selftest: 'failed', why: 'GHL token env var missing' });
      if (!ghlLocation()) return send(res, 500, { selftest: 'failed', why: 'GHL_LOCATION_ID env var missing' });
      const out = await pushToGHL(SELFTEST_SESSION);
      return send(res, out && out.error ? 502 : 200, { selftest: out && out.error ? 'failed' : 'ok', ...out });
    }

    // {"type":"capi-selftest","test_event_code":"TEST…"} — one fake Purchase to
    // Meta's Test events tab. The code is mandatory: without it Meta would
    // count the fake order as a real sale, so the request is refused.
    if (evt && evt.type === 'capi-selftest') {
      if (!/^TEST\w+$/.test(String(evt.test_event_code || ''))) {
        return send(res, 400, { capi: 'refused', why: 'a TEST… test_event_code from Events Manager is required' });
      }
      const fake = {
        id: 'cs_selftest_' + Date.now(), livemode: false, currency: 'cad', amount_total: 37900,
        customer: 'cus_selftest',
        metadata: { lang: 'fr', meta_consent: 'yes', meta_ids: 'selftest',
                    meta_ua: String(req.headers['user-agent'] || 'selftest'),
                    meta_ip: String(req.headers['x-forwarded-for'] || '').split(',')[0].trim() || undefined },
        customer_details: { email: SELFTEST_SESSION.customer_details.email, name: 'Vérification Site', phone: '' },
        shipping_details: SELFTEST_SESSION.shipping_details,
        line_items: { data: [{ quantity: 1 }] },
      };
      const host = req.headers.host || 'www.meublesconfortstyles.com';
      const out = await sendCapi(fake, 'https://' + host, evt.test_event_code);
      return send(res, out.error || out.skipped ? 502 : 200, { capi: out.sent ? 'ok' : 'failed', event_id: fake.id, ...out });
    }

    // {"type":"tax-status"} — read-only: report how tax is set up on the live
    // account, so checkout can opt into the mechanism that actually exists.
    // Dashboard configuration alone changes nothing: a Session collects tax
    // only when it asks, via automatic_tax or per-line tax_rates.
    if (evt && evt.type === 'tax-status') {
      const live = process.env.SK_LIVE || process.env.SK_Live;
      if (!live) return send(res, 500, { tax: 'failed', why: 'no live key' });
      const auth = { Authorization: 'Basic ' + Buffer.from(live + ':').toString('base64') };
      const grab = async (path) => {
        const r = await fetch('https://api.stripe.com' + path, { headers: auth });
        const j = await r.json().catch(() => null);
        return { ok: r.ok, j };
      };
      const rates = await grab('/v1/tax_rates?limit=100&active=true');
      const regs = await grab('/v1/tax/registrations?limit=100');
      const settings = await grab('/v1/tax/settings');
      // the newest Session proves what the deployed checkout actually asked for
      const last = await grab('/v1/checkout/sessions?limit=1');
      const sess = last.ok && last.j && last.j.data && last.j.data[0];
      return send(res, 200, {
        tax: 'report',
        lastSession: sess ? {
          id: sess.id,
          automaticTax: sess.automatic_tax,
          subtotal: sess.amount_subtotal,
          tax: sess.total_details && sess.total_details.amount_tax,
          total: sess.amount_total,
          currency: sess.currency,
        } : null,
        taxRates: rates.ok && rates.j && rates.j.data
          ? rates.j.data.map((t) => ({
              id: t.id, display: t.display_name, pct: t.percentage,
              inclusive: t.inclusive, juris: t.jurisdiction, country: t.country, state: t.state,
            }))
          : { error: rates.j && rates.j.error && rates.j.error.message },
        stripeTaxRegistrations: regs.ok && regs.j && regs.j.data
          ? regs.j.data.map((r2) => ({ id: r2.id, country: r2.country, state: r2.state, status: r2.status }))
          : { error: regs.j && regs.j.error && regs.j.error.message },
        stripeTaxStatus: settings.ok && settings.j
          ? { status: settings.j.status, defaultCode: settings.j.defaults && settings.j.defaults.tax_code,
              headOffice: !!settings.j.head_office }
          : { error: settings.j && settings.j.error && settings.j.error.message },
      });
    }

    // {"type":"setup-webhook"} — one-time, owner-authorized: register THIS
    // endpoint on the LIVE Stripe account so paid orders reach GHL. A
    // configuration call only; it can never move money. Idempotent: an
    // existing registration is reported, not duplicated.
    if (evt && evt.type === 'setup-webhook') {
      const live = process.env.SK_LIVE || process.env.SK_Live;
      if (!live) return send(res, 500, { setup: 'failed', why: 'no live key' });
      const host = req.headers.host || 'www.meublesconfortstyles.com';
      const auth = { Authorization: 'Basic ' + Buffer.from(live + ':').toString('base64') };
      const listR = await fetch('https://api.stripe.com/v1/webhook_endpoints?limit=100', { headers: auth });
      const list = await listR.json().catch(() => null);
      if (!listR.ok || !list) {
        return send(res, 502, { setup: 'failed', why: 'list', detail: list && list.error && list.error.message });
      }
      const mine = (list.data || []).find((w) => (w.url || '').startsWith('https://' + host + '/api/stripe-webhook/'));
      if (mine) return send(res, 200, { setup: 'exists', id: mine.id, status: mine.status });
      const q = new URLSearchParams();
      q.set('url', 'https://' + host + '/api/stripe-webhook/?key=' + process.env.HOOK_SECRET);
      q.append('enabled_events[]', 'checkout.session.completed');
      q.set('description', 'Commandes du site -> GoHighLevel');
      const mkR = await fetch('https://api.stripe.com/v1/webhook_endpoints', {
        method: 'POST',
        headers: { ...auth, 'Content-Type': 'application/x-www-form-urlencoded' },
        body: q.toString(),
      });
      const mk = await mkR.json().catch(() => null);
      if (!mkR.ok || !mk || !mk.id) {
        return send(res, 502, { setup: 'failed', why: 'create', detail: mk && mk.error && mk.error.message });
      }
      return send(res, 200, { setup: 'created', id: mk.id, status: mk.status });
    }

    if (!evt || evt.type !== 'checkout.session.completed') return send(res, 200, { ignored: true });

    const sessionId = evt.data && evt.data.object && evt.data.object.id;
    if (!sessionId) return send(res, 400, { error: 'no session' });

    const { key } = stripeKey();
    if (!key) return send(res, 500, { error: 'no stripe key' });

    const s = await stripeGet(key, '/v1/checkout/sessions/' + sessionId
      + '?expand[]=line_items&expand[]=customer_details');
    if (!s) return send(res, 502, { error: 'stripe fetch' });
    if (s.payment_status !== 'paid') return send(res, 200, { skipped: 'unpaid' });

    // Meta first and best-effort: a retry caused by GHL resends the same
    // event_id, which Meta drops as a duplicate.
    const capi = await sendCapi(s, 'https://' + (req.headers.host || 'www.meublesconfortstyles.com'))
      .catch(() => ({ error: 'meta request failed' }));

    if (!ghlToken() || !ghlLocation()) return send(res, 200, { ok: true, ghl: 'not configured', capi });
    const out = await pushToGHL(s);
    // a GHL failure returns 500 so Stripe retries; success/skip is 200
    if (out && out.error) return send(res, 500, { ...out, capi });
    return send(res, 200, { ok: true, ...out, capi });
  } catch (e) {
    return send(res, 500, { error: 'server' });
  }
};
