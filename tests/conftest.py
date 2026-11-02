import os, re, sys, tempfile
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
_fd, _path = tempfile.mkstemp(suffix='.db')
os.close(_fd)
os.environ['DATABASE_PATH'] = _path
os.environ['SECRET_KEY'] = 'test-secret'

import app as kw  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    """Wipe all tables between tests."""
    with kw.db() as c:
        for t in ('audit', 'disputes', 'notifications', 'payment_attempts', 'ledger',
                  'sale_items', 'sales', 'memberships', 'products', 'ledger_resets',
                  'shops', 'users'):
            c.execute(f'DELETE FROM {t}')
    kw._FAILED.clear()
    yield


class Client:
    def __init__(self, phone, role, name='User', shop=''):
        self.phone, self.role = phone, role
        self.http = kw.app.test_client()
        self.register(name, shop)
        self.login()

    def token(self, path='/login'):
        html = self.http.get(path).get_data(as_text=True)
        return re.search(r'name="_csrf" value="([^"]+)"', html).group(1)

    def register(self, name, shop):
        return self.http.post('/register', data=dict(
            _csrf=self.token('/register'), name=name, phone=self.phone,
            password='longpassword1', role=self.role, shopname=shop))

    def login(self, password='longpassword1'):
        return self.http.post('/login', data=dict(
            _csrf=self.token(), phone=self.phone, password=password))

    def post(self, path, **data):
        data['_csrf'] = self.token('/settings')
        return self.http.post(path, data=data, follow_redirects=True)

    def get(self, path):
        return self.http.get(path)

    @property
    def uid(self):
        with kw.db() as c:
            return c.execute('SELECT id FROM users WHERE phone=?', (self.phone,)).fetchone()[0]


@pytest.fixture
def shop():
    return Client('+250788000001', 'shopkeeper', 'Owner', 'Duka')


@pytest.fixture
def cust(shop):
    c = Client('+250788000002', 'customer', 'Alice')
    with kw.db() as db:
        code = db.execute('SELECT code FROM shops').fetchone()[0]
    c.post('/link', code=code)
    return c


def sale(shop, cust, qty='2', price='500', name='Sugar', unit='kg', product_id=''):
    return shop.post('/sale', customer=cust.uid, **{
        'product_id[]': [product_id], 'qty[]': [qty], 'unit_price[]': [price],
        'product_name[]': [name], 'unit[]': [unit]})


def bal(shop_client, cust_client):
    with kw.db() as c:
        sid = c.execute('SELECT id FROM shops').fetchone()[0]
        return kw.balance(c, sid, cust_client.uid)
