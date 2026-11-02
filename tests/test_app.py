from conftest import Client, bal, sale, kw


# ── auth & roles ─────────────────────────────────────────────────────────────
def test_register_validation_and_duplicate(shop):
    r = Client.__new__(Client)
    r.phone, r.role = '+250788000001', 'customer'
    r.http = kw.app.test_client()
    html = r.register('Dup', '').get_data(as_text=True)
    assert 'data-i18n="msg_register_check"' not in html   # valid input…
    with kw.db() as c:                               # …but phone already taken
        assert c.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 1


def test_bad_phone_rejected():
    c = kw.app.test_client()
    tok = Client.token(type('T', (), {'http': c})(), '/register')
    c.post('/register', data=dict(_csrf=tok, name='Bob', phone='0788', password='longpassword1',
                                  role='customer'))
    with kw.db() as db:
        assert db.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0


def test_csrf_required(shop):
    assert shop.http.post('/logout', data={}).status_code == 400


def test_role_enforcement(shop, cust):
    assert cust.get('/export').status_code == 403
    assert cust.post('/sale', customer=1).status_code == 403
    assert shop.post('/pay', shop=1, amount=10).status_code == 403


def test_login_throttle(shop):
    for _ in range(5):
        shop.login(password='wrongwrongwrong')
    r = shop.login()                                  # correct password but locked out
    assert r.status_code == 429


# ── dashboards no longer crash once data exists (regression) ─────────────────
def test_dashboards_render_with_data(shop, cust):
    sale(shop, cust)
    assert shop.get('/dashboard').status_code == 200
    assert cust.get('/dashboard').status_code == 200
    assert shop.get('/chart-data').get_json()['summary']['total_sales'] == 1000


# ── credit sales ─────────────────────────────────────────────────────────────
def test_credit_sale_updates_balance(shop, cust):
    sale(shop, cust, qty='2', price='500')
    assert bal(shop, cust) == 1000


def test_decimal_quantity_rounds_to_integer_rwf(shop, cust):
    sale(shop, cust, qty='1.5', price='333')            # 499.5 → 500
    assert bal(shop, cust) == 500


def test_unlinked_customer_rejected(shop):
    stranger = Client('+250788000009', 'customer', 'Eve')
    assert sale(shop, stranger).status_code == 403


def test_invalid_amounts_rejected(shop, cust):
    for qty, price in [('0', '500'), ('-1', '500'), ('abc', '500'), ('1', '0'), ('1', '1.5')]:
        sale(shop, cust, qty=qty, price=price)
    assert bal(shop, cust) == 0


def test_product_must_belong_to_shop(shop, cust):
    other = Client('+250788000003', 'shopkeeper', 'Other', 'Other shop')
    other.post('/products/add', name='Rice', unit='kg', price='900', category='Grains & Cereals')
    with kw.db() as c:
        pid = c.execute("SELECT id FROM products WHERE name='Rice'").fetchone()[0]
    sale(shop, cust, product_id=str(pid))
    assert bal(shop, cust) == 0


def test_stock_tracking_and_restore_on_reversal(shop, cust):
    shop.post('/products/add', name='Beans', unit='kg', price='800', stock='10',
              category='Grains & Cereals')
    with kw.db() as c:
        pid = c.execute("SELECT id FROM products WHERE name='Beans'").fetchone()[0]
    sale(shop, cust, qty='4', price='800', product_id=str(pid), name='x', unit='kg')
    stock = lambda: kw.db().execute('SELECT stock_qty FROM products WHERE id=?', (pid,)).fetchone()[0]
    assert stock() == 6
    sale(shop, cust, qty='7', price='800', product_id=str(pid))      # exceeds stock
    assert stock() == 6 and bal(shop, cust) == 3200
    with kw.db() as c:
        lid = c.execute("SELECT id FROM ledger WHERE kind='sale'").fetchone()[0]
    shop.post(f'/reverse/{lid}')
    assert stock() == 10 and bal(shop, cust) == 0


# ── repayments, overpayment, reversals ───────────────────────────────────────
def test_partial_then_full_repayment_updates_sale_status(shop, cust):
    sale(shop, cust, qty='1', price='1000')
    shop.post('/repay', customer=cust.uid, amount='400')
    st = lambda: kw.db().execute('SELECT status FROM sales').fetchone()[0]
    assert bal(shop, cust) == 600 and st() == 'partial'
    shop.post('/repay', customer=cust.uid, amount='600')
    assert bal(shop, cust) == 0 and st() == 'paid'


def test_overpayment_blocked(shop, cust):
    sale(shop, cust, qty='1', price='1000')
    shop.post('/repay', customer=cust.uid, amount='1001')
    assert bal(shop, cust) == 1000


def test_reversal_is_audited_and_single_use(shop, cust):
    sale(shop, cust, qty='1', price='1000')
    shop.post('/repay', customer=cust.uid, amount='300')
    with kw.db() as c:
        pay = c.execute("SELECT id FROM ledger WHERE kind='payment'").fetchone()[0]
    shop.post(f'/reverse/{pay}')
    shop.post(f'/reverse/{pay}')                                     # second attempt ignored
    with kw.db() as c:
        assert c.execute("SELECT COUNT(*) FROM ledger WHERE kind='reversal'").fetchone()[0] == 1
        assert c.execute("SELECT COUNT(*) FROM audit WHERE action='reversal'").fetchone()[0] == 1
    assert bal(shop, cust) == 1000


def test_cannot_reverse_sale_already_partly_paid(shop, cust):
    sale(shop, cust, qty='1', price='1000')
    shop.post('/repay', customer=cust.uid, amount='400')
    with kw.db() as c:
        lid = c.execute("SELECT id FROM ledger WHERE kind='sale'").fetchone()[0]
    shop.post(f'/reverse/{lid}')
    assert bal(shop, cust) == 600


def test_shop_isolation_on_reverse(shop, cust):
    sale(shop, cust)
    other = Client('+250788000003', 'shopkeeper', 'Other', 'Other shop')
    with kw.db() as c:
        lid = c.execute("SELECT id FROM ledger").fetchone()[0]
    assert other.post(f'/reverse/{lid}').status_code == 404


# ── MoMo simulation, SMS, disputes ───────────────────────────────────────────
def test_momo_simulated_success_and_failure(shop, cust):
    sale(shop, cust, qty='1', price='1000')
    with kw.db() as c:
        sid = c.execute('SELECT id FROM shops').fetchone()[0]
    cust.post('/pay', shop=sid, amount='400')
    cust.post('/pay', shop=sid, amount='999999')                    # exceeds balance
    with kw.db() as c:
        attempts = c.execute('SELECT id FROM payment_attempts').fetchall()
    assert len(attempts) == 1
    cust.post(f'/sandbox/{attempts[0][0]}/failed')
    assert bal(shop, cust) == 1000
    cust.post('/pay', shop=sid, amount='400')
    with kw.db() as c:
        pid = c.execute("SELECT id FROM payment_attempts WHERE status='pending'").fetchone()[0]
    cust.post(f'/sandbox/{pid}/success')
    cust.post(f'/sandbox/{pid}/success')                            # replay is a no-op
    assert bal(shop, cust) == 600
    assert kw.db().execute('SELECT status FROM sales').fetchone()[0] == 'partial'


def test_sms_reminder_only_when_owing(shop, cust):
    shop.post('/remind', customer=cust.uid)
    assert kw.db().execute('SELECT COUNT(*) FROM notifications').fetchone()[0] == 0
    sale(shop, cust)
    shop.post('/remind', customer=cust.uid)
    assert kw.db().execute('SELECT COUNT(*) FROM notifications').fetchone()[0] == 1
    cust.post('/set-language', lang='en')
    assert 'outstanding balance is 1,000 RWF' in cust.get('/dashboard').get_data(as_text=True)


def test_dispute_flow(shop, cust):
    sale(shop, cust)
    with kw.db() as c:
        lid = c.execute('SELECT id FROM ledger').fetchone()[0]
    cust.post('/dispute', ledger=lid, message='abc')                # too short
    cust.post('/dispute', ledger=lid, message='I never bought this')
    with kw.db() as c:
        d = c.execute('SELECT id, status FROM disputes').fetchall()
    assert len(d) == 1 and d[0][1] == 'open'
    assert 'I never bought this' in cust.get('/dashboard').get_data(as_text=True)
    shop.post(f'/disputes/{d[0][0]}/resolve')
    assert kw.db().execute('SELECT status FROM disputes').fetchone()[0] == 'resolved'
    assert cust.post(f'/disputes/{d[0][0]}/resolve').status_code == 403


# ── export, reset, settings ──────────────────────────────────────────────────
def test_csv_export(shop, cust):
    sale(shop, cust)
    r = shop.get('/export')
    assert r.mimetype == 'text/csv' and 'Sugar' in r.get_data(as_text=True)


def test_reset_requires_zero_balance_and_password(shop, cust):
    sale(shop, cust, qty='1', price='1000')
    shop.post('/ledger/reset', confirm_text='RESET', confirm_password='longpassword1')
    assert kw.db().execute('SELECT COUNT(*) FROM ledger').fetchone()[0] == 1   # still owed
    shop.post('/repay', customer=cust.uid, amount='1000')
    shop.post('/ledger/reset', confirm_text='RESET', confirm_password='wrong-password')
    assert kw.db().execute('SELECT COUNT(*) FROM ledger').fetchone()[0] == 2   # bad password
    shop.post('/ledger/reset', confirm_text='RESET', confirm_password='longpassword1')
    with kw.db() as c:
        assert c.execute('SELECT COUNT(*) FROM ledger').fetchone()[0] == 0
        assert c.execute('SELECT COUNT(*) FROM sale_items').fetchone()[0] == 0
        assert c.execute('SELECT record_count FROM ledger_resets').fetchone()[0] == 2


def test_password_change(shop):
    shop.post('/settings/password', current_password='longpassword1',
              new_password='anotherlongpass', confirm_password='anotherlongpass')
    assert shop.login(password='longpassword1').status_code == 200   # old password rejected
    c = kw.app.test_client()
    tok = Client.token(type('T', (), {'http': c})())
    r = c.post('/login', data=dict(_csrf=tok, phone=shop.phone, password='anotherlongpass'))
    assert r.status_code == 302


def test_account_deletion_blocks_login(cust):
    cust.post('/settings/delete', confirm_text='DELETE', confirm_password='longpassword1')
    c = kw.app.test_client()
    tok = Client.token(type('T', (), {'http': c})())
    r = c.post('/login', data=dict(_csrf=tok, phone=cust.phone, password='longpassword1'))
    assert r.status_code == 200          # re-rendered login with error, not redirected


def test_health():
    assert kw.app.test_client().get('/health').get_json()['real_momo'] is False
