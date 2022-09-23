from ..document import DocumentImplementation as DocumentImplementation
from ..instance import Instance as Instance
from .pymongo import (
    BaseWrappedCursor as BaseWrappedCursor,
    PyMongoBuilder as PyMongoBuilder,
    PyMongoDocument as PyMongoDocument,
)
from typing import Any

# FIXME Should inherit from mongomock.Cursor, but mongomock might not be installed
# There might be some missing attributes
class WrappedCursor(BaseWrappedCursor):
    def __len__(self) -> int: ...
    def __contains__(self, x: object) -> bool: ...

class MongoMockDocument(PyMongoDocument):
    cursor_cls: Any
    opts: Any

class MongoMockBuilder(PyMongoBuilder):
    BASE_DOCUMENT_CLS: Any

class MongoMockInstance(Instance):
    BUILDER_CLS: Any
    @staticmethod
    def is_compatible_with(db): ...
