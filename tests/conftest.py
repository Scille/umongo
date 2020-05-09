import pytest
from datetime import datetime
from functools import namedtuple

from umongo import Document, fields
from umongo.instance import Instance


@pytest.fixture
def instance(db):
    # `db` should be a fixture provided by the current framework's testbench
    return Instance(db)


@pytest.fixture
def classroom_model(instance):

    @instance.register
    class Teacher(Document):
        name = fields.StrField(required=True)

    @instance.register
    class Course(Document):
        name = fields.StrField(required=True)
        teacher = fields.ReferenceField(Teacher, required=True)

    @instance.register
    class Student(Document):
        name = fields.StrField(required=True)
        birthday = fields.DateTimeField(default=datetime(1995, 12, 26))
        courses = fields.ListField(fields.ReferenceField(Course))

    return namedtuple('Mapping', ('Teacher', 'Course', 'Student'))(Teacher, Course, Student)
