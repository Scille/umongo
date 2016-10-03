from .instance import Instance
from .frameworks import (
    PyMongoInstance,
    TxMongoInstance,
    MotorAsyncIOInstance,
    MotorTornadoInstance,
    MongoMockInstance
)
from .document import Document
from .exceptions import (
    UMongoError,
    ValidationError,
    NoDBDefinedError,
    NotRegisteredDocumentError,
    AlreadyRegisteredDocumentError,
    BuilderNotDefinedError,
    UpdateError,
    MissingSchemaError,
    NotCreatedError,
    NoCollectionDefinedError,
    FieldNotLoadedError
)
from . import fields, validate
from .schema import BaseSchema, Schema, EmbeddedSchema
from .data_objects import Reference
from .embedded_document import EmbeddedDocument
from .i18n import set_gettext


__author__ = 'Emmanuel Leblond'
__email__ = 'emmanuel.leblond@gmail.com'
__version__ = '0.10.0'
__all__ = (
    'Instance',
    'PyMongoInstance',
    'TxMongoInstance',
    'MotorAsyncIOInstance',
    'MotorTornadoInstance',
    'MongoMockInstance',

    'Document',
    'EmbeddedDocument',

    'UMongoError',
    'ValidationError',
    'NoDBDefinedError',
    'NotRegisteredDocumentError',
    'AlreadyRegisteredDocumentError',
    'BuilderNotDefinedError',
    'UpdateError',
    'MissingSchemaError',
    'NotCreatedError',
    'NoCollectionDefinedError',
    'FieldNotLoadedError',

    'fields',

    'BaseSchema',
    'Schema',
    'EmbeddedSchema',

    'Reference',

    'set_gettext',

    'validate'
)
