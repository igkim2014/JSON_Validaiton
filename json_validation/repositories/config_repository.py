"""Configuration repository implementation"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from ..interfaces.repositories import IConfigRepository
from ..domain.exceptions import ConfigurationError


class ConfigRepository(IConfigRepository):
    """Repository for configuration data"""

    def __init__(self, config_dir: str = "config"):
        """
        Initialize configuration repository

        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir)
        self._config_cache: Dict[str, Any] = {}

    def load_validation_rules(self) -> List[Dict[str, Any]]:
        """
        Load validation rules from configuration

        Returns:
            List of validation rules

        Raises:
            ConfigurationError: If rules cannot be loaded
        """
        rules_file = self.config_dir / "validation_rules.json"
        if not rules_file.exists():
            raise ConfigurationError(f"Validation rules file not found: {rules_file}")

        try:
            with open(rules_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("rules", [])
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"Invalid JSON in validation rules: {e}")
        except Exception as e:
            raise ConfigurationError(f"Error loading validation rules: {e}")

    def load_config_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load configuration from file

        Args:
            file_path: Path to configuration file

        Returns:
            Configuration data

        Raises:
            ConfigurationError: If configuration cannot be loaded
        """
        path = Path(file_path)
        if not path.exists():
            raise ConfigurationError(f"Configuration file not found: {file_path}")

        try:
            with open(path, 'r', encoding='utf-8') as f:
                if path.suffix == '.json':
                    data = json.load(f)
                else:
                    # For non-JSON files, return as dictionary with content
                    data = {"content": f.read()}

            self._config_cache[file_path] = data
            return data
        except Exception as e:
            raise ConfigurationError(f"Error loading configuration: {e}")

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key

        Args:
            key: Configuration key (dot notation supported)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        if not self._config_cache:
            return default

        # Try to find in cached configs
        for config_data in self._config_cache.values():
            if isinstance(config_data, dict):
                value = self._get_nested_value(config_data, key)
                if value is not None:
                    return value

        return default

    def parse_search_config(self, config_file: str) -> List[str]:
        """
        Parse search configuration file and return search values

        Supports formats:
        1. Direct values: TE02.03.01
        2. Bullet format: * TE02.03.01
        3. ID format: ID: TE02.03.01

        Args:
            config_file: Path to config file

        Returns:
            List of search values

        Raises:
            ConfigurationError: If file cannot be read
        """
        path = Path(config_file)
        if not path.exists():
            raise ConfigurationError(f"Config file not found: {config_file}")

        search_values = []
        encodings = ['utf-8', 'euc-kr', 'cp949']
        file_content = None

        # Try different encodings
        for encoding in encodings:
            try:
                with open(path, 'r', encoding=encoding) as f:
                    file_content = f.read()
                break
            except UnicodeDecodeError:
                continue

        if file_content is None:
            raise ConfigurationError(f"Unable to read file with supported encodings: {config_file}")

        # Parse lines
        lines = file_content.splitlines()

        for line in lines:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Pattern 1: '* value' format
            match = re.search(r'^\*\s*(.*?)\s*$', line)
            if match and match.group(1):
                search_values.append(match.group(1))
                continue

            # Pattern 2: 'ID: value' format
            match = re.search(r'ID:\s*(.*?)\s*$', line)
            if match and match.group(1):
                search_values.append(match.group(1))
                continue

            # Pattern 3: TE number format (e.g., TE02.03.01)
            if re.match(r'^TE\d+\.\d+\.\d+$', line):
                search_values.append(line)
                continue

            # Pattern 4: General alphanumeric values
            if re.match(r'^[a-zA-Z0-9\.\-_]+$', line):
                search_values.append(line)
                continue

        # Remove duplicates while preserving order
        search_values = list(dict.fromkeys(search_values))

        return search_values

    def save_config(self, file_path: str, data: Dict[str, Any]) -> None:
        """
        Save configuration to file

        Args:
            file_path: Output file path
            data: Configuration data
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self._config_cache[file_path] = data
        except Exception as e:
            raise ConfigurationError(f"Error saving configuration: {e}")

    def create_sample_search_config(self, file_path: str) -> None:
        """
        Create sample search configuration file

        Args:
            file_path: Path for sample config file
        """
        sample_content = """# Search value list
# Enter search values, one per line

TE02.03.01
TE02.07.02
TE02.09.01
TE02.10.01
TE02.11.01
"""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(sample_content)
        except Exception as e:
            raise ConfigurationError(f"Error creating sample config: {e}")

    def _get_nested_value(self, data: Dict[str, Any], key: str) -> Optional[Any]:
        """Get value from nested dictionary using dot notation"""
        keys = key.split('.')
        current = data

        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return None

        return current

    def clear_cache(self) -> None:
        """Clear configuration cache"""
        self._config_cache.clear()
