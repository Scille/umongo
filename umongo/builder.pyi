from . import fields as fields
from .abstract import BaseSchema as BaseSchema
from .data_proxy import data_proxy_factory as data_proxy_factory
from .document import (
    DocumentImplementation as DocumentImplementation,
    DocumentOpts as DocumentOpts,
    DocumentTemplate as DocumentTemplate,
)
from .embedded_document import (
    EmbeddedDocumentImplementation as EmbeddedDocumentImplementation,
    EmbeddedDocumentOpts as EmbeddedDocumentOpts,
    EmbeddedDocumentTemplate as EmbeddedDocumentTemplate,
)
from .exceptions import (
    DocumentDefinitionError as DocumentDefinitionError,
    NotRegisteredDocumentError as NotRegisteredDocumentError,
)
from .mixin import (
    MixinDocumentImplementation as MixinDocumentImplementation,
    MixinDocumentOpts as MixinDocumentOpts,
    MixinDocumentTemplate as MixinDocumentTemplate,
)
from .template import Implementation as Implementation, Template as Template
from typing import Any

TEMPLATE_IMPLEMENTATION_MAPPING: Any
TEMPLATE_OPTIONS_MAPPING: Any

def camel_to_snake(name): ...

class BaseBuilder:
    BASE_DOCUMENT_CLS: Any
    instance: Any
    def __init__(self, instance) -> None: ...
    def build_from_template(self, template): ...
