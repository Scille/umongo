import pytest
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient

from ..common import BaseDBTest, get_pymongo_version, TEST_DB
from ..fixtures import classroom_model, instance

from umongo import (Document, EmbeddedDocument, fields, exceptions, Reference,
                    Instance, PyMongoInstance, NoDBDefinedError)


# Check if the required dependancies are met to run this driver's tests
major, minor, _ = get_pymongo_version()
if int(major) != 3 or int(minor) < 2:
    dep_error = "pymongo driver requires pymongo>=3.2.0"
else:
    dep_error = ''

if not dep_error:  # Make sure the module is valid by importing it
    from umongo.frameworks import pymongo as framework_pymongo


# Helper to sort indexes by name in order to have deterministic comparison
def name_sorted(indexes):
    return sorted(indexes, key=lambda x: x['name'])


@pytest.fixture
def db():
    return MongoClient()[TEST_DB]


@pytest.mark.skipif(dep_error is not None, reason=dep_error)
class TestPymongo(BaseDBTest):

    def test_auto_instance(self, db):
        instance = Instance(db)

        class Doc(Document):
            pass

        doc_impl_cls = instance.register(Doc)
        assert doc_impl_cls.collection == db['doc']
        assert issubclass(doc_impl_cls, framework_pymongo.PyMongoDocument)

    def test_lazy_loader_instance(self, db):
        instance = PyMongoInstance()

        class Doc(Document):
            pass

        doc_impl_cls = instance.register(Doc)
        assert issubclass(doc_impl_cls, framework_pymongo.PyMongoDocument)
        with pytest.raises(NoDBDefinedError):
            doc_impl_cls.collection
        instance.init(db)
        assert doc_impl_cls.collection == db['doc']

    def test_create(self, classroom_model):
        Student = classroom_model.Student
        john = Student(name='John Doe', birthday=datetime(1995, 12, 12))
        john.commit()
        assert john.to_mongo() == {
            '_id': john.id,
            'name': 'John Doe',
            'birthday': datetime(1995, 12, 12)
        }
        john2 = Student.find_one(john.id)
        assert john2._data == john._data

    def test_update(self, classroom_model):
        Student = classroom_model.Student
        john = Student(name='John Doe', birthday=datetime(1995, 12, 12))
        john.commit()
        john.name = 'William Doe'
        assert john.to_mongo(update=True) == {'$set': {'name': 'William Doe'}}
        john.commit()
        assert john.to_mongo(update=True) is None
        john2 = Student.find_one(john.id)
        assert john2._data == john._data
        # Update without changing anything
        john.name = john.name
        john.commit()
        # Test conditional commit
        john.name = 'Zorro Doe'
        with pytest.raises(exceptions.UpdateError):
            john.commit(conditions={'name': 'Bad Name'})
        john.commit(conditions={'name': 'William Doe'})
        john.reload()
        assert john.name == 'Zorro Doe'
        # Cannot use conditions when creating document
        with pytest.raises(RuntimeError):
            Student(name='Joe').commit(conditions={'name': 'dummy'})

    def test_delete(self, classroom_model):
        Student = classroom_model.Student
        Student.collection.drop()
        john = Student(name='John Doe', birthday=datetime(1995, 12, 12))
        with pytest.raises(exceptions.NotCreatedError):
            john.delete()
        john.commit()
        assert Student.collection.find().count() == 1
        john.delete()
        assert not john.is_created
        assert Student.collection.find().count() == 0
        with pytest.raises(exceptions.NotCreatedError):
            john.delete()
        # Can re-commit the document in database
        john.commit()
        assert john.is_created
        assert Student.collection.find().count() == 1
        # Finally try to delete a doc no longer in database
        Student.find_one(john.id).delete()
        with pytest.raises(exceptions.DeleteError):
            john.delete()

    def test_reload(self, classroom_model):
        Student = classroom_model.Student
        Student(name='Other dude').commit()
        john = Student(name='John Doe', birthday=datetime(1995, 12, 12))
        with pytest.raises(exceptions.NotCreatedError):
            john.reload()
        john.commit()
        john2 = Student.find_one(john.id)
        john2.name = 'William Doe'
        john2.commit()
        john.reload()
        assert john.name == 'William Doe'

    def test_cursor(self, classroom_model):
        Student = classroom_model.Student
        Student.collection.drop()
        for i in range(10):
            Student(name='student-%s' % i).commit()
        cursor = Student.find(limit=5, skip=6)
        assert cursor.count() == 10
        assert cursor.count(with_limit_and_skip=True) == 4
        names = []
        for elem in cursor:
            assert isinstance(elem, Student)
            names.append(elem.name)
        assert sorted(names) == ['student-%s' % i for i in range(6, 10)]

        cursor = Student.find(limit=5, skip=6)
        assert isinstance(cursor[0], Student)

        # Make sure this kind of notation doesn't create new cursor
        cursor = Student.find()
        cursor_limit = cursor.limit(5)
        cursor_skip = cursor.skip(6)
        assert cursor is cursor_limit is cursor_skip

    def test_classroom(self, classroom_model):
        student = classroom_model.Student(name='Marty McFly', birthday=datetime(1968, 6, 9))
        student.commit()
        teacher = classroom_model.Teacher(name='M. Strickland')
        teacher.commit()
        course = classroom_model.Course(name='Overboard 101', teacher=teacher)
        course.commit()
        assert student.courses == []
        student.courses.append(course)
        student.commit()
        assert student.to_mongo() == {
            '_id': student.pk,
            'name': 'Marty McFly',
            'birthday': datetime(1968, 6, 9),
            'courses': [course.pk]
        }

    def test_reference(self, classroom_model):
        teacher = classroom_model.Teacher(name='M. Strickland')
        teacher.commit()
        course = classroom_model.Course(name='Overboard 101', teacher=teacher)
        course.commit()
        assert isinstance(course.teacher, Reference)
        teacher_fetched = course.teacher.fetch()
        assert teacher_fetched == teacher
        # Test bad ref as well
        course.teacher = Reference(classroom_model.Teacher, ObjectId())
        with pytest.raises(exceptions.ValidationError) as exc:
            course.io_validate()
        assert exc.value.messages == {'teacher': ['Reference not found for document Teacher.']}

    def test_required(self, classroom_model):
        Student = classroom_model.Student
        student = Student(birthday=datetime(1968, 6, 9))

        with pytest.raises(exceptions.ValidationError):
            student.io_validate()

        with pytest.raises(exceptions.ValidationError):
            student.commit()

        student.name = 'Marty'
        student.commit()
        # TODO ?
        # with pytest.raises(exceptions.ValidationError):
        #     Student.build_from_mongo({})

    def test_io_validate(self, instance, classroom_model):
        Student = classroom_model.Student

        io_field_value = 'io?'
        io_validate_called = False

        def io_validate(field, value):
            assert field == IOStudent.schema.fields['io_field']
            assert value == io_field_value
            nonlocal io_validate_called
            io_validate_called = True

        @instance.register
        class IOStudent(Student):
            io_field = fields.StrField(io_validate=io_validate)

        student = IOStudent(name='Marty', io_field=io_field_value)
        assert not io_validate_called

        student.io_validate()
        assert io_validate_called

    def test_io_validate_error(self, instance, classroom_model):
        Student = classroom_model.Student

        def io_validate(field, value):
            raise exceptions.ValidationError('Ho boys !')

        @instance.register
        class IOStudent(Student):
            io_field = fields.StrField(io_validate=io_validate)

        student = IOStudent(name='Marty', io_field='io?')
        with pytest.raises(exceptions.ValidationError) as exc:
            student.io_validate()
        assert exc.value.messages == {'io_field': ['Ho boys !']}

    def test_io_validate_multi_validate(self, instance, classroom_model):
        Student = classroom_model.Student
        called = []

        def io_validate1(field, value):
            called.append('io_validate1')

        def io_validate2(field, value):
            called.append('io_validate2')

        @instance.register
        class IOStudent(Student):
            io_field = fields.StrField(io_validate=(io_validate1, io_validate2))

        student = IOStudent(name='Marty', io_field='io?')
        student.io_validate()
        assert called == ['io_validate1', 'io_validate2']

    def test_io_validate_list(self, instance, classroom_model):
        Student = classroom_model.Student
        called = []
        values = [1, 2, 3, 4]

        def io_validate(field, value):
            called.append(value)

        @instance.register
        class IOStudent(Student):
            io_field = fields.ListField(fields.IntField(io_validate=io_validate))

        student = IOStudent(name='Marty', io_field=values)
        student.io_validate()
        assert called == values

    def test_indexes(self, instance):

        @instance.register
        class SimpleIndexDoc(Document):
            indexed = fields.StrField()
            no_indexed = fields.IntField()

            class Meta:
                collection_name = 'simple_index_doc'
                indexes = ['indexed']

        SimpleIndexDoc.collection.drop_indexes()

        # Now ask for indexes building
        SimpleIndexDoc.ensure_indexes()
        indexes = [e for e in SimpleIndexDoc.collection.list_indexes()]
        expected_indexes = [
            {
                'key': {'_id': 1},
                'name': '_id_',
                'ns': '%s.simple_index_doc' % TEST_DB,
                'v': 1
            },
            {
                'v': 1,
                'key': {'indexed': 1},
                'name': 'indexed_1',
                'ns': '%s.simple_index_doc' % TEST_DB
            }
        ]
        assert indexes == expected_indexes

        # Redoing indexes building should do nothing
        SimpleIndexDoc.ensure_indexes()
        assert indexes == expected_indexes

    def test_indexes_inheritance(self, instance):

        @instance.register
        class SimpleIndexDoc(Document):
            indexed = fields.StrField()
            no_indexed = fields.IntField()

            class Meta:
                indexes = ['indexed']

        SimpleIndexDoc.collection.drop_indexes()

        # Now ask for indexes building
        SimpleIndexDoc.ensure_indexes()
        indexes = [e for e in SimpleIndexDoc.collection.list_indexes()]
        expected_indexes = [
            {
                'key': {'_id': 1},
                'name': '_id_',
                'ns': '%s.simple_index_doc' % TEST_DB,
                'v': 1
            },
            {
                'v': 1,
                'key': {'indexed': 1},
                'name': 'indexed_1',
                'ns': '%s.simple_index_doc' % TEST_DB
            }
        ]
        assert indexes == expected_indexes

        # Redoing indexes building should do nothing
        SimpleIndexDoc.ensure_indexes()
        assert indexes == expected_indexes

    def test_unique_index(self, instance):

        @instance.register
        class UniqueIndexDoc(Document):
            not_unique = fields.StrField(unique=False)
            sparse_unique = fields.IntField(unique=True)
            required_unique = fields.IntField(unique=True, required=True)

        UniqueIndexDoc.collection.drop()
        UniqueIndexDoc.collection.drop_indexes()

        # Now ask for indexes building
        UniqueIndexDoc.ensure_indexes()
        indexes = [e for e in UniqueIndexDoc.collection.list_indexes()]
        expected_indexes = [
            {
                'key': {'_id': 1},
                'name': '_id_',
                'ns': '%s.unique_index_doc' % TEST_DB,
                'v': 1
            },
            {
                'v': 1,
                'key': {'required_unique': 1},
                'name': 'required_unique_1',
                'unique': True,
                'ns': '%s.unique_index_doc' % TEST_DB
            },
            {
                'v': 1,
                'key': {'sparse_unique': 1},
                'name': 'sparse_unique_1',
                'unique': True,
                'sparse': True,
                'ns': '%s.unique_index_doc' % TEST_DB
            },
        ]
        assert name_sorted(indexes) == name_sorted(expected_indexes)

        # Redoing indexes building should do nothing
        UniqueIndexDoc.ensure_indexes()
        indexes = [e for e in UniqueIndexDoc.collection.list_indexes()]
        assert name_sorted(indexes) == name_sorted(expected_indexes)

        UniqueIndexDoc(not_unique='a', required_unique=1).commit()
        UniqueIndexDoc(not_unique='a', sparse_unique=1, required_unique=2).commit()
        with pytest.raises(exceptions.ValidationError) as exc:
            UniqueIndexDoc(not_unique='a', required_unique=1).commit()
        assert exc.value.messages == {'required_unique': 'Field value must be unique.'}
        with pytest.raises(exceptions.ValidationError) as exc:
            UniqueIndexDoc(not_unique='a', sparse_unique=1, required_unique=3).commit()
        assert exc.value.messages == {'sparse_unique': 'Field value must be unique.'}

    def test_unique_index_compound(self, instance):

        @instance.register
        class UniqueIndexCompoundDoc(Document):
            compound1 = fields.IntField()
            compound2 = fields.IntField()
            not_unique = fields.StrField()

            class Meta:
                # Must define custom index to do that
                indexes = [{'key': ('compound1', 'compound2'), 'unique': True}]

        UniqueIndexCompoundDoc.collection.drop()
        UniqueIndexCompoundDoc.collection.drop_indexes()

        # Now ask for indexes building
        UniqueIndexCompoundDoc.ensure_indexes()
        indexes = [e for e in UniqueIndexCompoundDoc.collection.list_indexes()]
        expected_indexes = [
            {
                'key': {'_id': 1},
                'name': '_id_',
                'ns': '%s.unique_index_compound_doc' % TEST_DB,
                'v': 1
            },
            {
                'v': 1,
                'key': {'compound1': 1, 'compound2': 1},
                'name': 'compound1_1_compound2_1',
                'unique': True,
                'ns': '%s.unique_index_compound_doc' % TEST_DB
            }
        ]
        assert name_sorted(indexes) == name_sorted(expected_indexes)

        # Redoing indexes building should do nothing
        UniqueIndexCompoundDoc.ensure_indexes()
        indexes = [e for e in UniqueIndexCompoundDoc.collection.list_indexes()]
        assert name_sorted(indexes) == name_sorted(expected_indexes)

        # Index is on the tuple (compound1, compound2)
        UniqueIndexCompoundDoc(not_unique='a', compound1=1, compound2=1).commit()
        UniqueIndexCompoundDoc(not_unique='a', compound1=1, compound2=2).commit()
        UniqueIndexCompoundDoc(not_unique='a', compound1=2, compound2=1).commit()
        UniqueIndexCompoundDoc(not_unique='a', compound1=2, compound2=2).commit()
        with pytest.raises(exceptions.ValidationError) as exc:
            UniqueIndexCompoundDoc(not_unique='a', compound1=1, compound2=1).commit()
        assert exc.value.messages == {
            'compound2': "Values of fields ['compound1', 'compound2'] must be unique together.",
            'compound1': "Values of fields ['compound1', 'compound2'] must be unique together."
        }
        with pytest.raises(exceptions.ValidationError) as exc:
            UniqueIndexCompoundDoc(not_unique='a', compound1=2, compound2=1).commit()
        assert exc.value.messages == {
            'compound2': "Values of fields ['compound1', 'compound2'] must be unique together.",
            'compound1': "Values of fields ['compound1', 'compound2'] must be unique together."
        }

    @pytest.mark.xfail
    def test_unique_index_inheritance(self, instance):

        @instance.register
        class UniqueIndexParentDoc(Document):
            not_unique = fields.StrField(unique=False)
            unique = fields.IntField(unique=True)

            class Meta:
                allow_inheritance = True

        @instance.register
        class UniqueIndexChildDoc(UniqueIndexParentDoc):
            child_not_unique = fields.StrField(unique=False)
            child_unique = fields.IntField(unique=True)
            manual_index = fields.IntField()

            class Meta:
                indexes = ['manual_index']

        UniqueIndexChildDoc.collection.drop_indexes()

        # Now ask for indexes building
        UniqueIndexChildDoc.ensure_indexes()
        indexes = [e for e in UniqueIndexChildDoc.collection.list_indexes()]
        expected_indexes = [
            {
                'key': {'_id': 1},
                'name': '_id_',
                'ns': '%s.unique_index_inheritance_doc' % TEST_DB,
                'v': 1
            },
            {
                'v': 1,
                'key': {'unique': 1},
                'name': 'unique_1',
                'unique': True,
                'ns': '%s.unique_index_inheritance_doc' % TEST_DB
            },
            {
                'v': 1,
                'key': {'manual_index': 1, '_cls': 1},
                'name': 'manual_index_1__cls_1',
                'ns': '%s.unique_index_inheritance_doc' % TEST_DB
            },
            {
                'v': 1,
                'key': {'_cls': 1},
                'name': '_cls_1',
                'unique': True,
                'ns': '%s.unique_index_inheritance_doc' % TEST_DB
            },
            {
                'v': 1,
                'key': {'child_unique': 1, '_cls': 1},
                'name': 'child_unique_1__cls_1',
                'unique': True,
                'ns': '%s.unique_index_inheritance_doc' % TEST_DB
            }
        ]
        assert name_sorted(indexes) == name_sorted(expected_indexes)

        # Redoing indexes building should do nothing
        UniqueIndexChildDoc.ensure_indexes()
        indexes = [e for e in UniqueIndexChildDoc.collection.list_indexes()]
        assert name_sorted(indexes) == name_sorted(expected_indexes)

    def test_inheritance_search(self, instance):

        @instance.register
        class InheritanceSearchParent(Document):
            pf = fields.IntField()

            class Meta:
                allow_inheritance = True

        @instance.register
        class InheritanceSearchChild1(InheritanceSearchParent):
            c1f = fields.IntField()

            class Meta:
                allow_inheritance = True

        @instance.register
        class InheritanceSearchChild1Child(InheritanceSearchChild1):
            sc1f = fields.IntField()

        @instance.register
        class InheritanceSearchChild2(InheritanceSearchParent):
            c2f = fields.IntField(required=True)

        InheritanceSearchParent.collection.drop()

        InheritanceSearchParent(pf=0).commit()
        InheritanceSearchChild1(pf=1, c1f=1).commit()
        InheritanceSearchChild1Child(pf=1, sc1f=1).commit()
        InheritanceSearchChild2(pf=2, c2f=2).commit()

        assert InheritanceSearchParent.find().count() == 4
        assert InheritanceSearchChild1.find().count() == 2
        assert InheritanceSearchChild1Child.find().count() == 1
        assert InheritanceSearchChild2.find().count() == 1

        res = InheritanceSearchParent.find_one({'sc1f': 1})
        assert isinstance(res, InheritanceSearchChild1Child)

        res = InheritanceSearchParent.find({'pf': 1})
        for r in res:
            assert isinstance(r, InheritanceSearchChild1)

    def test_search(self, instance):

        @instance.register
        class Author(EmbeddedDocument):
            name = fields.StrField(attribute='an')

        @instance.register
        class Chapter(EmbeddedDocument):
            name = fields.StrField(attribute='cn')

        @instance.register
        class Book(Document):
            title = fields.StrField(attribute='t')
            author = fields.EmbeddedField(Author, attribute='a')
            chapters = fields.ListField(fields.EmbeddedField(Chapter), attribute='c')

        Book.collection.drop()
        Book(title='The Hobbit', author={'name': 'JRR Tolkien'}, chapters=[
            {'name': 'An Unexpected Party'},
            {'name': 'Roast Mutton'},
            {'name': 'A Short Rest'},
            {'name': 'Over Hill And Under Hill'},
            {'name': 'Riddles In The Dark'}
        ]).commit()
        Book(title="Harry Potter and the Philosopher's Stone",
             author={'name': 'JK Rowling'},
             chapters=[
                {'name': 'The Boy Who Lived'},
                {'name': 'The Vanishing Glass'},
                {'name': 'The Letters from No One'},
                {'name': 'The Keeper of the Keys'},
                {'name': 'Diagon Alley'}
        ]).commit()
        Book(title='A Game of Thrones', author={'name': 'George RR Martin'}, chapters=[
            {'name': 'Prologue'},
            {'name': 'Bran I'},
            {'name': 'Catelyn I'},
            {'name': 'Daenerys I'},
            {'name': 'Eddard I'},
            {'name': 'Jon I'}
        ]).commit()

        assert Book.find({'title': 'The Hobbit'}).count() == 1
        assert Book.find({'author.name': {'$in': ['JK Rowling', 'JRR Tolkien']}}).count() == 2
        assert Book.find({'$and': [{'chapters.name': 'Roast Mutton'}, {'title': 'The Hobbit'}]}).count() == 1
        assert Book.find({'chapters.name': {'$all': ['Roast Mutton', 'A Short Rest']}}).count() == 1
