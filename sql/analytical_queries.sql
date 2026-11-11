-- ==============================================================================
-- Consultas Analíticas de Negocio (Retail Business Intelligence)
-- ==============================================================================

-- 1. Top Productos por Ingresos Totales y Unidades Vendidas
SELECT 
    p.product_name,
    p.category,
    SUM(f.units_sold) AS total_units,
    SUM(f.total_revenue) AS total_sales_clp,
    ROUND(AVG(f.unit_price), 0) AS avg_realized_price
FROM fact_sales f
JOIN dim_products p ON f.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category
ORDER BY total_sales_clp DESC;

-- 2. Rendimiento por Región y Formato de Tienda
SELECT 
    s.region,
    s.store_format,
    COUNT(DISTINCT s.store_id) AS active_stores,
    SUM(f.total_revenue) AS regional_revenue_clp,
    ROUND(SUM(f.total_revenue) * 1.0 / SUM(f.units_sold), 0) AS avg_ticket_unit
FROM fact_sales f
JOIN dim_stores s ON f.store_id = s.store_id
GROUP BY s.region, s.store_format
ORDER BY regional_revenue_clp DESC;

-- 3. Análisis de Uplift por Promoción (Efectividad Promocional)
SELECT 
    p.category,
    f.is_promo,
    COUNT(*) AS total_transactions,
    ROUND(AVG(f.units_sold), 1) AS avg_units_per_tx,
    ROUND(AVG(f.unit_price), 0) AS avg_price_clp,
    SUM(f.total_revenue) AS total_revenue_clp
FROM fact_sales f
JOIN dim_products p ON f.product_id = p.product_id
GROUP BY p.category, f.is_promo
ORDER BY p.category, f.is_promo DESC;

-- 4. Sensibilidad al Clima: Demanda según Rango de Temperatura
SELECT 
    CASE 
        WHEN f.temperature_celsius < 18 THEN 'Fresco (< 18°C)'
        WHEN f.temperature_celsius BETWEEN 18 AND 24 THEN 'Templado (18-24°C)'
        ELSE 'Cálido (> 24°C)'
    END AS temp_range,
    p.category,
    ROUND(AVG(f.units_sold), 1) AS avg_units_sold,
    SUM(f.units_sold) AS total_units_volume
FROM fact_sales f
JOIN dim_products p ON f.product_id = p.product_id
GROUP BY temp_range, p.category
ORDER BY p.category, avg_units_sold DESC;

-- 5. Media Móvil de 7 Días de Demanda para Detección de Tendencias (Window Function)
SELECT 
    sale_date,
    product_id,
    total_units_sold,
    ROUND(AVG(total_units_sold) OVER (
        PARTITION BY product_id 
        ORDER BY sale_date 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 1) AS moving_avg_7d
FROM agg_daily_product_demand
ORDER BY product_id, sale_date DESC
LIMIT 50;
