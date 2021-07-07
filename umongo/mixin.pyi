from .template import Implementation, Template
from typing import Any

class MixinDocumentTemplate(Template): ...

MixinDocument = MixinDocumentTemplate

class MixinDocumentOpts:
    instance: Any
    template: Any
    def __init__(self, instance, template) -> None: ...

class MixinDocumentImplementation(Implementation):
    opts: Any
