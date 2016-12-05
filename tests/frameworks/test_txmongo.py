import pytest
from datetime import datetime
from bson import ObjectId
from functools import wraps

from ..common import BaseDBTest, get_pymongo_version, TEST_DB, con
from ..fixtures import classroom_model, instance

# Check if the required dependancies are met to run this driver's tests
dep_error = None
try:
    import pytest_twisted as _
    from txmongo import MongoConnection
    major, minor, _ = get_pymongo_version()
    if major != 3 or minor < 2:
        dep_error = "txmongo driver requires pymongo>=3.2.0"
    else:
        from pymongo.results import InsertOneResult, UpdateResult, DeleteResult
    from twisted.internet.defer import Deferred, inlineCallbacks, succeed
except ImportError:
    dep_error = 'Missing txmongo module or pytest_twisted'

    # Given the test function are generator, we must wrap them into a dummy
    # function that pytest can skip
    def skip_wrapper(f):

        @wraps(f)
        def wrapper(self):
            pass

        return wrapper

    pytest_inlineCallbacks = skip_wrapper
else:
    pytest_inlineCallbacks = pytest.inlineCallbacks

from umongo import (Document, EmbeddedDocument, fields, exceptions, Reference,
                    Instance, TxMongoInstance, NoDBDefinedError)


if not dep_error:  # Make sure the module is valid by importing it
    from umongo.frameworks import txmongo as framework


# Helper to sort indexes by name in order to have deterministic comparison
def name_sorted(indexes):
    return sorted(indexes, key=lambda x: x['name'])


@pytest.fixture
def db():
    return MongoConnection()[TEST_DB]


@pytest.mark.skipif(dep_error is not None, reason=dep_error)
class TestTxMongo(BaseDBTest):

    def test_auto_instance(self, db):
        instance = Instance(db)

        class Doc(Document):
            pass

        doc_impl_cls = instance.register(Doc)
        assert doc_impl_cls.collection == db['doc']
        assert issubclass(doc_impl_cls, framework.TxMongoDocument)

    def test_lazy_loader_instance(self, db):
        instance = TxMongoInstance()

        class Doc(Document):
            pass

        doc_impl_cls = instance.register(Doc)
        assert issubclass(doc_impl_cls, framework.TxMongoDocument)
        with pytest.raises(NoDBDefinedError):
            doc_impl_cls.collection
        instance.init(db)
        assert doc_impl_cls.collection == db['doc']

    @pytest_inlineCallbacks
    def test_create(self, classroom_model):
        Student = classroom_model.Student
        john = Student(name='John Doe', birthday=datetime(1995, 12, 12))
        ret = yield john.commit()
        assert isinstance(ret, InsertOneResult)
        assert john.to_mongo() == {
            '_id': john.id,
            'name': 'John Doe',
            'birthday': datetime(1995, 12, 12)
        }

        john2 = yield Student.find_one(john.id)
        assert john2._data == john._data
        # Double commit should do nothing
        ret = yield john.commit()
        assert ret is None

    @pytest_inlineCallbacks
    def test_update(self, classroom_model):
        Student = classroom_model.Student
        john = Student(name='John Doe', birthday=datetime(1995, 12, 12))
        yield john.commit()
        john.name = 'William Doe'
        assert john.to_mongo(update=True) == {'$set': {'name': 'William Doe'}}
        ret = yield john.commit()
        assert isinstance(ret, UpdateResult)
        assert john.to_mongo(update=True) is None
        john2 = yield Student.find_one(john.id)
        assert john2._data == john._data
        # Update without changing anything
        john.name = john.name
        yield john.commit()
        # Test conditional commit
        john.name = 'Zorro Doe'
        with pytest.raises(exceptions.UpdateError):
            yield john.commit(conditions={'name': 'Bad Name'})
        yield john.commit(conditions={'name': 'William Doe'})
        yield john.reload()
        assert john.name == 'Zorro Doe'
        # Cannot use conditions when creating document
        with pytest.raises(RuntimeError):
            yield Student(name='Joe').commit(conditions={'name': 'dummy'})

    @pytest_inlineCallbacks
    def test_delete(self, classroom_model):
        Student = classroom_model.Student
        yield Student.collection.drop()
        john = Student(name='John Doe', birthday=datetime(1995, 12, 12))
        with pytest.raises(exceptions.NotCreatedError):
            yield john.delete()
        yield john.commit()
        students = yield Student.find()
        assert len(students) == 1
        ret = yield john.delete()
        assert isinstance(ret, DeleteResult)
        assert not john.is_created
        students = yield Student.find()
        assert len(students) == 0
        with pytest.raises(exceptions.NotCreatedError):
            yield john.delete()
        # Can re-commit the document in database
        yield john.commit()
        assert john.is_created
        students = yield Student.find()
        assert len(students) == 1
        # Test conditional delete
        with pytest.raises(exceptions.DeleteError):
            yield john.delete(conditions={'name': 'Bad Name'})
        yield john.delete(conditions={'name': 'John Doe'})
        # Finally try to delete a doc no longer in database
        yield john.commit()
        yield students[0].delete()
        with pytest.raises(exceptions.DeleteError):
            yield john.delete()

    @pytest_inlineCallbacks
    def test_reload(self, classroom_model):
        Student = classroom_model.Student
        yield Student(name='Other dude').commit()
        john = Student(name='John Doe', birthday=datetime(1995, 12, 12))
        with pytest.raises(exceptions.NotCreatedError):
            yield john.reload()
        yield john.commit()
        john2 = yield Student.find_one(john.id)
        john2.name = 'William Doe'
        yield john2.commit()
        yield john.reload()
        assert john.name == 'William Doe'

    @pytest_inlineCallbacks
    def test_find_no_cursor(self, classroom_model):
        Student = classroom_model.Student
        Student.collection.drop()
        for i in range(10):
            yield Student(name='student-%s' % i).commit()
        results = yield Student.find(limit=5, skip=6)
        assert isinstance(results, list)
        assert len(results) == 4
        names = []
        for elem in results:
            assert isinstance(elem, Student)
            names.append(elem.name)
        assert sorted(names) == ['student-%s' % i for i in range(6, 10)]

    @pytest_inlineCallbacks
    def test_find_with_cursor(self, classroom_model):
        Student = classroom_model.Student
        Student.collection.drop()
        for i in range(10):
            yield Student(name='student-%s' % i).commit()
        batch1, cursor1 = yield Student.find(limit=5, skip=6, cursor=True)
        assert len(batch1) == 4
        batch2, cursor2 = yield cursor1
        assert len(batch2) == 0
        assert cursor2 is None
        names = []
        for elem in batch1:
            assert isinstance(elem, Student)
            names.append(elem.name)
        assert sorted(names) == ['student-%s' % i for i in range(6, 10)]

    @pytest_inlineCallbacks
    def test_classroom(self, classroom_model):
        student = classroom_model.Student(name='Marty McFly', birthday=datetime(1968, 6, 9))
        yield student.commit()
        teacher = classroom_model.Teacher(name='M. Strickland')
        yield teacher.commit()
        course = classroom_model.Course(name='Hoverboard 101', teacher=teacher)
        yield course.commit()
        assert student.courses == []
        student.courses.append(course)
        yield student.commit()
        assert student.to_mongo() == {
            '_id': student.pk,
            'name': 'Marty McFly',
            'birthday': datetime(1968, 6, 9),
            'courses': [course.pk]
        }

    @pytest_inlineCallbacks
    def test_validation_on_commit(self, instance):

        def io_validate(field, value):
            raise exceptions.ValidationError('Ho boys !')

        @instance.register
        class Dummy(Document):
            required_name = fields.StrField(required=True)
            always_io_fail = fields.IntField(io_validate=io_validate)

        with pytest.raises(exceptions.ValidationError) as exc:
            yield Dummy().commit()
        assert exc.value.messages == {'required_name': ['Missing data for required field.']}
        with pytest.raises(exceptions.ValidationError) as exc:
            yield Dummy(required_name='required', always_io_fail=42).commit()
        assert exc.value.messages == {'always_io_fail': ['Ho boys !']}

        dummy = Dummy(required_name='required')
        yield dummy.commit()
        del dummy.required_name
        with pytest.raises(exceptions.ValidationError) as exc:
            yield dummy.commit()
        assert exc.value.messages == {'required_name': ['Missing data for required field.']}

    @pytest_inlineCallbacks
    def test_reference(self, classroom_model):
        teacher = classroom_model.Teacher(name='M. Strickland')
        yield teacher.commit()
        course = classroom_model.Course(name='Hoverboard 101', teacher=teacher)
        yield course.commit()
        assert isinstance(course.teacher, Reference)
        teacher_fetched = yield course.teacher.fetch()
        assert teacher_fetched == teacher
        # Test bad ref as well
        course.teacher = Reference(classroom_model.Teacher, ObjectId())
        with pytest.raises(exceptions.ValidationError) as exc:
            yield course.io_validate()
        assert exc.value.messages == {'teacher': ['Reference not found for document Teacher.']}

    @pytest_inlineCallbacks
    def test_io_validate(self, instance, classroom_model):
        Student = classroom_model.Student

        io_field_value = 'io?'
        io_validate_called = False

        def io_validate(field, value):
            assert field == IOStudent.schema.fields['io_field']
            assert value == io_field_value
            nonlocal io_validate_called
            io_validate_called = True
            return succeed(None)

        @instance.register
        class IOStudent(Student):
            io_field = fields.StrField(io_validate=io_validate)

        student = IOStudent(name='Marty', io_field=io_field_value)
        assert not io_validate_called

        yield student.io_validate()
        assert io_validate_called

    @pytest_inlineCallbacks
    def test_io_validate_error(self, instance, classroom_model):
        Student = classroom_model.Student

        def io_validate(field, value):
            raise exceptions.ValidationError('Ho boys !')

        @instance.register
        class EmbeddedDoc(EmbeddedDocument):
            io_field = fields.IntField(io_validate=io_validate)

        @instance.register
        class IOStudent(Student):
            io_field = fields.StrField(io_validate=io_validate)
            list_io_field = fields.ListField(fields.IntField(io_validate=io_validate))
            reference_io_field = fields.ReferenceField(classroom_model.Course, io_validate=io_validate)
            embedded_io_field = fields.EmbeddedField(EmbeddedDoc, io_validate=io_validate)

        bad_reference = ObjectId()
        student = IOStudent(
            name='Marty',
            io_field='io?',
            list_io_field=[1, 2],
            reference_io_field=bad_reference,
            embedded_io_field={'io_field': 42}
        )
        with pytest.raises(exceptions.ValidationError) as exc:
            yield student.io_validate()
        assert exc.value.messages == {
            'io_field': ['Ho boys !'],
            'list_io_field': {0: ['Ho boys !'], 1: ['Ho boys !']},
            'reference_io_field': ['Ho boys !', 'Reference not found for document Course.'],
            'embedded_io_field': {'io_field': ['Ho boys !']}
        }

    @pytest_inlineCallbacks
    def test_io_validate_multi_validate(self, instance, classroom_model):
        Student = classroom_model.Student
        called = []

        defer1 = Deferred()
        defer2 = Deferred()
        defer3 = Deferred()
        defer4 = Deferred()

        @inlineCallbacks
        def io_validate11(field, value):
            called.append(1)
            defer1.callback(None)
            yield defer3
            called.append(4)
            defer4.callback(None)

        @inlineCallbacks
        def io_validate12(field, value):
            yield defer4
            called.append(5)

        @inlineCallbacks
        def io_validate21(field, value):
            yield defer2
            called.append(3)
            defer3.callback(None)

        @inlineCallbacks
        def io_validate22(field, value):
            yield defer1
            called.append(2)
            defer2.callback(None)

        @instance.register
        class IOStudent(Student):
            io_field1 = fields.StrField(io_validate=(io_validate11, io_validate12))
            io_field2 = fields.StrField(io_validate=(io_validate21, io_validate22))

        student = IOStudent(name='Marty', io_field1='io1', io_field2='io2')
        yield student.io_validate()
        assert called == [1, 2, 3, 4, 5]

    @pytest_inlineCallbacks
    def test_io_validate_list(self, instance, classroom_model):
        Student = classroom_model.Student
        called = []
        values = [1, 2, 3, 4]

        @inlineCallbacks
        def io_validate(field, value):
            yield called.append(value)

        @instance.register
        class IOStudent(Student):
            io_field = fields.ListField(fields.IntField(io_validate=io_validate))

        student = IOStudent(name='Marty', io_field=values)
        yield student.io_validate()
        assert called == values

    @pytest_inlineCallbacks
    def test_indexes(self, instance):

        @instance.register
        class SimpleIndexDoc(Document):
            indexed = fields.StrField()
            no_indexed = fields.IntField()

            class Meta:
                collection = 'simple_index_doc'
                indexes = ['indexed']

        yield SimpleIndexDoc.collection.drop_indexes()

        # Now ask for indexes building
        yield SimpleIndexDoc.ensure_indexes()
        # SimpleIndexDoc.collection.index_information doesn't seems to work...
        indexes = [e for e in con[TEST_DB].simple_index_doc.list_indexes()]
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
        assert name_sorted(indexes) == name_sorted(expected_indexes)

        # Redoing indexes building should do nothing
        yield SimpleIndexDoc.ensure_indexes()
        indexes = [e for e in con[TEST_DB].simple_index_doc.list_indexes()]
        assert name_sorted(indexes) == name_sorted(expected_indexes)

    @pytest_inlineCallbacks
    def test_indexes_inheritance(self, instance):

        @instance.register
        class SimpleIndexDoc(Document):
            indexed = fields.StrField()
            no_indexed = fields.IntField()

            class Meta:
                collection = 'simple_index_doc'
                indexes = ['indexed']

        yield SimpleIndexDoc.collection.drop_indexes()

        # Now ask for indexes building
        yield SimpleIndexDoc.ensure_indexes()
        # SimpleIndexDoc.collection.index_information doesn't seems to work...
        indexes = [e for e in con[TEST_DB].simple_index_doc.list_indexes()]
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
        assert name_sorted(indexes) == name_sorted(expected_indexes)

        # Redoing indexes building should do nothing
        yield SimpleIndexDoc.ensure_indexes()
        indexes = [e for e in con[TEST_DB].simple_index_doc.list_indexes()]
        assert name_sorted(indexes) == name_sorted(expected_indexes)

    @pytest_inlineCallbacks
    def test_unique_index(self, instance):

        @instance.register
        class UniqueIndexDoc(Document):
            not_unique = fields.StrField(unique=False)
            sparse_unique = fields.IntField(unique=True)
            required_unique = fields.IntField(unique=True, required=True)

            class Meta:
                collection = 'unique_index_doc'

        yield UniqueIndexDoc.collection.drop()
        yield UniqueIndexDoc.collection.drop_indexes()

        # Now ask for indexes building
        yield UniqueIndexDoc.ensure_indexes()
        indexes = [e for e in con[TEST_DB].unique_index_doc.list_indexes()]
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
        yield UniqueIndexDoc.ensure_indexes()
        indexes = [e for e in con[TEST_DB].unique_index_doc.list_indexes()]
        assert name_sorted(indexes) == name_sorted(expected_indexes)

        yield UniqueIndexDoc(not_unique='a', required_unique=1).commit()
        yield UniqueIndexDoc(not_unique='a', sparse_unique=1, required_unique=2).commit()
        with pytest.raises(exceptions.ValidationError) as exc:
            yield UniqueIndexDoc(not_unique='a', required_unique=1).commit()
        assert exc.value.messages == {'required_unique': 'Field value must be unique.'}
        with pytest.raises(exceptions.ValidationError) as exc:
            yield UniqueIndexDoc(not_unique='a', sparse_unique=1, required_unique=3).commit()
        assert exc.value.messages == {'sparse_unique': 'Field value must be unique.'}

    @pytest_inlineCallbacks
    def test_unique_index_compound(self, instance):

        @instance.register
        class UniqueIndexCompoundDoc(Document):
            compound1 = fields.IntField()
            compound2 = fields.IntField()
            not_unique = fields.StrField()

            class Meta:
                collection = 'unique_index_compound_doc'
                # Must define custom index to do that
                indexes = [{'key': ('compound1', 'compound2'), 'unique': True}]

        yield UniqueIndexCompoundDoc.collection.drop()
        yield UniqueIndexCompoundDoc.collection.drop_indexes()

        # Now ask for indexes building
        yield UniqueIndexCompoundDoc.ensure_indexes()
        indexes = [e for e in con[TEST_DB].unique_index_compound_doc.list_indexes()]
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
        yield UniqueIndexCompoundDoc.ensure_indexes()
        indexes = [e for e in con[TEST_DB].unique_index_compound_doc.list_indexes()]
        assert name_sorted(indexes) == name_sorted(expected_indexes)

        # Index is on the tuple (compound1, compound2)
        yield UniqueIndexCompoundDoc(not_unique='a', compound1=1, compound2=1).commit()
        yield UniqueIndexCompoundDoc(not_unique='a', compound1=1, compound2=2).commit()
        yield UniqueIndexCompoundDoc(not_unique='a', compound1=2, compound2=1).commit()
        yield UniqueIndexCompoundDoc(not_unique='a', compound1=2, compound2=2).commit()
        with pytest.raises(exceptions.ValidationError) as exc:
            yield UniqueIndexCompoundDoc(not_unique='a', compound1=1, compound2=1).commit()
        assert exc.value.messages == {
            'compound2': "Values of fields ['compound1', 'compound2'] must be unique together.",
            'compound1': "Values of fields ['compound1', 'compound2'] must be unique together."
        }
        with pytest.raises(exceptions.ValidationError) as exc:
            yield UniqueIndexCompoundDoc(not_unique='a', compound1=2, compound2=1).commit()
        assert exc.value.messages == {
            'compound2': "Values of fields ['compound1', 'compound2'] must be unique together.",
            'compound1': "Values of fields ['compound1', 'compound2'] must be unique together."
        }

    @pytest.mark.xfail
    @pytest_inlineCallbacks
    def test_unique_index_inheritance(self, instance):

        @instance.register
        class UniqueIndexParentDoc(Document):
            not_unique = fields.StrField(unique=False)
            unique = fields.IntField(unique=True)

            class Meta:
                collection = 'unique_index_inheritance_doc'
                allow_inheritance = True

        @instance.register
        class UniqueIndexChildDoc(UniqueIndexParentDoc):
            child_not_unique = fields.StrField(unique=False)
            child_unique = fields.IntField(unique=True)
            manual_index = fields.IntField()

            class Meta:
                indexes = ['manual_index']

        yield UniqueIndexChildDoc.collection.drop_indexes()

        # Now ask for indexes building
        yield UniqueIndexChildDoc.ensure_indexes()
        indexes = [e for e in con[TEST_DB].unique_index_inheritance_doc.list_indexes()]
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
        yield UniqueIndexChildDoc.ensure_indexes()
        indexes = [e for e in con[TEST_DB].unique_index_inheritance_doc.list_indexes()]
        assert name_sorted(indexes) == name_sorted(expected_indexes)

    @pytest_inlineCallbacks
    def test_inheritance_search(self, instance):

        @instance.register
        class InheritanceSearchParent(Document):
            pf = fields.IntField()

            class Meta:
                collection = 'inheritance_search'
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

        yield InheritanceSearchParent.collection.drop()

        yield InheritanceSearchParent(pf=0).commit()
        yield InheritanceSearchChild1(pf=1, c1f=1).commit()
        yield InheritanceSearchChild1Child(pf=1, sc1f=1).commit()
        yield InheritanceSearchChild2(pf=2, c2f=2).commit()

        res = yield InheritanceSearchParent.find()
        assert len(res) == 4
        res = yield InheritanceSearchChild1.find()
        assert len(res) == 2
        res = yield InheritanceSearchChild1Child.find()
        assert len(res) == 1
        res = yield InheritanceSearchChild2.find()
        assert len(res) == 1

        res = yield InheritanceSearchParent.find_one({'sc1f': 1})
        assert isinstance(res, InheritanceSearchChild1Child)

        res = yield InheritanceSearchParent.find({'pf': 1})
        for r in res:
            assert isinstance(r, InheritanceSearchChild1)

    @pytest_inlineCallbacks
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
        yield Book(title='The Hobbit',
            author={'name': 'JRR Tolkien'},
            chapters=[
                {'name': 'An Unexpected Party'},
                {'name': 'Roast Mutton'},
                {'name': 'A Short Rest'},
                {'name': 'Over Hill And Under Hill'},
                {'name': 'Riddles In The Dark'}
        ]).commit()
        yield Book(title="Harry Potter and the Philosopher's Stone",
             author={'name': 'JK Rowling'},
             chapters=[
                {'name': 'The Boy Who Lived'},
                {'name': 'The Vanishing Glass'},
                {'name': 'The Letters from No One'},
                {'name': 'The Keeper of the Keys'},
                {'name': 'Diagon Alley'}
        ]).commit()
        yield Book(title='A Game of Thrones',
            author={'name': 'George RR Martin'},
            chapters=[
                {'name': 'Prologue'},
                {'name': 'Bran I'},
                {'name': 'Catelyn I'},
                {'name': 'Daenerys I'},
                {'name': 'Eddard I'},
                {'name': 'Jon I'}
        ]).commit()

        res = yield Book.find({'title': 'The Hobbit'})
        assert len(res) == 1
        res = yield Book.find({'author.name': {'$in': ['JK Rowling', 'JRR Tolkien']}})
        assert len(res) == 2
        res = yield Book.find({'$and': [{'chapters.name': 'Roast Mutton'}, {'title': 'The Hobbit'}]})
        assert len(res) == 1
        res = yield Book.find({'chapters.name': {'$all': ['Roast Mutton', 'A Short Rest']}})
        assert len(res) == 1

    @pytest_inlineCallbacks
    def test_pre_post_hooks(self, instance):

        callbacks = []

        @instance.register
        class Person(Document):
            name = fields.StrField()
            age = fields.IntField()

            def pre_insert(self):
                callbacks.append('pre_insert')

            def pre_update(self):
                callbacks.append('pre_update')

            def pre_delete(self):
                callbacks.append('pre_delete')

            def post_insert(self, ret):
                assert isinstance(ret, InsertOneResult)
                callbacks.append('post_insert')

            def post_update(self, ret):
                assert isinstance(ret, UpdateResult)
                callbacks.append('post_update')

            def post_delete(self, ret):
                assert isinstance(ret, DeleteResult)
                callbacks.append('post_delete')


        p = Person(name='John', age=20)
        yield p.commit()
        assert callbacks == ['pre_insert', 'post_insert']

        callbacks.clear()
        p.age = 22
        yield p.commit({'age': 22})
        assert callbacks == ['pre_update', 'post_update']

        callbacks.clear()
        yield p.delete()
        assert callbacks == ['pre_delete', 'post_delete']

    @pytest_inlineCallbacks
    def test_pre_post_hooks_with_defers(self, instance):

        events = []

        @instance.register
        class Person(Document):
            name = fields.StrField()
            age = fields.IntField()

            @inlineCallbacks
            def pre_insert(self):
                events.append('start pre_insert')
                yield succeed
                events.append('end pre_insert')

            @inlineCallbacks
            def post_insert(self, ret):
                events.append('start post_insert')
                yield succeed
                events.append('end post_insert')

        p = Person(name='John', age=20)
        yield p.commit()
        assert events == [
            'start pre_insert',
            'end pre_insert',
            'start post_insert',
            'end post_insert'
        ]

    @pytest_inlineCallbacks
    def test_modify_in_pre_hook(self, instance):

        @instance.register
        class Person(Document):
            version = fields.IntField(required=True, attribute='_version')
            name = fields.StrField()
            age = fields.IntField()

            def pre_insert(self):
                self.version = 1

            def pre_update(self):
                # Prevent concurrency by checking a version number on update
                last_version = self.version
                self.version += 1
                return {'version': last_version}

            def pre_delete(self):
                return {'version': self.version}


        p = Person(name='John', age=20)
        yield p.commit()

        assert p.version == 1
        p_concurrent = yield Person.find_one(p.pk)

        p.age = 22
        yield p.commit()
        assert p.version == 2

        # Concurrent should not be able to commit it modifications
        p_concurrent.name = 'John'
        with pytest.raises(exceptions.UpdateError):
            yield p_concurrent.commit()

        yield p_concurrent.reload()
        assert p_concurrent.version == 2

        p.age = 24
        yield p.commit()
        assert p.version == 3
        yield p.delete()
        yield p.commit()
        with pytest.raises(exceptions.DeleteError):
            yield p_concurrent.delete()
        yield p.delete()
