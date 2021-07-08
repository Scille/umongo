from ..document import DocumentImplementation as DocumentImplementation
from ..instance import Instance as Instance
from .pymongo import (
    BaseWrappedCursor as BaseWrappedCursor,
    PyMongoBuilder as PyMongoBuilder,
    PyMongoDocument as PyMongoDocument,
)
from mongomock.collection import Cursor
from typing import Any

class WrappedCursor(BaseWrappedCursor, Cursor): ...

class MongoMockDocument(PyMongoDocument):
    cursor_cls: Any
    opts: Any

class MongoMockBuilder(PyMongoBuilder):
    BASE_DOCUMENT_CLS: Any

class MongoMockInstance(Instance):
    BUILDER_CLS: Any
    @staticmethod
    def is_compatible_with(db): ...
