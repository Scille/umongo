from copy import copy, deepcopy

import pytest

from marshmallow import ValidationError, missing

from umongo.data_proxy import data_proxy_factory
from umongo import Document, EmbeddedDocument, fields, exceptions

from .common import BaseTest


class TestEmbeddedDocument(BaseTest):

    def test_embedded_inheritance(self):
        @self.instance.register
        class MyChildEmbeddedDocument(EmbeddedDocument):
            num = fields.IntField()

        @self.instance.register
        class MyParentEmbeddedDocument(EmbeddedDocument):
            embedded = fields.EmbeddedField(MyChildEmbeddedDocument)

        @self.instance.register
        class MyDoc(Document):
            embedded = fields.EmbeddedField(MyParentEmbeddedDocument)

        document = MyDoc(**{
            "embedded": {"embedded": {"num": 1}}
        })

        assert document is not None

    def test_embedded_document(self):
        @self.instance.register
        class MyEmbeddedDocument(EmbeddedDocument):
            a = fields.IntField(attribute='in_mongo_a')
            b = fields.IntField()

        embedded = MyEmbeddedDocument()
        assert embedded.to_mongo(update=True) is None
        assert not embedded.is_modified()

        @self.instance.register
        class MyDoc(Document):
            embedded = fields.EmbeddedField(MyEmbeddedDocument,
                attribute='in_mongo_embedded', allow_none=True)

        MySchema = MyDoc.Schema

        # Make sure embedded document doesn't have implicit _id field
        assert '_id' not in MyEmbeddedDocument.Schema().fields
        assert 'id' not in MyEmbeddedDocument.Schema().fields

        MyDataProxy = data_proxy_factory('My', MySchema())
        d = MyDataProxy()
        d.from_mongo(data={'in_mongo_embedded': {'in_mongo_a': 1, 'b': 2}})
        assert d.dump() == {'embedded': {'a': 1, 'b': 2}}
        embedded = d.get('embedded')
        assert type(embedded) == MyEmbeddedDocument
        assert embedded.a == 1
        assert embedded.b == 2
        assert embedded.dump() == {'a': 1, 'b': 2}
        assert embedded.to_mongo() == {'in_mongo_a': 1, 'b': 2}
        assert d.to_mongo() == {'in_mongo_embedded': {'in_mongo_a': 1, 'b': 2}}

        d2 = MyDataProxy()
        d2.from_mongo(data={'in_mongo_embedded': {'in_mongo_a': 1, 'b': 2}})
        assert d == d2

        embedded.a = 3
        assert embedded.is_modified()
        assert embedded.to_mongo(update=True) == {'$set': {'in_mongo_a': 3}}
        assert d.to_mongo(update=True) == {'$set': {'in_mongo_embedded': {'in_mongo_a': 3, 'b': 2}}}
        embedded.clear_modified()
        assert embedded.to_mongo(update=True) is None
        assert d.to_mongo(update=True) is None

        del embedded.a
        assert embedded.to_mongo(update=True) == {'$unset': {'in_mongo_a': ''}}
        assert d.to_mongo(update=True) == {'$set': {'in_mongo_embedded': {'b': 2}}}

        d.set('embedded', MyEmbeddedDocument(a=4))
        assert d.get('embedded').to_mongo(update=True) == {'$set': {'in_mongo_a': 4}}
        d.get('embedded').clear_modified()
        assert d.get('embedded').to_mongo(update=True) is None
        assert d.to_mongo(update=True) == {'$set': {'in_mongo_embedded': {'in_mongo_a': 4}}}

        embedded_doc = MyEmbeddedDocument(a=1, b=2)
        assert embedded_doc.a == 1
        assert embedded_doc.b == 2
        assert embedded_doc == {'in_mongo_a': 1, 'b': 2}
        assert embedded_doc == MyEmbeddedDocument(a=1, b=2)
        assert embedded_doc['a'] == 1
        assert embedded_doc['b'] == 2

        embedded_doc.clear_modified()
        embedded_doc.update({'b': 42})
        assert embedded_doc.is_modified()
        assert embedded_doc.a == 1
        assert embedded_doc.b == 42

        with pytest.raises(ValidationError):
            MyEmbeddedDocument(in_mongo_a=1, b=2)

        embedded_doc['a'] = 1
        assert embedded_doc.a == embedded_doc['a'] == 1
        del embedded_doc['a']
        assert embedded_doc.a is embedded_doc['a'] is None

        # Test repr readability
        repr_d = repr(MyEmbeddedDocument(a=1, b=2))
        assert 'tests.test_embedded_document.MyEmbeddedDocument' in repr_d
        assert "'in_mongo_a'" not in repr_d
        assert "'a': 1" in repr_d
        assert "'b': 2" in repr_d

        # Test unknown fields
        with pytest.raises(AttributeError):
            embedded_doc.dummy
        with pytest.raises(AttributeError):
            embedded_doc.dummy = None
        with pytest.raises(AttributeError):
            del embedded_doc.dummy
        with pytest.raises(KeyError):
            embedded_doc['dummy']
        with pytest.raises(KeyError):
            embedded_doc['dummy'] = None
        with pytest.raises(KeyError):
            del embedded_doc['dummy']

        # Test allow_none
        d3 = MyDataProxy({'embedded': None})
        assert d3.to_mongo() == {'in_mongo_embedded': None}
        d3.from_mongo({'in_mongo_embedded': None})
        assert d3.get('embedded') is None

    def test_bad_embedded_document(self):

        @self.instance.register
        class MyEmbeddedDocument(EmbeddedDocument):
            a = fields.IntField()

        @self.instance.register
        class MyDoc(Document):
            e = fields.EmbeddedField(MyEmbeddedDocument)
            l = fields.ListField(fields.EmbeddedField(MyEmbeddedDocument))
            b = fields.IntField(required=True)

        with pytest.raises(ValidationError) as exc:
            MyDoc(l={})
        assert exc.value.args[0] == {'l': ['Not a valid list.']}

        with pytest.raises(ValidationError) as exc:
            MyDoc(l=True)
        assert exc.value.args[0] == {'l': ['Not a valid list.']}

        with pytest.raises(ValidationError) as exc:
            MyDoc(l="string is not a list")
        assert exc.value.args[0] == {'l': ['Not a valid list.']}

        with pytest.raises(ValidationError) as exc:
            MyDoc(l=[42])
        assert exc.value.args[0] == {'l': {0: {'_schema': ['Invalid input type.']}}}

        with pytest.raises(ValidationError) as exc:
            MyDoc(l=[{}, 42])
        assert exc.value.args[0] == {'l': {1: {'_schema': ['Invalid input type.']}}}

        with pytest.raises(ValidationError) as exc:
            MyDoc(b=[{}])
        assert exc.value.args[0] == {'b': ['Not a valid integer.']}

        with pytest.raises(ValidationError) as exc:
            MyDoc(e=[{}])
        assert exc.value.args[0] == {'e': {'_schema': ['Invalid input type.']}}

    def test_inheritance(self):
        @self.instance.register
        class EmbeddedParent(EmbeddedDocument):
            a = fields.IntField(attribute='in_mongo_a_parent')
            b = fields.IntField()

        @self.instance.register
        class EmbeddedChild(EmbeddedParent):
            a = fields.IntField(attribute='in_mongo_a_child')
            c = fields.IntField()

        @self.instance.register
        class GrandChild(EmbeddedChild):
            d = fields.IntField()

        @self.instance.register
        class OtherEmbedded(EmbeddedDocument):
            pass

        @self.instance.register
        class MyDoc(Document):
            parent = fields.EmbeddedField(EmbeddedParent)
            child = fields.EmbeddedField(EmbeddedChild)

        assert EmbeddedParent.opts.offspring == {EmbeddedChild, GrandChild}
        assert EmbeddedChild.opts.offspring == {GrandChild}
        assert GrandChild.opts.offspring == set()
        assert OtherEmbedded.opts.offspring == set()

        parent = EmbeddedParent(a=1)
        child = EmbeddedChild(a=1, b=2, c=3)
        grandchild = GrandChild(d=4)

        assert parent.to_mongo() == {'in_mongo_a_parent': 1}
        assert child.to_mongo() == {'in_mongo_a_child': 1, 'b': 2, 'c': 3, '_cls': 'EmbeddedChild'}
        assert grandchild.to_mongo() == {'d': 4, '_cls': 'GrandChild'}

        with pytest.raises(ValidationError) as exc:
            MyDoc(parent=OtherEmbedded())
        assert exc.value.args[0] == {'parent': {'_schema': ['Invalid input type.']}}
        with pytest.raises(ValidationError):
            MyDoc(child=parent)
        doc = MyDoc(parent=child, child=child)
        assert doc.child == doc.parent

        doc = MyDoc(child={'a': 1, 'cls': 'GrandChild'},
                    parent={'cls': 'EmbeddedChild', 'a': 1})
        assert doc.child.to_mongo() == {'in_mongo_a_child': 1, '_cls': 'GrandChild'}
        assert doc.parent.to_mongo() == {'in_mongo_a_child': 1, '_cls': 'EmbeddedChild'}

        with pytest.raises(ValidationError) as exc:
            MyDoc(child={'a': 1, '_cls': 'GrandChild'})
        assert exc.value.messages == {'child': {'_cls': ['Unknown field.']}}

        # Try to build a non-child document
        with pytest.raises(ValidationError) as exc:
            MyDoc(child={'cls': 'OtherEmbedded'})
        assert exc.value.messages == {'child': ['Unknown document `OtherEmbedded`.']}

        # Test embedded child deserialization from mongo
        child = EmbeddedChild(c=69)
        doc = MyDoc(parent=child)
        mongo_data = doc.to_mongo()
        doc2 = MyDoc.build_from_mongo(mongo_data)
        assert isinstance(doc2.parent, EmbeddedChild)
        assert doc._data == doc2._data

        # Test grandchild can be passed as parent
        doc = MyDoc(parent={'cls': 'GrandChild', 'd': 2})
        assert doc.parent.to_mongo() == {'d': 2, '_cls': 'GrandChild'}

    def test_abstract_inheritance(self):
        class AlienClass:
            pass

        @self.instance.register
        class AbstractParent(EmbeddedDocument):
            a = fields.IntField(attribute='in_mongo_a_parent')
            b = fields.IntField()

            class Meta:
                abstract = True

        @self.instance.register
        class AbstractChild(AbstractParent):
            a = fields.IntField(attribute='in_mongo_a_child')
            c = fields.IntField()

            class Meta:
                abstract = True

        @self.instance.register
        class ConcreteChild(AbstractParent, AlienClass):
            c = fields.IntField()

            class Meta:
                allow_inheritance = True

        @self.instance.register
        class ConcreteGrandChild(AbstractChild):
            d = fields.IntField()

        @self.instance.register
        class ConcreteConcreteGrandChild(ConcreteChild):
            d = fields.IntField()

        @self.instance.register
        class OtherEmbedded(EmbeddedDocument):
            pass

        with pytest.raises(exceptions.AbstractDocumentError) as exc:
            AbstractParent()
        assert exc.value.args[0] == "Cannot instantiate an abstract EmbeddedDocument"

        # test
        cc = ConcreteChild(a=1, b=2, c=3)
        cgc = ConcreteGrandChild(a=1, b=2, c=3, d=4)
        ccgc = ConcreteConcreteGrandChild(a=1, b=2, c=3, d=4)

        assert cc.to_mongo() == {'in_mongo_a_parent': 1, 'b': 2, 'c': 3, '_cls': 'ConcreteChild'}
        assert cgc.to_mongo() == {'in_mongo_a_child': 1, 'b': 2, 'c': 3, 'd': 4, '_cls': 'ConcreteGrandChild'}
        assert ccgc.to_mongo() == {'in_mongo_a_parent': 1, 'b': 2, 'c': 3, 'd': 4, '_cls': 'ConcreteConcreteGrandChild'}

    def test_bad_inheritance(self):
        with pytest.raises(exceptions.DocumentDefinitionError) as exc:
            @self.instance.register
            class BadAbstract(EmbeddedDocument):
                class Meta:
                    allow_inheritance = False
                    abstract = True
        assert exc.value.args[0] == "Abstract embedded document cannot disable inheritance"

        @self.instance.register
        class NotParent(EmbeddedDocument):
            class Meta:
                allow_inheritance = False

        with pytest.raises(exceptions.DocumentDefinitionError) as exc:
            @self.instance.register
            class ImpossibleChild1(NotParent):
                pass
        assert exc.value.args[0] == ("EmbeddedDocument"
            " <Implementation class 'tests.test_embedded_document.NotParent'>"
            " doesn't allow inheritance")

        @self.instance.register
        class NotAbstractParent(EmbeddedDocument):
            class Meta:
                allow_inheritance = True

        # Unlike Document, EmbeddedDocument should allow inheritance by default
        assert NotAbstractParent.opts.allow_inheritance

        with pytest.raises(exceptions.DocumentDefinitionError) as exc:
            @self.instance.register
            class ImpossibleChild2(NotAbstractParent):
                class Meta:
                    abstract = True
        assert exc.value.args[0] == "Abstract embedded document should have all it parents abstract"

    def test_property(self):
        @self.instance.register
        class MyEmbeddedDoc(EmbeddedDocument):
            _prop = fields.FloatField()

            @property
            def prop(self):
                return self._prop

            @prop.setter
            def prop(self, value):
                self._prop = value

            @prop.deleter
            def prop(self):
                del self._prop

        emb = MyEmbeddedDoc()
        emb.prop = 42
        assert emb.prop == 42
        del emb.prop
        assert emb.prop is None

    def test_equality(self):
        @self.instance.register
        class MyChildEmbeddedDocument(EmbeddedDocument):
            num = fields.IntField()

        @self.instance.register
        class MyParentEmbeddedDocument(EmbeddedDocument):
            embedded = fields.EmbeddedField(MyChildEmbeddedDocument)

        emb_1 = MyParentEmbeddedDocument(embedded={'num': 1})
        emb_2 = MyParentEmbeddedDocument(embedded={'num': 1})
        emb_3 = MyParentEmbeddedDocument(embedded={})
        emb_4 = MyParentEmbeddedDocument()

        assert emb_1 == emb_2
        assert emb_1 != emb_3
        assert emb_1 != emb_4
        assert emb_1 != None  # noqa: E711 (None comparison)
        assert emb_1 != missing
        assert None != emb_1  # noqa: E711 (None comparison)
        assert missing != emb_1

    def test_strict_embedded_document(self):
        @self.instance.register
        class StrictEmbeddedDoc(EmbeddedDocument):
            a = fields.IntField()

        @self.instance.register
        class NonStrictEmbeddedDoc(EmbeddedDocument):
            a = fields.IntField()

            class Meta:
                strict = False

        data_with_bonus = {'a': 42, 'b': 'foo'}
        with pytest.raises(exceptions.UnknownFieldInDBError):
            StrictEmbeddedDoc.build_from_mongo(data_with_bonus)

        non_strict_doc = NonStrictEmbeddedDoc.build_from_mongo(data_with_bonus)
        assert non_strict_doc.to_mongo() == data_with_bonus
        non_strict_doc.dump() == {'a': 42}

        with pytest.raises(exceptions.ValidationError) as exc:
            NonStrictEmbeddedDoc(a=42, b='foo')
        assert exc.value.messages == {'b': ['Unknown field.']}

    def test_deepcopy(self):

        @self.instance.register
        class Child(EmbeddedDocument):
            name = fields.StrField()

        @self.instance.register
        class Parent(EmbeddedDocument):
            name = fields.StrField()
            child = fields.EmbeddedField(Child)

        john = Parent(name='John Doe', child={'name': 'John Doe Jr.'})
        jane = copy(john)
        assert jane.name == john.name
        assert jane.child is john.child
        jane = deepcopy(john)
        assert jane.name == john.name
        assert jane.child == john.child
        assert jane.child is not john.child
