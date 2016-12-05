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

This is the data from outside μMongo, it can be JSON dict from your web framework
(i.g. ``request.get_json()`` with `flask <http://flask.pocoo.org/>`_ or
``json.loads(request.raw_post_data)`` in `django <https://www.djangoproject.com/>`_)
or it could be regular Python dict with Python-typed data

JSON dict example

.. code-block:: python

    >>> {"str_field": "hello world", "int_field": 42, "date_field": "2015-01-01T00:00:00Z"}

Python dict example

.. code-block:: python

    >>> {"str_field": "hello world", "int_field": 42, "date_field": datetime(2015, 1, 1)}

To be integrated into μMongo, those data need to be unserialized. Same thing
to leave μMongo they need to be serialized (under the hood
μMongo uses `marshmallow <http://marshmallow.readthedocs.org/>`_ schema).
The unserialization operation is done automatically when instantiating a
:class:`umongo.Document`. The serialization is done when calling
:meth:`umongo.Document.dump` on a document instance.


Object Oriented world
---------------------

So what's good about :class:`umongo.Document` ? Well it allows you to work
with your data as Objects and to guarantee there validity against a model.

First let's define a document with few :mod:`umongo.fields`

.. code-block:: python

    @instance.register
    class Dog(Document):
        name = fields.StrField(required=True)
        breed = fields.StrField(missing="Mongrel")
        birthday = fields.DateTimeField()

First don't pay attention to the ``@instance.register``, this is for later ;-)

Note that each field can be customized with special attributes like
``required`` (which is pretty self-explanatory) or ``missing`` (if the
field is missing during unserialization it will take this value).

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
            allow_inheritance = True
            abstract = True

    @instance.register
    class Dog(Animal):
        name = fields.StrField(required=True)

    @instance.register
    class Duck(Animal):
        pass

Note the ``Meta`` subclass, it is used (along with inherited Meta classes from
parent documents) to configure the document class, you can access this final
config through the ``opts`` attribute.

Here we use this to allow ``Animal`` to be inheritable and to make it abstract.

.. code-block:: python

    >>> Animal.opts
    <DocumentOpts(instance=<umongo.frameworks.PyMongoInstance object at 0x7efe7daa9320>, template=<Document template class '__main__.Animal'>, abstract=True, allow_inheritance=True, collection_name=None, is_child=False, base_schema_cls=<class 'umongo.schema.Schema'>, indexes=[], offspring={<Implementation class '__main__.Duck'>, <Implementation class '__main__.Dog'>})>
    >>> Dog.opts
    <DocumentOpts(instance=<umongo.frameworks.PyMongoInstance object at 0x7efe7daa9320>, template=<Document template class '__main__.Dog'>, abstract=False, allow_inheritance=False, collection_name=dog, is_child=False, base_schema_cls=<class 'umongo.schema.Schema'>, indexes=[], offspring=set())>
    >>> class NotAllowedSubDog(Dog): pass
    [...]
    DocumentDefinitionError: Document <class '__main__.Dog'> doesn't allow inheritance
    >>> Animal(breed="Mutant")
    [...]
    AbstractDocumentError: Cannot instantiate an abstract Document


Mongo world
-----------

What the point of a MongoDB ODM without MongoDB ? So here it is !

Mongo world consist of data returned in a format comprehensible by a MongoDB
driver (`pymongo <https://api.mongodb.org/python/current/>`_ for instance).

.. code-block:: python

    >>> odwin.to_mongo()
    {'birthday': datetime.datetime(2001, 9, 22, 0, 0), 'name': 'Odwin'}

Well it our case the data haven't change much (if any !). Let's consider something more complex:

.. code-block:: python

    @instance.register
    class Dog(Document):
        name = fields.StrField(attribute='_id')

Here we decided to use the name of the dog as our ``_id`` key, but for
readability we keep it as ``name`` inside our document.

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

But what about if we what to retrieve the ``_id`` field whatever it name is ?
No problem, use the ``pk`` property:

.. code-block:: python

    >>> odwin.pk
    'Odwin'
    >>> Duck().pk
    None

Ok so now we got our data in a way we can insert it to MongoDB through our favorite driver.
In fact most of the time you don't need to use ``to_mongo`` directly.
Instead you can directly ask the document to ``commit`` it changes in database:

.. code-block:: python

    >>> odwin = Dog(name='Odwin', breed='Labrador')
    >>> odwin.commit()

You get also access to Object Oriented version of your driver methods:

.. code-block:: python

    >>> Dog.find()
    <umongo.dal.pymongo.WrappedCursor object at 0x7f169851ba68>
    >>> next(Dog.find())
    <object Document __main__.Dog({'id': 'Odwin', 'breed': 'Labrador'})>
    Dog.find_one({'_id': 'Odwin'})
    <object Document __main__.Dog({'id': 'Odwin', 'breed': 'Labrador'})>

You can also access the collection used by the document at any time
(for example to do more low-level operations):

.. code-block:: python

    >>> Dog.collection
    Collection(Database(MongoClient(host=['localhost:27017'], document_class=dict, tz_aware=False, connect=True), 'test'), 'dog')

.. note::
    By default the collection to use is the snake-cased version of the
    document's name (e.g. ``Dog`` => ``dog``, ``HTTPError`` => ``http_error``).
    However, you can configure (remember the ``Meta`` class ?) the collection
    to use for a document with the ``collection_name`` meta attribute.


Multi-driver support
====================

Remember the ``@insance.register`` ? That's now it kicks in !

The idea behind μMongo is to allow the same document definition to be used
with diferent mongoDB drivers.

To achieve that the user only define document templates. Templates which
will be implemented when registered by an instance:

.. figure:: instance_template.png
   :alt: instance/template mechanism in μMongo

Basically an instance provide three informations:

- the mongoDB driver type to use
- the database to use
- the documents implemented

This way a template can be implemented by multiple instances, this can be
useful for example to:

- store the same documents in differents databases
- define an instance with async driver for a web server and a
  sync one for shell interactions

But enough of theory, let's create our first instance !

.. code-block:: python

    >>> from umongo import Instance
    >>> import pymongo
    >>> con = pymongo.MongoClient()
    >>> instance1 = Instance(con.db1)
    >>> instance2 = Instance(con.db2)

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
    >>> DogInstance1Impl.find().count()
    1
    >>> DogInstance2Impl.find().count()
    0

.. note::
    You can use ``instance.register`` as a decoration to replace the template
    by it implementation. This is expecially useful if you only use a single
    instance:

    .. code-block:: python

        >>> @instance.register
        ... class Dog(Document):
        ...     pass
        >>> Dog().commit()

.. note::
    Often in more complex applications you won't have your driver ready
    when defining your documents. In such case you should use a special
    instance with lazy db loader depending of your driver:

    .. code-block:: python

        >>> from umongo import TxMongoInstance
        >>> instance = TxMongoInstance()
        >>> @instance.register
        ... class Dog(Document):
        ...     pass
        >>> # Don't try to use Dog (except for inheritance) now !
        >>> db = create_txmongo_database()
        >>> instance.init(db)
        >>> # Now instance is ready
        >>> yield Dog().commit()


For the moment all examples have been done with pymongo, but thing are
pretty the same with other drivers, just configure the ``instance``
and you're good to go:

.. code-block:: python

    >>> db = motor.motor_asyncio.AsyncIOMotorClient()['umongo_test']
    >>> instance = Instance(db)
    >>> @instance.register
    ... class Dog(Document):
    ...     name = fields.StrField(attribute='_id')
    ...     breed = fields.StrField(missing="Mongrel")

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
    ...     class Meta:
    ...         allow_inheritance = True
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
    >>> [x.document for x in Parent.opts.indexes]
    [{'key': SON([('unique_in_parent', 1)]), 'name': 'unique_in_parent_1', 'sparse': True, 'unique': True}]

.. warning:: You must ``register`` a parent before it child inside a given instance.


Indexes
=======

.. warning:: Indexes must be first submitted to MongoDB. To do so you should
             call :meth:`umongo.Document.ensure_indexes` once for each document


In fields, ``unique`` attribute is implicitly handled by an index:

.. code-block:: python

    >>> @instance.register
    ... class WithUniqueEmail(Document):
    ...     email = fields.StrField(unique=True)
    >>> [x.document for x in WithUniqueEmail.opts.indexes]
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
    >>> [x.document for x in CustomIndexes.opts.indexes]
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

In case of a field defined in a child document, it index is automatically
compounded with the ``_cls``

.. code-block:: python

      >>> @instance.register
      ... class Parent(Document):
      ...     unique_in_parent = fields.IntField(unique=True)
      ...     class Meta:
      ...         allow_inheritance = True
      >>> @instance.register
      ... class Child(Parent):
      ...     unique_in_child = fields.StrField(unique=True)
      ...     class Meta:
      ...         indexes = ['#unique_in_parent']
      >>> [x.document for x in Child.opts.indexes]
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
for all it data validation work.

However an ODM has some special needs (i.g. handling ``required`` fields through MongoDB's
unique indexes) that force to extend marshmallow base types.

In short, you should not try to use marshmallow base types (:class:`marshmallow.Schema`,
:class:`marshmallow.fields.Field` or :class:`marshmallow.validate.Validator` for instance)
in a μMongo document but instead use their μMongo equivalents (respectively
:class:`umongo.abstract.BaseSchema`, :class:`umongo.abstract.BaseField` and
:class:`umongo.abstract.BaseValidator`).

Now let's go back to the `Base concepts`_, the schema contains a little...
simplification !

According to it, the client and OO worlds are made of the same data, but only
in a different form (serialized vs object oriented).
However it happened pretty often the API you want to provide doesn't strictly
follow your datamodel (e.g. you don't want to display or allow modification
of the passwords in your `/users` route)

Let's go back to our `Dog` document, in real life you can rename your dog but
not change it breed. So in our user API we should have a schema that enforce this !

.. code-block:: python

    >>> DogMaSchema = Dog.schema.as_marshmallow_schema()

As you can imagine, ``as_marshmallow_schema`` convert the original umongo's
schema into a pure marshmallow schema. This way we can now customize it
by subclassing it:

.. code-block:: python

    >>> class PatchDogSchema(DogMaSchema):
    ...     class Meta:
    ...         fields = ('name', )
    >>> patch_dog_schema = PatchDogSchema()
    >>> patch_dog_schema.load({'name': 'Scruffy', 'breed': 'Golden retriever'}).errors
    {'_schema': ['Unknown field name breed.']}
    >>> ret = patch_dog_schema.load({'name': 'Scruffy'})
    >>> ret.errors
    {}
    >>> ret.data
    {'name': 'Scruffy'}

Finally we can integrated the validated data into OO world:

.. code-block:: python

    >>> my_dog.update(ret.data)
    >>> my_dog.name
    'Scruffy'

.. note:: When instantiating a custom marshmallow schema, you can use`strict=True`
    to make the schema raise a `ValidationError` instead of returning an error dict.
    This allow a better integration in umongo own error handling:

    .. code-block:: python

        try:
            data, _ = patch_dog_schema.load(payload)
            my_dog.update(data)
            my_dog.commit()
        except (ValidationError, UMongoError) as e:
            # error handling

This works great when you want to add special behavior depending of the situation.
For more simple usecases we could use the
`marshmallow pre/post precessors  <http://marshmallow.readthedocs.io/en/latest/extending.html#pre-processing-and-post-processing-methods>`_
. For example to simply customize the dump:

.. code-block:: python

    >>> from umongo import post_dump  # same as `from marshmallow import post_dump`
    >>> @instance.register
    ... class Dog(Document):
    ...     name = fields.StrField(required=True)
    ...     breed = fields.StrField(missing="Mongrel")
    ...     birthday = fields.DateTimeField()
    ...     @post_dump
    ...     def customize_dump(self, data):
    ...         data['name'] = data['name'].capitalize()
    ...         data['brief'] = "Hi ! My name is %s and I'm a %s" % (data['name'], data['breed'])"
    ...
    >>> Dog(name='scruffy').dump()
    {'name': 'Scruffy', 'breed': 'Mongrel', 'brief': "Hi ! My name is Scruffy and I'm a Mongrel"}

Now let's imagine we want to allow the per-breed creation of a massive number of ducks.
The API would accept a really different format that our datamodel:

.. code-block:: python

    {
        'breeds': [
            {'name': 'Mandarin Duck', 'births': ['2016-08-29T00:00:00', '2016-08-31T00:00:00', ...]},
            {'name': 'Mallard', 'births': ['2016-08-27T00:00:00', ...]},
            ...
        ]
    }

Now starting from the umongo schema would not help, so we will create our schema
from scratch... almost:

.. code-block:: python

    >>> MassiveBreedSchema(marshmallow.Schema):
    ...     name = Duck.schema.fields['breed'].as_marshmallow_field()
    ...     births = marshmallow.fields.List(
    ...         Duck.schema.fields['birthday'].as_marshmallow_field())
    >>> MassiveDuckSchema(marshmallow.Schema):
    ...     breeds = marshmallow.fields.List(marshmallow.fields.Nested(MassiveBreedSchema))

.. note:: A custom marshmallow schema :class:`umongo.marshmallow_bonus.SchemaFromUmongo`
    can be used instead of regular :class:`marshmallow.Schema` to benefit a tighter
    integration with umongo (unknown field checking and access to missing fields
    instead of serializing them as `None`)

This time we directly convert umongo schema's fields into there marshmallow
equivalent with ``as_marshmallow_field``. Now we can build our ducks easily:

.. code-block:: python

    try:
        data, _ =  MassiveDuckSchema(strict=True).load(payload)
        ducks = []
        for breed in data['breeds']:
            for birthday in breed['births']:
                duck = Duck(breed=breed['name']), birthday=birthday)
                duck.commit()
                ducks.append(duck)
    except ValidationError as e:
        # Error handling
        ...


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

Now sometime you'll need for your validator to query your database (this
is mainly done to validate a :class:`umongo.data_objects.Reference`). For
this need you can use the ``io_validate`` attribute.
This attribute should get passed a function (or a list of functions) that
will do database access in accordance with the used mongodb driver.

For example with Motor-asyncio driver, ``io_validate``'s functions will be
wrapped by :class:`asyncio.coroutine` and called with ``yield from``.

.. code-block:: python

    from motor.motor_asyncio import AsyncIOMotorClient
    db = AsyncIOMotorClient().test
    instance = Instance(db)

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
