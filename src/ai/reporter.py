# @project   Retail Sales & Demand Analytics Pipeline
# @author    Juan Covili <https://github.com/juanCovili>
# @repo      https://github.com/juanCovili/retail-sales-etl-pipeline
# @portfolio https://juancovili.com
# @copyright Copyright (c) 2026 Juan Covili. Todos los derechos reservados.
__author__ = "Juan Covili"
__github__ = "https://github.com/juanCovili"
__portfolio__ = "https://juancovili.com"
import sqlite3
import json
from typing import Dict, Any, List
from src.config import DATABASE_PATH
from src.ml.forecaster import DemandForecaster

class BusinessIntelligenceReporter:
    """
    Módulo de Inteligencia de Negocios y Generación de Reportes Ejecutivos.
    Sintetiza métricas de la base de datos SQL y proyecciones de Machine Learning
    en resúmenes accionables para operaciones y logística.
    """

    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        self.forecaster = DemandForecaster(db_path)

    def get_kpis(self) -> Dict[str, Any]:
        """Obtiene métricas agregadas clave de ventas y operaciones."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Ventas totales y volumen
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_tx,
                    SUM(total_revenue) as total_revenue,
                    SUM(units_sold) as total_units,
                    ROUND(AVG(unit_price), 0) as avg_price
                FROM fact_sales;
            """)
            totals = dict(cursor.fetchone())

            # Top productos
            cursor.execute("""
                SELECT 
                    p.product_name,
                    p.category,
                    SUM(f.units_sold) as units,
                    SUM(f.total_revenue) as revenue
                FROM fact_sales f
                JOIN dim_products p ON f.product_id = p.product_id
                GROUP BY p.product_id
                ORDER BY revenue DESC
                LIMIT 3;
            """)
            top_products = [dict(r) for r in cursor.fetchall()]

            # Rendimiento por región
            cursor.execute("""
                SELECT 
                    s.region,
                    SUM(f.total_revenue) as revenue,
                    SUM(f.units_sold) as units
                FROM fact_sales f
                JOIN dim_stores s ON f.store_id = s.store_id
                GROUP BY s.region
                ORDER BY revenue DESC;
            """)
            by_region = [dict(r) for r in cursor.fetchall()]

            # Uplift promocional
            cursor.execute("""
                SELECT 
                    is_promo,
                    ROUND(AVG(units_sold), 1) as avg_units
                FROM fact_sales
                GROUP BY is_promo;
            """)
            promo_stats = {r['is_promo']: r['avg_units'] for r in cursor.fetchall()}

        promo_uplift_pct = 0.0
        if 0 in promo_stats and 1 in promo_stats and promo_stats[0] > 0:
            promo_uplift_pct = round(((promo_stats[1] - promo_stats[0]) / promo_stats[0]) * 100, 1)

        return {
            "total_revenue_clp": totals['total_revenue'],
            "total_units_sold": totals['total_units'],
            "total_transactions": totals['total_tx'],
            "average_unit_price": totals['avg_price'],
            "top_products": top_products,
            "regional_performance": by_region,
            "promo_uplift_percentage": promo_uplift_pct
        }

    def generate_executive_brief(self, focus_product_id: str = "PRD-01") -> Dict[str, Any]:
        """
        Genera un informe ejecutivo consolidado combinando
        análisis descriptivo (SQL) y analítica predictiva (ML).
        """
        kpis = self.get_kpis()
        ml_prediction = self.forecaster.predict_next_7_days(focus_product_id)

        projected_units_7d = sum(f['predicted_units'] for f in ml_prediction['forecast_7_days'])
        peak_day = max(ml_prediction['forecast_7_days'], key=lambda x: x['predicted_units'])

        # Alertas operacionales y recomendaciones logísticas
        alerts = []
        if peak_day['predicted_units'] > 160:
            alerts.append(
                f"ALERTA DE CAPACIDAD: Se proyecta un pico de {peak_day['predicted_units']} unidades "
                f"el {peak_day['day_name']} {peak_day['date']} debido a temperaturas estimadas de {peak_day['expected_temp_c']}°C."
            )

        if kpis['promo_uplift_percentage'] > 15.0:
            alerts.append(
                f"IMPACTO PROMOCIONAL: Las campañas de descuento generan un incremento de demanda de +{kpis['promo_uplift_percentage']}%. "
                "Coordinar stock buffer en centros mayoristas."
            )

        markdown_report = f"""# 📊 Resumen Ejecutivo de Demanda y Operaciones Retail

**Fecha de Generación:** Automatizada por Pipeline ETL & ML  
**Métrica Clave:** Proyección a 7 Días para SKU Líder (`{focus_product_id}`)

---

### 1. Resumen de Desempeño Comercial
- **Ingresos Totales Acumulados:** ${kpis['total_revenue_clp']:,} CLP
- **Volumen Total Distribuido:** {kpis['total_units_sold']:,} unidades en {kpis['total_transactions']:,} transacciones.
- **Efectividad Promocional:** Las promociones impulsan un **+{kpis['promo_uplift_percentage']}%** en volumen unitario promedio.
- **Región con Mayor Tracción:** {kpis['regional_performance'][0]['region']} con ${kpis['regional_performance'][0]['revenue']:,} CLP.

### 2. Proyección Predictiva (Modelo Ridge Regression - $R^2$: {ml_prediction['metrics']['r2']})
- **Demanda Proyectada (Próximos 7 días):** **{projected_units_7d:,} unidades**
- **Día de Mayor Demanda:** {peak_day['day_name']} {peak_day['date']} ({peak_day['predicted_units']} unidades).
- **Margen de Error del Modelo:** MAE de ±{ml_prediction['metrics']['mae']} unidades (RMSE: {ml_prediction['metrics']['rmse']}).

### 3. Alertas y Recomendaciones para Logística
{chr(10).join(f"- ⚠️ {a}" for a in alerts)}
"""

        return {
            "kpis": kpis,
            "forecast_summary": {
                "product_id": focus_product_id,
                "projected_units_7d": projected_units_7d,
                "peak_day": peak_day,
                "model_metrics": ml_prediction['metrics'],
                "daily_breakdown": ml_prediction['forecast_7_days']
            },
            "alerts": alerts,
            "markdown_brief": markdown_report
        }

if __name__ == "__main__":
    reporter = BusinessIntelligenceReporter()
    brief = reporter.generate_executive_brief("PRD-01")
    print(brief["markdown_brief"])
