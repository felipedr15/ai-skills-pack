"""Structured error types for the AI OS service layer."""
from __future__ import annotations


class ServiceError(Exception):
    """Base service error with structured response."""

    def __init__(self, code: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict:
        result = {"error": self.code, "message": self.message}
        if self.details:
            result["details"] = self.details
        return result


class InvalidRequest(ServiceError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__("invalid_request", message, details)


class NotFound(ServiceError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__("not_found", message, details)


class Forbidden(ServiceError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__("forbidden", message, details)


class PathRejected(ServiceError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__("path_rejected", message, details)


class LimitExceeded(ServiceError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__("limit_exceeded", message, details)


class MalformedArtifact(ServiceError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__("malformed_artifact", message, details)


class Unavailable(ServiceError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__("unavailable", message, details)


class InternalError(ServiceError):
    def __init__(self, message: str, details: dict | None = None):
        super().__init__("internal_error", message, details)
