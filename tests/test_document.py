import pytest
from datetime import datetime
from bson import ObjectId, DBRef

from umongo import (Document, EmbeddedDocument, Schema, fields, exceptions,
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
            'birthday': '1995-12-12T00:00:00+00:00',
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
            '_id': 1, 'in_mongo__id': 2, 'in_mongo__id': 3, 'pk': 4
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


class TestConfig(BaseTest):

    def test_missing_schema(self):
        # No exceptions should occur

        @self.instance.register
        class Doc(Document):
            pass

        d = Doc()
        assert isinstance(d.schema, Schema)

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
            def dump_custom_cls_name(self, data):
                data['race'] = data.pop('cls')
                return data

            @pre_load
            def load_custom_cls_name(self, data):
                data.pop('race', None)
                return data

            @validates_schema(pass_original=True)
            def custom_validate(self, data, original_data):
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
