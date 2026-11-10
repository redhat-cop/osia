"""Module provides access to configuration via Dynaconf"""
from .config import read_config, resolve_credentials_file, settings

__all__ = ['read_config', 'resolve_credentials_file', 'settings']
