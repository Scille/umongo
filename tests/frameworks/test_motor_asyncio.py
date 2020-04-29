import asyncio
from datetime import datetime

import pytest

from bson import ObjectId

# Check if the required dependancies are met to run this driver's tests
try:
    from motor.motor_asyncio import AsyncIOMotorClient
    from motor import version_tuple as MOTOR_VERSION
except ImportError as e:
    dep_error = str(e)
else:
    dep_error = None

from ..common import BaseDBTest, TEST_DB

from umongo import Document, EmbeddedDocument, fields, exceptions, Reference

if not dep_error:  # Make sure the module is valid by importing it
    from umongo.frameworks import motor_asyncio as framework  # noqa
    from pymongo.results import InsertOneResult, UpdateResult, DeleteResult


def _stripped(indexes):
    # With pymongo==2.8 a `ns` field is returned with Mongodb>=3 but
    # not with MongoDB<2, thus we have to clean this before doing comparing
    # Version may differ between database versions and configurations so it
    # shall not be checked
    return {
        k: {sk: sv for sk, sv in v.items() if sk not in ('ns', 'v')}
        for k, v in indexes.items()
    }


# Helper to sort indexes by name in order to have deterministic comparison
def name_sorted(indexes):
    return sorted(indexes, key=lambda x: x['name'])


def make_db():
    return AsyncIOMotorClient()[TEST_DB]


@pytest.fixture
def db():
    return make_db()


@pytest.fixture
def loop():
    return asyncio.get_event_loop()


@pytest.mark.skipif(dep_error is not None, reason=dep_error)
class TestMotorAsyncio(BaseDBTest):

    def test_create(self, loop, classroom_model):
        Student = classroom_model.Student

        async def do_test():
            john = Student(name='John Doe', birthday=datetime(1995, 12, 12))
            ret = await john.commit()
            assert isinstance(ret, InsertOneResult)
            assert john.to_mongo() == {
                '_id': john.id,
                'name': 'John Doe',
                'birthday': datetime(1995, 12, 12)
            }

            john2 = await Student.find_one(john.id)
            assert john2._data == john._data
            # Double commit should do nothing
            ret = await john.commit()
            assert ret is None

        loop.run_until_complete(do_test())

    def test_update(self, loop, classroom_model):
        Student = classroom_model.Student

        async def do_test():
            john = Student(name='John Doe', birthday=datetime(1995, 12, 12))
            await john.commit()
            john.name = 'William Doe'
            assert john.to_mongo(update=True) == {'$set': {'name': 'William Doe'}}
            ret = await john.commit()
            assert isinstance(ret, UpdateResult)
            assert john.to_mongo(update=True) is None
            john2 = await Student.find_one(john.id)
            assert john2._data == john._data
            # Update without changing anything
            john.name = john.name
            await john.commit()
            # Test conditional commit
            john.name = 'Zorro Doe'
            with pytest.raises(exceptions.UpdateError):
                await john.commit(conditions={'name': 'Bad Name'})
            await john.commit(conditions={'name': 'William Doe'})
            await john.reload()
            assert john.name == 'Zorro Doe'
            # Cannot use conditions when creating document
            with pytest.raises(RuntimeError):
                await Student(name='Joe').commit(conditions={'name': 'dummy'})

        loop.run_until_complete(do_test())

    def test_remove(self, loop, classroom_model):
        Student = classroom_model.Student

        async def do_test():
            await Student.collection.drop()
            john = Student(name='John Doe', birthday=datetime(1995, 12, 12))
            with pytest.raises(exceptions.NotCreatedError):
                await john.remove()
            await john.commit()
            assert (await Student.count_documents()) == 1
            ret = await john.remove()
            assert isinstance(ret, DeleteResult)
            assert not john.is_created
            assert (await Student.count_documents()) == 0
            with pytest.raises(exceptions.NotCreatedError):
                await john.remove()
            # Can re-commit the document in database
            await john.commit()
            assert john.is_created
            assert (await Student.count_documents()) == 1
            # Test conditional delete
            with pytest.raises(exceptions.DeleteError):
                await john.remove(conditions={'name': 'Bad Name'})
            await john.remove(conditions={'name': 'John Doe'})
            # Finally try to remove a doc no longer in database
            await john.commit()
            await (await Student.find_one(john.id)).remove()
            with pytest.raises(exceptions.DeleteError):
                await john.remove()

        loop.run_until_complete(do_test())

    def test_reload(self, loop, classroom_model):
        Student = classroom_model.Student

        async def do_test():
            await Student(name='Other dude').commit()
            john = Student(name='John Doe', birthday=datetime(1995, 12, 12))
            with pytest.raises(exceptions.NotCreatedError):
                await john.reload()
            await john.commit()
            john2 = await Student.find_one(john.id)
            john2.name = 'William Doe'
            await john2.commit()
            await john.reload()
            assert john.name == 'William Doe'

        loop.run_until_complete(do_test())

    def test_cursor(self, loop, classroom_model):
        Student = classroom_model.Student

        async def do_test():
            await Student.collection.drop()

            for i in range(10):
                await Student(name='student-%s' % i).commit()
            cursor = Student.find(limit=5, skip=6)
            if MOTOR_VERSION < (2, 0):
                # this test doesn't make as much sense in motor>2.0, since the cursor no
                # longer supports a count() method
                count = await cursor.count()
                assert count == 10
                count_with_limit_and_skip = await cursor.count(with_limit_and_skip=True)
                assert count_with_limit_and_skip == 4
            else:
                assert (await Student.count_documents()) == 10
                assert (await Student.count_documents(limit=5, skip=6)) == 4

            # to_list with callback should fail
            error = NotImplementedError if MOTOR_VERSION < (2, 0, 0) else TypeError
            with pytest.raises(error):
                await cursor.to_list(length=100, callback=lambda r, e: r if r else e)

            # Make sure returned documents are wrapped
            names = []
            for elem in (await cursor.to_list(length=100)):
                assert isinstance(elem, Student)
                names.append(elem.name)
            assert sorted(names) == ['student-%s' % i for i in range(6, 10)]

            # Try with fetch_next as well
            names = []
            cursor.rewind()
            while (await cursor.fetch_next):
                elem = cursor.next_object()
                assert isinstance(elem, Student)
                names.append(elem.name)
            assert sorted(names) == ['student-%s' % i for i in range(6, 10)]

            # Try with each as well
            names = []
            cursor.rewind()
            future = asyncio.Future()

            def callback(result, error):
                if error:
                    future.set_exception(error)
                elif result is None:
                    # Iteration complete
                    future.set_result(names)
                else:
                    names.append(result.name)

            cursor.each(callback=callback)
            await future
            assert sorted(names) == ['student-%s' % i for i in range(6, 10)]

            # Make sure this kind of notation doesn't create new cursor
            cursor = Student.find()
            cursor_limit = cursor.limit(5)
            cursor_skip = cursor.skip(6)
            assert cursor is cursor_limit is cursor_skip

            # Test clone&rewind as well
            cursor = Student.find()
            cursor2 = cursor.clone()
            await cursor.fetch_next
            await cursor2.fetch_next
            cursor_student = cursor.next_object()
            cursor2_student = cursor2.next_object()
            assert cursor_student == cursor2_student

            # Filter + projection
            cursor = Student.find({'name': 'student-0'}, ['name'])
            students = list(await cursor.to_list(length=100))
            assert len(students) == 1
            assert students[0].name == 'student-0'

        loop.run_until_complete(do_test())

    def test_classroom(self, loop, classroom_model):

        async def do_test():

            student = classroom_model.Student(name='Marty McFly', birthday=datetime(1968, 6, 9))
            await student.commit()
            teacher = classroom_model.Teacher(name='M. Strickland')
            await teacher.commit()
            course = classroom_model.Course(name='Hoverboard 101', teacher=teacher)
            await course.commit()
            assert student.courses is None
            student.courses = []
            assert student.courses == []
            student.courses.append(course)
            await student.commit()
            assert student.to_mongo() == {
                '_id': student.pk,
                'name': 'Marty McFly',
                'birthday': datetime(1968, 6, 9),
                'courses': [course.pk]
            }

        loop.run_until_complete(do_test())

    def test_validation_on_commit(self, loop, instance):

        async def do_test():

            async def io_validate(field, value):
                raise exceptions.ValidationError('Ho boys !')

            @instance.register
            class Dummy(Document):
                required_name = fields.StrField(required=True)
                always_io_fail = fields.IntField(io_validate=io_validate)

            with pytest.raises(exceptions.ValidationError) as exc:
                await Dummy().commit()
            assert exc.value.messages == {'required_name': ['Missing data for required field.']}
            with pytest.raises(exceptions.ValidationError) as exc:
                await Dummy(required_name='required', always_io_fail=42).commit()
            assert exc.value.messages == {'always_io_fail': ['Ho boys !']}

            dummy = Dummy(required_name='required')
            await dummy.commit()
            del dummy.required_name
            with pytest.raises(exceptions.ValidationError) as exc:
                await dummy.commit()
            assert exc.value.messages == {'required_name': ['Missing data for required field.']}

        loop.run_until_complete(do_test())

    def test_reference(self, loop, classroom_model):

        async def do_test():

            teacher = classroom_model.Teacher(name='M. Strickland')
            await teacher.commit()
            course = classroom_model.Course(name='Hoverboard 101', teacher=teacher)
            await course.commit()
            assert isinstance(course.teacher, Reference)
            teacher_fetched = await course.teacher.fetch()
            assert teacher_fetched == teacher
            # Change in referenced document is not seen until referenced
            # document is committed and referencer is reloaded
            teacher.name = 'Dr. Brown'
            teacher_fetched = await course.teacher.fetch()
            assert teacher_fetched.name == 'M. Strickland'
            await teacher.commit()
            teacher_fetched = await course.teacher.fetch()
            assert teacher_fetched.name == 'M. Strickland'
            await course.reload()
            teacher_fetched = await course.teacher.fetch()
            assert teacher_fetched.name == 'Dr. Brown'
            # But we can force reload as soon as referenced document is committed
            # without having to reload the whole referencer
            teacher.name = 'M. Strickland'
            teacher_fetched = await course.teacher.fetch()
            assert teacher_fetched.name == 'Dr. Brown'
            teacher_fetched = await course.teacher.fetch(force_reload=True)
            assert teacher_fetched.name == 'Dr. Brown'
            await teacher.commit()
            teacher_fetched = await course.teacher.fetch()
            assert teacher_fetched.name == 'Dr. Brown'
            teacher_fetched = await course.teacher.fetch(force_reload=True)
            assert teacher_fetched.name == 'M. Strickland'
            # Test bad ref as well
            course.teacher = Reference(classroom_model.Teacher, ObjectId())
            with pytest.raises(exceptions.ValidationError) as exc:
                await course.io_validate()
            assert exc.value.messages == {'teacher': ['Reference not found for document Teacher.']}

        loop.run_until_complete(do_test())

    def test_io_validate(self, loop, instance, classroom_model):

        async def do_test():

            Student = classroom_model.Student

            io_field_value = 'io?'
            io_validate_called = False

            async def io_validate(field, value):
                assert field == IOStudent.schema.fields['io_field']
                assert value == io_field_value
                nonlocal io_validate_called
                io_validate_called = True

            @instance.register
            class IOStudent(Student):
                io_field = fields.StrField(io_validate=io_validate)

            student = IOStudent(name='Marty', io_field=io_field_value)
            assert not io_validate_called

            await student.io_validate()
            assert io_validate_called

        loop.run_until_complete(do_test())

    def test_io_validate_error(self, loop, instance, classroom_model):

        async def do_test():

            Student = classroom_model.Student

            async def io_validate(field, value):
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
                await student.io_validate()
            assert exc.value.messages == {
                'io_field': ['Ho boys !'],
                'list_io_field': {0: ['Ho boys !'], 1: ['Ho boys !']},
                'reference_io_field': ['Ho boys !', 'Reference not found for document Course.'],
                'embedded_io_field': {'io_field': ['Ho boys !']}
            }

        loop.run_until_complete(do_test())

    def test_io_validate_multi_validate(self, loop, instance, classroom_model):

        async def do_test():

            Student = classroom_model.Student
            called = []

            future1 = asyncio.Future()
            future2 = asyncio.Future()
            future3 = asyncio.Future()
            future4 = asyncio.Future()

            async def io_validate11(field, value):
                called.append(1)
                future1.set_result(None)
                await future3
                called.append(4)
                future4.set_result(None)

            async def io_validate12(field, value):
                await future4
                called.append(5)

            async def io_validate21(field, value):
                await future2
                called.append(3)
                future3.set_result(None)

            async def io_validate22(field, value):
                await future1
                called.append(2)
                future2.set_result(None)

            @instance.register
            class IOStudent(Student):
                io_field1 = fields.StrField(io_validate=(io_validate11, io_validate12))
                io_field2 = fields.StrField(io_validate=(io_validate21, io_validate22))

            student = IOStudent(name='Marty', io_field1='io1', io_field2='io2')
            await student.io_validate()
            assert called == [1, 2, 3, 4, 5]

        loop.run_until_complete(do_test())

    def test_io_validate_list(self, loop, instance, classroom_model):

        async def do_test():

            Student = classroom_model.Student
            called = []

            values = [1, 2, 3, 4]
            total = len(values)
            futures = [asyncio.Future() for _ in range(total * 2)]

            async def io_validate(field, value):
                futures[total - value + 1].set_result(None)
                await futures[value]
                called.append(value)

            @instance.register
            class IOStudent(Student):
                io_field = fields.ListField(fields.IntField(io_validate=io_validate))

            student = IOStudent(name='Marty', io_field=values)
            await student.io_validate()
            assert set(called) == set(values)

        loop.run_until_complete(do_test())

    def test_indexes(self, loop, instance):

        async def do_test():

            @instance.register
            class SimpleIndexDoc(Document):
                indexed = fields.StrField()
                no_indexed = fields.IntField()

                class Meta:
                    indexes = ['indexed']

            await SimpleIndexDoc.collection.drop_indexes()

            # Now ask for indexes building
            await SimpleIndexDoc.ensure_indexes()
            indexes = await SimpleIndexDoc.collection.index_information()
            expected_indexes = {
                '_id_': {
                    'key': [('_id', 1)],
                },
                'indexed_1': {
                    'key': [('indexed', 1)],
                }
            }
            assert _stripped(indexes) == expected_indexes

            # Redoing indexes building should do nothing
            await SimpleIndexDoc.ensure_indexes()
            indexes = await SimpleIndexDoc.collection.index_information()
            assert _stripped(indexes) == expected_indexes

        loop.run_until_complete(do_test())

    def test_indexes_inheritance(self, loop, instance):

        async def do_test():

            @instance.register
            class SimpleIndexDoc(Document):
                indexed = fields.StrField()
                no_indexed = fields.IntField()

                class Meta:
                    indexes = ['indexed']

            await SimpleIndexDoc.collection.drop_indexes()

            # Now ask for indexes building
            await SimpleIndexDoc.ensure_indexes()
            indexes = await SimpleIndexDoc.collection.index_information()
            expected_indexes = {
                '_id_': {
                    'key': [('_id', 1)],
                },
                'indexed_1': {
                    'key': [('indexed', 1)],
                }
            }
            assert _stripped(indexes) == expected_indexes

            # Redoing indexes building should do nothing
            await SimpleIndexDoc.ensure_indexes()
            indexes = await SimpleIndexDoc.collection.index_information()
            assert _stripped(indexes) == expected_indexes

        loop.run_until_complete(do_test())

    def test_unique_index(self, loop, instance):

        async def do_test():

            @instance.register
            class UniqueIndexDoc(Document):
                not_unique = fields.StrField(unique=False)
                sparse_unique = fields.IntField(unique=True)
                required_unique = fields.IntField(unique=True, required=True)

            await UniqueIndexDoc.collection.drop()
            await UniqueIndexDoc.collection.drop_indexes()

            # Now ask for indexes building
            await UniqueIndexDoc.ensure_indexes()
            indexes = await UniqueIndexDoc.collection.index_information()
            expected_indexes = {
                '_id_': {
                    'key': [('_id', 1)],
                },
                'required_unique_1': {
                    'key': [('required_unique', 1)],
                    'unique': True
                },
                'sparse_unique_1': {
                    'key': [('sparse_unique', 1)],
                    'unique': True,
                    'sparse': True
                }
            }
            assert _stripped(indexes) == expected_indexes

            # Redoing indexes building should do nothing
            await UniqueIndexDoc.ensure_indexes()
            indexes = await UniqueIndexDoc.collection.index_information()
            assert _stripped(indexes) == expected_indexes

            await UniqueIndexDoc(not_unique='a', required_unique=1).commit()
            await UniqueIndexDoc(not_unique='a', sparse_unique=1, required_unique=2).commit()
            with pytest.raises(exceptions.ValidationError) as exc:
                await UniqueIndexDoc(not_unique='a', required_unique=1).commit()
            assert exc.value.messages == {'required_unique': 'Field value must be unique.'}
            with pytest.raises(exceptions.ValidationError) as exc:
                await UniqueIndexDoc(not_unique='a', sparse_unique=1, required_unique=3).commit()
            assert exc.value.messages == {'sparse_unique': 'Field value must be unique.'}

        loop.run_until_complete(do_test())

    def test_unique_index_compound(self, loop, instance):

        async def do_test():

            @instance.register
            class UniqueIndexCompoundDoc(Document):
                compound1 = fields.IntField()
                compound2 = fields.IntField()
                not_unique = fields.StrField()

                class Meta:
                    # Must define custom index to do that
                    indexes = [{'key': ('compound1', 'compound2'), 'unique': True}]

            await UniqueIndexCompoundDoc.collection.drop()
            await UniqueIndexCompoundDoc.collection.drop_indexes()

            # Now ask for indexes building
            await UniqueIndexCompoundDoc.ensure_indexes()
            indexes = await UniqueIndexCompoundDoc.collection.index_information()
            # Must sort compound indexes to avoid random inconsistence
            indexes['compound1_1_compound2_1']['key'] = sorted(indexes['compound1_1_compound2_1']['key'])
            expected_indexes = {
                '_id_': {
                    'key': [('_id', 1)],
                },
                'compound1_1_compound2_1': {
                    'key': [('compound1', 1), ('compound2', 1)],
                    'unique': True
                }
            }
            assert _stripped(indexes) == expected_indexes

            # Redoing indexes building should do nothing
            await UniqueIndexCompoundDoc.ensure_indexes()
            indexes = await UniqueIndexCompoundDoc.collection.index_information()
            # Must sort compound indexes to avoid random inconsistence
            indexes['compound1_1_compound2_1']['key'] = sorted(indexes['compound1_1_compound2_1']['key'])
            assert _stripped(indexes) == expected_indexes

            # Index is on the tuple (compound1, compound2)
            await UniqueIndexCompoundDoc(not_unique='a', compound1=1, compound2=1).commit()
            await UniqueIndexCompoundDoc(not_unique='a', compound1=1, compound2=2).commit()
            await UniqueIndexCompoundDoc(not_unique='a', compound1=2, compound2=1).commit()
            await UniqueIndexCompoundDoc(not_unique='a', compound1=2, compound2=2).commit()
            with pytest.raises(exceptions.ValidationError) as exc:
                await UniqueIndexCompoundDoc(not_unique='a', compound1=1, compound2=1).commit()
            assert exc.value.messages == {
                'compound2': "Values of fields ['compound1', 'compound2'] must be unique together.",
                'compound1': "Values of fields ['compound1', 'compound2'] must be unique together."
            }
            with pytest.raises(exceptions.ValidationError) as exc:
                await UniqueIndexCompoundDoc(not_unique='a', compound1=2, compound2=1).commit()
            assert exc.value.messages == {
                'compound2': "Values of fields ['compound1', 'compound2'] must be unique together.",
                'compound1': "Values of fields ['compound1', 'compound2'] must be unique together."
            }

        loop.run_until_complete(do_test())

    @pytest.mark.xfail
    def test_unique_index_inheritance(self, loop, instance):

        async def do_test():

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

            await UniqueIndexChildDoc.collection.drop_indexes()

            # Now ask for indexes building
            await UniqueIndexChildDoc.ensure_indexes()
            indexes = [e async for e in UniqueIndexChildDoc.collection.list_indexes()]
            expected_indexes = [
                {
                    'key': {'_id': 1},
                    'name': '_id_',
                    'ns': '%s.unique_index_inheritance_doc' % TEST_DB,
                },
                {
                    'key': {'unique': 1},
                    'name': 'unique_1',
                    'unique': True,
                    'ns': '%s.unique_index_inheritance_doc' % TEST_DB
                },
                {
                    'key': {'manual_index': 1, '_cls': 1},
                    'name': 'manual_index_1__cls_1',
                    'ns': '%s.unique_index_inheritance_doc' % TEST_DB
                },
                {
                    'key': {'_cls': 1},
                    'name': '_cls_1',
                    'unique': True,
                    'ns': '%s.unique_index_inheritance_doc' % TEST_DB
                },
                {
                    'key': {'child_unique': 1, '_cls': 1},
                    'name': 'child_unique_1__cls_1',
                    'unique': True,
                    'ns': '%s.unique_index_inheritance_doc' % TEST_DB
                }
            ]
            assert name_sorted(indexes) == name_sorted(expected_indexes)

            # Redoing indexes building should do nothing
            await UniqueIndexChildDoc.ensure_indexes()
            indexes = [e for e in (await UniqueIndexChildDoc.collection.list_indexes())]
            assert name_sorted(indexes) == name_sorted(expected_indexes)

        loop.run_until_complete(do_test())

    def test_inheritance_search(self, loop, instance):

        async def do_test():

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

            await InheritanceSearchParent.collection.drop()

            await InheritanceSearchParent(pf=0).commit()
            await InheritanceSearchChild1(pf=1, c1f=1).commit()
            await InheritanceSearchChild1Child(pf=1, sc1f=1).commit()
            await InheritanceSearchChild2(pf=2, c2f=2).commit()

            assert (await InheritanceSearchParent.count_documents()) == 4
            assert (await InheritanceSearchChild1.count_documents()) == 2
            assert (await InheritanceSearchChild1Child.count_documents()) == 1
            assert (await InheritanceSearchChild2.count_documents()) == 1

            res = await InheritanceSearchParent.find_one({'sc1f': 1})
            assert isinstance(res, InheritanceSearchChild1Child)

            cursor = InheritanceSearchParent.find({'pf': 1})
            for r in (await cursor.to_list(length=100)):
                assert isinstance(r, InheritanceSearchChild1)

            isc = InheritanceSearchChild1(pf=2, c1f=2)
            await isc.commit()
            res = await InheritanceSearchChild1.find_one(isc.id)
            assert res == isc

            res = await InheritanceSearchChild1.find_one(isc.id, ['c1f'])
            assert res.c1f == 2

        loop.run_until_complete(do_test())

    def test_search(self, loop, instance):

        async def do_test():

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

            await Book.collection.drop()
            await Book(
                title='The Hobbit',
                author={'name': 'JRR Tolkien'},
                chapters=[
                    {'name': 'An Unexpected Party'},
                    {'name': 'Roast Mutton'},
                    {'name': 'A Short Rest'},
                    {'name': 'Over Hill And Under Hill'},
                    {'name': 'Riddles In The Dark'}
                ]
            ).commit()
            await Book(
                title="Harry Potter and the Philosopher's Stone",
                author={'name': 'JK Rowling'},
                chapters=[
                    {'name': 'The Boy Who Lived'},
                    {'name': 'The Vanishing Glass'},
                    {'name': 'The Letters from No One'},
                    {'name': 'The Keeper of the Keys'},
                    {'name': 'Diagon Alley'}
                ]
            ).commit()
            await Book(
                title='A Game of Thrones',
                author={'name': 'George RR Martin'},
                chapters=[
                    {'name': 'Prologue'},
                    {'name': 'Bran I'},
                    {'name': 'Catelyn I'},
                    {'name': 'Daenerys I'},
                    {'name': 'Eddard I'},
                    {'name': 'Jon I'}
                ]
            ).commit()

            res = await Book.count_documents({'title': 'The Hobbit'})
            assert res == 1
            res = await Book.count_documents({'author.name': {'$in': ['JK Rowling', 'JRR Tolkien']}})
            assert res == 2
            res = await Book.count_documents({'$and': [{'chapters.name': 'Roast Mutton'}, {'title': 'The Hobbit'}]})
            assert res == 1
            res = await Book.count_documents({'chapters.name': {'$all': ['Roast Mutton', 'A Short Rest']}})
            assert res == 1

        loop.run_until_complete(do_test())

    def test_pre_post_hooks(self, loop, instance):

        async def do_test():

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
            await p.commit()
            assert callbacks == ['pre_insert', 'post_insert']

            callbacks.clear()
            p.age = 22
            await p.commit({'age': 22})
            assert callbacks == ['pre_update', 'post_update']

            callbacks.clear()
            await p.delete()
            assert callbacks == ['pre_delete', 'post_delete']

        loop.run_until_complete(do_test())

    def test_pre_post_hooks_with_defers(self, loop, instance):

        async def do_test():

            events = []

            @instance.register
            class Person(Document):
                name = fields.StrField()
                age = fields.IntField()

                async def pre_insert(self):
                    events.append('start pre_insert')
                    future = asyncio.Future()
                    future.set_result(True)
                    await future
                    events.append('end pre_insert')

                async def post_insert(self, ret):
                    events.append('start post_insert')
                    future = asyncio.Future()
                    future.set_result(True)
                    await future
                    events.append('end post_insert')

            p = Person(name='John', age=20)
            await p.commit()
            assert events == [
                'start pre_insert',
                'end pre_insert',
                'start post_insert',
                'end post_insert'
            ]

        loop.run_until_complete(do_test())

    def test_modify_in_pre_hook(self, loop, instance):

        async def do_test():

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
            await p.commit()

            assert p.version == 1
            p_concurrent = await Person.find_one(p.pk)

            p.age = 22
            await p.commit()
            assert p.version == 2

            # Concurrent should not be able to commit it modifications
            p_concurrent.name = 'John'
            with pytest.raises(exceptions.UpdateError):
                await p_concurrent.commit()

            await p_concurrent.reload()
            assert p_concurrent.version == 2

            p.age = 24
            await p.commit()
            assert p.version == 3
            await p.delete()
            await p.commit()
            with pytest.raises(exceptions.DeleteError):
                await p_concurrent.delete()
            await p.delete()

        loop.run_until_complete(do_test())
