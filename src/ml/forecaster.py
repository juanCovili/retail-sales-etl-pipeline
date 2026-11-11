import sqlite3
import math
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta
from src.config import DATABASE_PATH

class DemandForecaster:
    """
    Módulo de Machine Learning para Proyección de Demanda Diaria
    basado en Regresión Ridge Multivariable (Ecuación Normal con Regularización L2).
    """

    def __init__(self, db_path=DATABASE_PATH):
        self.db_path = db_path

    def get_training_data(self, product_id: str) -> List[Dict[str, Any]]:
        """Extrae series temporales con métricas agregadas desde la base de datos."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    sale_date,
                    product_id,
                    total_units_sold,
                    avg_price,
                    avg_temperature,
                    promo_flag
                FROM agg_daily_product_demand
                WHERE product_id = ?
                ORDER BY sale_date ASC;
            """, (product_id,))
            rows = [dict(r) for r in cursor.fetchall()]
        return rows

    def build_features(self, rows: List[Dict[str, Any]]) -> Tuple[List[List[float]], List[float]]:
        """
        Ingeniería de Características (Feature Engineering):
        - Bias / Intercepto
        - Día de la semana (0 a 6)
        - Indicador de fin de semana (0 o 1)
        - Temperatura ambiente (°C)
        - Flag de promoción (0 o 1)
        - Lag 1 día de demanda
        - Lag 7 días de demanda (estacionalidad semanal)
        """
        X = []
        y = []

        for i in range(7, len(rows)):
            curr = rows[i]
            prev_1 = rows[i - 1]
            prev_7 = rows[i - 7]

            dt = datetime.strptime(curr['sale_date'], '%Y-%m-%d')
            is_weekend = 1.0 if dt.weekday() >= 5 else 0.0
            day_of_week = float(dt.weekday())
            temp = float(curr['avg_temperature'])
            promo = float(curr['promo_flag'])
            lag_1 = float(prev_1['total_units_sold'])
            lag_7 = float(prev_7['total_units_sold'])

            features = [1.0, day_of_week, is_weekend, temp, promo, lag_1, lag_7]
            target = float(curr['total_units_sold'])

            X.append(features)
            y.append(target)

        return X, y

    def _solve_ridge(self, X: List[List[float]], y: List[float], lambda_reg: float = 1.0) -> List[float]:
        """
        Calcula la solución analítica cerrada para Regresión Ridge:
        w = (X^T * X + lambda * I)^(-1) * X^T * y
        Garantiza convergencia exacta e instantánea sin hiperparámetros de épocas.
        """
        n_samples = len(X)
        n_features = len(X[0])

        # Calcular X^T * X + lambda * I
        XtX = [[0.0] * n_features for _ in range(n_features)]
        for i in range(n_features):
            for j in range(n_features):
                val = sum(X[k][i] * X[k][j] for k in range(n_samples))
                if i == j and i > 0:  # No regularizar el término de sesgo/intercepto
                    val += lambda_reg
                XtX[i][j] = val

        # Calcular X^T * y
        Xty = [sum(X[k][i] * y[k] for k in range(n_samples)) for i in range(n_features)]

        # Resolver el sistema lineal (XtX) * w = Xty usando Eliminación Gaussiana con pivoteo parcial
        M = [XtX[i][:] + [Xty[i]] for i in range(n_features)]
        for i in range(n_features):
            max_row = max(range(i, n_features), key=lambda r: abs(M[r][i]))
            M[i], M[max_row] = M[max_row], M[i]
            pivot = M[i][i]
            if abs(pivot) < 1e-12:
                pivot = 1e-12
            for j in range(i, n_features + 1):
                M[i][j] /= pivot
            for r in range(n_features):
                if r != i:
                    factor = M[r][i]
                    for c in range(i, n_features + 1):
                        M[r][c] -= factor * M[i][c]

        return [M[i][n_features] for i in range(n_features)]

    def evaluate(self, y_true: List[float], y_pred: List[float]) -> Dict[str, float]:
        """Calcula métricas estándar de evaluación: MAE, RMSE y R²."""
        n = len(y_true)
        if n == 0:
            return {"mae": 0.0, "rmse": 0.0, "r2": 0.0}

        mae = sum(abs(t - p) for t, p in zip(y_true, y_pred)) / n
        mse = sum((t - p) ** 2 for t, p in zip(y_true, y_pred)) / n
        rmse = math.sqrt(mse)

        mean_y = sum(y_true) / n
        ss_tot = sum((t - mean_y) ** 2 for t in y_true)
        ss_res = sum((t - p) ** 2 for t, p in zip(y_true, y_pred))
        r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        return {
            "mae": round(mae, 2),
            "rmse": round(rmse, 2),
            "r2": round(max(0.0, min(1.0, r2)), 3)
        }

    def predict_next_7_days(self, product_id: str) -> Dict[str, Any]:
        """
        Entrena el modelo sobre datos históricos del producto
        y genera la proyección de los próximos 7 días comerciales.
        """
        rows = self.get_training_data(product_id)
        if len(rows) < 14:
            raise ValueError(f"Datos insuficientes para el producto {product_id}")

        X, y = self.build_features(rows)
        
        # Train / Test split 80% / 20%
        split_idx = int(len(X) * 0.8)
        X_train, y_train = X[:split_idx], y[:split_idx]
        X_test, y_test = X[split_idx:], y[split_idx:]

        weights = self._solve_ridge(X_train, y_train, lambda_reg=2.0)

        # Evaluar sobre conjunto de prueba
        y_test_pred = [sum(w * x for w, x in zip(weights, sample)) for sample in X_test]
        metrics = self.evaluate(y_test, y_test_pred)

        # Proyectar próximos 7 días
        last_date = datetime.strptime(rows[-1]['sale_date'], '%Y-%m-%d')
        last_units = [r['total_units_sold'] for r in rows[-7:]]
        
        forecast = []
        dias_espanol = {
            'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
            'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
        }

        for day_offset in range(1, 8):
            next_date = last_date + timedelta(days=day_offset)
            is_weekend = 1.0 if next_date.weekday() >= 5 else 0.0
            day_of_week = float(next_date.weekday())
            est_temp = 24.0 + (day_offset * 0.5)
            promo = 1.0 if next_date.weekday() == 5 else 0.0  # Sábado promocional
            lag_1 = float(last_units[-1])
            lag_7 = float(last_units[-7])

            x_future = [1.0, day_of_week, is_weekend, est_temp, promo, lag_1, lag_7]
            pred_units = max(1, int(round(sum(w * x for w, x in zip(weights, x_future)))))
            
            day_en = next_date.strftime('%A')
            forecast.append({
                "date": next_date.strftime('%Y-%m-%d'),
                "day_name": dias_espanol.get(day_en, day_en),
                "predicted_units": pred_units,
                "expected_temp_c": round(est_temp, 1),
                "is_promo": bool(promo)
            })
            last_units.append(pred_units)

        return {
            "product_id": product_id,
            "metrics": metrics,
            "forecast_7_days": forecast
        }

if __name__ == "__main__":
    forecaster = DemandForecaster()
    result = forecaster.predict_next_7_days("PRD-01")
    print("Forecaster Result PRD-01:")
    print(f"Metrics: MAE = {result['metrics']['mae']}, RMSE = {result['metrics']['rmse']}, R² = {result['metrics']['r2']}")
    print("Next 7 Days Forecast:")
    for f in result['forecast_7_days']:
        print(f" - {f['date']} ({f['day_name']}): {f['predicted_units']} unidades (Temp: {f['expected_temp_c']}°C, Promo: {f['is_promo']})")
