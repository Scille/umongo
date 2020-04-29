from copy import copy, deepcopy
from datetime import datetime

import pytest

from bson import ObjectId, DBRef

from umongo import (Document, EmbeddedDocument, BaseSchema, fields, exceptions,
                    post_dump, pre_load, validates_schema)

from .common import BaseTest


class BaseStudent(Document):
    name = fields.StrField(required=True)
    birthday = fields.DateTimeField()
    gpa = fields.FloatField()

    class Meta:
        abstract = True


class Student(BaseStudent):
    pass


class EasyIdStudent(BaseStudent):
    id = fields.IntField(attribute='_id')

    class Meta:
        collection_name = 'student'


class TestDocument(BaseTest):

    def setup(self):
        super().setup()
        self.instance.register(BaseStudent)
        self.Student = self.instance.register(Student)
        self.EasyIdStudent = self.instance.register(EasyIdStudent)

    def test_repr(self):
        # I love readable stuff !
        john = self.Student(name='John Doe', birthday=datetime(1995, 12, 12), gpa=3.0)
        assert 'tests.test_document.Student' in repr(john)
        assert 'name' in repr(john)
        assert 'birthday' in repr(john)
        assert 'gpa' in repr(john)

    def test_create(self):
        john = self.Student(name='John Doe', birthday=datetime(1995, 12, 12), gpa=3.0)
        assert john.to_mongo() == {
            'name': 'John Doe',
            'birthday': datetime(1995, 12, 12),
            'gpa': 3.0
        }
        assert john.is_created is False
        with pytest.raises(exceptions.NotCreatedError):
            john.to_mongo(update=True)

    def test_from_mongo(self):
        john = self.Student.build_from_mongo(data={
            'name': 'John Doe', 'birthday': datetime(1995, 12, 12), 'gpa': 3.0})
        assert john.to_mongo(update=True) is None
        assert john.is_created is True
        assert john.to_mongo() == {
            'name': 'John Doe',
            'birthday': datetime(1995, 12, 12),
            'gpa': 3.0
        }

    def test_update(self):
        john = self.Student.build_from_mongo(data={
            'name': 'John Doe', 'birthday': datetime(1995, 12, 12), 'gpa': 3.0})
        john.name = 'William Doe'
        john.birthday = datetime(1996, 12, 12)
        assert john.to_mongo(update=True) == {
            '$set': {'name': 'William Doe', 'birthday': datetime(1996, 12, 12)}}
        john.clear_modified()
        assert john.to_mongo(update=True) is None

    def test_dump(self):
        john = self.Student.build_from_mongo(data={
            'name': 'John Doe', 'birthday': datetime(1995, 12, 12), 'gpa': 3.0})
        assert john.dump() == {
            'name': 'John Doe',
            'birthday': '1995-12-12T00:00:00',
            'gpa': 3.0
        }

    def test_fields_by_attr(self):
        john = self.Student.build_from_mongo(data={
            'name': 'John Doe', 'birthday': datetime(1995, 12, 12), 'gpa': 3.0})
        assert john.name == 'John Doe'
        john.name = 'William Doe'
        assert john.name == 'William Doe'
        del john.name
        assert john.name is None
        with pytest.raises(AttributeError):
            john.missing
        with pytest.raises(AttributeError):
            john.missing = None
        with pytest.raises(AttributeError):
            del john.missing
        with pytest.raises(AttributeError):
            del john.commit

    def test_fields_by_items(self):
        john = self.Student.build_from_mongo(data={
            'name': 'John Doe', 'birthday': datetime(1995, 12, 12), 'gpa': 3.0})
        assert john['name'] == 'John Doe'
        john['name'] = 'William Doe'
        assert john['name'] == 'William Doe'
        del john['name']
        assert john['name'] is None
        with pytest.raises(KeyError):
            john['missing']
        with pytest.raises(KeyError):
            john['missing'] = None
        with pytest.raises(KeyError):
            del john['missing']

    def test_property(self):
        @self.instance.register
        class HeavyStudent(BaseStudent):
            _weight = fields.FloatField()

            @property
            def weight(self):
                return self._weight

            @weight.setter
            def weight(self, value):
                self._weight = value

            @weight.deleter
            def weight(self):
                del self._weight

        john = HeavyStudent()
        john.weight = 42
        assert john.weight == 42
        del john.weight
        assert john.weight is None

    def test_pk(self):
        john = self.Student.build_from_mongo(data={
            'name': 'John Doe', 'birthday': datetime(1995, 12, 12), 'gpa': 3.0})
        assert john.pk is None
        john_id = ObjectId("5672d47b1d41c88dcd37ef05")
        john = self.Student.build_from_mongo(data={
            '_id': john_id, 'name': 'John Doe',
            'birthday': datetime(1995, 12, 12), 'gpa': 3.0})
        assert john.pk == john_id

        # Don't do that in real life !
        @self.instance.register
        class CrazyNaming(Document):
            id = fields.IntField(attribute='in_mongo_id')
            _id = fields.IntField(attribute='in_mongo__id')
            pk = fields.IntField()
            real_pk = fields.IntField(attribute='_id')

        crazy = CrazyNaming.build_from_mongo(data={
            '_id': 1, 'in_mongo_id': 2, 'in_mongo__id': 3, 'pk': 4
        })
        assert crazy.pk == crazy.real_pk == 1
        assert crazy['pk'] == 4

    def test_dbref(self):
        student = self.Student()
        with pytest.raises(exceptions.NotCreatedError):
            student.dbref
        # Fake document creation
        student.id = ObjectId('573b352e13adf20d13d01523')
        student.is_created = True
        student.clear_modified()
        assert student.dbref == DBRef(collection='student',
                                      id=ObjectId('573b352e13adf20d13d01523'))

    def test_equality(self):
        john_data = {
            '_id': 42, 'name': 'John Doe', 'birthday': datetime(1995, 12, 12), 'gpa': 3.0
        }
        john = self.EasyIdStudent.build_from_mongo(data=john_data)
        john2 = self.EasyIdStudent.build_from_mongo(data=john_data)
        phillipe = self.EasyIdStudent.build_from_mongo(data={
            '_id': 3, 'name': 'Phillipe J. Fry', 'birthday': datetime(1995, 12, 12), 'gpa': 3.0})

        assert john != phillipe
        assert john2 == john
        assert john == DBRef(collection='student', id=john.pk)

        john.name = 'William Doe'
        assert john == john2

        newbie = self.EasyIdStudent(name='Newbie')
        newbie2 = self.EasyIdStudent(name='Newbie')
        assert newbie != newbie2

    def test_required_fields(self):
        # Should be able to instanciate document without their required fields
        student = self.Student()
        with pytest.raises(exceptions.ValidationError):
            student.required_validate()

        student = self.Student(gpa=2.8)
        with pytest.raises(exceptions.ValidationError):
            student.required_validate()

        student = self.Student(gpa=2.8, name='Marty')
        student.required_validate()

    def test_auto_id_field(self):
        my_id = ObjectId('5672d47b1d41c88dcd37ef05')

        @self.instance.register
        class AutoId(Document):

            class Meta:
                allow_inheritance = True

        assert 'id' in AutoId.schema.fields

        # default id field is only dumpable
        with pytest.raises(exceptions.ValidationError):
            AutoId(id=my_id)

        autoid = AutoId.build_from_mongo({'_id': my_id})
        assert autoid.id == my_id
        assert autoid.pk == autoid.id
        assert autoid.dump() == {'id': '5672d47b1d41c88dcd37ef05'}

        @self.instance.register
        class AutoIdInheritance(AutoId):
            pass

        assert 'id' in AutoIdInheritance.schema.fields

    def test_custom_id_field(self):
        my_id = ObjectId('5672d47b1d41c88dcd37ef05')

        @self.instance.register
        class CustomId(Document):
            int_id = fields.IntField(attribute='_id')

            class Meta:
                allow_inheritance = True

        assert 'id' not in CustomId.schema.fields
        with pytest.raises(exceptions.ValidationError):
            CustomId(id=my_id)
        customid = CustomId(int_id=42)
        with pytest.raises(exceptions.ValidationError):
            customid.int_id = my_id
        assert customid.int_id == 42
        assert customid.pk == customid.int_id
        assert customid.to_mongo() == {'_id': 42}

        @self.instance.register
        class CustomIdInheritance(CustomId):
            pass

        assert 'id' not in CustomIdInheritance.schema.fields

    def test_is_modified(self):

        @self.instance.register
        class Vehicle(EmbeddedDocument):
            name = fields.StrField()

        @self.instance.register
        class Driver(Document):
            name = fields.StrField()
            vehicle = fields.EmbeddedField(Vehicle)

        driver = Driver()
        assert driver.is_modified()
        driver.is_created = True
        assert not driver.is_modified()

        driver = Driver(name='Marty')
        assert driver.is_modified()
        driver.clear_modified()
        assert driver.is_modified()
        driver.is_created = True
        assert not driver.is_modified()
        driver.name = 'Marty McFly'
        assert driver.is_modified()
        driver.clear_modified()
        assert not driver.is_modified()
        vehicle = Vehicle(name='Hoverboard')
        assert vehicle.is_modified()
        vehicle.clear_modified()
        assert not vehicle.is_modified()
        driver.vehicle = vehicle
        assert driver.is_modified()
        driver.clear_modified()
        assert not driver.is_modified()
        vehicle.name = 'DeLorean DMC-12'
        assert vehicle.is_modified()
        assert driver.is_modified()
        driver.clear_modified()
        assert not vehicle.is_modified()
        assert not driver.is_modified()

    def test_inheritance_from_template(self):
        # It is legal (and equivalent) to make a child inherit from
        # a template instead of from an implementation

        class ParentAsTemplate(Document):
            class Meta:
                allow_inheritance = True

        Parent = self.instance.register(ParentAsTemplate)

        assert Parent.opts.template is ParentAsTemplate

        @self.instance.register
        class Child(ParentAsTemplate):
            pass

    def test_grand_child_inheritance(self):
        @self.instance.register
        class GrandParent(Document):
            class Meta:
                allow_inheritance = True

        @self.instance.register
        class Parent(GrandParent):
            class Meta:
                allow_inheritance = True

        @self.instance.register
        class Uncle(GrandParent):
            class Meta:
                allow_inheritance = True

        @self.instance.register
        class Child(Parent):
            pass

        @self.instance.register
        class Cousin(Uncle):
            pass

        assert GrandParent.opts.offspring == {Parent, Uncle, Child, Cousin}
        assert Parent.opts.offspring == {Child}
        assert Uncle.opts.offspring == {Cousin}
        assert Child.opts.offspring == set()
        assert Cousin.opts.offspring == set()

    def test_instanciate_template(self):

        class Doc(Document):
            pass

        with pytest.raises(NotImplementedError):
            Doc()

    def test_deepcopy(self):

        @self.instance.register
        class Child(EmbeddedDocument):
            name = fields.StrField()

        @self.instance.register
        class Parent(Document):
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

    def test_clone(self):

        @self.instance.register
        class Child(EmbeddedDocument):
            name = fields.StrField()

        @self.instance.register
        class Parent(Document):
            name = fields.StrField()
            birthday = fields.DateTimeField(dump_only=True)
            child = fields.EmbeddedField(Child)

        john = Parent(name='John Doe', child={'name': 'John Jr.'})
        john.birthday = datetime(1995, 12, 12)
        john.id = ObjectId("5672d47b1d41c88dcd37ef05")
        jane = john.clone()
        assert isinstance(jane, Parent)
        assert isinstance(jane.child, Child)
        assert jane.id is None
        assert jane.birthday == datetime(1995, 12, 12)
        assert jane.name == 'John Doe'
        assert jane.child == john.child
        assert jane.child is not john.child

    def test_clone_default_id(self):
        """Check clone gets a new default id if defaut is provided"""

        @self.instance.register
        class Parent(Document):
            id = fields.ObjectIdField(attribute='_id', default=ObjectId)
            name = fields.StrField()

        john = Parent(name='John Doe')
        jane = john.clone()
        assert isinstance(jane, Parent)
        assert isinstance(john.id, ObjectId)
        assert isinstance(jane.id, ObjectId)
        assert jane.id != john.id
        assert jane.name == 'John Doe'

    def test_modify_pk_field(self):

        @self.instance.register
        class User(Document):
            primary_key = fields.ObjectIdField(attribute='_id', default=ObjectId)
            name = fields.StrField()

        john = User()
        john.primary_key = ObjectId()
        john.from_mongo({'name': 'John Doc'})
        assert john.is_created
        with pytest.raises(exceptions.AlreadyCreatedError):
            john.primary_key = ObjectId()
        with pytest.raises(exceptions.AlreadyCreatedError):
            john['primary_key'] = ObjectId()
        with pytest.raises(exceptions.AlreadyCreatedError):
            del john.primary_key
        with pytest.raises(exceptions.AlreadyCreatedError):
            del john['primary_key']
        with pytest.raises(exceptions.AlreadyCreatedError):
            john.update({'primary_key': ObjectId()})


class TestConfig(BaseTest):

    def test_missing_schema(self):
        # No exceptions should occur

        @self.instance.register
        class Doc(Document):
            pass

        d = Doc()
        assert isinstance(d.schema, BaseSchema)

    def test_base_config(self):

        @self.instance.register
        class Doc(Document):
            pass

        assert Doc.opts.collection_name == 'doc'
        assert Doc.opts.abstract is False
        assert Doc.opts.allow_inheritance is False
        assert Doc.opts.instance is self.instance
        assert Doc.opts.is_child is False
        assert Doc.opts.indexes == []
        assert Doc.opts.offspring == set()

    def test_inheritance(self):

        @self.instance.register
        class AbsDoc(Document):

            class Meta:
                abstract = True

        @self.instance.register
        class DocChild1(AbsDoc):

            class Meta:
                allow_inheritance = True
                collection_name = 'col1'

        @self.instance.register
        class DocChild1Child(DocChild1):
            pass

        @self.instance.register
        class DocChild2(AbsDoc):

            class Meta:
                collection_name = 'col2'

        assert DocChild1.opts.collection_name is 'col1'
        assert DocChild1Child.opts.collection_name is 'col1'
        assert DocChild1Child.opts.allow_inheritance is False
        assert DocChild2.opts.collection_name == 'col2'

    def test_marshmallow_tags_build(self):

        @self.instance.register
        class Animal(Document):
            name = fields.StringField()

            @pre_load
            def test(self, data, **kwargs):
                return data

        Animal(name='Scruffy')

    def test_marshmallow_tags(self):

        @self.instance.register
        class Animal(Document):
            name = fields.StrField(attribute='_id')  # Overwrite automatic pk

            class Meta:
                allow_inheritance = True

        @self.instance.register
        class Dog(Animal):
            pass

        @self.instance.register
        class Duck(Animal):
            @post_dump
            def dump_custom_cls_name(self, data, **kwargs):
                data['race'] = data.pop('cls')
                return data

            @pre_load
            def load_custom_cls_name(self, data, **kwargs):
                data.pop('race', None)
                return data

            @validates_schema(pass_original=True)
            def custom_validate(self, data, original_data, **kwargs):
                if original_data['name'] != 'Donald':
                    raise exceptions.ValidationError('Not suitable name for duck !', 'name')

        duck = Duck(name='Donald')
        dog = Dog(name='Pluto')
        assert 'load_custom_cls_name' not in dir(Duck)
        assert 'dump_custom_cls_name' not in dir(Duck)
        assert duck.dump() == {'name': 'Donald', 'race': 'Duck'}
        assert dog.dump() == {'name': 'Pluto', 'cls': 'Dog'}
        assert Duck(name='Donald', race='Duck')._data == duck._data

        with pytest.raises(exceptions.ValidationError) as exc:
            Duck(name='Roger')
        exc.value.args[0] == {'name': 'Not suitable name for duck !'}

    def test_bad_inheritance(self):
        with pytest.raises(exceptions.DocumentDefinitionError) as exc:
            @self.instance.register
            class BadAbstractDoc(Document):
                class Meta:
                    allow_inheritance = False
                    abstract = True
        assert exc.value.args[0] == "Abstract document cannot disable inheritance"

        @self.instance.register
        class NotParent(Document):
            pass

        assert not NotParent.opts.allow_inheritance

        with pytest.raises(exceptions.DocumentDefinitionError) as exc:
            @self.instance.register
            class ImpossibleChildDoc1(NotParent):
                pass
        assert exc.value.args[0] == ("Document"
            " <Implementation class 'tests.test_document.NotParent'>"
            " doesn't allow inheritance")

        @self.instance.register
        class NotAbstractParent(Document):
            class Meta:
                allow_inheritance = True

        with pytest.raises(exceptions.DocumentDefinitionError) as exc:
            @self.instance.register
            class ImpossibleChildDoc2(NotAbstractParent):
                class Meta:
                    abstract = True
        assert exc.value.args[0] == "Abstract document should have all it parents abstract"

        @self.instance.register
        class ParentWithCol1(Document):
            class Meta:
                allow_inheritance = True
                collection_name = 'col1'

        @self.instance.register
        class ParentWithCol2(Document):
            class Meta:
                allow_inheritance = True
                collection_name = 'col2'

        with pytest.raises(exceptions.DocumentDefinitionError) as exc:
            @self.instance.register
            class ImpossibleChildDoc3(ParentWithCol1):
                class Meta:
                    collection_name = 'col42'
        assert exc.value.args[0].startswith(
            "Cannot redefine collection_name in a child, use abstract instead")

        with pytest.raises(exceptions.DocumentDefinitionError) as exc:
            @self.instance.register
            class ImpossibleChildDoc4(ParentWithCol1, ParentWithCol2):
                pass
        assert exc.value.args[0].startswith(
            "Cannot redefine collection_name in a child, use abstract instead")

    def test_strict_document(self):
        @self.instance.register
        class StrictDoc(Document):
            a = fields.IntField()

        @self.instance.register
        class NonStrictDoc(Document):
            a = fields.IntField()

            class Meta:
                strict = False

        data_with_bonus = {'a': 42, 'b': 'foo'}
        with pytest.raises(exceptions.UnknownFieldInDBError):
            StrictDoc.build_from_mongo(data_with_bonus)

        non_strict_doc = NonStrictDoc.build_from_mongo(data_with_bonus)
        assert non_strict_doc.to_mongo() == data_with_bonus
        non_strict_doc.dump() == {'a': 42}

        with pytest.raises(exceptions.ValidationError) as exc:
            NonStrictDoc(a=42, b='foo')
        assert exc.value.messages == {'b': ['Unknown field.']}
