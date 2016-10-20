=======
History
=======

dev
---

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
* Fix `__getitem__` for Pymongo.Cursor wrapper
* Add `conditions` argument to Document.commit
* Add `count` method to txmongo

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

