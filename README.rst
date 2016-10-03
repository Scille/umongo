======================
μMongo: sync/async ODM
======================

.. image:: https://img.shields.io/pypi/v/umongo.svg
        :target: https://pypi.python.org/pypi/umongo

.. image:: https://img.shields.io/travis/Scille/umongo.svg
        :target: https://travis-ci.org/Scille/umongo

.. image:: https://readthedocs.org/projects/umongo/badge/?version=latest
        :target: http://umongo.readthedocs.org/en/latest/?badge=latest
        :alt: Documentation Status

.. image:: https://coveralls.io/repos/github/Scille/umongo/badge.svg?branch=master
    :target: https://coveralls.io/github/Scille/umongo?branch=master
    :alt: Code coverage

μMongo is a Python MongoDB ODM. It inception comes from two needs:
the lack of async ODM and the difficulty to do document (un)serialization
with existing ODMs.

From this point, μMongo made a few design choices:

- Stay close to the standards MongoDB driver to keep the same API when possible:
  use ``find({"field": "value"})`` like usual but retrieve your data nicely OO wrapped !
- Work with multiple drivers (PyMongo_, TxMongo_, motor_asyncio_ and mongomock_ for the moment)
- Tight integration with Marshmallow_ serialization library to easily
  dump and load your data with the outside world
- i18n integration to localize validation error messages
- Free software: MIT license
- Test with 90%+ coverage ;-)

.. _PyMongo: https://api.mongodb.org/python/current/
.. _TxMongo: https://txmongo.readthedocs.org/en/latest/
.. _motor_asyncio: https://motor.readthedocs.org/en/stable/
.. _mongomock: https://github.com/vmalloc/mongomock
.. _Marshmallow: http://marshmallow.readthedocs.org

Quick example

.. code-block:: python

    from datetime import datetime
    from pymongo import MongoClient
    from umongo import Instance, Document, fields, validate

    db = MongoClient().test
    instance = Instance(db)

    @instance.register
    class User(Document):
        email = fields.EmailField(required=True, unique=True)
        birthday = fields.DateTimeField(validate=validate.Range(min=datetime(1900, 1, 1)))
        friends = fields.ListField(fields.ReferenceField("User"))

        class Meta:
            collection = db.user

    goku = User(email='goku@sayen.com', birthday=datetime(1984, 11, 20))
    goku.commit()
    vegeta = User(email='vegeta@over9000.com', friends=[goku])
    vegeta.commit()

    vegeta.friends
    # <object umongo.data_objects.List([<object umongo.dal.pymongo.PyMongoReference(document=User, pk=ObjectId('5717568613adf27be6363f78'))>])>
    vegeta.dump()
    # {id': '570ddb311d41c89cabceeddc', 'email': 'vegeta@over9000.com', friends': ['570ddb2a1d41c89cabceeddb']}
    User.find_one({"email": 'goku@sayen.com'})
    # <object Document __main__.User({'id': ObjectId('570ddb2a1d41c89cabceeddb'), 'friends': <object umongo.data_objects.List([])>,
    #                                 'email': 'goku@sayen.com', 'birthday': datetime.datetime(1984, 11, 20, 0, 0)})>

Get it now::

    $ pip install umongo
    $ pip install my-mongo-driver  # Note you have to manually install the mongodb driver

Or to get it along with the MongoDB driver you're planing to use::

    $ pip install umongo[pymongo]   # choose
    $ pip install umongo[motor]     # one
    $ pip install umongo[txmongo]   # of
    $ pip install umongo[mongomock] # them ;-)
