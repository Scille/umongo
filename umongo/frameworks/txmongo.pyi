from ..builder import BaseBuilder as BaseBuilder
from ..data_objects import Reference as Reference
from ..document import DocumentImplementation as DocumentImplementation
from ..exceptions import (
    DeleteError as DeleteError,
    NoneReferenceError as NoneReferenceError,
    NotCreatedError as NotCreatedError,
    UpdateError as UpdateError,
)
from ..fields import (
    DictField as DictField,
    EmbeddedField as EmbeddedField,
    ListField as ListField,
    ReferenceField as ReferenceField,
)
from ..instance import Instance as Instance
from ..query_mapper import map_query as map_query
from .tools import (
    cook_find_filter as cook_find_filter,
    remove_cls_field_from_embedded_docs as remove_cls_field_from_embedded_docs,
)
from typing import Any, Optional

class TxMongoDocument(DocumentImplementation):
    opts: Any
    def reload(self) -> None: ...
    is_created: bool
    def commit(
        self,
        io_validate_all: bool = ...,
        conditions: Optional[Any] = ...,
        replace: bool = ...,
    ): ...
    def delete(self, conditions: Optional[Any] = ...): ...
    def io_validate(self, validate_all: bool = ...): ...
    @classmethod
    def find_one(cls, filter: Optional[Any] = ..., *args, **kwargs): ...
    @classmethod
    def find(cls, filter: Optional[Any] = ..., *args, **kwargs): ...
    @classmethod
    def find_with_cursor(cls, filter: Optional[Any] = ..., *args, **kwargs): ...
    @classmethod
    def count(cls, filter: Optional[Any] = ..., **kwargs): ...
    @classmethod
    def ensure_indexes(cls) -> None: ...

class TxMongoReference(Reference):
    def __init__(self, *args, **kwargs) -> None: ...
    def fetch(self, no_data: bool = ..., force_reload: bool = ...) -> None: ...

class TxMongoBuilder(BaseBuilder):
    BASE_DOCUMENT_CLS: Any

class TxMongoInstance(Instance):
    BUILDER_CLS: Any
    @staticmethod
    def is_compatible_with(db): ...

class TxMongoMigrationInstance(TxMongoInstance):
    def migrate_2_to_3(self) -> None: ...
