"""Validator interfaces - Validation contracts"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
from ..domain.models import ValidationResult, ComplianceResult, TestItemData, ValidationRule


class IValidator(ABC):
    """Base validator interface"""

    @abstractmethod
    def validate(self, data: Any) -> ComplianceResult:
        """Validate data and return compliance result"""
        pass

    @abstractmethod
    def get_validation_type(self) -> str:
        """Get the type of validation this validator performs"""
        pass


class IMetadataValidator(IValidator):
    """Interface for metadata validation"""

    @abstractmethod
    def validate_metadata_completeness(self, test_item: TestItemData) -> ComplianceResult:
        """Validate that all required metadata fields are present"""
        pass

    @abstractmethod
    def validate_metadata_format(self, test_item: TestItemData) -> ComplianceResult:
        """Validate metadata field formats"""
        pass


class ITableValidator(IValidator):
    """Interface for table structure validation"""

    @abstractmethod
    def validate_table_structure(self, table_data: List[Dict[str, Any]]) -> ComplianceResult:
        """Validate table structure"""
        pass

    @abstractmethod
    def validate_table_headers(self, table_data: List[Dict[str, Any]], expected_headers: List[str]) -> ComplianceResult:
        """Validate table headers"""
        pass


class IContentValidator(IValidator):
    """Interface for content validation"""

    @abstractmethod
    def validate_content_accuracy(self, test_item: TestItemData, rules: List[ValidationRule]) -> ComplianceResult:
        """Validate content accuracy against rules"""
        pass

    @abstractmethod
    def validate_required_fields(self, test_item: TestItemData, required_fields: List[str]) -> ComplianceResult:
        """Validate presence of required fields"""
        pass


class IElementValidator(IValidator):
    """Interface for element presence validation"""

    @abstractmethod
    def validate_required_elements(self, data: Dict[str, Any], required_elements: List[str]) -> ComplianceResult:
        """Validate presence of required elements"""
        pass


class IComplianceChecker(ABC):
    """Interface for compliance checking orchestration"""

    @abstractmethod
    def check_compliance(self, test_item: TestItemData, rules: List[ValidationRule]) -> List[ComplianceResult]:
        """Perform all compliance checks"""
        pass

    @abstractmethod
    def register_validator(self, validator: IValidator) -> None:
        """Register a validator"""
        pass

    @abstractmethod
    def calculate_score(self, compliance_results: List[ComplianceResult], rules: List[ValidationRule]) -> float:
        """Calculate overall compliance score"""
        pass
