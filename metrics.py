import time
import functools

from prometheus_client import Counter, Histogram

PREDICTIONS_TOTAL = Counter(
    "predictions_total",
    "Общее количество предсказаний модели, с лейблом result (violation / no_violation)",
    ["result"],
)

PREDICTION_DURATION = Histogram(
    "prediction_duration_seconds",
    "Время выполнения предсказания ML-моделью (только инференс)",
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

PREDICTION_ERRORS_TOTAL = Counter(
    "prediction_errors_total",
    "Количество ошибок при предсказании, с лейблом error_type (model_unavailable / prediction_error)",
    ["error_type"],
)

MODEL_PREDICTION_PROBABILITY = Histogram(
    "model_prediction_probability",
    "Распределение вероятностей нарушений от ML-модели",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
)

DB_QUERY_DURATION = Histogram(
    "db_query_duration_seconds",
    "Время выполнения запросов к PostgreSQL, с лейблом query_type (select / insert / update / delete)",
    ["query_type"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
)


def measure_db_query(query_type: str):
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                DB_QUERY_DURATION.labels(query_type=query_type).observe(
                    duration
                )

        return wrapper

    return decorator
