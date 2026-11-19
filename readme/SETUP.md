# Prerequisites, configuration and setup

## Supported complete setup

- Linux x86_64 (for example, Ubuntu on an x86_64 PC).
- Python 3.12 or later with pip and venv. Python 3.14 was used for verification.
- A browser and internet access during dependency/binary installation.
- Writable space in the cloned project for the virtual environment, downloaded
  binaries, application database and monitoring data; allow several GB.
- Available localhost ports 5001, 9090 and 3000, or choose alternatives below.

On Debian/Ubuntu, if Python's venv support is missing, install your distribution's
`python3-venv` package first. The monitoring installer uses pinned Linux x86_64
binaries; native Windows/macOS require platform-specific monitoring binaries and
launcher changes. Use the documented Linux environment for the full assignment setup.
The frontend has no Node/npm build step. SQLite is included with Python.

## Fresh clone

Clone the submitted Git repository using its supplied URL, then change into the
repository root. No files or databases from the author's home directory are needed.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic current
.venv/bin/python monitoring/install.py
```

Expected database revision: `0002_users_and_carts (head)`.
The database starts with 20 toy vehicles and no user accounts. The installer downloads
Prometheus 3.5.0 and Grafana OSS 12.1.0 from official release hosts, verifies SHA256
checksums, and extracts them under `monitoring/bin/`. No administrator rights or Docker
are needed. These pinned binaries support the local assignment demonstration.

The installer can be rerun; it verifies cached archives before extracting them again.
Do not commit those archives or binaries. A fresh clone downloads its own copies.

## Start all components

```sh
.venv/bin/python monitoring/stack.py --app-port 5001 --demo
```

The launcher starts Waitress/Flask, Prometheus and Grafana and checks their readiness.
Use http://127.0.0.1:5001/ for all shopping interactions. Existing users and products are
read from the same `products.db` used in Parts 1 and 2.

Register a new shop account. Grafana uses a separate administrator account: read the
`grafana_username` and `grafana_password` values from the generated private file
`monitoring/runtime/credentials.json`. Its `metrics_token` is for Prometheus scraping,
not for logging in to the shop or Grafana. The dashboard is automatically provisioned;
no manual datasource creation or dashboard import is necessary.

For normal use, omit `--demo`; controlled-failure requests then return 404 for an
authenticated caller. To switch modes, stop the running stack before restarting it.

## Run the application without monitoring services

```sh
.venv/bin/python app.py
```

This serves the shop at http://127.0.0.1:5000/. Application instrumentation and logging
still work, but Prometheus/Grafana are not started. Use Flask/Waitress rather than
Live Server: serving raw HTML cannot enforce backend page authentication.

## Configuration

Defaults require no environment-file editing. Environment variables are read by
[app.py](../app.py); the stack launcher configures service-specific settings for you.

| Setting | Default and meaning |
| --- | --- |
| `DATABASE_PATH` | Project `products.db`; shared by app startup and Alembic CLI |
| `SECRET_KEY` | Generated private `.session-secret` when unset; signs sessions |
| `COOKIE_SECURE` | Set to `1` for HTTPS; left unset for the local HTTP demonstration |
| `APP_HOST`, `APP_PORT` | `127.0.0.1`, `5000` when running app.py alone |
| `MONITORING_DATABASE` | Separate `monitoring/runtime/monitoring.db` |
| `MONITORING_LOG_DIR` | `monitoring/runtime/logs/` |
| `METRICS_TOKEN` | Stack supplies a generated scrape token; standalone app without it restricts metrics to loopback |
| `ENABLE_FAILURE_DEMO` | Disabled unless `1`; stack `--demo` enables it |

The launcher sets app/monitoring paths and credentials explicitly. Change service
ports through its flags, which also update the Prometheus target and Grafana datasource:

```sh
.venv/bin/python monitoring/stack.py --app-port 5002 --prometheus-port 9091 --grafana-port 3001 --demo
```

When changing ports, pass matching `--app-url`, `--prometheus-url`, and `--grafana-url`
to demo/verification scripts. For example:

```sh
.venv/bin/python monitoring/demo.py --app-url http://127.0.0.1:5002 --prometheus-url http://127.0.0.1:9091 --seconds 60
.venv/bin/python monitoring/verify_dashboard.py --grafana-url http://127.0.0.1:3001
```

## Demonstrate monitoring

With the stack running in demo mode, use another terminal at the repository root:

```sh
.venv/bin/python monitoring/demo.py --app-url http://127.0.0.1:5001 --seconds 60
.venv/bin/python monitoring/verify_dashboard.py
```

The demo creates a dedicated account with a random password held only in memory. It
browses products, adds/updates/removes cart items, submits invalid quantities and an
out-of-stock product, fails a login, and triggers two non-destructive 500 errors.
It waits for Prometheus to scrape the results and verifies counter increases.

Open http://127.0.0.1:3000/d/toy-shop and select **Last 15 minutes** with 5-second refresh.
The request volume, error rate, latency and cart-operation panels reflect the traffic.
Reports are written to `monitoring/evidence/`. Logs can be read from
`monitoring/runtime/logs/application.jsonl` or the separate monitoring SQLite database.

## Stop and restart

Press **Ctrl+C in the terminal running stack.py**. All three child services are stopped;
products, accounts, carts, Grafana settings and retained Prometheus history stay saved.
On later runs, only the stack command is needed. If a terminal is closed unexpectedly
and ports remain busy, identify the launcher before stopping it:

```sh
pgrep -af '[m]onitoring/stack.py'
ss -ltnp '( sport = :5001 or sport = :9090 or sport = :3000 )'
```

Send `kill -TERM PID` using the actual PID of that stack launcher. Its signal handler
stops its app, Prometheus and Grafana children. Do not delete databases to free ports.

## Common problems

| Symptom | Action |
| --- | --- |
| `Port ... is busy` | Stop the old stack or use the port flags above |
| Demo says “Start the stack with --demo” | Restart stack.py with `--demo`; setting a flag only on demo.py does not enable server failures |
| Grafana login fails | Read this computer's generated Grafana credentials, not a shop user's credentials |
| Empty charts | Check Prometheus `/targets`, generate traffic on the monitored app URL, allow two scrapes and select a time range containing traffic |
| Missing Prometheus/Grafana executable | Run `monitoring/install.py` after installing Python requirements |
| Module not found | Use `.venv/bin/python` and reinstall `requirements.txt` |
| Startup fails | Inspect `monitoring/runtime/application-process.log`, `prometheus-process.log`, or `grafana-process.log` |

Changing the credentials JSON after Grafana's initial setup does not reset its existing
admin password. Keep the initially generated file alongside its runtime data.
