#!/usr/bin/env python3
# @project   Retail Sales & Demand Analytics Pipeline
# @author    Juan Covili <https://github.com/juanCovili>
# @repo      https://github.com/juanCovili/retail-sales-etl-pipeline
# @portfolio https://juancovili.com
# @copyright Copyright (c) 2026 Juan Covili. Todos los derechos reservados.
"""
Retail Sales & Demand Analytics Pipeline - CLI Entrypoint
Ejecuta el ciclo de vida completo: Ingesta ETL -> Data Warehouse SQL -> Machine Learning -> IA Insights.
"""

__author__ = "Juan Covili"
__github__ = "https://github.com/juanCovili"
__portfolio__ = "https://juancovili.com"

import sys
import json
from pathlib import Path
from src.etl.pipeline import RetailETLPipeline
from src.ml.forecaster import DemandForecaster
from src.ai.reporter import BusinessIntelligenceReporter
from src.config import PROCESSED_DATA_DIR

def main():
    print("=" * 70)
    print("🚀 RETAIL SALES & DEMAND ANALYTICS PIPELINE")
    print("=" * 70)

    # 1. Pipeline ETL
    print("\n[ETL] Ingestando y transformando fuentes de datos (CSV + JSON)...")
    etl = RetailETLPipeline()
    etl_metrics = etl.run()
    print(f"  ✓ Tiendas cargadas: {etl_metrics['stores_loaded']}")
    print(f"  ✓ Productos cargados: {etl_metrics['products_loaded']}")
    print(f"  ✓ Transacciones de venta procesadas: {etl_metrics['transactions_loaded']:,}")
    print(f"  ✓ Agregaciones diarias calculadas: {etl_metrics['daily_aggregates_created']}")
    print(f"  ✓ Tiempo de ejecución: {etl_metrics['elapsed_seconds']}s")

    # 2. Machine Learning Demand Forecast
    print("\n[ML] Entrenando modelo predictivo de demanda (Ridge Regression)...")
    forecaster = DemandForecaster()
    target_sku = "PRD-01"
    ml_result = forecaster.predict_next_7_days(target_sku)
    metrics = ml_result["metrics"]
    print(f"  ✓ SKU Objetivo: {target_sku} (Bebida Cola Clásica 1.5L)")
    print(f"  ✓ Bondad de ajuste (R²): {metrics['r2']} ({metrics['r2']*100:.1f}%)")
    print(f"  ✓ Error Medio Absoluto (MAE): ±{metrics['mae']} unidades")
    print(f"  ✓ RMSE: {metrics['rmse']}")
    print("\n  Proyección Próximos 7 Días:")
    for f in ml_result["forecast_7_days"]:
        promo_tag = " [PROMO]" if f["is_promo"] else ""
        print(f"    • {f['date']} ({f['day_name']}): {f['predicted_units']} u. ({f['expected_temp_c']}°C){promo_tag}")

    # 3. Business Intelligence & AI Insights
    print("\n[BI & IA] Generando diagnóstico ejecutivo y recomendaciones logísticas...")
    reporter = BusinessIntelligenceReporter()
    report = reporter.generate_executive_brief(target_sku)

    # Guardar artefactos
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    report_md_path = PROCESSED_DATA_DIR / "executive_report.md"
    report_json_path = PROCESSED_DATA_DIR / "executive_report.json"

    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write(report["markdown_brief"])

    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"  ✓ Reporte Markdown exportado a: {report_md_path}")
    print(f"  ✓ Reporte JSON estructurado exportado a: {report_json_path}")
    print("\n" + "=" * 70)
    print("✅ Pipeline ejecutado exitosamente en su totalidad.")
    print("=" * 70)

if __name__ == "__main__":
    main()
