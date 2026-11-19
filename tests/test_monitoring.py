"""No user secrets in telemetry; isolated monitoring storage and meaningful metrics."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from app import create_app
from test_auth_cart import BufferedClient
import test_auth_cart as auth_tests


class MonitoringTests(unittest.TestCase):
    form_token = auth_tests.AuthenticationAndCartTests.form_token
    register = auth_tests.AuthenticationAndCartTests.register
    headers = auth_tests.AuthenticationAndCartTests.headers

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.app = create_app({"TESTING": True, "SECRET_KEY": "secret-test-key",
                               "DATABASE": self.root / "shop.db", "MONITORING_LOG_DIR": self.root / "logs",
                               "MONITORING_DATABASE": self.root / "monitoring.db", "METRICS_TOKEN": "private-scrape-token",
                               "ENABLE_FAILURE_DEMO": True})
        self.monitor = self.app.extensions['monitoring']
        self.addCleanup(self.monitor.close)
        self.app.test_client_class = BufferedClient
        self.client = self.app.test_client()

    def logs(self):
        self.monitor.flush()
        return (self.root/'logs/application.jsonl').read_text()

    def test_metrics_scrape_has_no_shop_database_access(self):
        self.assertEqual(self.client.get('/metrics').status_code,403)
        with patch('app.get_database',side_effect=AssertionError('must not query shop database')):
            response=self.client.get('/metrics',headers={'Authorization':'Bearer private-scrape-token'})
        self.assertEqual(response.status_code,200)
        self.assertIn('shop_http_requests_total',response.text)
        self.assertIn('shop_http_request_duration_seconds_bucket',response.text)
        self.assertIn('shop_http_errors_total',response.text)
        self.assertIn('shop_cart_operations_total',response.text)
        self.assertNotIn('private-scrape-token',response.text)

    def test_http_counts_errors_and_latency_include_denied_requests(self):
        response = self.client.get('/api/products')
        self.assertEqual(response.status_code, 401)
        labels = {'method': 'GET', 'endpoint': 'products_api', 'status': '401'}
        self.assertEqual(self.monitor.registry.get_sample_value('shop_http_requests_total', labels), 1)
        self.assertEqual(self.monitor.registry.get_sample_value('shop_http_errors_total', labels), 1)
        latency_labels = {'method': 'GET', 'endpoint': 'products_api'}
        self.assertEqual(self.monitor.registry.get_sample_value('shop_http_request_duration_seconds_count', latency_labels), 1)
        self.assertGreater(self.monitor.registry.get_sample_value('shop_http_request_duration_seconds_sum', latency_labels), 0)

    def test_request_ids_and_auth_failure_logs_do_not_contain_secrets(self):
        secret='SensitivePassword!'
        response=self.client.post('/login?token=SensitiveQuery',data={
            'username':'private_person','password':secret,
            'csrf_token':self.form_token(self.client,'/login')},
            headers={'Authorization':'Bearer SensitiveHeader','X-Request-ID':'SensitiveId'})
        self.assertEqual(response.status_code,401)
        logs=self.logs()
        for value in [secret,'SensitiveQuery','SensitiveHeader','SensitiveId','private_person','secret-test-key']:
            self.assertNotIn(value,logs)
        events=[json.loads(line) for line in logs.splitlines()]
        failures=[event for event in events if event['event']=='authentication_failed']
        self.assertEqual(len(failures),1)
        self.assertEqual(failures[0]['request_id'],response.headers['X-Request-ID'])
        for event in events:
            self.assertIn('timestamp',event)
            self.assertIn('level',event)
        self.assertEqual(self.monitor.auth_failures._value.get(),1)
        with closing(sqlite3.connect(self.root/'shop.db')) as db:
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='events'").fetchone())
        with closing(sqlite3.connect(self.root/'monitoring.db')) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0],len(events))

    def test_exceptions_are_sanitized_and_counted(self):
        self.register(self.client)
        for error,metric in [(sqlite3.OperationalError('SECRET SQL and token'),self.monitor.db_errors),
                             (RuntimeError('SECRET user information'),self.monitor.exceptions)]:
            with patch('app.get_database',side_effect=error):
                response=self.client.get('/api/products')
            self.assertEqual(response.status_code,500)
            self.assertNotIn('SECRET',response.text)
            self.assertEqual(metric._value.get(),1)
        logs=self.logs()
        self.assertIn('database_error',logs)
        self.assertIn('application_exception',logs)
        self.assertNotIn('SECRET',logs)
        self.assertIn('frames',logs)

    def test_committed_cart_operations_are_counted_not_rejected_operations(self):
        self.register(self.client)
        headers=self.headers(self.client)
        self.client.post('/api/cart/items',json={'product_id':1,'quantity':2},headers=headers)
        self.client.patch('/api/cart/items/1',json={'quantity':3},headers=headers)
        self.client.patch('/api/cart/items/1',json={'quantity':100},headers=headers)
        self.client.delete('/api/cart/items/1',headers=headers)
        for operation in ('add','update','remove'):
            self.assertEqual(self.monitor.cart_operations.labels(operation)._value.get(),1)
        self.assertEqual(self.monitor.cart_added._value.get(),2)

    def test_failure_demo_is_disabled_by_default_and_requires_login_and_csrf(self):
        self.assertEqual(self.client.post('/api/demo/failure').status_code,401)
        self.register(self.client)
        self.assertEqual(self.client.post('/api/demo/failure').status_code,400)
        headers=self.headers(self.client)
        self.app.config['ENABLE_FAILURE_DEMO']=False
        self.assertEqual(self.client.post('/api/demo/failure',headers=headers).status_code,404)
        self.app.config['ENABLE_FAILURE_DEMO']=True
        self.assertEqual(self.client.post('/api/demo/failure',headers=headers).status_code,500)
        self.assertEqual(self.client.post('/api/demo/failure?kind=database',headers=headers).status_code,500)
        self.assertEqual(self.monitor.exceptions._value.get(),1)
        self.assertEqual(self.monitor.db_errors._value.get(),1)

    def test_metrics_labels_use_endpoint_names_not_user_supplied_paths(self):
        self.client.get('/api/unrecognized/secret-person?password=secret')
        response=self.client.get('/metrics',headers={'Authorization':'Bearer private-scrape-token'})
        self.assertIn('endpoint="unmatched"',response.text)
        self.assertNotIn('secret-person',response.text)
        self.assertNotIn('password',response.text)


if __name__=='__main__':
    unittest.main()
