#!/usr/bin/env python3
"""
Storage Module

Provides both file-based and database storage with automatic switching.
"""

from .local_storage import LocalStorage, get_storage
from .adapter import StorageAdapter, get_storage_adapter

__all__ = ['LocalStorage', 'get_storage', 'StorageAdapter', 'get_storage_adapter']