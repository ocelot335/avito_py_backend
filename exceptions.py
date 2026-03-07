class AdvertisementNotFoundError(Exception):
    pass


class ModelIsNotAvailable(Exception):
    pass


class ErrorInPrediction(Exception):
    pass


class TaskNotFoundError(Exception):
    pass


class MessageBrokerError(Exception):
    pass


class MaxRetriesExceededError(Exception):
    pass
