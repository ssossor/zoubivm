"""Client utilities."""


class RootMeRateLimitError(Exception):
    """Exception levée quand le site web ou l'API nous bloque"""
    pass


class RootMeApiError(Exception):
    def __init__(self, message, data):
        super().__init__(message)
        self.data = data
