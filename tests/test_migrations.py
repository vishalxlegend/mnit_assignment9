"""Alembic compatibility, preservation and transactional upgrade tests."""
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest

from alembic import command
from db_migrations import ROOT, migration_config, upgrade_database

HEAD = "0002_users_and_carts"


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "migration.db"

    def test_fresh_database_and_repeated_upgrade(self):
        upgrade_database(self.database)
        with closing(sqlite3.connect(self.database)) as db:
            self.assertEqual(db.execute("SELECT version_num FROM alembic_version").fetchone()[0], HEAD)
            before = db.execute("SELECT * FROM products ORDER BY id").fetchall()
            self.assertEqual(len(before), 20)
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
        upgrade_database(self.database)
        with closing(sqlite3.connect(self.database)) as db:
            self.assertEqual(db.execute("SELECT * FROM products ORDER BY id").fetchall(), before)

    def test_part1_upgrade_preserves_every_product_field(self):
        with closing(sqlite3.connect(self.database)) as db:
            db.executescript((ROOT / "migrations/data/part1_products.sql").read_text())
            db.execute("UPDATE products SET name = 'Original vehicle', description = 'Custom record', "
                       "price_paise = 76543210, image_url = '/custom.jpg', stock = 42 WHERE id = 1")
            db.execute("INSERT INTO products VALUES (77, 'Extra', 'Part 1 custom product', 12345, '/77.jpg', 9)")
            db.commit()
            before = db.execute("SELECT * FROM products ORDER BY id").fetchall()
        upgrade_database(self.database)
        with closing(sqlite3.connect(self.database)) as db:
            self.assertEqual(db.execute("SELECT * FROM products ORDER BY id").fetchall(), before)
            self.assertEqual(db.execute("SELECT version_num FROM alembic_version").fetchone()[0], HEAD)
            for table in ["users", "carts", "cart_items"]:
                self.assertEqual(db.execute(f"SELECT count(*) FROM {table}").fetchone()[0], 0)
            db.execute("PRAGMA foreign_keys=ON")
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("INSERT INTO carts (user_id) VALUES (999)")

    def test_adopts_legacy_users_and_carts_without_data_loss(self):
        with closing(sqlite3.connect(self.database)) as db:
            db.executescript((ROOT / "schema.sql").read_text())
            db.execute("INSERT INTO users (id, name, username, password_hash) VALUES (7, 'Existing User', 'existing', 'unchanged-hash')")
            db.execute("INSERT INTO carts (id, user_id) VALUES (12, 7)")
            db.execute("INSERT INTO cart_items VALUES (12, 1, 3)")
            db.commit()
            before = {table: db.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
                      for table in ["products", "users", "carts", "cart_items"]}
        upgrade_database(self.database)
        upgrade_database(self.database)
        with closing(sqlite3.connect(self.database)) as db:
            for table, rows in before.items():
                self.assertEqual(db.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall(), rows)
            self.assertEqual(db.execute("SELECT version_num FROM alembic_version").fetchone()[0], HEAD)

    def test_failed_revision_rolls_back_schema_and_version(self):
        # Start at a legitimate prior revision, then introduce an incompatible legacy table.
        command.upgrade(migration_config(self.database), "0001_products")
        with closing(sqlite3.connect(self.database)) as db:
            db.execute("CREATE TABLE carts (wrong_column TEXT)")
            db.execute("INSERT INTO carts VALUES ('preserve me')")
            db.commit()
            products = db.execute("SELECT * FROM products ORDER BY id").fetchall()
        with self.assertRaisesRegex(RuntimeError, "incompatible schema"):
            upgrade_database(self.database)
        with closing(sqlite3.connect(self.database)) as db:
            self.assertEqual(db.execute("SELECT version_num FROM alembic_version").fetchone()[0], "0001_products")
            # The users table created earlier in the failed revision must also roll back.
            self.assertIsNone(db.execute("SELECT name FROM sqlite_master WHERE name='users'").fetchone())
            self.assertEqual(db.execute("SELECT * FROM carts").fetchall(), [('preserve me',)])
            self.assertEqual(db.execute("SELECT * FROM products ORDER BY id").fetchall(), products)


if __name__ == "__main__":
    unittest.main()
