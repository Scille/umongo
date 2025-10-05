from mongomock.collection import Cursor
from mongomock.database import Database

from umongo.document import DocumentImplementation
from umongo.instance import Instance

from .pymongo import BaseWrappedCursor, PyMongoBuilder, PyMongoDocument

# Mongomock aims at working like pymongo


class WrappedCursor(BaseWrappedCursor, Cursor):
    __slots__ = ()


class MongoMockDocument(PyMongoDocument):
    __slots__ = ()
    cursor_cls = WrappedCursor
    opts = DocumentImplementation.opts


class MongoMockBuilder(PyMongoBuilder):
    BASE_DOCUMENT_CLS = MongoMockDocument


class MongoMockInstance(Instance):
    """:class:`umongo.instance.Instance` implementation for mongomock"""

    BUILDER_CLS = MongoMockBuilder

    @staticmethod
    def is_compatible_with(db):
        return isinstance(db, Database)
