# @project   Retail Sales & Demand Analytics Pipeline
# @author    Juan Covili <https://github.com/juanCovili>
# @repo      https://github.com/juanCovili/retail-sales-etl-pipeline
# @portfolio https://juancovili.com
# @copyright Copyright (c) 2026 Juan Covili. Todos los derechos reservados.
__author__ = "Juan Covili"
__github__ = "https://github.com/juanCovili"
__portfolio__ = "https://juancovili.com"
import unittest
from pathlib import Path
from src.etl.pipeline import RetailETLPipeline
from src.ml.forecaster import DemandForecaster
from src.ai.reporter import BusinessIntelligenceReporter

class TestForecasterAndReporter(unittest.TestCase):
    """Pruebas unitarias para los módulos de Machine Learning y Reportería."""

    @classmethod
    def setUpClass(cls):
        cls.test_db = Path("/tmp/test_forecast_dw.db")
        if cls.test_db.exists():
            cls.test_db.unlink()
        cls.pipeline = RetailETLPipeline(db_path=cls.test_db)
        cls.pipeline.run()
        cls.forecaster = DemandForecaster(db_path=cls.test_db)
        cls.reporter = BusinessIntelligenceReporter(db_path=cls.test_db)

    @classmethod
    def tearDownClass(cls):
        if cls.test_db.exists():
            cls.test_db.unlink()

    def test_forecast_generation(self):
        """Verifica que el modelo genere 7 días de proyecciones válidas."""
        res = self.forecaster.predict_next_7_days("PRD-01")
        self.assertEqual(len(res["forecast_7_days"]), 7)
        
        # Validar métricas
        metrics = res["metrics"]
        self.assertIn("mae", metrics)
        self.assertIn("rmse", metrics)
        self.assertIn("r2", metrics)
        self.assertGreaterEqual(metrics["r2"], 0.0)
        self.assertLessEqual(metrics["r2"], 1.0)

        # Validar que las unidades proyectadas sean positivas
        for day in res["forecast_7_days"]:
            self.assertGreater(day["predicted_units"], 0)
            self.assertIn("date", day)
            self.assertIn("day_name", day)

    def test_reporter_kpis(self):
        """Verifica que el generador de reportes extraiga KPIs comerciales consistentes."""
        kpis = self.reporter.get_kpis()
        self.assertGreater(kpis["total_revenue_clp"], 0)
        self.assertGreater(kpis["total_units_sold"], 0)
        self.assertGreater(len(kpis["top_products"]), 0)
        self.assertGreater(len(kpis["regional_performance"]), 0)

    def test_executive_brief_structure(self):
        """Valida que el informe ejecutivo contenga secciones y alertas estructuradas."""
        brief = self.reporter.generate_executive_brief("PRD-01")
        self.assertIn("markdown_brief", brief)
        self.assertIn("forecast_summary", brief)
        self.assertIn("alerts", brief)
        self.assertIn("Resumen Ejecutivo", brief["markdown_brief"])

if __name__ == "__main__":
    unittest.main()
