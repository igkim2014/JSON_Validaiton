"""Document service - Document operations orchestration"""

from typing import Dict, Any, List, Optional
from ..interfaces.services import IDocumentService
from ..interfaces.repositories import IJsonRepository, IFileRepository
from ..domain.models import DocumentMetadata, TestItemData
from ..domain.exceptions import DataExtractionError


class DocumentService(IDocumentService):
    """
    Service for document operations
    Follows Single Responsibility Principle - handles document-related use cases
    """

    def __init__(
        self,
        json_repository: IJsonRepository,
        file_repository: IFileRepository
    ):
        """
        Initialize document service with dependencies

        Args:
            json_repository: Repository for JSON operations
            file_repository: Repository for file operations
        """
        self._json_repo = json_repository
        self._file_repo = file_repository

    def load_document(self, file_path: str) -> Dict[str, Any]:
        """
        Load document (JSON or PDF)

        Args:
            file_path: Path to document

        Returns:
            Document data

        Raises:
            DataExtractionError: If document cannot be loaded
        """
        if not self._file_repo.exists(file_path):
            raise DataExtractionError(f"Document not found: {file_path}")

        ext = self._file_repo.get_file_extension(file_path)

        if ext.lower() == '.json':
            return self._json_repo.load(file_path)
        elif ext.lower() == '.pdf':
            # PDF loading will be handled by conversion service
            raise DataExtractionError(
                "PDF files must be converted to JSON first. Use ConversionService."
            )
        else:
            raise DataExtractionError(f"Unsupported file type: {ext}")

    def get_document_metadata(self, file_path: str) -> DocumentMetadata:
        """
        Get document metadata

        Args:
            file_path: Path to document

        Returns:
            Document metadata
        """
        return DocumentMetadata.from_file(file_path)

    def search_in_document(
        self,
        json_data: Dict[str, Any],
        search_values: List[str]
    ) -> Dict[str, Any]:
        """
        Search for values in document

        Args:
            json_data: JSON document data
            search_values: List of values to search for

        Returns:
            Dictionary with search results
        """
        results = {
            "found": {},
            "not_found": []
        }

        for value in search_values:
            matches = self._json_repo.search_text_in_pages(json_data, value)

            if matches:
                results["found"][value] = matches
            else:
                results["not_found"].append(value)

        return results

    def extract_test_item(
        self,
        te_number: str,
        json_data: Dict[str, Any]
    ) -> Optional[TestItemData]:
        """
        Extract test item data from document

        Args:
            te_number: Test item number (e.g., "TE02.03.01")
            json_data: JSON document data

        Returns:
            Test item data or None if not found
        """
        # Search for TE number in document
        matches = self._json_repo.search_text_in_pages(json_data, te_number)

        if not matches:
            return None

        # Extract test item data
        test_item = TestItemData(te_number=te_number)

        # Try to find table data for this TE number
        table_data = self.find_test_result_table(te_number, json_data)
        if table_data:
            test_item.table_data = [table_data]

        # Extract context from matches
        if matches:
            test_item.metadata["matches"] = matches
            # Use first match for context
            first_match = matches[0]
            test_item.description = first_match.get("context", "")

        return test_item

    def find_test_result_table(
        self,
        te_number: str,
        json_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Find test result table for TE number

        Args:
            te_number: Test item number
            json_data: JSON document data

        Returns:
            Table data or None if not found
        """
        pages = json_data.get("pages", [])

        for page in pages:
            if not page:
                continue

            tables = page.get("tables", [])
            for table in tables:
                if not table:
                    continue

                # Check if table contains TE number
                caption = table.get("caption", "")
                cells = str(table.get("cells", []))

                if te_number in caption or te_number in cells:
                    return {
                        "te_number": te_number,
                        "page": page.get("page_number"),
                        "caption": caption,
                        "cells": table.get("cells", []),
                        "table_data": table
                    }

        return None

    def get_page_count(self, json_data: Dict[str, Any]) -> int:
        """
        Get number of pages in document

        Args:
            json_data: JSON document data

        Returns:
            Number of pages
        """
        pages = json_data.get("pages", [])
        return len(pages) if pages else 0

    def get_all_te_numbers(self, json_data: Dict[str, Any]) -> List[str]:
        """
        Extract all TE numbers from document

        Args:
            json_data: JSON document data

        Returns:
            List of TE numbers found
        """
        import re

        te_pattern = r'TE\d+\.\d+\.\d+'
        te_numbers = set()

        pages = json_data.get("pages", [])
        for page in pages:
            if not page:
                continue

            # Search in page text
            page_text = page.get("text", "")
            matches = re.findall(te_pattern, str(page_text))
            te_numbers.update(matches)

            # Search in text blocks
            for text_block in page.get("text_blocks", []):
                if text_block and "text" in text_block:
                    block_text = text_block.get("text", "")
                    matches = re.findall(te_pattern, str(block_text))
                    te_numbers.update(matches)

        return sorted(list(te_numbers))
