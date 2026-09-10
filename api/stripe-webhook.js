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

const GHL_BASE = 'https://rest.gohighlevel.com/v1';
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
      Authorization: 'Bearer ' + process.env.GHL_API_KEY,
      'Content-Type': 'application/json',
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
  const firstName = sp[0] || '';
  const lastName = sp.slice(1).join(' ');
  const email = cd.email || '';
  const phone = cd.phone || '';
  if (!email && !phone) return { skipped: 'no email or phone' };

  const orderTag = process.env.GHL_ORDER_TAG || 'commande-site';
  const portalTag = process.env.GHL_PORTAL_TAG || 'portal-invite';
  const tags = [orderTag, portalTag];

  const fields = {
    email, phone, firstName, lastName,
    address1: ship.line1 || '', city: ship.city || '',
    state: ship.state || '', postalCode: ship.postal_code || '',
    country: ship.country || 'CA',
    source: 'Site web — Confort & Style',
    tags,
  };

  // upsert by email: look first so a repeat buyer is updated, not duplicated
  let contactId = null;
  if (email) {
    const look = await ghl('GET', '/contacts/lookup?email=' + encodeURIComponent(email));
    if (look.ok && look.json && Array.isArray(look.json.contacts) && look.json.contacts[0]) {
      contactId = look.json.contacts[0].id;
    }
  }
  if (contactId) {
    await ghl('PUT', '/contacts/' + contactId, fields);
    await ghl('POST', '/contacts/' + contactId + '/tags/', { tags });
  } else {
    const made = await ghl('POST', '/contacts/', fields);
    contactId = made.json && (made.json.contact ? made.json.contact.id : made.json.id);
  }
  if (!contactId) return { error: 'contact not created' };

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
  await ghl('POST', '/contacts/' + contactId + '/notes/', { body: note });

  return { contactId };
}

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
    if (!evt || evt.type !== 'checkout.session.completed') return send(res, 200, { ignored: true });

    const sessionId = evt.data && evt.data.object && evt.data.object.id;
    if (!sessionId) return send(res, 400, { error: 'no session' });

    const { key } = stripeKey();
    if (!key) return send(res, 500, { error: 'no stripe key' });

    const s = await stripeGet(key, '/v1/checkout/sessions/' + sessionId
      + '?expand[]=line_items&expand[]=customer_details');
    if (!s) return send(res, 502, { error: 'stripe fetch' });
    if (s.payment_status !== 'paid') return send(res, 200, { skipped: 'unpaid' });

    if (!process.env.GHL_API_KEY) return send(res, 200, { ok: true, ghl: 'not configured' });
    const out = await pushToGHL(s);
    // a GHL failure returns 500 so Stripe retries; success/skip is 200
    if (out && out.error) return send(res, 500, out);
    return send(res, 200, { ok: true, ...out });
  } catch (e) {
    return send(res, 500, { error: 'server' });
  }
};
