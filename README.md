# Kwishyura — local testing edition

A runnable Flask + SQLite application for testing the core shop credit workflow **before deployment**. This is an independently packaged local implementation, not an export of the Replit project. It is not production-ready and does not implement every item in the master requirements document.

## Run locally (Ubuntu / Linux / macOS)

```bash
cd Kwishyura
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open **http://127.0.0.1:5000**. On Windows, activate the virtual environment with `.venv\Scripts\activate` instead.

For repeatable sessions, set `SECRET_KEY` to a long random value in your shell (otherwise sessions reset every restart). Set `FLASK_DEBUG=1` only for local debugging. SQLite database `kwishyura.db` is created automatically on first start. No external database is needed for this local prototype.

## Test walkthrough

1. Register a **shopkeeper** with a fictional +2507XXXXXXXX phone number and password of at least 10 characters; enter a shop name.
2. Note the generated shop invitation code on the dashboard.
3. In another private/incognito browser window register a **customer** using a different fictional phone number.
4. Log in as the customer, enter the shop invitation code, and link the shop.
5. Refresh the shopkeeper dashboard, create a credit sale with quantity and price.
6. Confirm the customer's outstanding balance and purchase history.
7. Record a partial cash repayment as the shopkeeper, and verify both dashboards.
8. As the customer, initiate a **simulated** MoMo payment and explicitly simulate success or failure. This is not a real payment.
9. Generate a **simulated** SMS reminder from the shopkeeper account and verify it appears in the customer's reminder log. No real SMS is sent.
10. Export the ledger as CSV, submit a dispute (the shopkeeper can then mark it resolved), and test a reversal.

## Run the automated tests

```bash
pip install -r requirements-dev.txt
pytest tests -q
```

The suite uses a throwaway SQLite file and covers auth/roles, CSRF, login throttling, credit sales, stock, repayments, overpayment, reversals, simulated MoMo, SMS logs, disputes, CSV export, ledger reset and account settings.

## Features

- Registration, password hashing, cookie sessions, shopkeeper/customer role checks
- Customer-initiated shop linking by invitation code
- Shop-isolated ledger with credit sales, cash repayments, reversals and reference IDs
- Integer RWF accounting, server-side validations, transactional writes, overdraft prevention
- Separate dashboards, transaction history, CSV export, disputes and audit table
- Explicitly simulated MoMo pending/success/failure and SMS reminder logs
- Multi-product credit sales with optional stock tracking (stock is checked on sale and restored on reversal)
- Product catalogue, RW/EN/FR language switcher (Kinyarwanda default, saved per account), light/dark theme, balance charts (Chart.js via CDN)
- Dispute submission by customers and resolution by shopkeepers
- Login throttling (5 failed attempts / 5 min per phone + IP, in-memory)
- Responsive layouts with Kwishyura branding

## Languages

All user-facing text lives in **one** file, `translations.py` (Kinyarwanda / English / French on the same row, so a key can never be missing from one language). The server renders each page in the signed-in user's language, and `static/i18n.js` re-translates the page instantly when RW / EN / FR is clicked and saves the choice to the account (`users.language`, default `rw`). To add or change a string, edit its row in `translations.py` and use `{{ t('key') }}` / `data-i18n="key"` in templates or `flash_t('key')` in `app.py`.

## Limitations — do not deploy for real financial use

- **SQLite instead of requested PostgreSQL/Prisma/Next.js stack**; suitable for a small local test, not the specified production architecture.
- MoMo and SMS are **simulated only**; customer-triggered sandbox success is strictly a development feature, not a trustworthy real-world payment confirmation.
- No production payment gateway, webhook verification, real SMS provider, scheduled reminders, password reset, phone verification, encryption at rest, admin portal, formal migrations.
- Invitation codes are bearer secrets: only share with intended customers; production onboarding requires stronger verification and invitation expiry.
- Login throttling is in-memory and per-process only (resets on restart); no other operational security hardening; set up HTTPS, rate limiting, backups, monitoring, stronger onboarding, and penetration tests before deployment.
- Reversal of a paid credit sale may be rejected to preserve nonnegative balances. Multi-sale payment allocation is aggregate by customer/shop, not per invoice.
- The interface shows recent shop transactions only; export includes all transactions.

## Next development stage

Migrate to PostgreSQL, introduce a formal ORM/migrations, add strong phone verification and tenant permissions, build verified provider callbacks and background SMS scheduling, implement admin and password recovery, and add automated financial/security tests before any production deployment.
