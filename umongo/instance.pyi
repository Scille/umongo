import abc
from .document import DocumentTemplate as DocumentTemplate, DocumentImplementation
from .embedded_document import EmbeddedDocumentTemplate as EmbeddedDocumentTemplate
from .exceptions import (
    AlreadyRegisteredDocumentError as AlreadyRegisteredDocumentError,
    NoDBDefinedError as NoDBDefinedError,
    NotRegisteredDocumentError as NotRegisteredDocumentError,
)
from .template import get_template as get_template
from typing import Any, Optional, Type, Generic, TypeVar

TDocImpl = TypeVar("TDocImpl", bound=DocumentImplementation)

class Instance(abc.ABC, Generic[TDocImpl], metaclass=abc.ABCMeta):
    BUILDER_CLS: Any
    builder: Any
    def __init__(self, db: Optional[Any] = ...) -> None: ...
    @classmethod
    def from_db(cls, db): ...
    def retrieve_document(self, name_or_template): ...
    def retrieve_embedded_document(self, name_or_template): ...
    def register(self, template: Type[DocumentTemplate]) -> Type[TDocImpl]: ...
    @property
    def db(self): ...
    @abc.abstractmethod
    def is_compatible_with(self, db): ...
    def set_db(self, db) -> None: ...
