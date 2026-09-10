// Shared Stripe key resolver. Underscore-prefixed, so Vercel does not route it.
//
// Two keys can live side by side on the project — SK_TEST for rehearsal and
// SK_Live for real money — and STRIPE_MODE decides which one is active.
// The default is 'test' ON PURPOSE: a deploy never starts charging real cards
// until someone sets STRIPE_MODE=live, and if the chosen mode's key is missing
// the caller sees no key and pauses rather than falling back to the other mode.
module.exports.stripeKey = function stripeKey() {
  const live = process.env.SK_LIVE || process.env.SK_Live || null;
  const test = process.env.SK_TEST || process.env.STRIPE_SECRET_KEY_TEST || null;
  const mode = String(process.env.STRIPE_MODE || 'test').toLowerCase() === 'live'
    ? 'live' : 'test';
  return { key: mode === 'live' ? live : test, mode };
};
