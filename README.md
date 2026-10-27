# kwishyura — Trust in Every Transaction.

A web app that replaces paper credit notebooks in small shops. Shopkeepers record credit sales and repayments; customers see their own balances and statements, can start (simulated) Mobile Money payments, and receive SMS reminders.

> **Status: development build.** The MTN MoMo integration and any real SMS gateway are **not** implemented. Both run in clearly labelled simulation modes. Do not treat this as production-ready (see *Limitations*).

## Quick start
```bash
npm install
cp .env.example .env        # then set AUTH_SECRET to a random string of 32+ characters
npm run seed                # fictional demo data (safe to re-run)
npm run dev                 # http://localhost:3000
npm run worker              # (second terminal) SMS reminders + sending, every 60 s
```
Requires Node 22.13+ (uses the built-in `node:sqlite`; Node prints an "experimental" warning). The database is the file `dev.db`, created automatically.

**Demo accounts** (all fictional, password `DemoPass123!`): shopkeeper `+250788000001`; linked customer `+250788000101`. The seed script prints invite codes for two unlinked demo customers.

## Commands
| Command | What it does |
|---|---|
| `npm test` | Vitest: ledger rules, database layer, linking/access, payments, SMS, disputes, CSV, password reset (33 tests) |
| `npm run typecheck` / `npm run build` | Type check / production build |
| `npm run worker` | Background reminder + SMS sender |
| `npm run seed` | Demo data |

## What is implemented
- **Auth:** shopkeeper and customer registration, login/logout, password reset (single-use 30-minute token, only a hash stored), server-side role checks on every page/action, login and link-code rate limiting.
- **Shopkeeper:** customers (search, add), credit sales (server-calculated totals, idempotent submit), cash repayments, reversals with a mandatory reason, statement with running balance, dashboard totals (credit issued / repayments received / outstanding / overdue shown separately), customer questions, SMS settings and log, CSV export (`/dashboard/export?from=YYYY-MM-DD&to=YYYY-MM-DD`).
- **Customer:** links a shop with a one-time invite code that must match their registered phone number; read-only statements; sandbox Mobile Money payments with status tracking; questions about a transaction.
- **Ledger rules:** integer RWF amounts; append-only entries; `balance = credit sales − confirmed repayments + adjustments`, excluding reversed/failed/pending entries; repayments cannot exceed the balance; repayments apply to the oldest credit first (FIFO). Every sensitive action is written to the `audit` table.
- **Payments (sandbox):** pending → verified success creates the repayment. Signature-checked webhook (`POST /api/payments/webhook`, header `x-signature`), duplicate/replayed events ignored, wrong amount or overpayment routed to "Under review", timeouts expire, late success still honoured.
- **SMS:** adapter interface, development log provider (no real SMS), de-duplicated reminders (upcoming; overdue at most weekly), retries with backoff (2/4/8/16 min, fail after 5), status tracking. Trigger externally with `POST /api/cron/reminders` and `Authorization: Bearer $CRON_SECRET`.

## Configuration (`.env`)
`DATABASE_URL` is unused (kept for a future Postgres move). Used: `AUTH_SECRET` (required, 32+ chars), `PAYMENT_PROVIDER=sandbox`, `SANDBOX_WEBHOOK_SECRET` (**required in production mode**), `SMS_PROVIDER=dev-log`, `APP_URL` (links in reset SMS), `CRON_SECRET`, `KW_DB` (database path, default `dev.db`).
In development the password-reset link appears in the **server console** (dev SMS log).

## Enabling real providers (not done)
- **MTN MoMo:** needs approved MTN credentials and their official API docs. Implement `PaymentProvider` (`src/lib/payments/provider.ts`: `initiate`, `verifyWebhook`), add it to `getProvider()`, and query the provider for status before expiring pending payments. No endpoints are assumed here.
- **SMS gateway:** implement `SmsProvider` (`src/lib/sms.ts`) and add it to `getSmsProvider()`.

## Limitations (please read)
Not built: real MTN MoMo and SMS adapters; **phone-number verification**; **system-administrator role** and audited support access; **MoMo agent module**; charts; printable receipts/statements; shopkeeper screen for resolving "Under review" payments; customer deactivation UI; product catalogue; end-to-end browser tests and mobile layout testing (layouts are responsive CSS but were not tested on devices); load testing against the 3-second target.
Security gaps: phone numbers and purchases are **not encrypted at rest** (the project brief asks for it; use disk/database encryption or field encryption before production); rate limiting is in-memory (single process only); CSRF relies on Next.js Server Action origin checks plus SameSite=Lax cookies; no Content-Security-Policy yet; SQLite is single-writer and suited to development or very small deployments — plan a PostgreSQL move for real use. Dates are stored in UTC; due dates are treated as UTC calendar days.
**Backups:** stop the app or use `sqlite3 dev.db ".backup backup.db"`; test restores before relying on them.
