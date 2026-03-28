/**
 * KV Iyengars — Sarvam Voice Support Widget
 *
 * Drop this script on any page and it renders a floating chat button
 * (bottom-right corner).  Clicking opens the support agent in a slide-up panel.
 *
 * Configuration (set BEFORE the script tag):
 *   window.KVISupport = { apiUrl: "https://your-backend.railway.app" }
 *
 * Shopify installation — add to theme.liquid before </body>:
 *   <script>window.KVISupport = { apiUrl: "{{ shop.metafields.support.api_url | default: 'https://your-backend.railway.app' }}" };</script>
 *   <script src="https://your-backend.railway.app/widget.js" defer></script>
 */

(function () {
  'use strict';

  var cfg = window.KVISupport || {};
  var API_URL = (cfg.apiUrl || 'http://localhost:8000').replace(/\/$/, '');
  var SESSION_ID = 'kvi_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8);

  // ── Styles ────────────────────────────────────────────────────────────────
  var css = [
    '#kvi-launcher{position:fixed;bottom:24px;right:24px;z-index:999999;',
    'width:56px;height:56px;border-radius:50%;background:#4f46e5;border:none;',
    'box-shadow:0 4px 20px rgba(79,70,229,.5);cursor:pointer;display:flex;',
    'align-items:center;justify-content:center;transition:transform .2s;}',
    '#kvi-launcher:hover{transform:scale(1.08);}',
    '#kvi-launcher svg{width:26px;height:26px;fill:none;stroke:#fff;stroke-width:2;}',
    '#kvi-panel{position:fixed;bottom:92px;right:24px;z-index:999998;',
    'width:380px;height:560px;border-radius:16px;overflow:hidden;',
    'box-shadow:0 8px 40px rgba(0,0,0,.25);transition:opacity .25s,transform .25s;',
    'opacity:0;transform:translateY(12px) scale(.97);pointer-events:none;}',
    '#kvi-panel.open{opacity:1;transform:translateY(0) scale(1);pointer-events:all;}',
    '#kvi-panel iframe{width:100%;height:100%;border:none;}',
    '#kvi-close{position:absolute;top:10px;right:10px;z-index:10;',
    'background:rgba(0,0,0,.4);border:none;border-radius:50%;width:28px;height:28px;',
    'cursor:pointer;display:flex;align-items:center;justify-content:center;}',
    '#kvi-close svg{width:14px;height:14px;stroke:#fff;stroke-width:2.5;fill:none;}',
    '@media(max-width:440px){#kvi-panel{width:calc(100vw - 16px);right:8px;bottom:80px;height:70vh;}}',
  ].join('');

  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  // ── Launcher button ───────────────────────────────────────────────────────
  var launcher = document.createElement('button');
  launcher.id = 'kvi-launcher';
  launcher.setAttribute('aria-label', 'Open support chat');
  launcher.innerHTML = '<svg viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round"'
    + ' d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.97-4.03 9-9 9a9 9 0 01-4.5-1.21L3 21l1.21-4.5A9 9 0 013 12c0-4.97 4.03-9 9-9s9 4.03 9 9z"/></svg>';

  // ── Chat panel (iframe wrapper) ───────────────────────────────────────────
  var panel = document.createElement('div');
  panel.id = 'kvi-panel';

  var closeBtn = document.createElement('button');
  closeBtn.id = 'kvi-close';
  closeBtn.setAttribute('aria-label', 'Close support chat');
  closeBtn.innerHTML = '<svg viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';

  var iframe = document.createElement('iframe');
  // The iframe points at the React frontend served by the backend
  iframe.src = API_URL + '/?session=' + SESSION_ID + '&embedded=1';
  iframe.setAttribute('allow', 'microphone');
  iframe.setAttribute('title', 'KV Iyengars Support');

  panel.appendChild(closeBtn);
  panel.appendChild(iframe);

  // ── Mount ─────────────────────────────────────────────────────────────────
  document.body.appendChild(launcher);
  document.body.appendChild(panel);

  // ── Toggle logic ──────────────────────────────────────────────────────────
  var isOpen = false;

  launcher.addEventListener('click', function () {
    isOpen = !isOpen;
    if (isOpen) {
      panel.classList.add('open');
      launcher.setAttribute('aria-expanded', 'true');
    } else {
      panel.classList.remove('open');
      launcher.setAttribute('aria-expanded', 'false');
    }
  });

  closeBtn.addEventListener('click', function () {
    isOpen = false;
    panel.classList.remove('open');
    launcher.setAttribute('aria-expanded', 'false');

    // Notify backend to clean up session (best-effort)
    if (navigator.sendBeacon) {
      navigator.sendBeacon(API_URL + '/session/' + SESSION_ID, '{}');
    }
  });

  // ── Pass logged-in Shopify customer name if available ─────────────────────
  // Shopify exposes window.__st.cid and meta[name="customer-id"] for logged-in users.
  // We use the data injected by the Liquid snippet below.
  if (cfg.customerName) {
    fetch(API_URL + '/session/' + SESSION_ID + '/set-customer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: cfg.customerName }),
    }).catch(function () {});
  }
})();
