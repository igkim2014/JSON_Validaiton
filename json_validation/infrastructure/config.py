"""Configuration management"""

import os
from pathlib import Path
from typing import Any, Dict, Optional


class Config:
    """
    Centralized configuration management
    Follows KISS principle - simple dictionary-based configuration
    """

    _instance: Optional['Config'] = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        """Singleton pattern for configuration"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize_defaults()
        return cls._instance

    def _initialize_defaults(self) -> None:
        """Initialize default configuration"""
        base_dir = Path.cwd()

        self._config = {
            # Paths
            "base_dir": str(base_dir),
            "config_dir": str(base_dir / "config"),
            "output_dir": str(base_dir / "out"),
            "temp_dir": str(base_dir / "temp"),
            "fonts_dir": str(base_dir / "fonts"),
            "images_dir": str(base_dir / "extracted_images"),
            "table_images_dir": str(base_dir / "extracted_table_images"),

            # Files
            "validation_rules_file": "config/validation_rules.json",

            # Validation settings
            "min_pass_score": 0.8,
            "enable_strict_mode": False,

            # PDF extraction settings
            "enable_ocr": True,
            "ocr_language": "eng+kor",
            "image_dpi": 300,

            # Font settings
            "default_font": "NotoSansKR-Regular.ttf",
            "fallback_font": "MalgunGothic.ttf",
            "font_size": 10,

            # GUI settings
            "window_width": 1200,
            "window_height": 800,
            "theme": "default",

            # Logging
            "log_level": "INFO",
            "enable_debug": False,
        }

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value

        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value

        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split('.')
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def update(self, config_dict: Dict[str, Any]) -> None:
        """
        Update configuration with dictionary

        Args:
            config_dict: Dictionary of configuration values
        """
        self._config.update(config_dict)

    def get_path(self, key: str) -> Path:
        """
        Get path configuration as Path object

        Args:
            key: Configuration key

        Returns:
            Path object
        """
        value = self.get(key)
        return Path(value) if value else Path.cwd()

    def ensure_directories(self) -> None:
        """Ensure all configured directories exist"""
        dir_keys = [
            "output_dir",
            "temp_dir",
            "images_dir",
            "table_images_dir",
        ]

        for key in dir_keys:
            path = self.get_path(key)
            path.mkdir(parents=True, exist_ok=True)

    def load_from_env(self) -> None:
        """Load configuration from environment variables"""
        env_mappings = {
            "JSON_VALIDATION_CONFIG_DIR": "config_dir",
            "JSON_VALIDATION_OUTPUT_DIR": "output_dir",
            "JSON_VALIDATION_LOG_LEVEL": "log_level",
            "JSON_VALIDATION_DEBUG": "enable_debug",
        }

        for env_var, config_key in env_mappings.items():
            value = os.environ.get(env_var)
            if value:
                # Convert boolean strings
                if value.lower() in ('true', 'false'):
                    value = value.lower() == 'true'
                self.set(config_key, value)

    def to_dict(self) -> Dict[str, Any]:
        """
        Get all configuration as dictionary

        Returns:
            Configuration dictionary
        """
        return self._config.copy()

    def reset(self) -> None:
        """Reset configuration to defaults"""
        self._initialize_defaults()


# Global configuration instance
config = Config()
