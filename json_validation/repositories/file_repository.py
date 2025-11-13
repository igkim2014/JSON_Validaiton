"""File repository implementation"""

import os
from pathlib import Path
from typing import List
from ..interfaces.repositories import IFileRepository
from ..domain.exceptions import DataExtractionError


class FileRepository(IFileRepository):
    """Repository for file operations"""

    def exists(self, file_path: str) -> bool:
        """
        Check if file exists

        Args:
            file_path: Path to file

        Returns:
            True if file exists
        """
        return Path(file_path).exists()

    def read(self, file_path: str) -> bytes:
        """
        Read file as bytes

        Args:
            file_path: Path to file

        Returns:
            File content as bytes

        Raises:
            DataExtractionError: If file cannot be read
        """
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except FileNotFoundError:
            raise DataExtractionError(f"File not found: {file_path}", source=file_path)
        except Exception as e:
            raise DataExtractionError(f"Error reading file: {e}", source=file_path)

    def write(self, file_path: str, content: bytes) -> None:
        """
        Write bytes to file

        Args:
            file_path: Path to output file
            content: Content to write

        Raises:
            DataExtractionError: If file cannot be written
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'wb') as f:
                f.write(content)
        except Exception as e:
            raise DataExtractionError(f"Error writing file: {e}", source=file_path)

    def delete(self, file_path: str) -> None:
        """
        Delete file

        Args:
            file_path: Path to file

        Raises:
            DataExtractionError: If file cannot be deleted
        """
        try:
            Path(file_path).unlink()
        except FileNotFoundError:
            pass  # Already deleted
        except Exception as e:
            raise DataExtractionError(f"Error deleting file: {e}", source=file_path)

    def list_files(self, directory: str, pattern: str = "*") -> List[str]:
        """
        List files in directory matching pattern

        Args:
            directory: Directory to search
            pattern: Glob pattern (default: "*")

        Returns:
            List of file paths

        Raises:
            DataExtractionError: If directory cannot be read
        """
        try:
            path = Path(directory)
            if not path.exists():
                return []

            if not path.is_dir():
                raise DataExtractionError(f"Not a directory: {directory}")

            files = [str(f) for f in path.glob(pattern) if f.is_file()]
            return sorted(files)
        except Exception as e:
            raise DataExtractionError(f"Error listing files: {e}", source=directory)

    def ensure_directory(self, directory: str) -> None:
        """
        Ensure directory exists, create if not

        Args:
            directory: Directory path
        """
        Path(directory).mkdir(parents=True, exist_ok=True)

    def get_file_size(self, file_path: str) -> int:
        """
        Get file size in bytes

        Args:
            file_path: Path to file

        Returns:
            File size in bytes
        """
        return Path(file_path).stat().st_size

    def get_file_extension(self, file_path: str) -> str:
        """
        Get file extension

        Args:
            file_path: Path to file

        Returns:
            File extension (e.g., '.json', '.pdf')
        """
        return Path(file_path).suffix
