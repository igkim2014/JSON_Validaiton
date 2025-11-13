"""Domain models - Core business entities"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
from .enums import ValidationStatus, ValidationType


@dataclass
class ValidationRule:
    """Validation rule definition"""
    rule_id: str
    description: str
    validation_type: ValidationType
    weight: float = 1.0
    required_fields: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None

    def __post_init__(self):
        if not 0 <= self.weight <= 1:
            raise ValueError(f"Rule weight must be between 0 and 1, got {self.weight}")


@dataclass
class ComplianceResult:
    """Result of a single compliance check"""
    rule_id: str
    status: ValidationStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def passed(self) -> bool:
        """Check if this compliance check passed"""
        return self.status == ValidationStatus.PASS


@dataclass
class ValidationResult:
    """Complete validation result for a test item"""
    te_number: str
    status: ValidationStatus
    score: float
    compliance_results: List[ComplianceResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def passed(self) -> bool:
        """Check if validation passed"""
        return self.status == ValidationStatus.PASS

    @property
    def total_checks(self) -> int:
        """Total number of checks performed"""
        return len(self.compliance_results)

    @property
    def passed_checks(self) -> int:
        """Number of checks that passed"""
        return sum(1 for r in self.compliance_results if r.passed)

    @property
    def failed_checks(self) -> int:
        """Number of checks that failed"""
        return self.total_checks - self.passed_checks

    def add_error(self, error: str) -> None:
        """Add an error message"""
        self.errors.append(error)
        if self.status == ValidationStatus.PASS:
            self.status = ValidationStatus.FAIL

    def add_warning(self, warning: str) -> None:
        """Add a warning message"""
        self.warnings.append(warning)


@dataclass
class TestItemData:
    """Data extracted from a test item"""
    te_number: str
    title: Optional[str] = None
    description: Optional[str] = None
    test_result: Optional[str] = None
    table_data: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def has_table_data(self) -> bool:
        """Check if test item has table data"""
        return len(self.table_data) > 0

    def get_metadata_value(self, key: str, default: Any = None) -> Any:
        """Get metadata value with default"""
        return self.metadata.get(key, default)


@dataclass
class DocumentMetadata:
    """Metadata about the document being validated"""
    filename: str
    file_path: str
    file_size: int
    creation_date: Optional[datetime] = None
    modification_date: Optional[datetime] = None
    document_type: str = "JSON"
    version: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_file(cls, file_path: str):
        """Create metadata from a file"""
        import os
        from pathlib import Path

        path = Path(file_path)
        stat = path.stat()

        return cls(
            filename=path.name,
            file_path=str(path.absolute()),
            file_size=stat.st_size,
            creation_date=datetime.fromtimestamp(stat.st_ctime),
            modification_date=datetime.fromtimestamp(stat.st_mtime),
        )


@dataclass
class TableData:
    """Structured table data"""
    headers: List[str]
    rows: List[List[str]]
    caption: Optional[str] = None
    page_number: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "headers": self.headers,
            "rows": self.rows,
            "caption": self.caption,
            "page_number": self.page_number,
        }

    @property
    def row_count(self) -> int:
        """Number of data rows"""
        return len(self.rows)

    @property
    def column_count(self) -> int:
        """Number of columns"""
        return len(self.headers)


@dataclass
class PDFPage:
    """Represents a page in a PDF document"""
    page_number: int
    text_blocks: List[Dict[str, Any]] = field(default_factory=list)
    tables: List[TableData] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    width: float = 0.0
    height: float = 0.0

    def has_tables(self) -> bool:
        """Check if page has tables"""
        return len(self.tables) > 0

    def has_images(self) -> bool:
        """Check if page has images"""
        return len(self.images) > 0
