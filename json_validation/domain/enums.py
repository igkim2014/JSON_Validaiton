"""Domain enumerations"""

from enum import Enum, auto


class ValidationStatus(Enum):
    """Validation result status"""
    PASS = "PASS"
    FAIL = "FAIL"
    WARNING = "WARNING"
    SKIP = "SKIP"

    def __str__(self):
        return self.value


class ValidationType(Enum):
    """Types of validation checks"""
    METADATA = auto()
    TABLE_STRUCTURE = auto()
    CONTENT_ACCURACY = auto()
    ELEMENT_PRESENCE = auto()
    COMPLIANCE = auto()

    def __str__(self):
        return self.name.replace('_', ' ').title()


class OutputFormat(Enum):
    """Validation report output formats"""
    TEXT = "text"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"

    def __str__(self):
        return self.value
