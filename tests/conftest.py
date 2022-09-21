import pytest
from functools import namedtuple

from umongo import Document, EmbeddedDocument, fields
from umongo.instance import Instance


@pytest.fixture
def instance(db):
    # `db` should be a fixture provided by the current framework's testbench
    return Instance.from_db(db)


@pytest.fixture
def classroom_model(instance):

    @instance.register
    class Teacher(Document):
        name = fields.StrField(required=True)
        has_apple = fields.BooleanField(required=False, attribute='_has_apple')

    @instance.register
    class Room(EmbeddedDocument):
        seats = fields.IntField(required=True, attribute='_seats')

    @instance.register
    class Course(Document):
        name = fields.StrField(required=True)
        teacher = fields.ReferenceField(Teacher, required=True, allow_none=True)
        room = fields.EmbeddedField(Room, required=False, allow_none=True)

    @instance.register
    class Student(Document):
        name = fields.StrField(required=True)
        birthday = fields.DateTimeField()
        courses = fields.ListField(fields.ReferenceField(Course))

    Mapping = namedtuple('Mapping', ('Teacher', 'Course', 'Student', 'Room'))
    return Mapping(Teacher, Course, Student, Room)
