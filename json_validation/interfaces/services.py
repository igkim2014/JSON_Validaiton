"""Service interfaces - Application service contracts"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from ..domain.models import ValidationResult, TestItemData, DocumentMetadata
from ..domain.enums import OutputFormat


class IValidationService(ABC):
    """Interface for validation orchestration"""

    @abstractmethod
    def validate_test_item(self, te_number: str, json_data: Dict[str, Any]) -> ValidationResult:
        """Validate a specific test item"""
        pass

    @abstractmethod
    def validate_multiple(self, te_numbers: List[str], json_data: Dict[str, Any]) -> List[ValidationResult]:
        """Validate multiple test items"""
        pass

    @abstractmethod
    def validate_from_file(self, te_number: str, json_file_path: str) -> ValidationResult:
        """Validate test item from JSON file"""
        pass

    @abstractmethod
    def format_result(self, result: ValidationResult, output_format: OutputFormat) -> str:
        """Format validation result to specified output format"""
        pass


class IConversionService(ABC):
    """Interface for PDF/JSON conversion"""

    @abstractmethod
    def pdf_to_json(self, pdf_path: str, output_path: Optional[str] = None) -> Dict[str, Any]:
        """Convert PDF to JSON"""
        pass

    @abstractmethod
    def json_to_pdf(self, json_path: str, output_path: str) -> None:
        """Convert JSON to PDF"""
        pass

    @abstractmethod
    def extract_tables_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """Extract tables from PDF"""
        pass

    @abstractmethod
    def extract_images_from_pdf(self, pdf_path: str, output_dir: str) -> List[str]:
        """Extract images from PDF and save to directory"""
        pass


class IDocumentService(ABC):
    """Interface for document operations"""

    @abstractmethod
    def load_document(self, file_path: str) -> Dict[str, Any]:
        """Load document (JSON or PDF)"""
        pass

    @abstractmethod
    def get_document_metadata(self, file_path: str) -> DocumentMetadata:
        """Get document metadata"""
        pass

    @abstractmethod
    def search_in_document(self, json_data: Dict[str, Any], search_values: List[str]) -> Dict[str, Any]:
        """Search for values in document"""
        pass

    @abstractmethod
    def extract_test_item(self, te_number: str, json_data: Dict[str, Any]) -> Optional[TestItemData]:
        """Extract test item data from document"""
        pass

    @abstractmethod
    def find_test_result_table(self, te_number: str, json_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Find test result table for TE number"""
        pass
