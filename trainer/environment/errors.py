from __future__ import annotations


class BackendError(RuntimeError):
    """Base class for backend integration failures."""


class BackendConnectionError(BackendError):
    """Raised when a backend cannot be reached or authenticated."""


class BackendProtocolError(BackendError):
    """Raised when a backend returns an unexpected payload or protocol frame."""
