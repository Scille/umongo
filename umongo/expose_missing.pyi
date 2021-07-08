import marshmallow as ma
from contextlib import AbstractContextManager
from typing import Any

class ExposeMissing(AbstractContextManager):
    token: Any
    def __enter__(self) -> None: ...
    def __exit__(self, *args, **kwargs) -> None: ...

class RemoveMissingSchema(ma.Schema):
    def dump(self, *args, **kwargs): ...
