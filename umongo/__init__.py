from marshmallow import ValidationError, missing

from . import fields, validate
from .data_objects import Reference
from .document import (
    Document,
    post_dump,
    post_load,
    pre_dump,
    pre_load,
    validates_schema,
)
from .embedded_document import EmbeddedDocument
from .exceptions import (
    AlreadyCreatedError,
    DeleteError,
    NoneReferenceError,
    NotCreatedError,
    UMongoError,
    UnknownFieldInDBError,
    UpdateError,
)
from .expose_missing import ExposeMissing, RemoveMissingSchema
from .i18n import set_gettext
from .instance import Instance
from .mixin import MixinDocument

__author__ = "Emmanuel Leblond, Jérôme Lafréchoux"
__email__ = "jerome@jolimont.fr"
__version__ = "3.1.0"
__all__ = (
    "AlreadyCreatedError",
    "DeleteError",
    "Document",
    "EmbeddedDocument",
    "ExposeMissing",
    "Instance",
    "MixinDocument",
    "NoneReferenceError",
    "NotCreatedError",
    "Reference",
    "RemoveMissingSchema",
    "UMongoError",
    "UnknownFieldInDBError",
    "UpdateError",
    "ValidationError",
    "fields",
    "missing",
    "post_dump",
    "post_load",
    "pre_dump",
    "pre_load",
    "set_gettext",
    "validate",
    "validates_schema",
)
