""" Overwrites __init__.py for mypy analysis.
    This file should be removed once everything is fully typed
"""
from .document import Document as _Document

Document = _Document
