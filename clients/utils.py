"""Client utilities."""


class RootMeRateLimitError(Exception):
    """Exception levée quand le site web ou l'API nous bloque"""
    pass


class RootMeApiError(Exception):
    def __init__(self, message, data):
        super().__init__(message)
        self.data = data


def describe_error(err: BaseException) -> str:
    """
    Describe an error with its causes, as httpx often hides them (ConnectError('')).

    Args:
        err: The error to describe

    Returns:
        The error and its causes, e.g. "ConnectError('') <- SSLError(...)"
    """
    causes = []
    while err is not None and len(causes) < 5:
        causes.append(repr(err))
        err = err.__cause__ or err.__context__
    return " <- ".join(causes)
