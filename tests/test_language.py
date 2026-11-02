"""Language / translation tests (Kinyarwanda default, English, French)."""
import re
from conftest import Client, kw, sale
from translations import TRANSLATIONS, LANGS, translate


def visible(html):
    """Server-rendered text of the page (scripts/styles/tags removed, entities decoded)."""
    import html as h
    html = re.sub(r'<script.*?</script>|<style.*?</style>', ' ', html, flags=re.S)
    return h.unescape(re.sub(r'<[^>]+>', ' ', html))


def all_pages(shop, cust):
    return [shop.get('/dashboard').get_data(as_text=True),
            shop.get('/settings').get_data(as_text=True),
            cust.get('/dashboard').get_data(as_text=True),
            cust.get('/settings').get_data(as_text=True)]


def seed(shop, cust):
    shop.post('/products/add', name='Sugar', category='Dairy', unit='packet', price='500', stock='10')
    sale(shop, cust)
    shop.post('/remind', customer=cust.uid)
    shop.post('/repay', customer=cust.uid, amount='100')
    cust.post('/pay', shop=1, amount='100')


# ── table integrity ──────────────────────────────────────────────────────────
def test_every_key_exists_in_all_three_languages():
    assert set(TRANSLATIONS['rw']) == set(TRANSLATIONS['en']) == set(TRANSLATIONS['fr'])
    for lang in LANGS:
        assert all(v.strip() for v in TRANSLATIONS[lang].values())


def test_placeholders_match_across_languages():
    ph = lambda s: sorted(re.findall(r'\{(\w+)\}', s))
    for key, rw in TRANSLATIONS['rw'].items():
        assert ph(rw) == ph(TRANSLATIONS['en'][key]) == ph(TRANSLATIONS['fr'][key]), key


def test_every_translation_key_used_in_templates_exists():
    import glob, os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    used = set()
    for f in glob.glob(os.path.join(root, 'templates', '*.html')) + [os.path.join(root, 'static', 'i18n.js')]:
        src = open(f, encoding='utf-8').read()
        used |= set(re.findall(r'data-i18n(?:-[a-z-]+)?="([a-z_0-9]+)"', src))
        used |= set(re.findall(r"\bt(?:x|a|_html)?\('([a-z_0-9]+)'", src))
        used |= set(re.findall(r"KW\.t\('([a-z_0-9]+)'", src))
    shop_js = open(os.path.join(root, 'templates', 'shop.html'), encoding='utf-8').read()
    used |= set(re.findall(r"KW\.t\('([a-z_0-9]+)'", shop_js))
    missing = {k for k in used if k not in TRANSLATIONS['en'] and not k.startswith('unit_')}
    assert not missing, missing


def test_every_server_message_key_exists():
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = open(os.path.join(root, 'app.py'), encoding='utf-8').read()
    keys = set(re.findall(r"(?:flash_t|L10nError)\('([a-z_0-9]+)'", src))
    keys = {k for k in keys if not k.endswith('_')}   # dynamic keys are listed explicitly:
    keys |= {'msg_product_marked_available', 'msg_product_marked_unavailable'}
    assert not {k for k in keys if k not in TRANSLATIONS['en']}


# ── default language ─────────────────────────────────────────────────────────
def test_kinyarwanda_is_default_for_new_accounts_and_visitors():
    c = kw.app.test_client()
    html = c.get('/login').get_data(as_text=True)
    assert '<html lang="rw">' in html and 'Murakaza neza' in visible(html)
    s = Client('+250788000011', 'shopkeeper', 'Owner', 'Duka')
    with kw.db() as db:
        assert db.execute('SELECT language FROM users WHERE id=?', (s.uid,)).fetchone()[0] == 'rw'
    assert '<html lang="rw">' in s.get('/dashboard').get_data(as_text=True)


# ── switching, persistence, isolation ────────────────────────────────────────
def test_switch_applies_to_every_page_for_both_accounts(shop, cust):
    seed(shop, cust)
    marker = {'rw': 'IKIBAHO CY', 'en': 'DASHBOARD', 'fr': 'TABLEAU DE BORD'}
    for lang in LANGS:
        shop.post('/set-language', lang=lang)
        cust.post('/set-language', lang=lang)
        for page in all_pages(shop, cust):
            assert f'<html lang="{lang}">' in page
        assert marker[lang] in all_pages(shop, cust)[0]
        assert marker[lang] in all_pages(shop, cust)[2]


def test_no_mixed_language_text_in_rendered_pages(shop, cust):
    """Strings that exist in only one language must not leak into the others."""
    seed(shop, cust)
    other_only = {}
    for lang in LANGS:
        mine = set(TRANSLATIONS[lang].values())
        others = set()
        for o in LANGS:
            if o != lang:
                others |= set(TRANSLATIONS[o].values())
        other_only[lang] = {v for v in others - mine if len(v) > 12 and '<' not in v and '{' not in v}
    for lang in LANGS:
        shop.post('/set-language', lang=lang)
        cust.post('/set-language', lang=lang)
        for page in all_pages(shop, cust):
            text = visible(page)
            leaked = [v for v in other_only[lang] if v in text]
            assert not leaked, (lang, leaked[:5])


def test_preference_saved_and_restored_after_logout_login(shop, cust):
    shop.post('/set-language', lang='fr')
    shop.post('/logout')
    with kw.db() as db:
        assert db.execute('SELECT language FROM users WHERE id=?', (shop.uid,)).fetchone()[0] == 'fr'
    other = kw.app.test_client()
    tok = Client.token(type('T', (), {'http': other})())
    other.post('/login', data=dict(_csrf=tok, phone=shop.phone, password='longpassword1'))
    assert '<html lang="fr">' in other.get('/dashboard').get_data(as_text=True)


def test_each_user_has_their_own_language(shop, cust):
    shop.post('/set-language', lang='en')
    assert '<html lang="en">' in shop.get('/dashboard').get_data(as_text=True)
    assert '<html lang="rw">' in cust.get('/dashboard').get_data(as_text=True)
    cust.post('/set-language', lang='fr')
    assert '<html lang="en">' in shop.get('/dashboard').get_data(as_text=True)
    assert '<html lang="fr">' in cust.get('/dashboard').get_data(as_text=True)
    with kw.db() as db:
        langs = dict(db.execute('SELECT role, language FROM users').fetchall())
    assert langs == {'shopkeeper': 'en', 'customer': 'fr'}


def test_invalid_language_rejected(shop):
    assert shop.post('/set-language', lang='de').status_code == 400
    assert '<html lang="rw">' in shop.get('/dashboard').get_data(as_text=True)


def test_anonymous_choice_is_kept_on_auth_pages_and_used_at_registration():
    c = kw.app.test_client()
    tok = Client.token(type('T', (), {'http': c})(), '/register')
    c.post('/set-language', data=dict(_csrf=tok, lang='en'))
    assert '<html lang="en">' in c.get('/register').get_data(as_text=True)
    c.post('/register', data=dict(_csrf=tok, name='Eve', phone='+250788000077',
                                  password='longpassword1', role='customer'))
    with kw.db() as db:
        assert db.execute("SELECT language FROM users WHERE phone='+250788000077'").fetchone()[0] == 'en'


# ── backend-generated messages ───────────────────────────────────────────────
def flash_text(resp):
    html = resp.get_data(as_text=True)
    m = re.search(r'<div class="alert [a-z]+"[^>]*>(.*?)</div>', html, re.S)
    import html as h
    return h.unescape(m.group(1)) if m else ''


def test_validation_errors_follow_selected_language(shop, cust):
    expected = {
        'rw': translate('rw', 'err_invalid_amount'),
        'en': 'Enter a valid positive amount.',
        'fr': translate('fr', 'err_invalid_amount'),
    }
    for lang in LANGS:
        shop.post('/set-language', lang=lang)
        r = shop.post('/repay', customer=cust.uid, amount='abc')
        assert flash_text(r) == expected[lang]


def test_flash_with_parameters_is_translated(shop, cust):
    for lang in LANGS:
        shop.post('/set-language', lang=lang)
        r = shop.post('/repay', customer=cust.uid, amount='5000')
        assert flash_text(r) == translate(lang, 'err_repay_exceeds', value='5,000', bal='0')


def test_http_error_pages_are_translated():
    c = kw.app.test_client()
    for lang, word in (('rw', 'Habaye ikibazo'), ('en', 'Something went wrong'), ('fr', 'Un problème est survenu')):
        tok = Client.token(type('T', (), {'http': c})())
        c.post('/set-language', data=dict(_csrf=tok, lang=lang))
        r = c.get('/nope')
        assert r.status_code == 404 and word in visible(r.get_data(as_text=True))


def test_reminder_text_is_shown_in_each_viewers_language(shop, cust):
    sale(shop, cust)
    shop.post('/remind', customer=cust.uid)
    shop.post('/set-language', lang='en')
    cust.post('/set-language', lang='fr')
    assert 'outstanding balance is 1,000 RWF' in visible(shop.get('/dashboard').get_data(as_text=True))
    assert 'votre solde impayé est de 1,000 RWF' in visible(cust.get('/dashboard').get_data(as_text=True))
    cust.post('/set-language', lang='rw')
    assert 'umwenda wawe usigaye ni 1,000 RWF' in visible(cust.get('/dashboard').get_data(as_text=True))


def test_legacy_english_reminders_are_translated_too(shop, cust):
    with kw.db() as db:
        sid = db.execute('SELECT id FROM shops').fetchone()[0]
        db.execute('INSERT INTO notifications(shop_id,customer_id,message) VALUES(?,?,?)',
                   (sid, cust.uid, 'Kwishyura: Alice, outstanding balance is 2,500 RWF. Please sign in to review.'))
    assert 'umwenda wawe usigaye ni 2,500 RWF' in visible(cust.get('/dashboard').get_data(as_text=True))


def test_csv_export_headers_translated_but_data_untouched(shop, cust):
    sale(shop, cust, name='Sugar')
    shop.post('/repay', customer=cust.uid, amount='200')
    shop.post('/set-language', lang='fr')
    body = shop.get('/export').get_data(as_text=True)
    assert body.splitlines()[0].startswith('Référence,Date,Client,Type,Montant RWF')
    assert 'Sugar' in body and 'Remboursement en espèces' in body and '1000' in body


# ── stored data and business logic are untouched ─────────────────────────────
def test_stored_data_is_not_translated_and_logic_is_unchanged(shop, cust):
    shop.post('/products/add', name='Imyumbati', category='Dairy', unit='packet', price='500')
    sale(shop, cust)
    shop.post('/repay', customer=cust.uid, amount='400')
    for lang in LANGS:
        shop.post('/set-language', lang=lang)
        page = shop.get('/dashboard').get_data(as_text=True)
        assert 'Imyumbati' in page and 'Alice' in page
    with kw.db() as db:
        assert db.execute('SELECT category, unit FROM products').fetchone()[:] == ('Dairy', 'packet')
        assert db.execute("SELECT item FROM ledger WHERE kind='payment'").fetchone()[0] == 'Cash repayment'
        assert db.execute('SELECT SUM(amount) FROM ledger WHERE kind="sale"').fetchone()[0] == 1000
