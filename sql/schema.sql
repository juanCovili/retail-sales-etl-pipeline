-- ==============================================================================
-- Retail & FMCG Data Warehouse Schema
-- Target: SQLite / PostgreSQL compatible
-- ==============================================================================

-- 1. Dimensión Tiendas
CREATE TABLE IF NOT EXISTS dim_stores (
    store_id TEXT PRIMARY KEY,
    store_name TEXT NOT NULL,
    region TEXT NOT NULL,
    store_format TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Dimensión Productos
CREATE TABLE IF NOT EXISTS dim_products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    base_price NUMERIC NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Tabla de Hechos: Transacciones de Venta Diarias
CREATE TABLE IF NOT EXISTS fact_sales (
    transaction_id TEXT PRIMARY KEY,
    sale_date DATE NOT NULL,
    store_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    units_sold INTEGER NOT NULL CHECK (units_sold >= 0),
    unit_price NUMERIC NOT NULL CHECK (unit_price > 0),
    total_revenue NUMERIC NOT NULL,
    is_promo INTEGER DEFAULT 0 CHECK (is_promo IN (0, 1)),
    temperature_celsius REAL,
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (store_id) REFERENCES dim_stores (store_id),
    FOREIGN KEY (product_id) REFERENCES dim_products (product_id)
);

-- Índices analíticos para optimización de queries
CREATE INDEX IF NOT EXISTS idx_sales_date ON fact_sales (sale_date);
CREATE INDEX IF NOT EXISTS idx_sales_product ON fact_sales (product_id);
CREATE INDEX IF NOT EXISTS idx_sales_store ON fact_sales (store_id);

-- 4. Tabla Agregada: Demanda Diaria por Producto para Modelado ML
CREATE TABLE IF NOT EXISTS agg_daily_product_demand (
    sale_date DATE NOT NULL,
    product_id TEXT NOT NULL,
    total_units_sold INTEGER NOT NULL,
    total_revenue NUMERIC NOT NULL,
    avg_price REAL NOT NULL,
    avg_temperature REAL NOT NULL,
    promo_flag INTEGER NOT NULL,
    PRIMARY KEY (sale_date, product_id),
    FOREIGN KEY (product_id) REFERENCES dim_products (product_id)
);
