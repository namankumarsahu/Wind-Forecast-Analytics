"""Domain exceptions raised by services and translated to HTTP errors in main.py."""


class ElexonError(Exception):
    """Base class for failures talking to the Elexon BMRS API."""


class ElexonTimeoutError(ElexonError):
    """Elexon did not answer within the timeout after all retries."""


class ElexonUpstreamError(ElexonError):
    """Elexon answered with an error status / malformed body after all retries."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class DataUnavailableError(Exception):
    """Required data is not cached and the service is in offline mode."""
