import pytest

from umongo.frameworks import BuilderRegisterer
from umongo.builder import BaseBuilder
from umongo.document import DocumentImplementation
from umongo.exceptions import NoCompatibleBuilderError


def create_env(prefix):
    db_cls = type('%sDB' % prefix, (), {})
    document_cls = type('%sDocument' % prefix, (DocumentImplementation, ), {})
    builder_cls = type('%sBuilder' % prefix, (BaseBuilder, ), {
        'BASE_DOCUMENT_CLS': document_cls,
        'is_compatible_with': staticmethod(lambda db: isinstance(db, db_cls))
    })
    return db_cls, document_cls, builder_cls


class TestBuilder:

    def test_basic_builder_registerer(self):
        registerer = BuilderRegisterer()
        AlphaDB, AlphaDocument, AlphaBuilder = create_env('Alpha')

        with pytest.raises(NoCompatibleBuilderError):
            registerer.find_from_db(AlphaDB())
        registerer.register(AlphaBuilder)
        assert registerer.find_from_db(AlphaDB()) is AlphaBuilder
        # Multiple registers does nothing
        registerer.register(AlphaBuilder)
        registerer.unregister(AlphaBuilder)
        with pytest.raises(NoCompatibleBuilderError):
            registerer.find_from_db(AlphaDB())

    def test_multi_builder(self):
        registerer = BuilderRegisterer()
        AlphaDB, AlphaDocument, AlphaBuilder = create_env('Alpha')
        BetaDB, BetaDocument, BetaBuilder = create_env('Beta')

        registerer.register(AlphaBuilder)
        assert registerer.find_from_db(AlphaDB()) is AlphaBuilder
        with pytest.raises(NoCompatibleBuilderError):
            registerer.find_from_db(BetaDB())
        registerer.register(BetaBuilder)
        assert registerer.find_from_db(BetaDB()) is BetaBuilder
        assert registerer.find_from_db(AlphaDB()) is AlphaBuilder

    def test_overload_builder(self):
        registerer = BuilderRegisterer()
        AlphaDB, AlphaDocument, AlphaBuilder = create_env('Alpha')

        registerer.register(AlphaBuilder)
        # Create a new builder compatible with AlphaDB
        class Alpha2Builder(AlphaBuilder):
            pass
        registerer.register(Alpha2Builder)

        # Last registered builder should be tested first
        assert registerer.find_from_db(AlphaDB()) is Alpha2Builder
