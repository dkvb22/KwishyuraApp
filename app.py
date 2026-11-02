import os, sqlite3, secrets, hmac, csv, io, re, time, json
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_HALF_UP
from functools import wraps
from flask import (Flask, request, session, redirect, url_for,
                   render_template, flash, abort, Response, jsonify, g)
from markupsafe import Markup, escape
from werkzeug.security import generate_password_hash, check_password_hash
from translations import TRANSLATIONS, LANGS, DEFAULT_LANG, translate

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', secrets.token_hex(32)),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.environ.get('HTTPS_ONLY') == '1'
)
DB = os.environ.get('DATABASE_PATH', os.path.join(os.path.dirname(__file__), 'kwishyura.db'))

UNITS = ['pcs', 'kg', 'g', 'L', 'ml', 'packet', 'bottle', 'box', 'other']
CATEGORIES = ['Food & Groceries', 'Beverages', 'Household', 'Personal Care',
              'Vegetables & Fruits', 'Dairy', 'Grains & Cereals', 'Other']

# ── Database ─────────────────────────────────────────────────────────────────
def db():
    c = sqlite3.connect(DB, timeout=15)
    c.row_factory = sqlite3.Row
    c.execute('PRAGMA foreign_keys=ON')
    c.execute('PRAGMA busy_timeout=15000')
    c.execute('PRAGMA journal_mode=WAL')
    return c

def init():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('shopkeeper','customer')),
            email TEXT DEFAULT '',
            language TEXT NOT NULL DEFAULT 'rw',
            created TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS shops(
            id INTEGER PRIMARY KEY,
            owner_id INTEGER NOT NULL UNIQUE REFERENCES users(id),
            name TEXT NOT NULL,
            code TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS products(
            id INTEGER PRIMARY KEY,
            shop_id INTEGER NOT NULL REFERENCES shops(id),
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT DEFAULT 'Other',
            unit TEXT NOT NULL DEFAULT 'pcs',
            price_per_unit INTEGER NOT NULL CHECK(price_per_unit > 0),
            stock_qty REAL DEFAULT NULL,
            status TEXT NOT NULL DEFAULT 'available' CHECK(status IN ('available','unavailable')),
            image_url TEXT DEFAULT '',
            created TEXT DEFAULT CURRENT_TIMESTAMP,
            updated TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS memberships(
            id INTEGER PRIMARY KEY,
            shop_id INTEGER NOT NULL REFERENCES shops(id),
            customer_id INTEGER NOT NULL REFERENCES users(id),
            active INTEGER DEFAULT 1,
            UNIQUE(shop_id, customer_id)
        );
        CREATE TABLE IF NOT EXISTS sales(
            id INTEGER PRIMARY KEY,
            shop_id INTEGER NOT NULL REFERENCES shops(id),
            customer_id INTEGER NOT NULL REFERENCES users(id),
            total_amount INTEGER NOT NULL CHECK(total_amount > 0),
            due_date TEXT,
            notes TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'unpaid' CHECK(status IN ('unpaid','partial','paid')),
            created_by INTEGER NOT NULL REFERENCES users(id),
            created TEXT DEFAULT CURRENT_TIMESTAMP,
            ref TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS sale_items(
            id INTEGER PRIMARY KEY,
            sale_id INTEGER NOT NULL REFERENCES sales(id),
            product_id INTEGER REFERENCES products(id),
            product_name TEXT NOT NULL,
            unit TEXT NOT NULL,
            unit_price INTEGER NOT NULL,
            qty REAL NOT NULL CHECK(qty > 0),
            subtotal INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ledger(
            id INTEGER PRIMARY KEY,
            shop_id INTEGER NOT NULL REFERENCES shops(id),
            customer_id INTEGER NOT NULL REFERENCES users(id),
            kind TEXT NOT NULL CHECK(kind IN ('sale','payment','reversal')),
            amount INTEGER NOT NULL CHECK(amount > 0),
            item TEXT NOT NULL,
            qty REAL DEFAULT 1,
            unit_price INTEGER DEFAULT 0,
            due_date TEXT,
            related_id INTEGER REFERENCES ledger(id),
            sale_id INTEGER REFERENCES sales(id),
            created_by INTEGER NOT NULL REFERENCES users(id),
            created TEXT DEFAULT CURRENT_TIMESTAMP,
            ref TEXT NOT NULL UNIQUE,
            UNIQUE(related_id)
        );
        CREATE TABLE IF NOT EXISTS payment_attempts(
            id INTEGER PRIMARY KEY,
            shop_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            ref TEXT UNIQUE NOT NULL,
            created TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS notifications(
            id INTEGER PRIMARY KEY,
            shop_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'simulated',
            created TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS disputes(
            id INTEGER PRIMARY KEY,
            shop_id INTEGER NOT NULL,
            customer_id INTEGER NOT NULL,
            ledger_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS audit(
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            detail TEXT NOT NULL,
            created TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS ledger_resets(
            id INTEGER PRIMARY KEY,
            shop_id INTEGER NOT NULL,
            done_by INTEGER NOT NULL,
            record_count INTEGER NOT NULL,
            note TEXT DEFAULT '',
            created TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS ix_ledger_shop_customer ON ledger(shop_id, customer_id);
        CREATE INDEX IF NOT EXISTS ix_products_shop ON products(shop_id);
        CREATE INDEX IF NOT EXISTS ix_sales_shop_customer ON sales(shop_id, customer_id);
        CREATE INDEX IF NOT EXISTS ix_sale_items_sale ON sale_items(sale_id);
        ''')
    # Migrations for existing DBs
    with db() as c:
        cols = [r[1] for r in c.execute('PRAGMA table_info(users)').fetchall()]
        if 'email' not in cols:
            c.execute('ALTER TABLE users ADD COLUMN email TEXT DEFAULT ""')
        if 'language' not in cols:
            # Per-account language preference; Kinyarwanda is the default.
            c.execute("ALTER TABLE users ADD COLUMN language TEXT NOT NULL DEFAULT 'rw'")
        lcols = [r[1] for r in c.execute('PRAGMA table_info(ledger)').fetchall()]
        if 'sale_id' not in lcols:
            c.execute('ALTER TABLE ledger ADD COLUMN sale_id INTEGER REFERENCES sales(id)')
        if 'qty' in lcols:
            # Make qty REAL if it was INTEGER — SQLite won't enforce but we store float
            pass

init()

# ── Helpers ──────────────────────────────────────────────────────────────────
def now_str(): return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
def ref(): return 'KW-' + secrets.token_hex(6).upper()

# ── Translation (one central mechanism: translations.py) ─────────────────────
class L10nError(ValueError):
    """A validation error carrying a translation key instead of English text."""
    def __init__(self, key, **params):
        super().__init__(key)
        self.key, self.params = key, params


def current_lang():
    """Language for this request: the logged-in user's saved preference, else
    the language chosen on the sign-in/register pages, else Kinyarwanda."""
    if 'kw_lang' in g:
        return g.kw_lang
    lang = session.get('lang')
    if session.get('uid') and lang not in LANGS:
        # Session created before language support: load the saved preference.
        with db() as c:
            row = c.execute('SELECT language FROM users WHERE id=?',
                            (session['uid'],)).fetchone()
        lang = row['language'] if row else None
        if lang in LANGS:
            session['lang'] = lang
    if lang not in LANGS:
        lang = DEFAULT_LANG
    g.kw_lang = lang
    return lang


def t(key, **params):
    return translate(current_lang(), key, **params)


def _slug(value):
    return re.sub(r'[^a-z0-9]+', '_', str(value).lower()).strip('_')


def _i18n_attrs(key, params=None):
    out = f' data-i18n="{escape(key)}"'
    if params:
        out += f' data-i18n-params="{escape(json.dumps({k: str(v) for k, v in params.items()}))}"'
    return out


def tx(key, **params):
    """Translated <span> that the browser can re-translate instantly."""
    return Markup(f'<span{_i18n_attrs(key, params)}>{escape(t(key, **params))}</span>')


def ta(key, **params):
    """Attributes for an element that already exists (data-i18n [+ params])."""
    return Markup(_i18n_attrs(key, params))


def t_html(key, **params):
    """Translation that contains trusted markup (<strong>); parameters escaped."""
    safe = {k: str(escape(str(v))) for k, v in params.items()}
    return Markup(translate(current_lang(), key, **safe))


def _vkey(prefix, value):
    key = f'{prefix}_{_slug(value)}'
    return key if key in TRANSLATIONS['en'] else None


def tv(prefix, value):
    """Translate a stored enum-like value (category, unit, status, kind, role)."""
    key = _vkey(prefix, value)
    return tx(key) if key else escape(value)


def tv_text(prefix, value):
    key = _vkey(prefix, value)
    return t(key) if key else value


def tva(prefix, value):
    key = _vkey(prefix, value)
    return ta(key) if key else Markup('')


_LEGACY_REMINDER = re.compile(
    r'^Kwishyura: (.*), outstanding balance is ([\d,]+) RWF\. Please sign in to review\.$', re.S)


def notif_text(message):
    """Reminder text, stored language-neutral so each viewer sees their own language."""
    try:
        d = json.loads(message)
        if isinstance(d, dict) and d.get('k') in TRANSLATIONS['en']:
            return tx(d['k'], **d.get('p', {}))
    except (ValueError, TypeError):
        pass
    m = _LEGACY_REMINDER.match(message or '')
    if m:
        return tx('notif_reminder', name=m.group(1), amount=m.group(2))
    return escape(message)


_SYSTEM_ITEMS = {'Cash repayment': 'item_cash_repayment',
                 'SIMULATED MoMo payment': 'item_simulated_momo'}


def item_text(item):
    """Ledger descriptions written by the system are translated; product lines
    and anything the user typed are shown exactly as stored."""
    if item in _SYSTEM_ITEMS:
        return tx(_SYSTEM_ITEMS[item])
    if item and item.startswith('Reversal of '):
        return tx('item_reversal_of', ref=item[len('Reversal of '):])
    return escape(item)


def flash_t(key, cat='success', **params):
    """Flash a message by translation key (translated per viewer, switchable live)."""
    flash(json.dumps({'k': key, 'p': {k: str(v) for k, v in params.items()}}), cat)


def flash_err(e):
    if isinstance(e, L10nError):
        flash_t(e.key, 'error', **e.params)
    else:
        flash_t('err_invalid_input', 'error')


def flash_parts(msg):
    """(key, params, text) for a stored flash message."""
    try:
        d = json.loads(msg)
        if isinstance(d, dict) and d.get('k') in TRANSLATIONS['en']:
            p = d.get('p', {})
            return d['k'], p, t(d['k'], **p)
    except (ValueError, TypeError):
        pass
    return None, {}, msg


def reset_session_keep_lang(**values):
    lang = current_lang()
    session.clear()
    session['lang'] = lang
    session.update(values)


app.jinja_env.globals.update(
    t=t, tx=tx, ta=ta, t_html=t_html, tv=tv, tv_text=tv_text, tva=tva,
    notif_text=notif_text, item_text=item_text, flash_parts=flash_parts,
    current_lang=current_lang)


@app.context_processor
def inject_i18n():
    return {'lang': current_lang(), 'i18n_table': TRANSLATIONS}


@app.post('/set-language')
def set_language():
    lang = request.form.get('lang', '')
    if lang not in LANGS:
        abort(400)
    session['lang'] = lang
    if session.get('uid'):
        with db() as c:
            c.execute('UPDATE users SET language=? WHERE id=?', (lang, session['uid']))
    g.kw_lang = lang
    return jsonify(lang=lang)


@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
def http_error(e):
    return render_template('error.html', code=e.code, message_key=f'err_{e.code}'), e.code


def csrf():
    if '_csrf' not in session:
        session['_csrf'] = secrets.token_urlsafe(32)
    return session['_csrf']

app.jinja_env.globals['csrf'] = csrf

def rwf(v):
    """Round a float/Decimal amount to nearest integer RWF."""
    return int(Decimal(str(v)).to_integral_value(rounding=ROUND_HALF_UP))

@app.before_request
def protect():
    if request.method == 'POST':
        expected = session.get('_csrf')
        sent = request.form.get('_csrf', '')
        # An empty/missing session token must never match an empty form token.
        if not expected or not hmac.compare_digest(str(sent), str(expected)):
            abort(400, 'Invalid form token')

_FAILED = defaultdict(deque)   # (ip, phone) -> timestamps of failed logins
MAX_FAILS, WINDOW = 5, 300

def _throttled(key):
    q = _FAILED[key]
    cutoff = time.time() - WINDOW
    while q and q[0] < cutoff:
        q.popleft()
    return len(q) >= MAX_FAILS

def logged(fn):
    @wraps(fn)
    def inner(*a, **kw):
        if not session.get('uid'):
            return redirect(url_for('login'))
        return fn(*a, **kw)
    return inner

def role(r):
    def wrap(fn):
        @wraps(fn)
        @logged
        def inner(*a, **kw):
            if session.get('role') != r:
                abort(403)
            return fn(*a, **kw)
        return inner
    return wrap

def get_shop(c):
    s = c.execute('SELECT * FROM shops WHERE owner_id=?', (session['uid'],)).fetchone()
    if not s:
        abort(403)
    return s

def parse_amount(v, allow_decimal=False):
    """Parse and validate a positive numeric amount."""
    try:
        s = str(v).strip()
        if allow_decimal:
            if not re.fullmatch(r'[0-9]+(\.[0-9]+)?', s):
                raise ValueError()
            n = float(s)
        else:
            if not re.fullmatch(r'[0-9]+', s):
                raise ValueError()
            n = int(s)
        if n <= 0 or n > 1_000_000_000:
            raise ValueError()
        return n
    except Exception:
        raise L10nError('err_invalid_amount')

def _active(rows):
    """Ledger rows that are neither reversals nor have been reversed."""
    reversed_ids = {r['related_id'] for r in rows if r['kind'] == 'reversal'}
    return [r for r in rows if r['kind'] != 'reversal' and r['id'] not in reversed_ids]

def balance(c, sid, cid):
    """Outstanding balance for a customer at a shop (sales minus payments)."""
    rows = c.execute(
        'SELECT id, kind, amount, related_id FROM ledger WHERE shop_id=? AND customer_id=?',
        (sid, cid)
    ).fetchall()
    return sum(r['amount'] if r['kind'] == 'sale' else -r['amount'] for r in _active(rows))

def customer_totals(c, sid):
    """{customer_id: (sold, paid)} counting only non-reversed entries."""
    rows = c.execute(
        'SELECT id, customer_id, kind, amount, related_id FROM ledger WHERE shop_id=?', (sid,)
    ).fetchall()
    out = defaultdict(lambda: [0, 0])
    for r in _active(rows):
        out[r['customer_id']][0 if r['kind'] == 'sale' else 1] += r['amount']
    return {k: tuple(v) for k, v in out.items()}

def reversed_entry_ids(c, sid):
    return {r[0] for r in c.execute(
        "SELECT related_id FROM ledger WHERE shop_id=? AND kind='reversal'", (sid,)
    ).fetchall() if r[0]}

def shop_financials(c, sid):
    """Return (total_sales, total_payments, outstanding) for a shop."""
    totals = customer_totals(c, sid)
    sales = sum(v[0] for v in totals.values())
    pays = sum(v[1] for v in totals.values())
    return sales, pays, max(0, sales - pays)

def sync_sale_statuses(c, sid, cid):
    """Keep sales.status consistent with the customer's current balance."""
    rows = c.execute(
        'SELECT id, kind, amount, related_id FROM ledger WHERE shop_id=? AND customer_id=?',
        (sid, cid)
    ).fetchall()
    active = _active(rows)
    bal = sum(r['amount'] if r['kind'] == 'sale' else -r['amount'] for r in active)
    sold = sum(r['amount'] for r in active if r['kind'] == 'sale')
    status = 'paid' if bal <= 0 else ('partial' if sold - bal > 0 else 'unpaid')
    c.execute(
        "UPDATE sales SET status=? WHERE shop_id=? AND customer_id=? AND id IN ("
        "SELECT sale_id FROM ledger WHERE shop_id=? AND customer_id=? AND kind='sale' "
        "AND sale_id IS NOT NULL AND id NOT IN "
        "(SELECT related_id FROM ledger WHERE related_id IS NOT NULL))",
        (status, sid, cid, sid, cid)
    )

def audit_log(c, action, detail):
    c.execute('INSERT INTO audit(user_id,action,detail) VALUES(?,?,?)',
              (session['uid'], action, detail))

def check_membership(c, sid, cid):
    if not c.execute(
        'SELECT 1 FROM memberships WHERE shop_id=? AND customer_id=? AND active=1',
        (sid, cid)
    ).fetchone():
        abort(403)

# ── Auth Routes ───────────────────────────────────────────────────────────────
@app.route('/')
def home():
    return redirect(url_for('dashboard') if session.get('uid') else url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        r = request.form.get('role')
        shopname = request.form.get('shopname', '').strip()
        if (len(name) < 2 or not re.fullmatch(r'\+2507\d{8}', phone)
                or len(password) < 10 or r not in ('customer', 'shopkeeper')
                or (r == 'shopkeeper' and not shopname)):
            flash_t('msg_register_check', 'error')
        else:
            try:
                with db() as c:
                    cur = c.execute(
                        'INSERT INTO users(name,phone,password,role,language) VALUES(?,?,?,?,?)',
                        (name, phone, generate_password_hash(password), r, current_lang())
                    )
                    uid = cur.lastrowid
                    if r == 'shopkeeper':
                        c.execute(
                            'INSERT INTO shops(owner_id,name,code) VALUES(?,?,?)',
                            (uid, shopname, secrets.token_hex(4).upper())
                        )
                flash_t('msg_account_created')
                return redirect(url_for('login'))
            except sqlite3.IntegrityError:
                flash_t('msg_phone_registered', 'error')
    return render_template('auth.html', mode='register')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone', '').strip()
        key = (request.remote_addr, phone)
        if _throttled(key):
            flash_t('msg_too_many_attempts', 'error')
            return render_template('auth.html', mode='login'), 429
        with db() as c:
            u = c.execute('SELECT * FROM users WHERE phone=?', (phone,)).fetchone()
        if u and u['password'] and check_password_hash(u['password'], request.form.get('password', '')):
            _FAILED.pop(key, None)
            # Restore this account's own saved language preference.
            saved = u['language'] if u['language'] in LANGS else DEFAULT_LANG
            session.clear()
            session.update(uid=u['id'], role=u['role'], name=u['name'], lang=saved)
            return redirect(url_for('dashboard'))
        _FAILED[key].append(time.time())
        flash_t('msg_invalid_login', 'error')
    return render_template('auth.html', mode='login')

@app.post('/logout')
def logout():
    reset_session_keep_lang()
    return redirect(url_for('login'))

# ── Dashboards ────────────────────────────────────────────────────────────────
@app.route('/dashboard')
@logged
def dashboard():
    with db() as c:
        if session['role'] == 'shopkeeper':
            s = get_shop(c)
            customers = c.execute(
                'SELECT u.*,m.id mid FROM memberships m '
                'JOIN users u ON u.id=m.customer_id '
                'WHERE m.shop_id=? AND m.active=1 ORDER BY u.name',
                (s['id'],)
            ).fetchall()
            entries = c.execute(
                'SELECT l.*,u.name customer FROM ledger l '
                'JOIN users u ON u.id=l.customer_id '
                'WHERE l.shop_id=? ORDER BY l.id DESC LIMIT 100',
                (s['id'],)
            ).fetchall()
            balances = {u['id']: balance(c, s['id'], u['id']) for u in customers}
            total = sum(balances.values())
            total_sales, total_payments, outstanding = shop_financials(c, s['id'])
            totals = customer_totals(c, s['id'])
            cust_sold = {u['id']: totals.get(u['id'], (0, 0))[0] for u in customers}
            reversed_ids = reversed_entry_ids(c, s['id'])
            # Count customers with outstanding debt
            debtors = sum(1 for v in balances.values() if v > 0)
            notifications = c.execute(
                'SELECT n.*,u.name customer FROM notifications n '
                'JOIN users u ON u.id=n.customer_id '
                'WHERE n.shop_id=? ORDER BY n.id DESC LIMIT 30',
                (s['id'],)
            ).fetchall()
            disputes = c.execute(
                'SELECT d.*,u.name customer FROM disputes d '
                'JOIN users u ON u.id=d.customer_id '
                'WHERE d.shop_id=? ORDER BY d.id DESC',
                (s['id'],)
            ).fetchall()
            products = c.execute(
                'SELECT * FROM products WHERE shop_id=? ORDER BY name',
                (s['id'],)
            ).fetchall()
            return render_template(
                'shop.html',
                s=s, customers=customers, entries=entries,
                balances=balances, total=total,
                total_sales=total_sales, total_payments=total_payments,
                outstanding=outstanding, debtors=debtors,
                notifications=notifications, disputes=disputes,
                products=products, units=UNITS, categories=CATEGORIES,
                cust_sold=cust_sold, reversed_ids=reversed_ids
            )
        # Customer dashboard
        memberships = c.execute(
            'SELECT m.*,s.name shop FROM memberships m '
            'JOIN shops s ON s.id=m.shop_id '
            'WHERE m.customer_id=? AND m.active=1',
            (session['uid'],)
        ).fetchall()
        entries = c.execute(
            'SELECT l.*,s.name shop FROM ledger l '
            'JOIN shops s ON s.id=l.shop_id '
            'WHERE l.customer_id=? AND l.shop_id IN '
            '(SELECT shop_id FROM memberships WHERE customer_id=? AND active=1) '
            'ORDER BY l.id DESC',
            (session['uid'], session['uid'])
        ).fetchall()
        balances = {m['shop_id']: balance(c, m['shop_id'], session['uid'])
                    for m in memberships}
        notifications = c.execute(
            'SELECT * FROM notifications WHERE customer_id=? ORDER BY id DESC LIMIT 30',
            (session['uid'],)
        ).fetchall()
        attempts = c.execute(
            'SELECT * FROM payment_attempts WHERE customer_id=? ORDER BY id DESC LIMIT 30',
            (session['uid'],)
        ).fetchall()
        my_disputes = c.execute(
            'SELECT d.*, l.ref ledger_ref FROM disputes d JOIN ledger l ON l.id=d.ledger_id '
            'WHERE d.customer_id=? ORDER BY d.id DESC LIMIT 30', (session['uid'],)
        ).fetchall()
        # Get products for each linked shop
        shop_products = {}
        for m in memberships:
            shop_products[m['shop_id']] = c.execute(
                "SELECT * FROM products WHERE shop_id=? AND status='available' ORDER BY name",
                (m['shop_id'],)
            ).fetchall()
        return render_template(
            'customer.html',
            memberships=memberships, entries=entries,
            balances=balances, notifications=notifications,
            attempts=attempts, total=sum(balances.values()),
            shop_products=shop_products, my_disputes=my_disputes
        )

# ── Membership ────────────────────────────────────────────────────────────────
@app.post('/link')
@role('customer')
def link():
    code = request.form.get('code', '').strip().upper()
    with db() as c:
        s = c.execute('SELECT * FROM shops WHERE code=?', (code,)).fetchone()
        if not s:
            flash_t('msg_shop_not_found', 'error')
        else:
            c.execute(
                'INSERT INTO memberships(shop_id,customer_id,active) VALUES(?,?,1) '
                'ON CONFLICT(shop_id,customer_id) DO UPDATE SET active=1',
                (s['id'], session['uid'])
            )
            audit_log(c, 'link_shop', code)
            flash_t('msg_shop_linked')
    return redirect(url_for('dashboard'))

@app.post('/customer')
@role('shopkeeper')
def add_customer():
    phone = request.form.get('phone', '').strip()
    with db() as c:
        get_shop(c)
        u = c.execute('SELECT * FROM users WHERE phone=? AND role="customer"',
                      (phone,)).fetchone()
        if not u:
            flash_t('msg_cust_not_registered', 'error')
        else:
            flash_t('msg_ask_customer_code')
    return redirect(url_for('dashboard'))

# ── Products ──────────────────────────────────────────────────────────────────
@app.post('/products/add')
@role('shopkeeper')
def product_add():
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'Other').strip()
        unit = request.form.get('unit', 'pcs').strip()
        price_raw = request.form.get('price', '').strip()
        stock_raw = request.form.get('stock', '').strip()
        status = request.form.get('status', 'available')

        if len(name) < 1 or len(name) > 120:
            raise L10nError('err_product_name')
        if unit not in UNITS:
            raise L10nError('err_invalid_unit')
        if status not in ('available', 'unavailable'):
            status = 'available'
        if category not in CATEGORIES:
            category = 'Other'
        price = parse_amount(price_raw)
        stock = None
        if stock_raw:
            stock = parse_amount(stock_raw, allow_decimal=True)

        with db() as c:
            s = get_shop(c)
            c.execute(
                'INSERT INTO products(shop_id,name,description,category,unit,'
                'price_per_unit,stock_qty,status) VALUES(?,?,?,?,?,?,?,?)',
                (s['id'], name, description, category, unit, price, stock, status)
            )
            audit_log(c, 'product_add', name)
        flash_t('msg_product_added', name=name)
    except ValueError as e:
        flash_err(e)
    return redirect(url_for('dashboard') + '#products')

@app.post('/products/<int:pid>/edit')
@role('shopkeeper')
def product_edit(pid):
    try:
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'Other').strip()
        unit = request.form.get('unit', 'pcs').strip()
        price_raw = request.form.get('price', '').strip()
        stock_raw = request.form.get('stock', '').strip()
        status = request.form.get('status', 'available')

        if len(name) < 1 or len(name) > 120:
            raise L10nError('err_product_name')
        if unit not in UNITS:
            raise L10nError('err_invalid_unit')
        if status not in ('available', 'unavailable'):
            status = 'available'
        if category not in CATEGORIES:
            category = 'Other'
        price = parse_amount(price_raw)
        stock = None
        if stock_raw:
            stock = parse_amount(stock_raw, allow_decimal=True)

        with db() as c:
            s = get_shop(c)
            p = c.execute('SELECT * FROM products WHERE id=? AND shop_id=?',
                          (pid, s['id'])).fetchone()
            if not p:
                abort(404)
            c.execute(
                'UPDATE products SET name=?,description=?,category=?,unit=?,'
                'price_per_unit=?,stock_qty=?,status=?,updated=? WHERE id=?',
                (name, description, category, unit, price, stock,
                 status, now_str(), pid)
            )
            audit_log(c, 'product_edit', f'id={pid} name={name}')
        flash_t('msg_product_updated', name=name)
    except ValueError as e:
        flash_err(e)
    return redirect(url_for('dashboard') + '#products')

@app.post('/products/<int:pid>/delete')
@role('shopkeeper')
def product_delete(pid):
    with db() as c:
        s = get_shop(c)
        p = c.execute('SELECT * FROM products WHERE id=? AND shop_id=?',
                      (pid, s['id'])).fetchone()
        if not p:
            abort(404)
        # Check if used in any sale_items
        used = c.execute('SELECT 1 FROM sale_items WHERE product_id=?', (pid,)).fetchone()
        if used:
            flash_t('err_product_in_use', 'error')
        else:
            c.execute('DELETE FROM products WHERE id=?', (pid,))
            audit_log(c, 'product_delete', f'id={pid}')
            flash_t('msg_product_deleted')
    return redirect(url_for('dashboard') + '#products')

@app.post('/products/<int:pid>/toggle')
@role('shopkeeper')
def product_toggle(pid):
    with db() as c:
        s = get_shop(c)
        p = c.execute('SELECT * FROM products WHERE id=? AND shop_id=?',
                      (pid, s['id'])).fetchone()
        if not p:
            abort(404)
        new_status = 'unavailable' if p['status'] == 'available' else 'available'
        c.execute('UPDATE products SET status=?,updated=? WHERE id=?',
                  (new_status, now_str(), pid))
        audit_log(c, 'product_toggle', f'id={pid} status={new_status}')
    flash_t('msg_product_marked_' + new_status)
    return redirect(url_for('dashboard') + '#products')

# API: get product details (for JS autofill)
@app.get('/products/<int:pid>/json')
@role('shopkeeper')
def product_json(pid):
    with db() as c:
        s = get_shop(c)
        p = c.execute('SELECT * FROM products WHERE id=? AND shop_id=?',
                      (pid, s['id'])).fetchone()
        if not p:
            abort(404)
        return jsonify(id=p['id'], name=p['name'], unit=p['unit'],
                       price=p['price_per_unit'], status=p['status'])

# ── Sales (Multi-product) ─────────────────────────────────────────────────────
@app.post('/sale')
@role('shopkeeper')
def sale():
    try:
        cid = int(request.form['customer'])
        due = request.form.get('due') or None
        notes = request.form.get('notes', '').strip()

        # Parse multi-product line items sent as:
        # product_id[], qty[], unit_price[], product_name[], unit[]
        product_ids = request.form.getlist('product_id[]')
        qtys = request.form.getlist('qty[]')
        prices = request.form.getlist('unit_price[]')
        product_names = request.form.getlist('product_name[]')
        units = request.form.getlist('unit[]')

        if not product_ids:
            raise L10nError('err_add_line_item')

        if len(product_ids) > 50:
            raise L10nError('err_too_many_items')
        if due:
            try:
                datetime.strptime(due, '%Y-%m-%d')
            except ValueError:
                raise L10nError('err_invalid_due')

        items = []
        total_amount = 0
        for i, pid_str in enumerate(product_ids):
            pname = (product_names[i] if i < len(product_names) else '').strip() or 'Item'
            unit = units[i] if i < len(units) else 'pcs'
            if unit not in UNITS:
                unit = 'other'
            qty = parse_amount(qtys[i], allow_decimal=True)
            price = parse_amount(prices[i])
            subtotal = rwf(qty * price)
            if subtotal < 1:
                raise L10nError('err_subtotal_small', name=pname)
            items.append({
                'product_id': int(pid_str) if pid_str and pid_str.isdigit() else None,
                'name': pname[:160],
                'unit': unit,
                'qty': qty,
                'price': price,
                'subtotal': subtotal
            })
            total_amount += subtotal

        if total_amount < 1 or total_amount > 1_000_000_000:
            raise L10nError('err_total_range')

        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            s = get_shop(c)
            check_membership(c, s['id'], cid)
            # Product references must belong to this shop; stock is enforced when tracked.
            for it in items:
                if it['product_id'] is None:
                    continue
                p = c.execute('SELECT * FROM products WHERE id=? AND shop_id=?',
                              (it['product_id'], s['id'])).fetchone()
                if not p:
                    raise L10nError('err_unknown_product')
                if p['stock_qty'] is not None and it['qty'] > p['stock_qty']:
                    raise L10nError('err_stock', name=p['name'],
                                    qty=f'{p["stock_qty"]:g}', unit=tv_text('unit', p['unit']))
                it['name'], it['unit'] = p['name'], p['unit']
            sale_ref = ref()
            # Insert sale header
            c.execute(
                'INSERT INTO sales(shop_id,customer_id,total_amount,due_date,'
                'notes,created_by,ref) VALUES(?,?,?,?,?,?,?)',
                (s['id'], cid, total_amount, due, notes, session['uid'], sale_ref)
            )
            sale_id = c.execute('SELECT last_insert_rowid()').fetchone()[0]

            # Insert sale items & one ledger entry per item (for history)
            for it in items:
                c.execute(
                    'INSERT INTO sale_items(sale_id,product_id,product_name,'
                    'unit,unit_price,qty,subtotal) VALUES(?,?,?,?,?,?,?)',
                    (sale_id, it['product_id'], it['name'],
                     it['unit'], it['price'], it['qty'], it['subtotal'])
                )
                # Update product stock if tracked
                if it['product_id']:
                    c.execute(
                        'UPDATE products SET stock_qty = CASE WHEN stock_qty IS NOT NULL '
                        'THEN stock_qty - ? ELSE NULL END WHERE id=?',
                        (it['qty'], it['product_id'])
                    )

            # Single ledger entry for the whole sale
            item_summary = ', '.join(
                f"{it['name']} x{it['qty']}{it['unit']}" for it in items
            )[:255]
            ledger_ref = ref()
            c.execute(
                'INSERT INTO ledger(shop_id,customer_id,kind,amount,item,'
                'qty,unit_price,due_date,sale_id,created_by,ref) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                (s['id'], cid, 'sale', total_amount, item_summary,
                 sum(it['qty'] for it in items), items[0]['price'] if len(items) == 1 else 0,
                 due, sale_id, session['uid'], ledger_ref)
            )
            audit_log(c, 'credit_sale', sale_ref)

        flash_t('msg_sale_saved', ref=sale_ref, total=f'{total_amount:,}')
    except (ValueError, KeyError, IndexError) as e:
        flash_err(e)
    return redirect(url_for('dashboard'))

# ── Repayments ────────────────────────────────────────────────────────────────
@app.post('/repay')
@role('shopkeeper')
def repay():
    try:
        cid = int(request.form['customer'])
        value = parse_amount(request.form['amount'])
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            s = get_shop(c)
            check_membership(c, s['id'], cid)
            bal = balance(c, s['id'], cid)
            if value > bal:
                raise L10nError('err_repay_exceeds', value=f'{value:,}', bal=f'{bal:,}')
            r = ref()
            c.execute(
                'INSERT INTO ledger(shop_id,customer_id,kind,amount,item,created_by,ref) '
                'VALUES(?,?,?,?,?,?,?)',
                (s['id'], cid, 'payment', value, 'Cash repayment', session['uid'], r)
            )
            sync_sale_statuses(c, s['id'], cid)
            audit_log(c, 'cash_repayment', r)
        flash_t('msg_repay_recorded', ref=r, value=f'{value:,}')
    except (ValueError, KeyError) as e:
        flash_err(e)
    return redirect(url_for('dashboard'))

# ── Reversal ──────────────────────────────────────────────────────────────────
@app.post('/reverse/<int:lid>')
@role('shopkeeper')
def reverse(lid):
    try:
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            s = get_shop(c)
            l = c.execute('SELECT * FROM ledger WHERE id=? AND shop_id=?',
                          (lid, s['id'])).fetchone()
            if not l or l['kind'] == 'reversal':
                abort(404)
            if c.execute('SELECT 1 FROM ledger WHERE related_id=?', (lid,)).fetchone():
                flash_t('err_already_reversed', 'error')
                return redirect(url_for('dashboard'))
            bal = balance(c, s['id'], l['customer_id'])
            if l['kind'] == 'payment' and bal + l['amount'] < 0:
                raise L10nError('err_invalid_reversal')
            if l['kind'] == 'sale' and bal - l['amount'] < 0:
                raise L10nError('err_reverse_paid')
            r = ref()
            c.execute(
                'INSERT INTO ledger(shop_id,customer_id,kind,amount,item,'
                'related_id,created_by,ref) VALUES(?,?,?,?,?,?,?,?)',
                (s['id'], l['customer_id'], 'reversal', l['amount'],
                 'Reversal of ' + l['ref'], lid, session['uid'], r)
            )
            if l['kind'] == 'sale' and l['sale_id']:
                # Put reversed goods back into tracked stock.
                for it in c.execute('SELECT product_id, qty FROM sale_items WHERE sale_id=?',
                                    (l['sale_id'],)).fetchall():
                    if it['product_id']:
                        c.execute('UPDATE products SET stock_qty = stock_qty + ? '
                                  'WHERE id=? AND stock_qty IS NOT NULL',
                                  (it['qty'], it['product_id']))
            sync_sale_statuses(c, s['id'], l['customer_id'])
            audit_log(c, 'reversal', r)
        flash_t('msg_reversed')
    except ValueError as e:
        flash_err(e)
    return redirect(url_for('dashboard'))

# ── SMS Reminder ──────────────────────────────────────────────────────────────
@app.post('/remind')
@role('shopkeeper')
def remind():
    try:
        cid = int(request.form['customer'])
    except (ValueError, KeyError):
        abort(400)
    with db() as c:
        s = get_shop(c)
        check_membership(c, s['id'], cid)
        v = balance(c, s['id'], cid)
        cu = c.execute('SELECT name FROM users WHERE id=?', (cid,)).fetchone()
        if v > 0:
            c.execute(
                'INSERT INTO notifications(shop_id,customer_id,message) VALUES(?,?,?)',
                (s['id'], cid,
                 json.dumps({'k': 'notif_reminder',
                             'p': {'name': cu['name'], 'amount': f'{v:,}'}}))
            )
            audit_log(c, 'simulated_sms', str(cid))
            flash_t('msg_reminder_logged')
        else:
            flash_t('msg_no_balance', 'error')
    return redirect(url_for('dashboard'))

# ── Customer: MoMo simulation ─────────────────────────────────────────────────
@app.post('/pay')
@role('customer')
def pay():
    try:
        sid = int(request.form['shop'])
        v = parse_amount(request.form['amount'])
        with db() as c:
            c.execute('BEGIN IMMEDIATE')
            check_membership(c, sid, session['uid'])
            if v > balance(c, sid, session['uid']):
                raise L10nError('err_amount_exceeds')
            r = ref()
            c.execute(
                'INSERT INTO payment_attempts(shop_id,customer_id,amount,ref) VALUES(?,?,?,?)',
                (sid, session['uid'], v, r)
            )
            audit_log(c, 'sandbox_payment_initiated', r)
        flash_t('msg_momo_initiated', ref=r)
    except (ValueError, KeyError) as e:
        flash_err(e)
    return redirect(url_for('dashboard'))

@app.post('/sandbox/<int:pid>/<outcome>')
@role('customer')
def sandbox(pid, outcome):
    if outcome not in ('success', 'failed'):
        abort(400)
    with db() as c:
        c.execute('BEGIN IMMEDIATE')
        p = c.execute('SELECT * FROM payment_attempts WHERE id=? AND customer_id=?',
                      (pid, session['uid'])).fetchone()
        if not p:
            abort(404)
        if p['status'] != 'pending':
            flash_t('err_payment_processed', 'error')
        elif outcome == 'success':
            if p['amount'] > balance(c, p['shop_id'], session['uid']):
                flash_t('err_balance_changed', 'error')
            else:
                c.execute('UPDATE payment_attempts SET status="simulated_success" WHERE id=?', (pid,))
                r = p['ref']
                c.execute(
                    'INSERT INTO ledger(shop_id,customer_id,kind,amount,item,created_by,ref) '
                    'VALUES(?,?,?,?,?,?,?)',
                    (p['shop_id'], session['uid'], 'payment', p['amount'],
                     'SIMULATED MoMo payment', session['uid'], r)
                )
                sync_sale_statuses(c, p['shop_id'], session['uid'])
                audit_log(c, 'sandbox_payment_success', r)
                flash_t('msg_payment_confirmed')
        else:
            c.execute('UPDATE payment_attempts SET status="failed" WHERE id=?', (pid,))
            audit_log(c, 'sandbox_payment_failed', p['ref'])
            flash_t('err_payment_failed', 'error')
    return redirect(url_for('dashboard'))

@app.post('/dispute')
@role('customer')
def dispute():
    try:
        lid = int(request.form['ledger'])
        message = request.form.get('message', '').strip()
        if not 5 <= len(message) <= 500:
            raise L10nError('err_dispute_len')
        with db() as c:
            l = c.execute('SELECT * FROM ledger WHERE id=? AND customer_id=?',
                          (lid, session['uid'])).fetchone()
            if not l:
                abort(404)
            check_membership(c, l['shop_id'], session['uid'])
            c.execute(
                'INSERT INTO disputes(shop_id,customer_id,ledger_id,message) VALUES(?,?,?,?)',
                (l['shop_id'], session['uid'], lid, message)
            )
            audit_log(c, 'dispute', str(lid))
        flash_t('msg_dispute_submitted')
    except (ValueError, KeyError) as e:
        flash_err(e)
    return redirect(url_for('dashboard'))

@app.post('/disputes/<int:did>/resolve')
@role('shopkeeper')
def dispute_resolve(did):
    with db() as c:
        s = get_shop(c)
        d = c.execute('SELECT * FROM disputes WHERE id=? AND shop_id=?', (did, s['id'])).fetchone()
        if not d:
            abort(404)
        c.execute("UPDATE disputes SET status='resolved' WHERE id=?", (did,))
        audit_log(c, 'dispute_resolved', str(did))
    flash_t('msg_dispute_resolved')
    return redirect(url_for('dashboard') + '#disputes')

# ── Ledger Reset ──────────────────────────────────────────────────────────────
@app.post('/ledger/reset')
@role('shopkeeper')
def ledger_reset():
    confirm_text = request.form.get('confirm_text', '').strip()
    confirm_pw = request.form.get('confirm_password', '')
    if confirm_text.upper() != 'RESET':
        flash_t('err_type_reset', 'error')
        return redirect(url_for('dashboard'))
    with db() as c:
        u = c.execute('SELECT * FROM users WHERE id=?', (session['uid'],)).fetchone()
        if not check_password_hash(u['password'], confirm_pw):
            flash_t('err_wrong_password_reset', 'error')
            return redirect(url_for('dashboard'))
        s = get_shop(c)
        c.execute('BEGIN IMMEDIATE')
        # Check outstanding balances
        customers = c.execute(
            'SELECT customer_id FROM memberships WHERE shop_id=? AND active=1', (s['id'],)
        ).fetchall()
        outstanding = sum(max(0, balance(c, s['id'], cu['customer_id'])) for cu in customers)
        if outstanding > 0:
            flash_t('err_cannot_reset', 'error', outstanding=f'{outstanding:,}')
            return redirect(url_for('dashboard'))
        # Count records
        count = c.execute(
            'SELECT COUNT(*) FROM ledger WHERE shop_id=?', (s['id'],)
        ).fetchone()[0]
        # Child rows first (foreign keys are enforced); the audit trail is kept.
        c.execute('DELETE FROM disputes WHERE shop_id=?', (s['id'],))
        c.execute('DELETE FROM ledger WHERE shop_id=?', (s['id'],))
        c.execute('DELETE FROM sale_items WHERE sale_id IN (SELECT id FROM sales WHERE shop_id=?)',
                  (s['id'],))
        c.execute('DELETE FROM sales WHERE shop_id=?', (s['id'],))
        c.execute("DELETE FROM payment_attempts WHERE shop_id=?", (s['id'],))
        c.execute(
            'INSERT INTO ledger_resets(shop_id,done_by,record_count,note) VALUES(?,?,?,?)',
            (s['id'], session['uid'], count, 'Full reset – all balances were zero')
        )
        audit_log(c, 'ledger_reset', f'shop={s["id"]} count={count}')
    flash_t('msg_reset_done', count=count)
    return redirect(url_for('dashboard'))

# ── Export ────────────────────────────────────────────────────────────────────
@app.get('/export')
@role('shopkeeper')
def export():
    with db() as c:
        s = get_shop(c)
        rows = c.execute(
            'SELECT l.ref, l.created, u.name, l.kind, l.amount, l.item, l.due_date '
            'FROM ledger l JOIN users u ON u.id=l.customer_id '
            'WHERE l.shop_id=? ORDER BY l.id',
            (s['id'],)
        ).fetchall()
    f = io.StringIO()
    w = csv.writer(f)
    w.writerow([t('csv_reference'), t('csv_date'), t('csv_customer'), t('csv_type'),
                t('csv_amount'), t('csv_description'), t('csv_due_date')])
    for r in rows:
        row = list(r)
        row[3] = tv_text('kind', row[3])
        if row[5] in _SYSTEM_ITEMS:
            row[5] = t(_SYSTEM_ITEMS[row[5]])
        elif row[5] and row[5].startswith('Reversal of '):
            row[5] = t('item_reversal_of', ref=row[5][len('Reversal of '):])
        w.writerow(row)
    return Response(
        f.getvalue(), mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=kwishyura-ledger.csv'}
    )

# ── Settings ──────────────────────────────────────────────────────────────────
@app.route('/settings', methods=['GET', 'POST'])
@logged
def settings():
    with db() as c:
        user = c.execute('SELECT * FROM users WHERE id=?', (session['uid'],)).fetchone()
        shoprow = None
        if session['role'] == 'shopkeeper':
            shoprow = c.execute('SELECT * FROM shops WHERE owner_id=?',
                                (session['uid'],)).fetchone()
    return render_template('settings.html', user=user, shoprow=shoprow)

@app.post('/settings/name')
@logged
def settings_name():
    name = request.form.get('name', '').strip()
    if len(name) < 2:
        flash_t('err_name_short', 'error')
    else:
        with db() as c:
            c.execute('UPDATE users SET name=? WHERE id=?', (name, session['uid']))
            audit_log(c, 'update_name', '')
        session['name'] = name
        flash_t('msg_name_updated')
    return redirect(url_for('settings'))

@app.post('/settings/email')
@logged
def settings_email():
    email = request.form.get('email', '').strip()
    if email and not re.fullmatch(r'[^@]+@[^@]+\.[^@]+', email):
        flash_t('err_email_invalid', 'error')
    else:
        with db() as c:
            c.execute('UPDATE users SET email=? WHERE id=?', (email, session['uid']))
            audit_log(c, 'update_email', '')
        flash_t('msg_email_updated')
    return redirect(url_for('settings'))

@app.post('/settings/password')
@logged
def settings_password():
    current = request.form.get('current_password', '')
    new_pw = request.form.get('new_password', '')
    confirm = request.form.get('confirm_password', '')
    if len(new_pw) < 10:
        flash_t('err_pw_short', 'error')
    elif new_pw != confirm:
        flash_t('err_pw_mismatch', 'error')
    else:
        with db() as c:
            u = c.execute('SELECT * FROM users WHERE id=?', (session['uid'],)).fetchone()
            if not check_password_hash(u['password'], current):
                flash_t('err_pw_current', 'error')
            else:
                c.execute('UPDATE users SET password=? WHERE id=?',
                          (generate_password_hash(new_pw), session['uid']))
                audit_log(c, 'update_password', '')
                flash_t('msg_pw_updated')
    return redirect(url_for('settings'))

@app.post('/settings/shopname')
@role('shopkeeper')
def settings_shopname():
    shopname = request.form.get('shopname', '').strip()
    if len(shopname) < 2:
        flash_t('err_shopname_short', 'error')
    else:
        with db() as c:
            c.execute('UPDATE shops SET name=? WHERE owner_id=?',
                      (shopname, session['uid']))
            audit_log(c, 'update_shopname', '')
        flash_t('msg_shopname_updated')
    return redirect(url_for('settings'))

@app.post('/settings/delete')
@logged
def settings_delete():
    confirm_text = request.form.get('confirm_text', '').strip()
    confirm_pw = request.form.get('confirm_password', '')
    if confirm_text.upper() != 'DELETE':
        flash_t('err_type_delete', 'error')
        return redirect(url_for('settings'))
    with db() as c:
        u = c.execute('SELECT * FROM users WHERE id=?', (session['uid'],)).fetchone()
        if not check_password_hash(u['password'], confirm_pw):
            flash_t('err_wrong_password_delete', 'error')
            return redirect(url_for('settings'))
        uid = session['uid']
        c.execute(
            'UPDATE users SET name="[Deleted]",phone=?,password="",email="" WHERE id=?',
            ('DEL-' + secrets.token_hex(8), uid)
        )
        if session['role'] == 'shopkeeper':
            c.execute(
                'UPDATE memberships SET active=0 WHERE shop_id='
                '(SELECT id FROM shops WHERE owner_id=?)', (uid,)
            )
        else:
            c.execute('UPDATE memberships SET active=0 WHERE customer_id=?', (uid,))
        reset_session_keep_lang()
    flash_t('msg_account_deleted')
    return redirect(url_for('login'))

# ── Chart & Financial API ──────────────────────────────────────────────────────
@app.get('/chart-data')
@role('shopkeeper')
def chart_data():
    period = request.args.get('period', 'all')  # day, week, month, all
    with db() as c:
        s = get_shop(c)
        sid = s['id']

        # Build date filter
        if period == 'week':
            since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime('%Y-%m-%d')
        elif period == 'month':
            since = (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y-%m-%d')
        elif period == 'day':
            since = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        else:
            since = '2000-01-01'

        # Daily grouped sales and payments
        rows = c.execute('''
            SELECT DATE(created) as day,
                   SUM(CASE WHEN kind='sale' THEN amount ELSE 0 END) as sales,
                   SUM(CASE WHEN kind='payment' THEN amount ELSE 0 END) as payments
            FROM ledger
            WHERE shop_id=? AND kind != 'reversal' AND DATE(created) >= ?
            GROUP BY DATE(created)
            ORDER BY day ASC
        ''', (sid, since)).fetchall()

        labels = [r['day'] for r in rows]
        daily_sales = [r['sales'] for r in rows]
        daily_payments = [r['payments'] for r in rows]

        # Cumulative outstanding balance over time
        running = 0
        balance_trend = []
        for r in rows:
            running += r['sales'] - r['payments']
            balance_trend.append(max(0, running))

        # Per-customer current balances
        customers = c.execute(
            'SELECT u.name, u.id, u.phone FROM memberships m '
            'JOIN users u ON u.id=m.customer_id '
            'WHERE m.shop_id=? AND m.active=1',
            (sid,)
        ).fetchall()
        cust_labels = [cu['name'] for cu in customers]
        cust_balances = [max(0, balance(c, sid, cu['id'])) for cu in customers]
        cust_sales = []
        cust_payments = []
        for cu in customers:
            rs = c.execute(
                'SELECT COALESCE(SUM(amount),0) FROM ledger '
                'WHERE shop_id=? AND customer_id=? AND kind="sale"',
                (sid, cu['id'])
            ).fetchone()[0]
            rp = c.execute(
                'SELECT COALESCE(SUM(amount),0) FROM ledger '
                'WHERE shop_id=? AND customer_id=? AND kind="payment"',
                (sid, cu['id'])
            ).fetchone()[0]
            cust_sales.append(rs)
            cust_payments.append(rp)

        # Summary totals
        total_sales, total_payments, outstanding = shop_financials(c, sid)
        debtors = sum(1 for v in cust_balances if v > 0)

    return jsonify(
        labels=labels,
        daily_sales=daily_sales,
        daily_payments=daily_payments,
        balance_trend=balance_trend,
        cust_labels=cust_labels,
        cust_balances=cust_balances,
        cust_sales=cust_sales,
        cust_payments=cust_payments,
        summary={
            'total_sales': total_sales,
            'total_payments': total_payments,
            'outstanding': outstanding,
            'debtors': debtors,
            'total_txns': len(labels)
        }
    )

@app.get('/health')
def health():
    return {'status': 'ok', 'mode': 'local-development', 'real_momo': False, 'real_sms': False}

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.environ.get('PORT', 5000)),
            debug=os.environ.get('FLASK_DEBUG') == '1')
