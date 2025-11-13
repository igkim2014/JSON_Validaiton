"""JSON repository implementation"""

import json
from typing import Any, Dict, List, Optional
from pathlib import Path
from ..interfaces.repositories import IJsonRepository
from ..domain.exceptions import DataExtractionError


class JsonRepository(IJsonRepository):
    """Repository for JSON data operations"""

    def __init__(self):
        """Initialize JSON repository"""
        self._cache: Dict[str, Dict[str, Any]] = {}

    def load(self, file_path: str) -> Dict[str, Any]:
        """
        Load JSON from file

        Args:
            file_path: Path to JSON file

        Returns:
            Parsed JSON data

        Raises:
            DataExtractionError: If file cannot be loaded or parsed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._cache[file_path] = data
                return data
        except FileNotFoundError:
            raise DataExtractionError(f"File not found: {file_path}", source=file_path)
        except json.JSONDecodeError as e:
            raise DataExtractionError(f"Invalid JSON file: {e}", source=file_path)
        except Exception as e:
            raise DataExtractionError(f"Error loading JSON: {e}", source=file_path)

    def save(self, file_path: str, data: Dict[str, Any]) -> None:
        """
        Save data to JSON file

        Args:
            file_path: Output file path
            data: Data to save
        """
        try:
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._cache[file_path] = data
        except Exception as e:
            raise DataExtractionError(f"Error saving JSON: {e}", source=file_path)

    def search_value(self, data: Dict[str, Any], search_path: str) -> Optional[Any]:
        """
        Search for value using path notation (e.g., 'pages[0].text')

        Args:
            data: JSON data to search
            search_path: Path to value (dot notation or bracket notation)

        Returns:
            Found value or None
        """
        if not data:
            return None

        try:
            parts = self._parse_path(search_path)
            current = data

            for part in parts:
                if isinstance(current, dict):
                    current = current.get(part)
                elif isinstance(current, list):
                    try:
                        index = int(part)
                        current = current[index] if 0 <= index < len(current) else None
                    except (ValueError, IndexError):
                        return None
                else:
                    return None

                if current is None:
                    return None

            return current
        except Exception:
            return None

    def find_by_key(self, data: Dict[str, Any], key: str) -> List[Any]:
        """
        Find all values with matching key recursively

        Args:
            data: JSON data to search
            key: Key to find

        Returns:
            List of found values
        """
        results = []
        self._find_by_key_recursive(data, key, results)
        return results

    def extract_field(self, data: Dict[str, Any], field_path: str, default: Any = None) -> Any:
        """
        Extract field using dot notation (e.g., 'metadata.title')

        Args:
            data: JSON data
            field_path: Field path using dot notation
            default: Default value if not found

        Returns:
            Field value or default
        """
        result = self.search_value(data, field_path)
        return result if result is not None else default

    def search_text_in_pages(self, data: Dict[str, Any], search_text: str) -> List[Dict[str, Any]]:
        """
        Search for text across all pages

        Args:
            data: JSON data with pages structure
            search_text: Text to search for

        Returns:
            List of matches with location information
        """
        matches = []
        pages = data.get("pages", [])

        for page in pages:
            if not page:
                continue

            page_num = page.get("page_number", "Unknown")

            # Search in page text
            page_text = page.get("text", "")
            if search_text in str(page_text):
                matches.append({
                    "page": page_num,
                    "location": "page_text",
                    "context": page_text[:200]
                })

            # Search in text blocks
            for text_block in page.get("text_blocks", []):
                if text_block and "text" in text_block:
                    block_text = text_block.get("text", "")
                    if search_text in str(block_text):
                        matches.append({
                            "page": page_num,
                            "location": "text_block",
                            "context": block_text[:200]
                        })

            # Search in tables
            for table in page.get("tables", []):
                if not table:
                    continue

                caption = table.get("caption", "")
                cells = str(table.get("cells", []))

                if search_text in caption or search_text in cells:
                    matches.append({
                        "page": page_num,
                        "location": "table",
                        "caption": caption,
                        "context": cells[:200]
                    })

        return matches

    def _parse_path(self, path: str) -> List[str]:
        """Parse path notation into parts"""
        # Simple implementation: split by dots
        # TODO: Handle bracket notation like 'pages[0].text'
        return path.split('.')

    def _find_by_key_recursive(self, data: Any, key: str, results: List[Any]) -> None:
        """Recursively find values by key"""
        if isinstance(data, dict):
            for k, v in data.items():
                if k == key:
                    results.append(v)
                self._find_by_key_recursive(v, key, results)
        elif isinstance(data, list):
            for item in data:
                self._find_by_key_recursive(item, key, results)

    def clear_cache(self) -> None:
        """Clear the internal cache"""
        self._cache.clear()
