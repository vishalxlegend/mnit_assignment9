# Requirements and verification

## Submission contents

GitHub publishing is left to the repository owner. Include the existing source and configuration together with this `readme/` folder; this folder is documentation, not a standalone copy of the application.

| Submission requirement | Included material |
| --- | --- |
| Frontend and backend source | Root HTML/CSS/JavaScript, product assets, [app.py](../app.py), [requirements.txt](../requirements.txt) and supporting Python modules. |
| Schema and migration scripts | [schema.sql](../schema.sql), [Alembic configuration](../alembic.ini), [migrations](../migrations), and [migration instructions](DATABASE.md). |
| Application and monitoring configuration | [setup/configuration guide](SETUP.md), [launcher](../monitoring/stack.py), [Prometheus configuration](../monitoring/prometheus.yml), [Grafana provisioning](../monitoring/grafana/provisioning) and [dashboard JSON](../monitoring/grafana/dashboards/toy-shop.json). |
| Prerequisites and single-computer commands | [README](README.md) and [SETUP](SETUP.md). |
| Architecture and decisions | [ARCHITECTURE](ARCHITECTURE.md). |
| Authentication, cart and Grafana screenshots | [Screenshot gallery](SCREENSHOTS.md) and its seven committed-ready PNG files. |

Keep generated secrets, real user databases, virtual environments, downloaded binaries and monitoring runtime data out of Git. Retain source assets, migrations, provisioning files and `readme/screenshots/`. No existing runtime database is needed for a fresh setup.

## Functional requirement mapping

| Requirement | Implementation / verification |
| --- | --- |
| Registration, login and secure passwords | Flask-Login, Werkzeug scrypt hashes, session cookies and CSRF checks; authentication tests. |
| Persistent authenticated sessions | Signed session cookie with an eight-hour lifetime and stable application secret; expiry or logout requires another login. |
| Backend authorization and private carts | Cart ownership derived from the authenticated user, with explicit access checks; two-user API tests reject cross-user access. |
| Add, change quantities and remove products | Catalog controls and cart controls use the same backend cart API; cart tests and screenshots. |
| Backend quantity/availability validation | Integer quantity limits and stock checks; invalid requests tested. |
| Trusted prices and displayed totals | Server reads product prices from SQL and returns calculated totals; client-supplied prices are not trusted. |
| SQL persistence | Users, carts and items stored in SQLite; persistence tests use new app instances. |
| Migration of existing Part 1 data | Alembic revisions and preservation/rollback tests; see [DATABASE](DATABASE.md). |
| Structured logs and sensitive-data protection | Allowlisted JSON events with timestamp, severity and request ID; privacy tests in [test_monitoring.py](../tests/test_monitoring.py). |
| HTTP and application metrics | Counters and latency histograms by endpoint/status; cart-operation and added-unit metrics. |
| Prometheus and Grafana | Scrape configuration, provisioned datasource and twelve-panel dashboard. |
| Traffic and controlled failures | Demo script exercises real requests and intentionally raises safe application/database exceptions; dashboard screenshots show the results. |

## Automated checks

From the repository root, after installing dependencies:

```sh
.venv/bin/python -m unittest discover -s tests -v
```

The recorded implementation verification passed all 23 tests. Tests cover authentication/cart ownership, migrations and monitoring. See [the monitoring verification record](../monitoring/VERIFICATION.md) for the recorded live run; numbers vary on subsequent runs.

To demonstrate cross-user protection, inspect [test_auth_cart.py](../tests/test_auth_cart.py) and run the suite. It uses separate authenticated clients and attempts API access to another user's cart. Backend rejection, rather than hidden buttons, establishes authorization.

## Repeat the live monitoring demonstration

Start the stack in one terminal:

```sh
.venv/bin/python monitoring/stack.py --app-port 5001 --demo
```

In a second terminal, from the same repository:

```sh
.venv/bin/python monitoring/verify_dashboard.py --baseline
.venv/bin/python monitoring/demo.py --app-url http://127.0.0.1:5001 --seconds 60
.venv/bin/python monitoring/verify_dashboard.py
```

Open Grafana at <http://127.0.0.1:3000>, choose the provisioned toy-shop dashboard and use a recent time range that includes the demo. Allow at least one five-second scrape interval. Request volume, error counts and cart-operation panels should increase. Authentication failures and both controlled exception types should appear in their panels. Inspect `monitoring/runtime/logs/application.jsonl` for corresponding sanitized events and request IDs.

The demo registers its own user, performs cart operations and deliberately sends invalid requests. The simulated database exception does not corrupt the database. The failure route requires authentication and CSRF and is enabled only with `--demo`.

Reports are generated under `monitoring/evidence/`. They are local runtime evidence, not required inputs for setup. Optional `--screenshots` on the dashboard verifier additionally requires Playwright and a compatible browser; it is not required to run the app or monitoring stack. Screenshots already included in this submission need no extra tooling to view.

## Manual acceptance check

1. Visit `/cart.html` while logged out: it should redirect to login.
2. Register a new account and add a product: quantity controls should appear at one.
3. Change quantities in the catalog and cart: totals should update after the server saves, without an Update button.
4. Restart the application, log in if necessary, and confirm the saved cart remains.
5. Register a second account: its cart should be separate. Run the API tests above to check manipulated requests.
6. Run the monitoring demo and observe the charts and failure events.

See [SCREENSHOTS](SCREENSHOTS.md) for the included visual evidence.
