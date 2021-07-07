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

SESSION: Any

class WrappedCursor:
    def __init__(self, document_cls, cursor) -> None: ...
    def __getattr__(self, name): ...
    def __setattr__(self, name, value): ...
    def clone(self): ...
    async def next(self): ...
    __anext__: Any
    def next_object(self): ...
    def each(self, callback): ...
    def to_list(self, length, callback: Optional[Any] = ...): ...

class MotorAsyncIODocument(DocumentImplementation):
    opts: Any
    async def reload(self) -> None: ...
    is_created: bool
    async def commit(
        self,
        io_validate_all: bool = ...,
        conditions: Optional[Any] = ...,
        replace: bool = ...,
    ): ...
    async def delete(self, conditions: Optional[Any] = ...): ...
    async def remove(self, conditions: Optional[Any] = ...): ...
    async def io_validate(self, validate_all: bool = ...): ...
    @classmethod
    async def find_one(cls, filter: Optional[Any] = ..., *args, **kwargs): ...
    @classmethod
    def find(cls, filter: Optional[Any] = ..., *args, **kwargs): ...
    @classmethod
    async def count_documents(
        cls, filter: Optional[Any] = ..., *, with_limit_and_skip: bool = ..., **kwargs
    ): ...
    @classmethod
    async def ensure_indexes(cls) -> None: ...

class MotorAsyncIOReference(Reference):
    def __init__(self, *args, **kwargs) -> None: ...
    async def fetch(self, no_data: bool = ..., force_reload: bool = ...): ...

class MotorAsyncIOBuilder(BaseBuilder):
    BASE_DOCUMENT_CLS: Any

class MotorAsyncIOInstance(Instance):
    BUILDER_CLS: Any
    @staticmethod
    def is_compatible_with(db): ...
    async def session(self) -> None: ...

class MotorAsyncIOMigrationInstance(MotorAsyncIOInstance):
    async def migrate_2_to_3(self) -> None: ...
