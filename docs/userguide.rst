.. _userguide:

==========
User guide
==========

Base concepts
=============


In μMongo 3 worlds are considered:

.. figure:: data_flow.png
   :alt: data flow in μMongo


Client world
------------

This is the data from outside μMongo, it can be a JSON dict from your web framework
(i.g. ``request.get_json()`` with `flask <http://flask.palletsprojects.com/>`_ or
``json.loads(request.raw_post_data)`` in `django <https://www.djangoproject.com/>`_)
or it could be a regular Python dict with Python-typed data.

JSON dict example

.. code-block:: python

    >>> {"str_field": "hello world", "int_field": 42, "date_field": "2015-01-01T00:00:00Z"}

Python dict example

.. code-block:: python

    >>> {"str_field": "hello world", "int_field": 42, "date_field": datetime(2015, 1, 1)}

To be integrated into μMongo, those data need to be deserialized and to leave
μMongo they need to be serialized (under the hood μMongo uses
`marshmallow <http://marshmallow.readthedocs.org/>`_ schema).

The deserialization operation is done automatically when instantiating a
:class:`umongo.Document`. The serialization is done when calling
:meth:`umongo.Document.dump` on a document instance.

Object Oriented world
---------------------

:class:`umongo.Document` allows you to work with your data as objects and to
guarantee their validity against a model.

First let's define a document with few :mod:`umongo.fields`

.. code-block:: python

    @instance.register
    class Dog(Document):
        name = fields.StrField(required=True)
        breed = fields.StrField(default="Mongrel")
        birthday = fields.DateTimeField()

Don't pay attention to the ``@instance.register`` for now.

Note that each field can be customized with special attributes like
``required`` (which is pretty self-explanatory) or ``default`` (if the
field is missing during deserialization it will take this value).

Now we can play back and forth between OO and client worlds

.. code-block:: python

    >>> client_data = {'name': 'Odwin', 'birthday': '2001-09-22T00:00:00Z'}
    >>> odwin = Dog(**client_data)
    >>> odwin.breed
    "Mongrel"
    >>> odwin.birthday
    datetime.datetime(2001, 9, 22, 0, 0)
    >>> odwin.breed = "Labrador"
    >>> odwin.dump()
    {'birthday': '2001-09-22T00:00:00+00:00', 'breed': 'Labrador', 'name': 'Odwin'}

.. note:: You can access the data as attribute (i.g. ``odwin.name``) or as item (i.g. ``odwin['name']``).
          The latter is specially useful if one of your field name clashes
          with :class:`umongo.Document`'s attributes.

OO world enforces model validation for each modification

.. code-block:: python

    >>> odwin.bad_field = 42
    [...]
    AttributeError: bad_field
    >>> odwin.birthday = "not_a_date"
    [...]
    ValidationError: "Not a valid datetime."

.. note: Just one exception: ``required`` attribute is validate at insertion time, we'll talk about that later.

Object orientation means inheritance, of course you can do that

.. code-block:: python

    @instance.register
    class Animal(Document):
        breed = fields.StrField()
        birthday = fields.DateTimeField()

        class Meta:
            abstract = True

    @instance.register
    class Dog(Animal):
        name = fields.StrField(required=True)

    @instance.register
    class Duck(Animal):
        pass

The ``Meta`` subclass is used (along with inherited Meta classes from parent
documents) to configure the document class, you can access this final config
through the ``opts`` attribute.

Here we use this to allow ``Animal`` to be inherited and to make it abstract.

.. code-block:: python

    >>> Animal.opts
    <DocumentOpts(instance=<umongo.frameworks.PyMongoInstance object at 0x7efe7daa9320>, template=<Document template class '__main__.Animal'>, abstract=True, collection_name=None, is_child=False, base_schema_cls=<class 'umongo.schema.Schema'>, indexes=[], offspring={<Implementation class '__main__.Duck'>, <Implementation class '__main__.Dog'>})>
    >>> Dog.opts
    <DocumentOpts(instance=<umongo.frameworks.PyMongoInstance object at 0x7efe7daa9320>, template=<Document template class '__main__.Dog'>, abstract=False, collection_name=dog, is_child=False, base_schema_cls=<class 'umongo.schema.Schema'>, indexes=[], offspring=set())>
    >>> class NotAllowedSubDog(Dog): pass
    [...]
    DocumentDefinitionError: Document <class '__main__.Dog'> doesn't allow inheritance
    >>> Animal(breed="Mutant")
    [...]
    AbstractDocumentError: Cannot instantiate an abstract Document


Mongo world
-----------

Mongo world consist of data returned in a format suitable for a MongoDB
driver (`pymongo <https://api.mongodb.org/python/current/>`_ for instance).

.. code-block:: python

    >>> odwin.to_mongo()
    {'birthday': datetime.datetime(2001, 9, 22, 0, 0), 'name': 'Odwin'}

In this case, the data is unchanged. Let's consider something more complex:

.. code-block:: python

    @instance.register
    class Dog(Document):
        name = fields.StrField(attribute='_id')

We use the name of the dog as our ``_id`` key, but for readability we keep it
as ``name`` inside our document.

.. code-block:: python

    >>> odwin = Dog(name='Odwin')
    >>> odwin.dump()
    {'name': 'Odwin'}
    >>> odwin.to_mongo()
    {'_id': 'Odwin'}
    >>> Dog.build_from_mongo({'_id': 'Scruffy'}).dump()
    {'name': 'Scruffy'}

.. note::
    If no field refers to ``_id`` in the document, a dump-only field ``id``
    will be automatically added:

    .. code-block:: python

        >>> class AutoId(Document):
        ...     pass
        >>> AutoId.find_one()
        <object Document __main__.AutoId({'id': ObjectId('5714b9a61d41c8feb01222c8')})>

To retrieve the ``_id`` field whatever its name is, use the ``pk`` property:

.. code-block:: python

    >>> odwin.pk
    'Odwin'
    >>> Duck().pk
    None

Most of the time, the user doesn't need to use ``to_mongo`` directly. It is
called internally by :meth:`umongo.Document.commit`` which is the method used
to commit changes to the database.

.. code-block:: python

    >>> odwin = Dog(name='Odwin', breed='Labrador')
    >>> odwin.commit()

μMongo provides access to Object Oriented versions of driver methods:

.. code-block:: python

    >>> Dog.find()
    <umongo.dal.pymongo.WrappedCursor object at 0x7f169851ba68>
    >>> next(Dog.find())
    <object Document __main__.Dog({'id': 'Odwin', 'breed': 'Labrador'})>
    Dog.find_one({'_id': 'Odwin'})
    <object Document __main__.Dog({'id': 'Odwin', 'breed': 'Labrador'})>

The user can also access the collection used by the document at any time
to perform more low-level operations:

.. code-block:: python

    >>> Dog.collection
    Collection(Database(MongoClient(host=['localhost:27017'], document_class=dict, tz_aware=False, connect=True), 'test'), 'dog')

.. note::
    By default the collection to use is the snake-cased version of the
    document's name (e.g. ``Dog`` => ``dog``, ``HTTPError`` => ``http_error``).
    However, you can configure, through the ``Meta`` class, the collection
    to use for a document with the ``collection_name`` meta attribute.


Multi-driver support
====================

The idea behind μMongo is to allow the same document definition to be used
with different MongoDB drivers.

To achieve that the user only defines document templates. Templates which
will be implemented when registered by an instance:

.. figure:: instance_template.png
   :alt: instance/template mechanism in μMongo

Basically an instance provide three informations:

- the mongoDB driver type to use
- the database to use
- the implemented documents

This way a template can be implemented by multiple instances, this can be
useful for example to:

- store the same documents in differents databases
- define an instance with async driver for a web server and a
  sync one for shell interactions

Here's how to create and use an instance:

.. code-block:: python

    >>> from umongo.frameworks import PyMongoInstance
    >>> import pymongo
    >>> con = pymongo.MongoClient()
    >>> instance1 = PyMongoInstance(con.db1)
    >>> instance2 = PyMongoInstance(con.db2)

Now we can define & register documents, then work with them:

.. code-block:: python

    >>> class Dog(Document):
    ...     pass
    >>> Dog  # mark as a template in repr
    <Template class '__main__.Dog'>
    >>> Dog.is_template
    True
    >>> DogInstance1Impl = instance1.register(Dog)
    >>> DogInstance1Impl  # mark as an implementation in repr
    <Implementation class '__main__.Dog'>
    >>> DogInstance1Impl.is_template
    False
    >>> DogInstance2Impl = instance2.register(Dog)
    >>> DogInstance1Impl().commit()
    >>> DogInstance1Impl.count_documents()
    1
    >>> DogInstance2Impl.count_documents()
    0

.. note::
    In most cases, only a single instance is used. In this case, one can use
    ``instance.register`` as a decoration to replace the template by its
    implementation.

    .. code-block:: python

        >>> @instance.register
        ... class Dog(Document):
        ...     pass
        >>> Dog().commit()

.. note::
    In real-life applications, the driver connection details may not be known
    when registering models. For instance, when using the Flask app factory
    pattern, one will instantiate the instance and register model documents
    at import time, then pass the database connection at app init time. This
    can be achieved with the ``set_db`` method. No database interaction can
    be performed until a database connection is set.

    .. code-block:: python

        >>> from umongo.frameworks import TxMongoInstance
        >>> # Don't pass a database connection when instantiating the instance
        >>> instance = TxMongoInstance()
        >>> @instance.register
        ... class Dog(Document):
        ...     pass
        >>> # Don't try to use Dog (except for inheritance) yet
        >>> # A database connection must be set first
        >>> db = create_txmongo_database()
        >>> instance.set_db(db)
        >>> # Now instance is ready
        >>> yield Dog().commit()


For the moment all examples have been done with pymongo. Things are pretty much
the same with other drivers, just configure the ``instance`` and you're good to go:

.. code-block:: python

    >>> from umongo.frameworks import MotorAsyncIOInstance
    >>> db = motor.motor_asyncio.AsyncIOMotorClient()['umongo_test']
    >>> instance = MotorAsyncIOInstance(db)
    >>> @instance.register
    ... class Dog(Document):
    ...     name = fields.StrField(attribute='_id')
    ...     breed = fields.StrField(default="Mongrel")

Of course the way you'll be calling methods will differ:

.. code-block:: python

    >>> odwin = Dog(name='Odwin', breed='Labrador')
    >>> yield from odwin.commit()
    >>> dogs = yield from Dog.find()


Inheritance
===========

Inheritance inside the same collection is achieve by adding a ``_cls`` field
(accessible in the document as ``cls``) in the document stored in MongoDB

.. code-block:: python

    >>> @instance.register
    ... class Parent(Document):
    ...     unique_in_parent = fields.IntField(unique=True)
    >>> @instance.register
    ... class Child(Parent):
    ...     unique_in_child = fields.StrField(unique=True)
    >>> child = Child(unique_in_parent=42, unique_in_child='forty_two')
    >>> child.cls
    'Child'
    >>> child.dump()
    {'cls': 'Child', 'unique_in_parent': 42, 'unique_in_child': 'forty_two'}
    >>> Parent(unique_in_parent=22).dump()
    {'unique_in_parent': 22}
    >>> [x.document for x in Parent.indexes]
    [{'key': SON([('unique_in_parent', 1)]), 'name': 'unique_in_parent_1', 'sparse': True, 'unique': True}]

.. warning:: You must ``register`` a parent before its child inside a given instance.

Due to the way document instances are created from templates, fields and
pre/post_dump/load methods can only be inherited from mixin classes by
explicitly using a :class:`umongo.MixinDocument`.

.. code-block:: python

    @instance.register
    class TimeMixin(MixinDocument):
        date_created = fields.DateTimeField()
        date_modified = fields.DateTimeField()

    @instance.register
    class MyDocument(Document, TimeMixin)
        name = fields.StringField()

A :class:`umongo.MixinDocument` can be inherited by both
:class:`umongo.Document` and :class:`umongo.EmbeddedDocument` classes.


Indexes
=======

.. warning:: Indexes must be first submitted to MongoDB. To do so you should
             call :meth:`umongo.Document.ensure_indexes` once for each document.


In fields, ``unique`` attribute is implicitly handled by an index:

.. code-block:: python

    >>> @instance.register
    ... class WithUniqueEmail(Document):
    ...     email = fields.StrField(unique=True)
    >>> [x.document for x in WithUniqueEmail.indexes]
    [{'key': SON([('email', 1)]), 'name': 'email_1', 'sparse': True, 'unique': True}]
    >>> WithUniqueEmail.ensure_indexes()
    >>> WithUniqueEmail().commit()
    >>> WithUniqueEmail().commit()
    [...]
    ValidationError: {'email': 'Field value must be unique'}

.. note:: The index params also depend of the ``required``, ``null`` field attributes

For more custom indexes, the ``Meta.indexes`` attribute should be used:

.. code-block:: python

    >>> @instance.register
    ... class CustomIndexes(Document):
    ...     name = fields.StrField()
    ...     age = fields.Int()
    ...     class Meta:
    ...         indexes = ('#name', 'age', ('-age', 'name'))
    >>> [x.document for x in CustomIndexes.indexes]
    [{'key': SON([('name', 'hashed')]), 'name': 'name_hashed'},
     {'key': SON([('age', 1), ]), 'name': 'age_1'},
     {'key': SON([('age', -1), ('name', 1)]), 'name': 'age_-1_name_1'}

.. note:: ``Meta.indexes`` should use the names of the fields as they appear
          in database (i.g. given a field ``nick = StrField(attribute='nk')``,
          you refer to it in ``Meta.indexes`` as ``nk``)

Indexes can be passed as:

- a string with an optional direction prefix (i.g. ``"my_field"``)
- a list of string with optional direction prefix for compound indexes
  (i.g. ``["field1", "-field2"]``)
- a :class:`pymongo.IndexModel` object
- a dict used to instantiate an :class:`pymongo.IndexModel` for custom configuration
  (i.g. ``{'key': ['field1', 'field2'], 'expireAfterSeconds': 42}``)

Allowed direction prefix are:
 - ``+`` for ascending
 - ``-`` for descending
 - ``$`` for text
 - ``#`` for hashed

.. note:: If no direction prefix is passed, ascending is assumed

In case of a field defined in a child document, its index is automatically
compounded with ``_cls``

.. code-block:: python

      >>> @instance.register
      ... class Parent(Document):
      ...     unique_in_parent = fields.IntField(unique=True)
      >>> @instance.register
      ... class Child(Parent):
      ...     unique_in_child = fields.StrField(unique=True)
      ...     class Meta:
      ...         indexes = ['#unique_in_parent']
      >>> [x.document for x in Child.indexes]
      [{'name': 'unique_in_parent_1', 'sparse': True, 'unique': True, 'key': SON([('unique_in_parent', 1)])},
       {'name': 'unique_in_parent_hashed__cls_1', 'key': SON([('unique_in_parent', 'hashed'), ('_cls', 1)])},
       {'name': '_cls_1', 'key': SON([('_cls', 1)])},
       {'name': 'unique_in_child_1__cls_1', 'sparse': True, 'unique': True, 'key': SON([('unique_in_child', 1), ('_cls', 1)])}]


I18n
====

μMongo provides a simple way to work with i18n (internationalization) through
the :func:`umongo.set_gettext`, for example to use python's default gettext:

.. code-block:: python

    from umongo import set_gettext
    from gettext import gettext
    set_gettext(gettext)

This way each error message will be passed to the custom ``gettext`` function
in order for it to return the localized version of it.

See `examples/flask <https://github.com/Scille/umongo/tree/master/examples/flask>`_
for a working example of i18n with `flask-babel <https://pythonhosted.org/Flask-Babel/>`_.

.. note::
    To set up i18n inside your app, you should start with `messages.pot
    <https://github.com/Scille/umongo/tree/master/messages.pot>`_ which is
    a translation template of all the messages used in umongo (and it dependancy marshmallow).


Marshmallow integration
=======================

Under the hood, μMongo heavily uses `marshmallow <http://marshmallow.readthedocs.org>`_
for all its data validation work.

However an ODM has some special needs (i.g. handling ``required`` fields through MongoDB's
unique indexes) that force to extend marshmallow base types.

In short, you should not try to use marshmallow base types (:class:`marshmallow.Schema`,
:class:`marshmallow.fields.Field` or :class:`marshmallow.validate.Validator` for instance)
in a μMongo document but instead use their μMongo equivalents (respectively
:class:`umongo.abstract.BaseSchema`, :class:`umongo.abstract.BaseField` and
:class:`umongo.abstract.BaseValidator`).

In the `Base concepts`_ paragraph, the schema contains a little simplification.
According to it, the client and OO worlds are made of the same data, but only
in a different form (serialized vs object oriented).
However, quite often, the application API doesn't strictly exposes the
datamodel (e.g. you don't want to display or allow modification
of the passwords in your `/users` route).

Back to our `Dog` document. In real life one can rename your dog but not change
its breed. The user API should have a schema that enforces this.

.. code-block:: python

    >>> DogMaSchema = Dog.schema.as_marshmallow_schema()

``as_marshmallow_schema`` convert the original µMongo schema into a pure
marshmallow schema that can be subclassed and customized:

.. code-block:: python

    >>> class PatchDogSchema(DogMaSchema):
    ...     class Meta:
    ...         fields = ('name', )
    >>> patch_dog_schema = PatchDogSchema()
    >>> patch_dog_schema.load({'name': 'Scruffy', 'breed': 'Golden retriever'}).errors
    {'_schema': ['Unknown field name breed.']}
    >>> ret = patch_dog_schema.load({'name': 'Scruffy'})
    >>> ret
    {'name': 'Scruffy'}

Finally we can integrate the validated data into OO world:

.. code-block:: python

    >>> my_dog.update(ret)
    >>> my_dog.name
    'Scruffy'

This works great when you want to add special behaviors depending of the situation.
For more simple usecases we could use the
`marshmallow pre/post precessors  <http://marshmallow.readthedocs.io/en/latest/extending.html#pre-processing-and-post-processing-methods>`_
. For example to simply customize the dump:

.. code-block:: python

    >>> from umongo import post_dump  # same as `from marshmallow import post_dump`
    >>> @instance.register
    ... class Dog(Document):
    ...     name = fields.StrField(required=True)
    ...     breed = fields.StrField(default="Mongrel")
    ...     birthday = fields.DateTimeField()
    ...     @post_dump
    ...     def customize_dump(self, data):
    ...         data['name'] = data['name'].capitalize()
    ...         data['brief'] = "Hi ! My name is %s and I'm a %s" % (data['name'], data['breed'])"
    ...
    >>> Dog(name='scruffy').dump()
    {'name': 'Scruffy', 'breed': 'Mongrel', 'brief': "Hi ! My name is Scruffy and I'm a Mongrel"}

Now let's imagine we want to allow the per-breed creation of a massive number of ducks.
The API would accept a really different format than our datamodel:

.. code-block:: python

    {
        'breeds': [
            {'name': 'Mandarin Duck', 'births': ['2016-08-29T00:00:00', '2016-08-31T00:00:00', ...]},
            {'name': 'Mallard', 'births': ['2016-08-27T00:00:00', ...]},
            ...
        ]
    }

Starting from the µMongo schema would not help, but one can create a new schema
using pure marshmallow fields generated with the
:meth:`umongo.BaseField.dump.as_marshmallow_field` method:

.. code-block:: python

    >>> MassiveBreedSchema(marshmallow.Schema):
    ...     name = Duck.schema.fields['breed'].as_marshmallow_field()
    ...     births = marshmallow.fields.List(
    ...         Duck.schema.fields['birthday'].as_marshmallow_field())
    >>> MassiveDuckSchema(marshmallow.Schema):
    ...     breeds = marshmallow.fields.List(marshmallow.fields.Nested(MassiveBreedSchema))

.. note:: A custom marshmallow schema :class:`umongo.schema.RemoveMissingSchema`
    can be used instead of regular :class:`marshmallow.Schema` to skip missing fields
    when dumping a :class:`umongo.Document` object.


.. code-block:: python

    try:
        data, _ = MassiveDuckSchema().load(payload)
        ducks = []
        for breed in data['breeds']:
            for birthday in breed['births']:
                duck = Duck(breed=breed['name']), birthday=birthday)
                duck.commit()
                ducks.append(duck)
    except ValidationError as e:
        # Error handling
        ...

.. note:: Field's ``missing`` and ``default`` attributes are not handled the
   same in marshmallow and umongo.

  In marshmallow ``default`` contains the value to use during serialization
  (i.e. calling ``schema.dump(doc)``) and ``missing`` the value for deserialization.

  In umongo however there is only a ``default`` attribute which will be used when
  creating (or loading from user world) a document where this field is missing.
  This is because you don't need to control how umongo will store the document in
  mongo world.

  So when you use ``as_marshmallow_field``, the resulting marshmallow field's
  ``missing``&``default`` will be by default both infered from the umongo's
  ``default`` field. You can overwrite this behavior by using
  ``marshmallow_load_default``/``marshmallow_dump_default`` attributes:

.. code-block:: python

    @instance.register
    class Employee(Document):
        name = fields.StrField(default='John Doe')
        birthday = fields.DateTimeField(marshmallow_load_default=dt.datetime(2000, 1, 1))
        # You can use `missing` singleton to overwrite `default` field inference
        skill = fields.StrField(default='Dummy', marshmallow_dump_default=missing)

    ret = Employee.schema.as_marshmallow_schema()().load({})
    assert ret == {'name': 'John Doe', 'birthday': datetime(2000, 1, 1, 0, 0, tzinfo=tzutc()), 'skill': 'Dummy'}
    ret = Employee.schema.as_marshmallow_schema()().dump({})
    assert ret == {'name': 'John Doe', 'birthday': '2000-01-01T00:00:00+00:00'}  # Note `skill` hasn't been serialized

It can be useful to let all the generated marshmallow schemas inherit a custom
base schema class. For instance to customize this base schema using a Meta class.

This can be done by defining a custom base schema class and passing it as a
class attribute to a custom :class:`umongo.Document` subclass.

Since the default base schema is :class:`umongo.abstract.BaseMarshmallowSchema`,
it makes sense to build from here.

.. code-block:: python

   class BaseMaSchema(umongo.abstract.BaseMarshmallowSchema):
      class Meta:
         ...  # Add custom attributes here

      # Implement custom methods here
      def custom_method(self):
         ...

    @instance.register
    class MyDocument(Document):
      MA_BASE_SCHEMA_CLS = BaseMaSchema

This is done at document level, but it is possible to do it in a custom base
``Document`` class to avoid duplication.


Field validate & io_validate
============================

Fields can be configured with special validators through the ``validate`` attribute:

.. code-block:: python

    from umongo import Document, fields, validate

    @instance.register
    class Employee(Document):
        name = fields.StrField(validate=[validate.Length(max=120), validate.Regexp(r"[a-zA-Z ']+")])
        age = fields.IntField(validate=validate.Range(min=18, max=65))
        email = fields.StrField(validate=validate.Email())
        type = fields.StrField(validate=validate.OneOf(['private', 'sergeant', 'general']))

Those validators will be enforced each time a field is modified:

.. code-block:: python

    >>> john = Employee(name='John Rambo')
    >>> john.age = 99  # it's not his war anymore...
    [...]
    ValidationError: ['Must be between 18 and 65.']

Validators may need to query the database (e.g. to validate
a :class:`umongo.data_objects.Reference`). For this need one can use the
``io_validate`` argument. It should be a function (or a list of functions) that
will do database access in accordance with the chosen mongodb driver.

For example with Motor-asyncio driver, ``io_validate``'s functions will be
wrapped by :class:`asyncio.coroutine` and called with ``yield from``.

.. code-block:: python

    from motor.motor_asyncio import AsyncIOMotorClient
    from umongo.frameworks import MotorAsyncIOInstance
    db = AsyncIOMotorClient().test
    instance = MotorAsyncIOInstance(db)

    @instance.register
    class TrendyActivity(Document):
        name = fields.StrField()


    @instance.register
    class Job(Document):

        def _is_dream_job(field, value):
            if not (yield from TrendyActivity.find_one(name=value)):
                raise ValidationError("No way I'm doing this !")

        activity = fields.StrField(io_validate=_is_dream_job)


    @asyncio.coroutine
    def run():
        yield from TrendyActivity(name='Pythoning').commit()
        yield from Job(activity='Pythoning').commit()
        yield from Job(activity='Javascripting...').commit()
        # raises ValidationError: {'activity': ["No way I'm doing this !"]}

.. warning:: When converting to marshmallow with `as_marshmallow_schema` and
    `as_marshmallow_fields`, `io_validate` attribute will not be preserved.
