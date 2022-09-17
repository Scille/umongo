import pytest

from pymongo import MongoClient

from umongo.frameworks import pymongo as framework_pymongo  # noqa
from umongo.frameworks.tools import cook_find_projection

from ..common import TEST_DB


# All dependencies here are mandatory
dep_error = None


def make_db():
    return MongoClient()[TEST_DB]


@pytest.fixture
def db():
    return make_db()


def test_cook_find_projection(classroom_model):
    projection = {'has_apple': 0}
    cooked = cook_find_projection(classroom_model.Teacher, projection=projection)
    assert cooked == {'_has_apple': 0}

    projection = ['has_apple']
    cooked = cook_find_projection(classroom_model.Teacher, projection=projection)
    assert cooked == {'_has_apple': 1}

    projection = ['name', 'has_apple']
    cooked = cook_find_projection(classroom_model.Teacher, projection=projection)
    assert cooked == {'name': 1, '_has_apple': 1}

    # projection into a nested document's field which has a specified `attribute`
    projection = ['room.seats']
    cooked = cook_find_projection(classroom_model.Course, projection=projection)
    assert cooked == {'room._seats': 1}

    projection = {'room.seats': 0}
    cooked = cook_find_projection(classroom_model.Course, projection=projection)
    assert cooked == {'room._seats': 0}
