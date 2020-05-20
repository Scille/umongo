from marshmallow import ValidationError, missing  # noqa, republishing

from .instance import Instance
from .frameworks import (
    PyMongoInstance,
    TxMongoInstance,
    MotorAsyncIOInstance,
    MongoMockInstance,
    MotorTornadoInstance
)
from .document import (
    Document,
    pre_load,
    post_load,
    pre_dump,
    post_dump,
    validates_schema
)
from .exceptions import (
    UMongoError,
    UpdateError,
    DeleteError,
    AlreadyCreatedError,
    NotCreatedError,
    NoneReferenceError,
    UnknownFieldInDBError,
)
from . import fields, validate
from .schema import Schema
from .data_objects import Reference
from .embedded_document import EmbeddedDocument
from .i18n import set_gettext


__author__ = 'Emmanuel Leblond'
__email__ = 'emmanuel.leblond@gmail.com'
__version__ = '3.0.0b7'
__all__ = (
    'missing',

    'Instance',
    'PyMongoInstance',
    'TxMongoInstance',
    'MotorAsyncIOInstance',
    'MongoMockInstance',

    'Document',
    'pre_load',
    'post_load',
    'pre_dump',
    'post_dump',
    'validates_schema',
    'EmbeddedDocument',

    'UMongoError',
    'ValidationError',
    'UpdateError',
    'DeleteError',
    'AlreadyCreatedError',
    'NotCreatedError',
    'NoneReferenceError',
    'UnknownFieldInDBError',

    'fields',

    'Schema',

    'Reference',

    'set_gettext',

    'validate'
)
