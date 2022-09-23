from .abstract import BaseMarshmallowSchema as BaseMarshmallowSchema
from typing import Any

class MetaTemplate(type):
    def __new__(cls, name, bases, nmspc): ...

class Template(metaclass=MetaTemplate):
    MA_BASE_SCHEMA_CLS: Any
    def __init__(self, *args, **kwargs) -> None: ...

class MetaImplementation(MetaTemplate):
    def __new__(cls, name, bases, nmspc): ...

class Implementation(metaclass=MetaImplementation):
    @property
    def opts(self) -> None: ...

def get_template(template_or_implementation): ...
