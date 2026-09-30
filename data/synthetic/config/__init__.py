"""Configuration contract of the synthetic dataset generator."""

from .config import (
    DEFAULT_CONFIG_PATH,
    ConfigError,
    DatasetConfig,
    Period,
    Scale,
    Scenario,
    load_config,
)

__all__ = [
    "ConfigError",
    "DatasetConfig",
    "Period",
    "Scale",
    "Scenario",
    "load_config",
    "DEFAULT_CONFIG_PATH",
]
