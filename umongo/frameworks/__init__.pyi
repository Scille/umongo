from .mongomock import MongoMockInstance as MongoMockInstance
from .motor_asyncio import MotorAsyncIOInstance as MotorAsyncIOInstance
from .pymongo import PyMongoInstance as PyMongoInstance
from .txmongo import TxMongoInstance as TxMongoInstance
from typing import Any

class InstanceRegisterer:
    instances: Any
    def __init__(self) -> None: ...
    def register(self, instance) -> None: ...
    def unregister(self, instance) -> None: ...
    def find_from_db(self, db): ...

default_instance_registerer: Any
register_instance: Any
unregister_instance: Any
find_instance_from_db: Any
