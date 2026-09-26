"""Excepciones propias de la aplicación.

El backend traduce las excepciones de Stem a estas clases para que la interfaz
no dependa de Stem.
"""


class TorManagerError(Exception):
    def __init__(self, message, detail=None):
        super().__init__(message)
        self.message = message
        self.detail = detail


class TorNotConnectedError(TorManagerError):
    pass


class TorLaunchError(TorManagerError):
    pass


class LaunchCancelledError(TorManagerError):
    pass


class TorConnectionError(TorManagerError):
    pass


class AuthenticationError(TorManagerError):
    pass


class PasswordRequiredError(AuthenticationError):
    pass


class IncorrectPasswordError(AuthenticationError):
    pass


class CookieAuthError(AuthenticationError):
    def __init__(self, message, detail=None, cookie_path=None):
        super().__init__(message, detail)
        self.cookie_path = cookie_path


class AuthMethodUnavailableError(AuthenticationError):
    pass


class TorRequestError(TorManagerError):
    pass


class TorTimeoutError(TorRequestError):
    pass


class CircuitExtensionError(TorRequestError):
    pass


class UnsupportedFeatureError(TorRequestError):
    pass
