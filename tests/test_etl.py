import unittest
import sqlite3
from pathlib import Path
from src.etl.pipeline import RetailETLPipeline
from src.config import DATABASE_PATH

class TestETLPipeline(unittest.TestCase):
    """Pruebas unitarias para validación del pipeline ETL."""

    @classmethod
    def setUpClass(cls):
        cls.test_db = Path("/tmp/test_retail_dw.db")
        if cls.test_db.exists():
            cls.test_db.unlink()
        cls.pipeline = RetailETLPipeline(db_path=cls.test_db)
        cls.metrics = cls.pipeline.run()

    @classmethod
    def tearDownClass(cls):
        if cls.test_db.exists():
            cls.test_db.unlink()

    def test_pipeline_execution_status(self):
        """Verifica que el pipeline termine con status SUCCESS."""
        self.assertEqual(self.metrics["status"], "SUCCESS")
        self.assertGreater(self.metrics["transactions_loaded"], 0)
        self.assertGreater(self.metrics["stores_loaded"], 0)
        self.assertGreater(self.metrics["products_loaded"], 0)

    def test_database_tables_exist(self):
        """Valida que todas las tablas de dimensiones y hechos hayan sido creadas."""
        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in cursor.fetchall()]

        expected_tables = ["dim_stores", "dim_products", "fact_sales", "agg_daily_product_demand"]
        for table in expected_tables:
            self.assertIn(table, tables, f"La tabla {table} no fue encontrada en la base de datos.")

    def test_foreign_key_integrity(self):
        """Verifica que no existan transacciones huérfanas sin tienda o producto asociado."""
        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM fact_sales f
                LEFT JOIN dim_stores s ON f.store_id = s.store_id
                WHERE s.store_id IS NULL;
            """)
            orphan_stores = cursor.fetchone()[0]
            self.assertEqual(orphan_stores, 0, "Existen transacciones con store_id inválido.")

            cursor.execute("""
                SELECT COUNT(*) FROM fact_sales f
                LEFT JOIN dim_products p ON f.product_id = p.product_id
                WHERE p.product_id IS NULL;
            """)
            orphan_products = cursor.fetchone()[0]
            self.assertEqual(orphan_products, 0, "Existen transacciones con product_id inválido.")

    def test_non_negative_constraints(self):
        """Valida que los montos e ítems vendidos sean estrictamente no negativos."""
        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM fact_sales WHERE units_sold < 0 OR total_revenue < 0;")
            invalid_rows = cursor.fetchone()[0]
            self.assertEqual(invalid_rows, 0, "Existen registros con valores numéricos negativos.")

if __name__ == "__main__":
    unittest.main()
