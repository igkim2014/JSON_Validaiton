"""Domain exceptions"""


class DomainException(Exception):
    """Base exception for domain errors"""
    pass


class ValidationError(DomainException):
    """Raised when validation fails"""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.details = details or {}


class ConfigurationError(DomainException):
    """Raised when configuration is invalid or missing"""
    pass


class DataExtractionError(DomainException):
    """Raised when data extraction fails"""

    def __init__(self, message: str, source: str = None):
        super().__init__(message)
        self.source = source


class RuleNotFoundError(ValidationError):
    """Raised when a validation rule cannot be found"""
    pass


class InvalidInputError(DomainException):
    """Raised when input data is invalid"""
    pass


class ConversionError(DomainException):
    """Raised when PDF/JSON conversion fails"""

    def __init__(self, message: str, source_format: str = None, target_format: str = None):
        super().__init__(message)
        self.source_format = source_format
        self.target_format = target_format
