// Kwishyura i18n (client side) + Theme.
//
// The translation table is NOT duplicated here: the server injects the single
// table from translations.py as window.KW_I18N (see templates/base.html), and
// renders every page already in the user's language.  This file only
//   * re-translates the page instantly when a language button is clicked,
//   * saves the choice to the user's account (POST /set-language),
//   * provides KW.t() for text built in the browser (line items, charts, ...).
(function () {
  var TABLE = window.KW_I18N || {};
  var LANG = window.KW_LANG || 'rw';

  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function raw(key) {
    var s = (TABLE[LANG] || {})[key];
    if (s === undefined) s = (TABLE.rw || {})[key];
    if (s === undefined) s = (TABLE.en || {})[key];
    return s === undefined ? key : s;
  }

  function fill(text, params, escape) {
    if (!params) return text;
    return text.replace(/\{(\w+)\}/g, function (m, name) {
      if (!Object.prototype.hasOwnProperty.call(params, name)) return m;
      return escape ? esc(params[name]) : String(params[name]);
    });
  }

  function t(key, params) { return fill(raw(key), params, false); }
  function tHtml(key, params) { return fill(raw(key), params, true); }

  function paramsOf(el) {
    var p = el.getAttribute('data-i18n-params');
    if (!p) return undefined;
    try { return JSON.parse(p); } catch (e) { return undefined; }
  }

  function slug(v) { return String(v).toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, ''); }

  // Label for a stored unit value ('pcs', 'packet', ...); unknown values pass through.
  function unit(u) {
    var key = 'unit_' + slug(u);
    return (TABLE.en && TABLE.en[key] !== undefined) ? t(key) : u;
  }

  function each(root, selector, fn) {
    if (root.nodeType === 1 && root.matches(selector)) fn(root);
    var list = root.querySelectorAll(selector);
    for (var i = 0; i < list.length; i++) fn(list[i]);
  }

  function apply(root) {
    root = root || document;
    each(root, '[data-i18n]', function (el) {
      var key = el.getAttribute('data-i18n');
      if (el.hasAttribute('data-i18n-html')) el.innerHTML = tHtml(key, paramsOf(el));
      else el.textContent = t(key, paramsOf(el));
    });
    ['placeholder', 'title', 'aria-label'].forEach(function (attr) {
      each(root, '[data-i18n-' + attr + ']', function (el) {
        el.setAttribute(attr, t(el.getAttribute('data-i18n-' + attr), paramsOf(el)));
      });
    });
  }

  function markActive() {
    var btns = document.querySelectorAll('.lang-btn');
    for (var i = 0; i < btns.length; i++) {
      btns[i].classList.toggle('active', btns[i].dataset.lang === LANG);
    }
  }

  function save(lang) {
    var body = new URLSearchParams();
    body.set('_csrf', window.KW_CSRF || '');
    body.set('lang', lang);
    return fetch('/set-language', {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: body.toString()
    }).catch(function () { /* the page is already translated; saving is retried on next switch */ });
  }

  // Switch language immediately (no reload) and remember it for this account.
  function setLang(lang, persist) {
    if (!TABLE[lang]) return;
    LANG = lang;
    window.KW_LANG = lang;
    document.documentElement.lang = lang;
    document.title = t('page_title');
    apply(document);
    markActive();
    document.dispatchEvent(new CustomEvent('kw:langchange', { detail: { lang: lang } }));
    if (persist) save(lang);
  }

  window.KW = { t: t, tHtml: tHtml, apply: apply, setLang: setLang, unit: unit,
                lang: function () { return LANG; } };

  // ── Theme ─────────────────────────────────────────────────────────────────
  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('kwishyura_theme', theme);
    var icon = document.getElementById('theme-icon');
    if (icon) icon.textContent = theme === 'dark' ? '\u2600\ufe0f' : '\ud83c\udf19';
  }

  function toggleTheme() {
    var current = document.documentElement.getAttribute('data-theme') || 'light';
    applyTheme(current === 'dark' ? 'light' : 'dark');
  }

  // Confirmation dialogs in the selected language:
  // <form data-confirm="confirm_key" data-i18n-params='{"name":"..."}'>
  document.addEventListener('submit', function (e) {
    var f = e.target;
    var key = f && f.getAttribute && f.getAttribute('data-confirm');
    if (key && !window.confirm(t(key, paramsOf(f)))) e.preventDefault();
  }, true);

  document.addEventListener('DOMContentLoaded', function () {
    // The language now lives on the server (per account); drop the old shared browser value.
    try { localStorage.removeItem('kwishyura_lang'); } catch (e) {}
    var savedTheme = 'light';
    try { savedTheme = localStorage.getItem('kwishyura_theme') || 'light'; } catch (e) {}
    applyTheme(savedTheme);
    markActive();
    var btns = document.querySelectorAll('.lang-btn');
    for (var i = 0; i < btns.length; i++) {
      btns[i].addEventListener('click', function () { setLang(this.dataset.lang, true); });
    }
    var themeBtn = document.getElementById('theme-toggle');
    if (themeBtn) themeBtn.addEventListener('click', toggleTheme);
  });
})();
