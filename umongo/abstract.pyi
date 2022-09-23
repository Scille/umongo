import marshmallow as ma
from .expose_missing import RemoveMissingSchema
from typing import Any, Optional
import abc

class I18nErrorDict(dict):
    def __getitem__(self, name): ...

class BaseMarshmallowSchema(RemoveMissingSchema):
    class Meta:
        ordered: bool

class BaseSchema(ma.Schema):
    MA_BASE_SCHEMA_CLS: Any
    class Meta:
        ordered: bool
    error_messages: Any
    def __init__(self, *args, **kwargs) -> None: ...
    def map_to_field(self, func) -> None: ...
    def as_marshmallow_schema(self): ...

class BaseField(ma.fields.Field):
    default_error_messages: Any
    MARSHMALLOW_ARGS_PREFIX: str
    error_messages: Any
    io_validate: Any
    io_validate_recursive: Any
    unique: Any
    instance: Any
    def __init__(
        self,
        *args,
        io_validate: Optional[Any] = ...,
        unique: bool = ...,
        instance: Optional[Any] = ...,
        **kwargs
    ) -> None: ...
    def serialize_to_mongo(self, obj): ...
    def deserialize_from_mongo(self, value): ...
    def as_marshmallow_field(self): ...

class BaseValidator(ma.validate.Validator, metaclass=abc.ABCMeta):
    def __init__(self, *args, **kwargs) -> None: ...

class BaseDataObject:
    def is_modified(self) -> None: ...
    def clear_modified(self) -> None: ...
    @classmethod
    def build_from_mongo(cls, data): ...
    def from_mongo(self, data): ...
    def to_mongo(self, update: bool = ...): ...
    def dump(self): ...
