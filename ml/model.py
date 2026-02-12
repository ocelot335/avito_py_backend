import os
import numpy as np
from sklearn.linear_model import LogisticRegression
import pickle
import mlflow
from config.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


def train_model() -> LogisticRegression:
    np.random.seed(42)
    # Признаки: [is_verified_seller, images_qty, description_length, category]
    X = np.random.rand(1000, 4)
    # Целевая переменная: 1 = нарушение, 0 = нет нарушения
    y = (X[:, 0] < 0.3) & (X[:, 1] < 0.2)
    y = y.astype(int)

    model = LogisticRegression()
    model.fit(X, y)
    return model


def save_model(model, path="model.pkl"):
    with open(path, "wb") as f:
        pickle.dump(model, f)


def load_model(path="model.pkl") -> LogisticRegression:
    with open(path, "rb") as f:
        model = pickle.load(f)
        logger.info("была загружена модель из файла")
        return model


def load_or_train_model() -> LogisticRegression:
    if settings.use_mlflow:
        return load_or_train_model_mlflow()
    else:
        return load_or_train_model_file()


def load_or_train_model_mlflow() -> LogisticRegression:
    model_uri = f"models:/{settings.mlflow_model_name}/{settings.mlflow_stage}"
    try:
        model = mlflow.sklearn.load_model(model_uri)
        logger.info("была загружена модель из mlflow")
        return model
    except Exception as e:
        logger.error(
            f"ошибка загрузки из MLflow:{e}, загрузка из файлового хранилища"
        )
        logger.warning("Пытаемся загрузить локальную резервную копию...")
        return load_or_train_model_file()


def load_or_train_model_file() -> LogisticRegression:
    model_path = settings.model_path
    if os.path.exists(model_path):
        return load_model(model_path)
    else:
        directory = os.path.dirname(model_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)

        model = train_model()
        save_model(model, model_path)
        return model
