from marshmallow import ValidationError, missing
import pytest

from umongo.data_proxy import DataProxy
from umongo import EmbeddedSchema, fields, EmbeddedDocument, validate, exceptions

from .common import BaseTest


class TestDataProxy(BaseTest):

    def test_repr(self):

        class MySchema(EmbeddedSchema):
            field_a = fields.IntField()
            field_b = fields.StrField()

        d = DataProxy(MySchema(), {'field_a': 1, 'field_b': 'value'})
        repr_d = repr(d)
        assert repr_d.startswith("<DataProxy(")
        assert "'field_a': 1" in repr_d
        assert "'field_b': 'value'" in repr_d

    def test_simple(self):

        class MySchema(EmbeddedSchema):
            a = fields.IntField()
            b = fields.IntField()

        d = DataProxy(MySchema())
        d.load({'a': 1, 'b': 2})
        assert d.get('a') == 1
        d.set('b', 3)
        assert d.get('b') == 3
        assert d._data == {'a': 1, 'b': 3}
        assert d.dump() == {'a': 1, 'b': 3}
        d.delete('b')
        assert d._data == {'a': 1, 'b': missing}
        assert d.dump() == {'a': 1}

    def test_load(self):

        class MySchema(EmbeddedSchema):
            a = fields.IntField()
            b = fields.IntField(attribute='in_mongo_b')

        d = DataProxy(MySchema())
        d.load({'a': 1, 'b': 2})
        assert d.to_mongo() == {'a': 1, 'in_mongo_b': 2}

        d.set('a', 3)
        assert d.to_mongo(update=True) == {'$set': {'a': 3}}

        d.load({'a': 4, 'b': 5})
        assert d.to_mongo(update=True) is None
        assert d.to_mongo() == {'a': 4, 'in_mongo_b': 5}

        d2 = DataProxy(MySchema(), data={'a': 4, 'b': 5})
        assert d == d2

    def test_modify(self):

        class MySchema(EmbeddedSchema):
            a = fields.IntField()
            b = fields.IntField(attribute='in_mongo_b')

        d = DataProxy(MySchema())
        d.load({'a': 1, 'b': 2})
        assert d.to_mongo() == {'a': 1, 'in_mongo_b': 2}
        assert d.to_mongo(update=True) is None
        d.set('a', 3)
        d.delete('b')
        assert d.to_mongo(update=True) == {'$set': {'a': 3}, '$unset': {'in_mongo_b': ''}}
        d.clear_modified()
        assert d.to_mongo(update=True) is None
        assert d.to_mongo() == {'a': 3}

    def test_complexe_field_clear_modified(self):

        @self.instance.register
        class MyEmbedded(EmbeddedDocument):
            aa = fields.IntField()

        class MySchema(EmbeddedSchema):
            # EmbeddedField need instance to retrieve implementation
            a = fields.EmbeddedField(MyEmbedded, instance=self.instance)
            b = fields.ListField(fields.IntField)

        d = DataProxy(MySchema())
        d.load({'a': {'aa': 1}, 'b': [2, 3]})
        assert d.to_mongo() == {'a': {'aa': 1}, 'b': [2, 3]}
        d.get('a').aa = 4
        d.get('b').append(5)
        assert d.to_mongo(update=True) == {'$set': {'a': {'aa': 4}, 'b': [2, 3, 5]}}
        d.clear_modified()
        assert d.to_mongo(update=True) is None
        assert not d.get('a').is_modified()
        assert not d.get('b').is_modified()

    def test_set(self):

        class MySchema(EmbeddedSchema):
            a = fields.IntField()
            b = fields.IntField(attribute='in_mongo_b')

        d = DataProxy(MySchema())
        d.load({'a': 1, 'b': 2})
        d.set('a', 3)
        assert d.to_mongo() == {'a': 3, 'in_mongo_b': 2}
        assert d.to_mongo(update=True) == {'$set': {'a': 3}}

        d.load({'a': 1, 'b': 2})
        d.set('b', 3)
        assert d.to_mongo() == {'a': 1, 'in_mongo_b': 3}
        assert d.to_mongo(update=True) == {'$set': {'in_mongo_b': 3}}

        with pytest.raises(KeyError):
            d.set('in_mongo_b', 2)

    def test_del(self):

        class MySchema(EmbeddedSchema):
            a = fields.IntField()
            b = fields.IntField(attribute='in_mongo_b')

        d = DataProxy(MySchema())
        d.load({'a': 1, 'b': 2})
        d.delete('b')
        assert d.to_mongo() == {'a': 1}
        assert d.to_mongo(update=True) == {'$unset': {'in_mongo_b': ''}}
        d.delete('a')
        assert d.to_mongo(update=True) == {'$unset': {'a': '', 'in_mongo_b': ''}}

        with pytest.raises(KeyError):
            d.delete('in_mongo_b')

    def test_route_naming(self):

        class MySchema(EmbeddedSchema):
            in_front = fields.IntField(attribute='in_mongo')

        d = DataProxy(MySchema())
        with pytest.raises(ValidationError):
            d.load({'in_mongo': 42})
        d.load({'in_front': 42})
        with pytest.raises(KeyError):
            d.get('in_mongo')
        assert d.get('in_front') == 42
        d.set('in_front', 24)
        assert d._data == {'in_mongo': 24}
        assert d.get('in_front') == 24
        assert d.dump() == {'in_front': 24}
        assert d.to_mongo() == {'in_mongo': 24}

    def test_from_mongo(self):

        class MySchema(EmbeddedSchema):
            in_front = fields.IntField(attribute='in_mongo')

        d = DataProxy(MySchema())
        with pytest.raises(KeyError):
            d.from_mongo({'in_front': 42})
        d.from_mongo({'in_mongo': 42})
        assert d.get('in_front') == 42

    def test_equality(self):

        class MySchema(EmbeddedSchema):
            a = fields.IntField()
            b = fields.IntField(attribute='in_mongo_b')

        d1 = DataProxy(MySchema())
        d1.load({'a': 1, 'b': 2})
        assert d1 == {'a': 1, 'in_mongo_b': 2}

        d2 = DataProxy(MySchema())
        d2.load({'a': 1, 'b': 2})
        assert d1 == d2

    def test_access_by_mongo_name(self):

        class MySchema(EmbeddedSchema):
            a = fields.IntField()
            b = fields.IntField(attribute='in_mongo_b')

        d = DataProxy(MySchema(), data={'a': 1, 'b': 2})
        assert d.get_by_mongo_name('in_mongo_b') == 2
        assert d.get_by_mongo_name('a') == 1
        with pytest.raises(KeyError):
            d.get_by_mongo_name('b')
        d.set_by_mongo_name('in_mongo_b', 3)
        assert d.to_mongo(update=True) == {'$set': {'in_mongo_b': 3}}
        assert d.get_by_mongo_name('in_mongo_b') == 3
        d.delete_by_mongo_name('in_mongo_b')
        assert d.to_mongo(update=True) == {'$unset': {'in_mongo_b': ''}}

    def test_set_to_missing_fields(self):

        class MySchema(EmbeddedSchema):
            a = fields.IntField()
            b = fields.IntField(attribute='in_mongo_b')

        d = DataProxy(MySchema(), data={'a': 1})
        assert d.get('b') is missing
        assert d.get_by_mongo_name('in_mongo_b') is missing
        assert d._data['in_mongo_b'] is missing
        d.set('b', 2)
        assert d.get('b') == 2
        d.delete('b')
        # Can do it two time in a row without error
        d.delete('b')
        assert d._data['in_mongo_b'] is missing

    def test_default(self):

        class MySchema(EmbeddedSchema):
            with_default = fields.StrField(default='default_value')
            with_missing = fields.StrField(missing='missing_value')

        d = DataProxy(MySchema(), data={})
        assert d._data['with_default'] is missing
        assert d._data['with_missing'] is 'missing_value'
        assert d.get('with_default') == 'default_value'
        assert d.get('with_missing') == 'missing_value'
        assert d.to_mongo() == {'with_missing': 'missing_value'}
        assert d.dump() == {'with_default': 'default_value', 'with_missing': 'missing_value'}

    def test_validate(self):

        class MySchema(EmbeddedSchema):
            with_max = fields.IntField(validate=validate.Range(max=99))

        d = DataProxy(MySchema(), data={})
        with pytest.raises(ValidationError) as exc:
            DataProxy(MySchema(), data={'with_max': 100})
        assert exc.value.args[0] == {'with_max': ['Must be at most 99.']}
        with pytest.raises(ValidationError) as exc:
            d.set('with_max', 100)
        assert exc.value.args[0] == ['Must be at most 99.']

    def test_partial(self):

        class MySchema(EmbeddedSchema):
            with_default = fields.StrField(default='default_value')
            with_missing = fields.StrField(missing='missing_value')
            normal = fields.StrField()
            loaded = fields.StrField()
            loaded_but_empty = fields.StrField()

        d = DataProxy(MySchema())
        d.from_mongo({'loaded': "foo", 'loaded_but_empty': missing}, partial=True)
        assert d.partial is True
        for field in ('with_default', 'with_missing', 'normal'):
            with pytest.raises(exceptions.FieldNotLoadedError):
                d.get(field)
            with pytest.raises(exceptions.FieldNotLoadedError):
                d.set(field, "test")
            with pytest.raises(exceptions.FieldNotLoadedError):
                d.delete(field)
        assert d.get('loaded') == "foo"
        assert d.get('loaded_but_empty') is missing
        d.set('loaded_but_empty', "bar")
        assert d.get('loaded_but_empty') == "bar"
        d.delete('loaded')
        # Can still access the deleted field
        assert d.get('loaded') is missing

        # Same test, but using `load`
        d = DataProxy(MySchema())
        d.load({'loaded': "foo", 'loaded_but_empty': missing}, partial=True)
        assert d.partial is True
        for field in ('with_default', 'with_missing', 'normal'):
            with pytest.raises(exceptions.FieldNotLoadedError):
                d.get(field)
            with pytest.raises(exceptions.FieldNotLoadedError):
                d.set(field, "test")
            with pytest.raises(exceptions.FieldNotLoadedError):
                d.delete(field)
        assert d.get('loaded') == "foo"
        assert d.get('loaded_but_empty') is missing
        d.set('loaded_but_empty', "bar")
        assert d.get('loaded_but_empty') == "bar"
        d.delete('loaded')
        # Can still access the deleted field
        assert d.get('loaded') is missing

        # Not partial
        d = DataProxy(MySchema())
        d.from_mongo({'loaded': "foo", 'loaded_but_empty': missing})
        assert d.partial is False
        assert d.get('with_default') == 'default_value'
        assert d.get('with_missing') == 'missing_value'
        assert d.get('normal') is missing
        assert d.get('loaded') == "foo"
        assert d.get('loaded_but_empty') == missing
        # Same test with load
        d = DataProxy(MySchema())
        d.load({'loaded': "foo", 'loaded_but_empty': missing})
        assert d.partial is False
        assert d.partial is False
        assert d.get('with_default') == 'default_value'
        assert d.get('with_missing') == 'missing_value'
        assert d.get('normal') is missing
        assert d.get('loaded') == "foo"
        assert d.get('loaded_but_empty') == missing
