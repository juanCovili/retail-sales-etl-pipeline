# @project   Retail Sales & Demand Analytics Pipeline
# @author    Juan Covili <https://github.com/juanCovili>
# @repo      https://github.com/juanCovili/retail-sales-etl-pipeline
# @portfolio https://juancovili.com
# @copyright Copyright (c) 2026 Juan Covili. Todos los derechos reservados.
__author__ = "Juan Covili"
__github__ = "https://github.com/juanCovili"
__portfolio__ = "https://juancovili.com"
import csv
import json
import sqlite3
import time
from typing import Dict, Any, List, Tuple
from src.config import (
    RAW_SALES_CSV,
    RAW_STORES_JSON,
    DATABASE_PATH,
    SCHEMA_SQL_PATH
)

class RetailETLPipeline:
    """
    Pipeline de Ingesta, Limpieza, Transformación y Carga (ETL)
    para datos transaccionales de venta en consumo masivo.
    """

    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def init_database(self) -> None:
        """Inicializa las tablas e índices del Data Warehouse relacional."""
        with open(SCHEMA_SQL_PATH, 'r', encoding='utf-8') as f:
            schema_ddl = f.read()

        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(schema_ddl)
            conn.commit()

    def extract_stores(self) -> List[Dict[str, Any]]:
        """Extrae metadata de tiendas desde JSON semiestructurado."""
        with open(RAW_STORES_JSON, 'r', encoding='utf-8') as f:
            stores = json.load(f)
        return stores

    def extract_sales(self) -> List[Dict[str, Any]]:
        """Extrae transacciones de ventas desde archivo CSV."""
        sales = []
        with open(RAW_SALES_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sales.append(row)
        return sales

    def transform_data(
        self, raw_sales: List[Dict[str, Any]], raw_stores: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Limpia, valida tipos, filtra registros corruptos y desacopla dimensiones.
        """
        # 1. Dimensión Tiendas
        clean_stores = []
        for s in raw_stores:
            clean_stores.append({
                'store_id': str(s['store_id']).strip(),
                'store_name': str(s['name']).strip(),
                'region': str(s['region']).strip(),
                'store_format': str(s['format']).strip()
            })

        # 2. Dimensión Productos (deduplicada de las transacciones)
        products_map = {}
        clean_facts = []

        for row in raw_sales:
            # Validación de nulos y tipos
            tx_id = str(row['transaction_id']).strip()
            sale_date = str(row['date']).strip()
            store_id = str(row['store_id']).strip()
            product_id = str(row['product_id']).strip()
            product_name = str(row['product_name']).strip()
            category = str(row['category']).strip()
            
            try:
                units = max(0, int(row['units_sold']))
                unit_price = max(0.0, float(row['unit_price']))
                total_amount = float(row.get('total_amount', units * unit_price))
                is_promo = int(row.get('is_promo', 0))
                temperature = float(row.get('temperature_celsius', 20.0))
            except (ValueError, TypeError):
                # Descartar filas con datos corruptos
                continue

            # Registrar producto si no está en el mapa
            if product_id not in products_map:
                products_map[product_id] = {
                    'product_id': product_id,
                    'product_name': product_name,
                    'category': category,
                    'base_price': unit_price
                }

            clean_facts.append({
                'transaction_id': tx_id,
                'sale_date': sale_date,
                'store_id': store_id,
                'product_id': product_id,
                'units_sold': units,
                'unit_price': unit_price,
                'total_revenue': total_amount,
                'is_promo': is_promo,
                'temperature_celsius': temperature
            })

        return clean_stores, list(products_map.values()), clean_facts

    def load_data(
        self,
        stores: List[Dict[str, Any]],
        products: List[Dict[str, Any]],
        facts: List[Dict[str, Any]]
    ) -> None:
        """Carga atómica de dimensiones y hechos en SQLite."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Cargar Tiendas (upsert)
            cursor.executemany("""
                INSERT OR REPLACE INTO dim_stores (store_id, store_name, region, store_format)
                VALUES (:store_id, :store_name, :region, :store_format)
            """, stores)

            # Cargar Productos (upsert)
            cursor.executemany("""
                INSERT OR REPLACE INTO dim_products (product_id, product_name, category, base_price)
                VALUES (:product_id, :product_name, :category, :base_price)
            """, products)

            # Cargar Hechos de Ventas
            cursor.executemany("""
                INSERT OR REPLACE INTO fact_sales (
                    transaction_id, sale_date, store_id, product_id,
                    units_sold, unit_price, total_revenue, is_promo, temperature_celsius
                ) VALUES (
                    :transaction_id, :sale_date, :store_id, :product_id,
                    :units_sold, :unit_price, :total_revenue, :is_promo, :temperature_celsius
                )
            """, facts)

            # Generar Agregaciones para Consumo Analítico y Modelado
            cursor.execute("DELETE FROM agg_daily_product_demand;")
            cursor.execute("""
                INSERT INTO agg_daily_product_demand (
                    sale_date, product_id, total_units_sold, total_revenue,
                    avg_price, avg_temperature, promo_flag
                )
                SELECT 
                    sale_date,
                    product_id,
                    SUM(units_sold) AS total_units_sold,
                    SUM(total_revenue) AS total_revenue,
                    ROUND(AVG(unit_price), 2) AS avg_price,
                    ROUND(AVG(temperature_celsius), 2) AS avg_temperature,
                    MAX(is_promo) AS promo_flag
                FROM fact_sales
                GROUP BY sale_date, product_id;
            """)
            conn.commit()

    def run(self) -> Dict[str, Any]:
        """Ejecuta el pipeline ETL completo con medición de métricas."""
        start_time = time.time()
        self.init_database()

        raw_stores = self.extract_stores()
        raw_sales = self.extract_sales()

        clean_stores, clean_products, clean_facts = self.transform_data(raw_sales, raw_stores)
        self.load_data(clean_stores, clean_products, clean_facts)

        elapsed = round(time.time() - start_time, 3)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM fact_sales")
            total_facts = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM agg_daily_product_demand")
            total_aggs = cursor.fetchone()[0]

        return {
            "status": "SUCCESS",
            "stores_loaded": len(clean_stores),
            "products_loaded": len(clean_products),
            "transactions_loaded": total_facts,
            "daily_aggregates_created": total_aggs,
            "elapsed_seconds": elapsed
        }

if __name__ == "__main__":
    pipeline = RetailETLPipeline()
    metrics = pipeline.run()
    print("ETL Execution Metrics:", json.dumps(metrics, indent=2))
