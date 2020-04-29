=======
History
=======

3.0.0b4 (2020-04-27)
--------------------

Features:

* *Backwards-incompatible*: Remove partial load feature (see #256).
* *Backwards-incompatible*: Add ``Document.pk_field`` and remove
  ``BaseDataProxy.*_by_mongo_name methods`` (see #257).
* *Backwards-incompatible*: Raise AlreadyCreatedError when modifying pk of
  created document (see #258).

3.0.0b3 (2020-04-26)
--------------------

Features:

* *Backwards-incompatible*: Replace ``ReferenceError`` with
  ``NoneReferenceError``. Review the list of exceptions importable from
  root ``umongo`` module. (see #251)

Bug fixes:

* Don't modify data when calling ``set_by_mongo_name`` on a field that was not
  loaded in a partial load. (see #253)

Other changes:

* *Backwards-incompatible*: Drop Python 3.5 support (see #248).

3.0.0b2 (2020-04-18)
--------------------

Features:

* Use fields for keys/values in DictField (see #245).

Bug fixes:

* Fix BaseField.__repr__ (see #247).

3.0.0b1 (2020-03-29)
--------------------

Features:

* Support marshmallow 3 (see #154).
* All field parameters beginning with ``"marshmallow_"`` are passed to the
  marshmallow schema, rather than only a given list of known parameters.
  (see #228)

Other changes:

* *Backwards-incompatible*: Drop support for marshmallow 2. See marshmallow
  upgrading guide for a comprehensive list of changes. (see #154)
* *Backwards-incompatible*: ``StrictDateTimeField`` is removed as marshmallow
  now provides ``NaiveDateTimeField`` and ``AwareDateTimeField``. (see #154)
* *Backwards-incompatible*: ``default`` shall now be provided in deserialized
  form. (see #154)

2.2.0 (2019-12-18)
------------------

Bug fixes:

* Fix ``find``/``find_one``: pass ``filter`` as first positional argument
  (see #215).

Other changes:

* Support Python 3.8 (see #210).

2.1.1 (2019-10-04)
------------------

Bug fixes:

* Fix ``ObjectId`` bonus field: catch ``TypeError`` when deserializing
  (see #207).

2.1.0 (2019-06-19)
------------------

Features:

* Add support for motor 2.+ by adding a ``count_documents`` class method to the
  ``MotorAsyncIODocument`` class. ``count_documents`` attempts to transparently
  use the correct motor call signature depending on which version of the
  driver is installed. Note that the behavior of the cursor object returned by
  ``MotorAsyncIODocument.find`` strictly adheres to the interface provided by
  the underlying driver.

2.0.5 (2019-06-13)
------------------

Bug fixes:

* Ensure ``Reference`` and ``GenericReference`` fields round-trip (see #200).

2.0.4 (2019-05-28)
------------------

Bug fixes:

* Include modified ``BaseDataObject`` in ``BaseDataProxy.get_modified_fields``
  and ``BaseDataProxy.get_modified_fields_by_mongo_name`` (see #195).
* Always return a boolean in ``List.is_modified`` (see #195).
* ``List``: call ``set_modified`` when deleting an element using the ``del``
  builtin (see #195).

2.0.3 (2019-04-10)
------------------

Bug fixes:

* Fix millisecond overflow when milliseconds round to 1s in
  ``StrictDateTimeField`` (see #189).

2.0.2 (2019-04-10)
------------------

Bug fixes:

* Fix millisecond overflow when milliseconds round to 1s in ``DateTimeField``
  and ``LocalDateTimeField`` (see #189).

2.0.1 (2019-03-25)
------------------

Bug fixes:

* Fix deserialization of ``EmbeddedDocument`` containing fields overriding
  ``_deserialize_from_mongo`` (see #186).

2.0.0 (2019-03-18)
------------------

Features:

* *Backwards-incompatible*: ``missing`` attribute is no longer used in umongo
  fields, only ``default`` is used. ``marshmallow_missing`` and
  ``marshmallow_default`` attribute can be used to overwrite the value to use
  in the pure marshmallow field returned by ``as_marshmallow_field`` method
  (see #36 and #107).
* *Backwards-incompatible*: ``as_marshmallow_field`` does not pass
  ``load_from``, ``dump_to`` and ``attribute`` to the pure marshmallow field
  anymore. It only passes ``validate``, ``required``, ``allow_none``,
  ``dump_only``, ``load_only`` and ``error_messages``, as well as ``default``
  and ``missing`` values inferred from umongo's ``default``. Parameters
  prefixed with ``marshmallow_`` in the umongo field are passed to the pure
  marshmallow field and override their non-prefixed counterpart. (see #170)
* *Backwards-incompatible*: ``DictField`` and ``ListField`` don't default to
  empty ``Dict``/``List``. To keep old behaviour, pass ``dict``/``list`` as
  default. (see #105)
* *Backwards-incompatible*: Serialize empty ``Dict``/``List`` as empty rather
  than missing (see #105).
* Round datetimes to millisecond precision in ``DateTimeField``,
  ``LocalDateTimeField`` and ``StrictDateTimeField`` to keep consistency
  between object and database representation (see #172 and #175).
* Add ``DateField`` (see #178).

Bug fixes:

* Fix passing a default value to a ``DictField``/``ListField`` as a raw Python
  ``dict``/``list`` (see #78).
* The ``default`` parameter of a Field is deserialized and validated (see #174).

Other changes:

* Support Python 3.7 (see #181).
* *Backwards-incompatible*: Drop Python 3.4 support (see #176) and only use
  async/await coroutine style in asyncio framework (see #179).

1.2.0 (2019-02-08)
------------------

* Add ``Schema`` cache to ``as_marshmallow_schema`` (see #165).
* Add ``DecimalField``. This field only works on MongoDB 3.4+. (see #162)

1.1.0 (2019-01-14)
------------------

* Fix bug when filtering by id in a Document subclass find query (see #145).
* Fix __getattr__ to allow copying and deepcopying Document and EmbeddedDocument
  (see #157).
* Add Document.clone() method (see #158).

1.0.0 (2018-11-29)
------------------
* Raise ``UnknownFieldInDBError`` when an unknown field is found in database
  and not using ``BaseNonStrictDataProxy`` (see #121)
* Fix (non fatal) crash in garbage collector when using ``WrappedCursor`` with
  mongomock
* Depend on pymongo 3.7+ (see #149)
* Pass ``as_marshmallow_schema params`` to nested schemas. Since this change, every
  field's ``as_marshmallow_schema`` method should expect unknown ``**kwargs`` (see #101).
* Pass params to container field in ``ListField.as_marshmallow_schema`` (see #150)
* Add ``meta`` kwarg to ``as_marshmallow_schema`` to pass a ``dict`` of attributes
  for the schema's ``Meta`` class (see #151)

0.15.0 (2017-08-15)
-------------------
* Add `strict` option to (Embedded)DocumentOpts to allow loading of document
  with unknown fields from mongo (see #115)
* Fix fields serialization/deserialization when allow_none is True (see #69)
* Fix ReferenceFild assignment from another ReferenceField (see #110)
* Fix deletion of field proxied by a property (see #109)
* Fix StrictDateTime bonus field: _deserialize does not accept datetime.datetime
  instances (see #106)
* Add force_reload param to Reference.fetch (see #96)

0.14.0 (2017-03-03)
-------------------
* Fix bug in mashmallow tag handling (see #90)
* Fix allow none in DataProxy.set (see #89)
* Support motor 1.1 (see #87)

0.13.0 (2017-01-02)
-------------------

* Fix deserialization error with nested EmbeddedDocuments (see #84, #67)
* Add ``abstract`` and ``allow_inheritance`` options to EmbeddedDocument
* Remove buggy ``as_marshmallow_schema``'s parameter ``missing_accessor`` (see #73, #74)

0.12.0 (2016-11-11)
-------------------

* Replace ``Document.opts.children`` by ``offspring`` and fix grand child
  inheritance issue (see #66)
* Fix dependency since release of motor 1.0 with breaking API

0.11.0 (2016-11-02)
-------------------

* data_objects ``Dict`` and ``List`` inherit builtins ``dict`` and ``list``
* Document&EmbeddedDocument store fields passed during initialization
  as modified (see #50)
* Required field inside embedded document are handled correctly (see #61)
* Document support marshmallow's pre/post processors

0.10.0 (2016-09-29)
-------------------

* Add pre/post update/insert/delete hooks (see #22)
* Provide Umongo to Marshmallow schema/field conversion with
  schema.as_marshmallow_schema() and field.as_marshmallow_field() (see #34)
* List and Dict inherit from collections's UserList and UserDict instead
  of builtins types (needed due to metaprogramming conflict otherwise)
* DeleteError and UpdateError returns the driver result object instead
  of the raw error dict (except for motor which only has raw error dict)

0.9.0 (2016-06-11)
------------------

* Queries can now be expressed with the document's fields name instead of the
  name in database
* ``EmbeddedDocument`` also need to be registered by and instance before use

0.8.1 (2016-05-19)
------------------

* Replace ``Document.created`` by ``is_created`` (see #14)

0.8.0 (2016-05-18)
------------------

* Heavy rewrite of the project, lost of API breakage
* Documents are now first defined as templates then implemented
  inside an Instance
* DALs has been replaced by frameworks implementations of Builder
* Fix ``__getitem__`` for Pymongo.Cursor wrapper
* Add ``conditions`` argument to Document.commit
* Add ``count`` method to txmongo

0.7.8 (2016-4-28)
-----------------

* Fix setup.py style preventing release of version 0.7.7

0.7.7 (2016-4-28)
-----------------

* Fix await error with Reference.fetch
* Pymongo is now only installed with extra flavours of umongo

0.7.6 (2016-4-28)
-----------------

* Use extras_require to install driver along with umongo

0.7.5 (2016-4-23)
-----------------

* Fixing await (Python >= 3.5) support for motor-asyncio

0.7.4 (2016-4-21)
-----------------

* Fix missing package in setup.py

0.7.3 (2016-4-21)
-----------------

* Fix setup.py style preventing from release

0.7.2 (2016-4-21)
-----------------

* Fix crash when generating indexes on EmbeddedDocument

0.7.1 (2016-4-21)
-----------------

* Fix setup.py not to install tests package
* Pass status to Beta

0.7.0 (2016-4-21)
-----------------

* Add i18n support
* Add MongoMock support
* Documentation has been a lot extended

0.6.1 (2016-4-13)
-----------------

* Add ``<dal>_lazy_loader`` to configure Document's lazy_collection

0.6.0 (2016-4-12)
-----------------

* Heavy improvements everywhere !

0.1.0 (2016-1-22)
-----------------

* First release on PyPI.

