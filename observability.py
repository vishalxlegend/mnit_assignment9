"""Bounded-cardinality metrics and sanitized logs, isolated from the shop database."""
import atexit
from datetime import datetime, timezone
import json
import logging
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler
from pathlib import Path
from queue import Queue
import secrets
import sqlite3
import time
import traceback
import uuid

from flask import Response, abort, g, has_request_context, jsonify, request
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST


class EventSink(logging.Handler):
    """Runs only on the log listener thread; never connects to products.db."""
    def __init__(self, directory, database, failures):
        super().__init__()
        directory.mkdir(parents=True, exist_ok=True)
        database.parent.mkdir(parents=True, exist_ok=True)
        self.database = database
        self.file = RotatingFileHandler(directory / 'application.jsonl', maxBytes=5_000_000, backupCount=3)
        self.file.setFormatter(logging.Formatter('%(message)s'))
        self.failures = failures
        self.written = 0
        self.connection = None

    def emit(self, record):
        # record.msg contains only our allowlisted, already serialized event.
        self.file.emit(record)
        try:
            if self.connection is None:
                self.connection = sqlite3.connect(self.database, timeout=1, check_same_thread=False)
                self.connection.execute('PRAGMA journal_mode=WAL')
                self.connection.execute('CREATE TABLE IF NOT EXISTS events ('
                                        'id INTEGER PRIMARY KEY, timestamp TEXT NOT NULL, level TEXT NOT NULL, '
                                        'event TEXT NOT NULL, request_id TEXT, payload TEXT NOT NULL)')
                self.connection.commit()
            with self.connection as db:
                data = json.loads(record.getMessage())
                db.execute('INSERT INTO events(timestamp, level, event, request_id, payload) VALUES(?,?,?,?,?)',
                           (data['timestamp'], data['level'], data['event'], data.get('request_id'), record.getMessage()))
                self.written += 1
                if self.written % 100 == 0:
                    db.execute('DELETE FROM events WHERE id <= (SELECT max(id) - 10000 FROM events)')
        except (sqlite3.Error, OSError):
            self.failures.inc()
            if self.connection is not None:
                self.connection.close()
                self.connection = None

    def close(self):
        if self.connection is not None:
            self.connection.close()
            self.connection = None
        self.file.close()
        super().close()


class SafeQueueHandler(QueueHandler):
    def __init__(self, queue, dropped):
        super().__init__(queue)
        self.dropped = dropped

    def handleError(self, record):
        # Full queues drop telemetry instead of delaying application requests.
        self.dropped.inc()


class Monitoring:
    def __init__(self, app):
        self.registry = CollectorRegistry()
        labels = ('method', 'endpoint', 'status')
        self.requests = Counter('shop_http_requests_total', 'Completed HTTP requests', labels, registry=self.registry)
        self.errors = Counter('shop_http_errors_total', 'HTTP responses with status >= 400', labels, registry=self.registry)
        self.latency = Histogram('shop_http_request_duration_seconds', 'Time to produce an HTTP response',
                                 ('method', 'endpoint'), buckets=(.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10), registry=self.registry)
        self.cart_operations = Counter('shop_cart_operations_total', 'Committed cart mutations', ('operation',), registry=self.registry)
        self.cart_added = Counter('shop_cart_products_added_total', 'Product units successfully added to carts', registry=self.registry)
        self.auth_failures = Counter('shop_auth_failures_total', 'Failed credential checks', registry=self.registry)
        self.db_errors = Counter('shop_database_errors_total', 'Application database failures', registry=self.registry)
        self.exceptions = Counter('shop_exceptions_total', 'Unexpected application exceptions', registry=self.registry)
        self.dropped = Counter('shop_log_events_dropped_total', 'Events dropped because the log queue is full', registry=self.registry)
        self.sink_failures = Counter('shop_log_storage_errors_total', 'Monitoring database write failures', registry=self.registry)
        for operation in ('add', 'update', 'remove'):
            self.cart_operations.labels(operation).inc(0)
        self.logger = logging.Logger('shop.events', level=logging.INFO)
        self.logger.propagate = False
        self.listener = None
        self.sink = None
        # Unit tests opt into a temporary log directory when testing log persistence.
        if not app.testing or app.config.get('MONITORING_LOG_DIR'):
            directory = Path(app.config['MONITORING_LOG_DIR'] or Path(app.root_path) / 'monitoring/runtime/logs')
            database = Path(app.config['MONITORING_DATABASE'] or Path(app.root_path) / 'monitoring/runtime/monitoring.db')
            if database.resolve() == Path(app.config['DATABASE']).resolve():
                raise ValueError('Monitoring and application databases must be different files.')
            self.sink = EventSink(directory, database, self.sink_failures)
            self.queue = Queue(maxsize=10000)
            self.logger.addHandler(SafeQueueHandler(self.queue, self.dropped))
            self.listener = QueueListener(self.queue, self.sink)
            self.listener.start()
            atexit.register(self.close)
        else:
            self.logger.addHandler(logging.NullHandler())

    def log(self, event, level='INFO', **fields):
        # Never accept arbitrary user values, raw URLs, headers, bodies, SQL,
        # exception messages or traceback locals. IDs are server-generated.
        allowed = {'method', 'endpoint', 'status', 'duration_ms', 'operation', 'error_type', 'frames'}
        data = {'timestamp': datetime.now(timezone.utc).isoformat(), 'level': level,
                'event': event, 'request_id': getattr(g, 'request_id', None) if has_request_context() else None}
        data.update({key: value for key, value in fields.items() if key in allowed})
        self.logger.log(getattr(logging, level), json.dumps(data, separators=(',', ':')))

    def failure(self, error, database=False):
        (self.db_errors if database else self.exceptions).inc()
        frames = [{'file': Path(frame.filename).name, 'line': frame.lineno, 'function': frame.name}
                  for frame in traceback.extract_tb(error.__traceback__)]
        self.log('database_error' if database else 'application_exception', 'ERROR',
                 error_type=type(error).__name__, frames=frames)

    def auth_failed(self):
        self.auth_failures.inc()
        self.log('authentication_failed', 'WARNING')

    def cart_completed(self, operation, added=0):
        self.cart_operations.labels(operation).inc()
        if added:
            self.cart_added.inc(added)
        self.log('cart_operation_completed', operation=operation)

    def flush(self):
        if self.listener:
            self.queue.join()

    def close(self):
        if self.listener:
            self.flush()
            self.listener.stop()
            self.listener = None
            self.sink.close()


def install_monitoring(app):
    monitor = Monitoring(app)
    app.extensions['monitoring'] = monitor

    @app.before_request
    def start_request():
        g.request_started = time.perf_counter()
        g.request_id = uuid.uuid4().hex

    @app.after_request
    def finish_request(response):
        elapsed = time.perf_counter() - getattr(g, 'request_started', time.perf_counter())
        # Flask endpoint names are bounded; raw paths/query strings never become labels.
        endpoint = request.endpoint or 'unmatched'
        method = request.method if request.method in {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'} else 'OTHER'
        status = str(response.status_code)
        monitor.requests.labels(method, endpoint, status).inc()
        monitor.latency.labels(method, endpoint).observe(elapsed)
        if response.status_code >= 400:
            monitor.errors.labels(method, endpoint, status).inc()
        response.headers['X-Request-ID'] = g.request_id
        if endpoint not in {'metrics', 'healthz'}:
            monitor.log('http_request', 'ERROR' if response.status_code >= 500 else 'WARNING' if response.status_code >= 400 else 'INFO',
                        method=method, endpoint=endpoint, status=response.status_code, duration_ms=round(elapsed * 1000, 3))
        return response

    @app.get('/metrics')
    def metrics():
        token = app.config.get('METRICS_TOKEN')
        if token:
            if not secrets.compare_digest(request.headers.get('Authorization', ''), 'Bearer ' + token):
                abort(403)
        elif request.remote_addr not in {'127.0.0.1', '::1'}:
            abort(403)
        return Response(generate_latest(monitor.registry), content_type=CONTENT_TYPE_LATEST)

    @app.get('/healthz')
    def healthz():
        return jsonify(status='ok')

    @app.errorhandler(sqlite3.Error)
    def database_error(error):
        monitor.failure(error, database=True)
        return jsonify(error='Database temporarily unavailable.', request_id=g.request_id), 500

    @app.errorhandler(Exception)
    def unexpected_error(error):
        monitor.failure(error)
        return jsonify(error='Unable to complete the request.', request_id=g.request_id), 500

    return monitor
