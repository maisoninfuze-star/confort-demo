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

    // {"type":"setup-webhook"} — one-time, owner-authorized: register THIS
    // endpoint on the LIVE Stripe account so paid orders reach GHL. A
    // configuration call only; it can never move money. Idempotent: an
    // existing registration is reported, not duplicated.
    if (evt && evt.type === 'setup-webhook') {
      const live = process.env.SK_LIVE || process.env.SK_Live;
      if (!live) return send(res, 500, { setup: 'failed', why: 'no live key' });
      const host = req.headers.host || 'www.meubleconfort.com';
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

    if (!ghlToken() || !ghlLocation()) return send(res, 200, { ok: true, ghl: 'not configured' });
    const out = await pushToGHL(s);
    // a GHL failure returns 500 so Stripe retries; success/skip is 200
    if (out && out.error) return send(res, 500, out);
    return send(res, 200, { ok: true, ...out });
  } catch (e) {
    return send(res, 500, { error: 'server' });
  }
};
