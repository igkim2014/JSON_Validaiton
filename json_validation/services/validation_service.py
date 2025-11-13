"""Validation service - Validation orchestration"""

from typing import List, Dict, Any
from ..interfaces.services import IValidationService, IDocumentService
from ..interfaces.repositories import IConfigRepository
from ..domain.models import ValidationResult, ValidationRule, TestItemData, ComplianceResult
from ..domain.enums import ValidationStatus, OutputFormat, ValidationType
from ..domain.exceptions import ValidationError, RuleNotFoundError
from datetime import datetime


class ValidationService(IValidationService):
    """
    Service for validation orchestration
    Coordinates validation workflow across multiple validators
    """

    def __init__(
        self,
        document_service: IDocumentService,
        config_repository: IConfigRepository
    ):
        """
        Initialize validation service

        Args:
            document_service: Service for document operations
            config_repository: Repository for configuration
        """
        self._doc_service = document_service
        self._config_repo = config_repository
        self._rules_cache: Dict[str, ValidationRule] = {}

    def validate_test_item(
        self,
        te_number: str,
        json_data: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate a specific test item

        Args:
            te_number: Test item number (e.g., "TE02.03.01")
            json_data: JSON document data

        Returns:
            Validation result
        """
        # Extract test item data
        test_item = self._doc_service.extract_test_item(te_number, json_data)

        if not test_item:
            return ValidationResult(
                te_number=te_number,
                status=ValidationStatus.FAIL,
                score=0.0,
                errors=[f"Test item {te_number} not found in document"]
            )

        # Load validation rules
        rules = self._load_rules_for_te(te_number)

        if not rules:
            return ValidationResult(
                te_number=te_number,
                status=ValidationStatus.WARNING,
                score=0.0,
                warnings=[f"No validation rules found for {te_number}"]
            )

        # Perform validation checks
        compliance_results = self._perform_validation_checks(test_item, rules)

        # Calculate score
        score = self._calculate_score(compliance_results, rules)

        # Determine overall status
        status = ValidationStatus.PASS if score >= 0.8 else ValidationStatus.FAIL

        # Build result
        result = ValidationResult(
            te_number=te_number,
            status=status,
            score=score,
            compliance_results=compliance_results,
            metadata={
                "test_item": test_item.to_dict() if hasattr(test_item, 'to_dict') else {},
                "rules_count": len(rules),
                "checks_performed": len(compliance_results)
            }
        )

        return result

    def validate_multiple(
        self,
        te_numbers: List[str],
        json_data: Dict[str, Any]
    ) -> List[ValidationResult]:
        """
        Validate multiple test items

        Args:
            te_numbers: List of test item numbers
            json_data: JSON document data

        Returns:
            List of validation results
        """
        results = []
        for te_number in te_numbers:
            result = self.validate_test_item(te_number, json_data)
            results.append(result)
        return results

    def validate_from_file(
        self,
        te_number: str,
        json_file_path: str
    ) -> ValidationResult:
        """
        Validate test item from JSON file

        Args:
            te_number: Test item number
            json_file_path: Path to JSON file

        Returns:
            Validation result
        """
        json_data = self._doc_service.load_document(json_file_path)
        return self.validate_test_item(te_number, json_data)

    def format_result(
        self,
        result: ValidationResult,
        output_format: OutputFormat
    ) -> str:
        """
        Format validation result to specified output format

        Args:
            result: Validation result
            output_format: Output format

        Returns:
            Formatted string
        """
        if output_format == OutputFormat.JSON:
            return self._format_as_json(result)
        elif output_format == OutputFormat.HTML:
            return self._format_as_html(result)
        elif output_format == OutputFormat.MARKDOWN:
            return self._format_as_markdown(result)
        else:
            return self._format_as_text(result)

    def _load_rules_for_te(self, te_number: str) -> List[ValidationRule]:
        """Load validation rules for specific TE number"""
        # Check cache first
        if te_number in self._rules_cache:
            return [self._rules_cache[te_number]]

        try:
            # Load all rules from configuration
            rules_data = self._config_repo.load_validation_rules()

            # Filter rules for this TE number
            matching_rules = []
            for rule_data in rules_data:
                if rule_data.get("te_number") == te_number or rule_data.get("applies_to_all"):
                    rule = ValidationRule(
                        rule_id=rule_data.get("id", ""),
                        description=rule_data.get("description", ""),
                        validation_type=self._parse_validation_type(rule_data.get("type", "")),
                        weight=rule_data.get("weight", 1.0),
                        required_fields=rule_data.get("required_fields", []),
                        conditions=rule_data.get("conditions", {}),
                        error_message=rule_data.get("error_message")
                    )
                    matching_rules.append(rule)

            return matching_rules

        except Exception as e:
            # Return default rule if configuration fails
            return [
                ValidationRule(
                    rule_id="default",
                    description="Default validation rule",
                    validation_type=ValidationType.COMPLIANCE,
                    weight=1.0
                )
            ]

    def _perform_validation_checks(
        self,
        test_item: TestItemData,
        rules: List[ValidationRule]
    ) -> List[ComplianceResult]:
        """Perform all validation checks"""
        results = []

        for rule in rules:
            # Check metadata completeness
            if rule.validation_type == ValidationType.METADATA:
                result = self._check_metadata(test_item, rule)
                results.append(result)

            # Check table structure
            elif rule.validation_type == ValidationType.TABLE_STRUCTURE:
                result = self._check_table_structure(test_item, rule)
                results.append(result)

            # Check content accuracy
            elif rule.validation_type == ValidationType.CONTENT_ACCURACY:
                result = self._check_content(test_item, rule)
                results.append(result)

            # Check element presence
            elif rule.validation_type == ValidationType.ELEMENT_PRESENCE:
                result = self._check_elements(test_item, rule)
                results.append(result)

        return results

    def _check_metadata(
        self,
        test_item: TestItemData,
        rule: ValidationRule
    ) -> ComplianceResult:
        """Check metadata completeness"""
        missing_fields = []

        for field in rule.required_fields:
            if not test_item.get_metadata_value(field):
                missing_fields.append(field)

        passed = len(missing_fields) == 0
        message = "Metadata complete" if passed else f"Missing fields: {', '.join(missing_fields)}"

        return ComplianceResult(
            rule_id=rule.rule_id,
            status=ValidationStatus.PASS if passed else ValidationStatus.FAIL,
            message=message,
            details={"missing_fields": missing_fields} if missing_fields else {}
        )

    def _check_table_structure(
        self,
        test_item: TestItemData,
        rule: ValidationRule
    ) -> ComplianceResult:
        """Check table structure"""
        has_table = test_item.has_table_data()
        passed = has_table

        message = "Table structure valid" if passed else "No table data found"

        return ComplianceResult(
            rule_id=rule.rule_id,
            status=ValidationStatus.PASS if passed else ValidationStatus.FAIL,
            message=message
        )

    def _check_content(
        self,
        test_item: TestItemData,
        rule: ValidationRule
    ) -> ComplianceResult:
        """Check content accuracy"""
        # Basic content check
        has_content = bool(test_item.description or test_item.table_data)
        passed = has_content

        message = "Content present" if passed else "No content found"

        return ComplianceResult(
            rule_id=rule.rule_id,
            status=ValidationStatus.PASS if passed else ValidationStatus.FAIL,
            message=message
        )

    def _check_elements(
        self,
        test_item: TestItemData,
        rule: ValidationRule
    ) -> ComplianceResult:
        """Check required elements"""
        # Check if TE number is present
        passed = bool(test_item.te_number)
        message = "Required elements present" if passed else "Missing TE number"

        return ComplianceResult(
            rule_id=rule.rule_id,
            status=ValidationStatus.PASS if passed else ValidationStatus.FAIL,
            message=message
        )

    def _calculate_score(
        self,
        compliance_results: List[ComplianceResult],
        rules: List[ValidationRule]
    ) -> float:
        """Calculate weighted score"""
        if not compliance_results:
            return 0.0

        total_weight = sum(rule.weight for rule in rules)
        if total_weight == 0:
            total_weight = len(rules)

        weighted_score = 0.0
        for result, rule in zip(compliance_results, rules):
            if result.passed:
                weighted_score += rule.weight

        return weighted_score / total_weight if total_weight > 0 else 0.0

    def _parse_validation_type(self, type_str: str) -> ValidationType:
        """Parse validation type from string"""
        type_map = {
            "metadata": ValidationType.METADATA,
            "table": ValidationType.TABLE_STRUCTURE,
            "content": ValidationType.CONTENT_ACCURACY,
            "element": ValidationType.ELEMENT_PRESENCE,
            "compliance": ValidationType.COMPLIANCE,
        }
        return type_map.get(type_str.lower(), ValidationType.COMPLIANCE)

    def _format_as_text(self, result: ValidationResult) -> str:
        """Format result as text"""
        lines = [
            f"Validation Result for {result.te_number}",
            f"Status: {result.status}",
            f"Score: {result.score:.2%}",
            f"Total Checks: {result.total_checks}",
            f"Passed: {result.passed_checks}",
            f"Failed: {result.failed_checks}",
        ]

        if result.errors:
            lines.append("\nErrors:")
            for error in result.errors:
                lines.append(f"  - {error}")

        if result.warnings:
            lines.append("\nWarnings:")
            for warning in result.warnings:
                lines.append(f"  - {warning}")

        return "\n".join(lines)

    def _format_as_json(self, result: ValidationResult) -> str:
        """Format result as JSON"""
        import json
        data = {
            "te_number": result.te_number,
            "status": str(result.status),
            "score": result.score,
            "total_checks": result.total_checks,
            "passed_checks": result.passed_checks,
            "failed_checks": result.failed_checks,
            "errors": result.errors,
            "warnings": result.warnings,
            "timestamp": result.timestamp.isoformat()
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def _format_as_html(self, result: ValidationResult) -> str:
        """Format result as HTML"""
        status_class = "pass" if result.passed else "fail"
        html = f"""
        <div class="validation-result {status_class}">
            <h2>Validation Result: {result.te_number}</h2>
            <p><strong>Status:</strong> {result.status}</p>
            <p><strong>Score:</strong> {result.score:.2%}</p>
            <p><strong>Checks:</strong> {result.passed_checks}/{result.total_checks} passed</p>
        </div>
        """
        return html

    def _format_as_markdown(self, result: ValidationResult) -> str:
        """Format result as Markdown"""
        status_emoji = "✅" if result.passed else "❌"
        lines = [
            f"# Validation Result: {result.te_number}",
            f"",
            f"{status_emoji} **Status:** {result.status}",
            f"**Score:** {result.score:.2%}",
            f"**Checks:** {result.passed_checks}/{result.total_checks} passed",
        ]
        return "\n".join(lines)
