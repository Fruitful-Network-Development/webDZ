"""Data environment errors."""
from __future__ import annotations


class DataEnvError(Exception):
    """Base data environment error."""


class DataEnvFileError(DataEnvError):
    def __init__(self, path: str, reason: str):
        super().__init__(f"Data env file error: {path}: {reason}")
        self.path = path
        self.reason = reason


class DataEnvValidationError(DataEnvError):
    def __init__(self, resource_id: str, reason: str):
        super().__init__(f"Invalid resource '{resource_id}': {reason}")
        self.resource_id = resource_id
        self.reason = reason


class DataEnvResourceNotFound(DataEnvError):
    def __init__(self, resource_id: str):
        super().__init__(f"Resource not found: {resource_id}")
        self.resource_id = resource_id


class DataEnvBootstrapError(DataEnvError):
    def __init__(self, path: str, reason: str):
        super().__init__(f"Bootstrap error: {path}: {reason}")
        self.path = path
        self.reason = reason

