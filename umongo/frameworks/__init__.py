"""
Frameworks
==========

"""

from importlib import import_module

from ..exceptions import NoCompatibleBuilderError
from ..instance import LazyLoaderInstance


__all__ = (
    'BuilderRegisterer',

    'default_builder_registerer',
    'register_builder',
    'unregister_builder',
    'find_builder_from_db',

    'PyMongoInstance',
    'TxMongoInstance',
    'MotorAsyncIOInstance',
    'MotorTornadoInstance',
    'MongoMockInstance'
)


class BuilderRegisterer:

    def __init__(self):
        self.builders = []

    def register(self, builder):
        if builder not in self.builders:
            # Insert new item first to overload older compatible builders
            self.builders.insert(0, builder)

    def unregister(self, builder):
        # Basically only used for tests
        self.builders.remove(builder)

    def find_from_db(self, db):
        for builder in self.builders:
            if builder.is_compatible_with(db):
                return builder
        raise NoCompatibleBuilderError(
            'Cannot find a umongo builder compatible with %s' % type(db))


default_builder_registerer = BuilderRegisterer()
register_builder = default_builder_registerer.register
unregister_builder = default_builder_registerer.unregister
find_builder_from_db = default_builder_registerer.find_from_db


# Define lazy loader instances for each builder

class PyMongoInstance(LazyLoaderInstance):
    """
    :class:`umongo.instance.LazyLoaderInstance` implementation for pymongo
    """
    def __init__(self, *args, **kwargs):
        self.BUILDER_CLS = import_module('umongo.frameworks.pymongo').PyMongoBuilder
        super().__init__(*args, **kwargs)


class TxMongoInstance(LazyLoaderInstance):
    """
    :class:`umongo.instance.LazyLoaderInstance` implementation for txmongo
    """
    def __init__(self, *args, **kwargs):
        self.BUILDER_CLS = import_module('umongo.frameworks.txmongo').TxMongoBuilder
        super().__init__(*args, **kwargs)


class MotorAsyncIOInstance(LazyLoaderInstance):
    """
    :class:`umongo.instance.LazyLoaderInstance` implementation for motor-asyncio
    """
    def __init__(self, *args, **kwargs):
        self.BUILDER_CLS = import_module('umongo.frameworks.motor_asyncio').MotorAsyncIOBuilder
        super().__init__(*args, **kwargs)


class MotorTornadoInstance(LazyLoaderInstance):
    """
    :class:`umongo.instance.LazyLoaderInstance` implementation for motor-tornado
    """
    def __init__(self, *args, **kwargs):
        self.BUILDER_CLS = import_module('umongo.frameworks.motor_tornado').MotorTornadoBuilder
        super().__init__(*args, **kwargs)


class MongoMockInstance(LazyLoaderInstance):
    """
    :class:`umongo.instance.LazyLoaderInstance` implementation for mongomock
    """
    def __init__(self, *args, **kwargs):
        self.BUILDER_CLS = import_module('umongo.frameworks.mongomock').MongoMockBuilder
        super().__init__(*args, **kwargs)


# try to load all the builders by default
try:
    from .pymongo import PyMongoBuilder
    register_builder(PyMongoBuilder)
except ImportError:  # pragma: no cover
    pass
try:
    from .txmongo import TxMongoBuilder
    register_builder(TxMongoBuilder)
except ImportError:  # pragma: no cover
    pass
try:
    from .motor_asyncio import MotorAsyncIOBuilder
    register_builder(MotorAsyncIOBuilder)
except ImportError:  # pragma: no cover
    pass
try:
    from .motor_tornado import MotorTornadoBuilder
    register_builder(MotorTornadoBuilder)
except ImportError:  # pragma: no cover
    pass
try:
    from .mongomock import MongoMockBuilder
    register_builder(MongoMockBuilder)
except ImportError:  # pragma: no cover
    pass
