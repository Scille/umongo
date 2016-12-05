from marshmallow import ValidationError, missing
import pytest

from umongo.data_proxy import data_proxy_factory
from umongo import EmbeddedSchema, fields, EmbeddedDocument, validate, exceptions

from .common import BaseTest


class TestDataProxy(BaseTest):

    def test_repr(self):

        class MySchema(EmbeddedSchema):
            field_a = fields.IntField(attribute='mongo_field_a')
            field_b = fields.StrField()

        MyDataProxy = data_proxy_factory('My', MySchema())
        d = MyDataProxy({'field_a': 1, 'field_b': 'value'})
        assert MyDataProxy.__name__ == 'MyDataProxy'
        repr_d = repr(d)
        assert repr_d.startswith("<MyDataProxy(")
        assert "'field_a': 1" in repr_d
        assert "'field_b': 'value'" in repr_d

    def test_simple(self):

        class MySchema(EmbeddedSchema):
            a = fields.IntField()
            b = fields.IntField()

        MyDataProxy = data_proxy_factory('My', MySchema())
        d = MyDataProxy()
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

        MyDataProxy = data_proxy_factory('My', MySchema())
        d = MyDataProxy()
        d.from_mongo({'a': 1, 'in_mongo_b': 2})
        assert d.to_mongo() == {'a': 1, 'in_mongo_b': 2}

        d.set('a', 3)
        assert d.to_mongo(update=True) == {'$set': {'a': 3}}

        d.from_mongo({'a': 4, 'in_mongo_b': 5})
        assert d.to_mongo(update=True) is None
        assert d.to_mongo() == {'a': 4, 'in_mongo_b': 5}

        d2 = MyDataProxy(data={'a': 4, 'b': 5})
        assert d == d2

    def test_modify(self):

        class MySchema(EmbeddedSchema):
            a = fields.IntField()
            b = fields.IntField(attribute='in_mongo_b')

        MyDataProxy = data_proxy_factory('My', MySchema())
        d = MyDataProxy()
        assert d.get_modified_fields() == []
        d.load({'a': 1, 'b': 2})
        assert list(sorted(d.get_modified_fields())) == ['a', 'b']
        d.from_mongo({'a': 1, 'in_mongo_b': 2})
        assert d.get_modified_fields() == []
        assert d.to_mongo() == {'a': 1, 'in_mongo_b': 2}
        assert d.to_mongo(update=True) is None
        d.set('a', 3)
        d.delete('b')
        assert d.to_mongo(update=True) == {'$set': {'a': 3}, '$unset': {'in_mongo_b': ''}}
        d.clear_modified()
        assert d.get_modified_fields() == []
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

        MyDataProxy = data_proxy_factory('My', MySchema())
        d = MyDataProxy()
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
            c = fields.IntField(
                allow_none=True,
                validate=validate.Range(min=1, max=5)
            )

        MyDataProxy = data_proxy_factory('My', MySchema())
        d = MyDataProxy()
        d.from_mongo({'a': 1, 'in_mongo_b': 2})
        d.set('a', 3)
        assert d.to_mongo() == {'a': 3, 'in_mongo_b': 2}
        assert d.to_mongo(update=True) == {'$set': {'a': 3}}

        d.from_mongo({'a': 1, 'in_mongo_b': 2})
        d.set('b', 3)
        assert d.to_mongo() == {'a': 1, 'in_mongo_b': 3}
        assert d.to_mongo(update=True) == {'$set': {'in_mongo_b': 3}}

        with pytest.raises(KeyError):
            d.set('in_mongo_b', 2)

        d.from_mongo({})
        d.set('c', None)
        assert d.to_mongo() == {'c': None}
        with pytest.raises(ValidationError):
            d.set('c', 69)

    def test_del(self):

        class MySchema(EmbeddedSchema):
            a = fields.IntField()
            b = fields.IntField(attribute='in_mongo_b')

        MyDataProxy = data_proxy_factory('My', MySchema())
        d = MyDataProxy()
        d.from_mongo({'a': 1, 'in_mongo_b': 2})
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

        MyDataProxy = data_proxy_factory('My', MySchema())
        d = MyDataProxy()
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

        MyDataProxy = data_proxy_factory('My', MySchema())
        d = MyDataProxy()
        with pytest.raises(KeyError):
            d.from_mongo({'in_front': 42})
        d.from_mongo({'in_mongo': 42})
        assert d.get('in_front') == 42

    def test_equality(self):

        class MySchema(EmbeddedSchema):
            a = fields.IntField()
            b = fields.IntField(attribute='in_mongo_b')

        MyDataProxy = data_proxy_factory('My', MySchema())
        d1 = MyDataProxy()
        d1.load({'a': 1, 'b': 2})
        assert d1 == {'a': 1, 'in_mongo_b': 2}

        d2 = MyDataProxy()
        d2.load({'a': 1, 'b': 2})
        assert d1 == d2

    def test_share_ressources(self):

        class MySchema(EmbeddedSchema):
            a = fields.IntField()
            b = fields.IntField(attribute='in_mongo_b')

        MyDataProxy = data_proxy_factory('My', MySchema())
        d1 = MyDataProxy()
        d2 = MyDataProxy()
        for field in ('schema', '_fields', '_fields_from_mongo_key'):
            assert getattr(d1, field) is getattr(d2, field)
        d1.load({'a': 1})
        d2.load({'b': 2})
        assert d1 != d2

    def test_access_by_mongo_name(self):

        class MySchema(EmbeddedSchema):
            a = fields.IntField()
            b = fields.IntField(attribute='in_mongo_b')

        MyDataProxy = data_proxy_factory('My', MySchema())
        d = MyDataProxy()
        d.from_mongo({'a': 1, 'in_mongo_b': 2})
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

        MyDataProxy = data_proxy_factory('My', MySchema())
        d = MyDataProxy(data={'a': 1})
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

        MyDataProxy = data_proxy_factory('My', MySchema())
        d = MyDataProxy(data={})
        assert d._data['with_default'] is missing
        assert d._data['with_missing'] is 'missing_value'
        assert d.get('with_default') == 'default_value'
        assert d.get('with_missing') == 'missing_value'
        assert d.to_mongo() == {'with_missing': 'missing_value'}
        assert d.dump() == {'with_default': 'default_value', 'with_missing': 'missing_value'}

    def test_validate(self):

        class MySchema(EmbeddedSchema):
            with_max = fields.IntField(validate=validate.Range(max=99))

        MyDataProxy = data_proxy_factory('My', MySchema())
        d = MyDataProxy(data={})
        with pytest.raises(ValidationError) as exc:
            MyDataProxy(data={'with_max': 100})
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
            normal_with_attribute = fields.StrField(attribute='in_mongo_field')

        MyDataProxy = data_proxy_factory('My', MySchema())
        d = MyDataProxy()
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
        d = MyDataProxy()
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
        d = MyDataProxy()
        d.from_mongo({'loaded': "foo", 'loaded_but_empty': missing})
        assert d.partial is False
        assert d.get('with_default') == 'default_value'
        assert d.get('with_missing') == 'missing_value'
        assert d.get('normal') is missing
        assert d.get('loaded') == "foo"
        assert d.get('loaded_but_empty') == missing
        # Same test with load
        d = MyDataProxy()
        d.load({'loaded': "foo", 'loaded_but_empty': missing})
        assert d.partial is False
        assert d.partial is False
        assert d.get('with_default') == 'default_value'
        assert d.get('with_missing') == 'missing_value'
        assert d.get('normal') is missing
        assert d.get('loaded') == "foo"
        assert d.get('loaded_but_empty') == missing

        # Partial, then not partial
        d = MyDataProxy()
        d.from_mongo({'loaded': "foo", 'loaded_but_empty': missing}, partial=True)
        assert d.partial is True
        d.from_mongo({'loaded': "foo", 'loaded_but_empty': missing})
        assert d.partial is False
        # Same test with load
        d = MyDataProxy()
        d.load({'loaded': "foo", 'loaded_but_empty': missing}, partial=True)
        assert d.partial is True
        d.load({'loaded': "foo", 'loaded_but_empty': missing})
        assert d.partial is False

        # Partial, then update turns it into not partial
        d = MyDataProxy()
        d.from_mongo({'loaded': "foo", 'loaded_but_empty': missing}, partial=True)
        assert len(d.not_loaded_fields) == 4
        d.update({'with_default': 'test', 'with_missing': 'test', 'normal_with_attribute': 'foo'})
        assert len(d.not_loaded_fields) == 1
        assert d.partial is True
        d.update({'normal': 'test'})
        assert d.partial is False
        assert not d.not_loaded_fields

    def test_required_validate(self):

        @self.instance.register
        class MyEmbedded(EmbeddedDocument):
            required = fields.IntField(required=True)

        class MySchema(EmbeddedSchema):
            # EmbeddedField need instance to retrieve implementation
            listed = fields.ListField(fields.EmbeddedField(MyEmbedded, instance=self.instance))
            embedded = fields.EmbeddedField(MyEmbedded, instance=self.instance)
            required = fields.IntField(required=True)

        MyDataProxy = data_proxy_factory('My', MySchema())
        d = MyDataProxy()

        d.load({'embedded': {'required': 42}, 'required': 42, 'listed': [{'required': 42}]})
        d.required_validate()
        # Empty list should not trigger required it embedded field require check
        d.load({'embedded': {'required': 42}, 'required': 42})
        d.required_validate()

        d.load({'embedded': {'required': 42}})
        with pytest.raises(ValidationError) as exc:
            d.required_validate()
        assert exc.value.messages == {'required': ['Missing data for required field.']}

        # Missing embedded is valid even though some fields are required in the embedded document
        d.load({'required': 42})
        d.required_validate()
        # Required fields in the embedded document are only checked if the document is not missing
        d.load({'embedded': {}, 'required': 42})
        with pytest.raises(ValidationError) as exc:
            d.required_validate()
        assert exc.value.messages == {'embedded': {'required': ['Missing data for required field.']}}

        d.load({'embedded': {'required': 42}, 'required': 42, 'listed': [{}]})
        with pytest.raises(ValidationError) as exc:
            d.required_validate()
        assert exc.value.messages == {'listed': {0: {'required': ['Missing data for required field.']}}}
