"""Repository interfaces - Data access contracts"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pathlib import Path


class IFileRepository(ABC):
    """Interface for file operations"""

    @abstractmethod
    def exists(self, file_path: str) -> bool:
        """Check if file exists"""
        pass

    @abstractmethod
    def read(self, file_path: str) -> bytes:
        """Read file as bytes"""
        pass

    @abstractmethod
    def write(self, file_path: str, content: bytes) -> None:
        """Write bytes to file"""
        pass

    @abstractmethod
    def delete(self, file_path: str) -> None:
        """Delete file"""
        pass

    @abstractmethod
    def list_files(self, directory: str, pattern: str = "*") -> List[str]:
        """List files in directory matching pattern"""
        pass


class IJsonRepository(ABC):
    """Interface for JSON data access"""

    @abstractmethod
    def load(self, file_path: str) -> Dict[str, Any]:
        """Load JSON from file"""
        pass

    @abstractmethod
    def save(self, file_path: str, data: Dict[str, Any]) -> None:
        """Save data to JSON file"""
        pass

    @abstractmethod
    def search_value(self, data: Dict[str, Any], search_path: str) -> Optional[Any]:
        """Search for value in JSON data using path notation"""
        pass

    @abstractmethod
    def find_by_key(self, data: Dict[str, Any], key: str) -> List[Any]:
        """Find all values with matching key"""
        pass

    @abstractmethod
    def extract_field(self, data: Dict[str, Any], field_path: str, default: Any = None) -> Any:
        """Extract field using dot notation (e.g., 'metadata.title')"""
        pass


class IConfigRepository(ABC):
    """Interface for configuration data access"""

    @abstractmethod
    def load_validation_rules(self) -> List[Dict[str, Any]]:
        """Load validation rules from configuration"""
        pass

    @abstractmethod
    def load_config_file(self, file_path: str) -> Dict[str, Any]:
        """Load configuration from file"""
        pass

    @abstractmethod
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key"""
        pass

    @abstractmethod
    def parse_search_config(self, config_file: str) -> List[str]:
        """Parse search configuration file and return search values"""
        pass


class IPDFRepository(ABC):
    """Interface for PDF operations"""

    @abstractmethod
    def extract_to_json(self, pdf_path: str) -> Dict[str, Any]:
        """Extract PDF content to JSON structure"""
        pass

    @abstractmethod
    def generate_from_json(self, json_data: Dict[str, Any], output_path: str) -> None:
        """Generate PDF from JSON structure"""
        pass

    @abstractmethod
    def get_page_count(self, pdf_path: str) -> int:
        """Get number of pages in PDF"""
        pass


class IImageRepository(ABC):
    """Interface for image operations"""

    @abstractmethod
    def save_image(self, image_data: bytes, file_path: str) -> None:
        """Save image to file"""
        pass

    @abstractmethod
    def load_image(self, file_path: str) -> bytes:
        """Load image from file"""
        pass

    @abstractmethod
    def create_table_image(self, table_data: List[List[str]], output_path: str) -> None:
        """Create image from table data"""
        pass
