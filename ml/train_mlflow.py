import mlflow
from mlflow.sklearn import log_model
from config.config import get_settings
from ml.model import train_model

settings = get_settings()


def train_and_mlflow_log():

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(settings.mlflow_model_name)

    with mlflow.start_run():
        model = train_model()
        log_model(
            model, "model", registered_model_name=settings.mlflow_model_name
        )


if __name__ == "__main__":
    train_and_mlflow_log()
