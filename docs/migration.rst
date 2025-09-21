.. _migration:

=========
Migrating
=========

Migrating from umongo 2 to umongo 3
===================================

For a full list of changes, see the CHANGELOG.

Database migration
------------------

Aside from changes in application code, migrating from umongo 2 to umongo 3
requires changes in the database.

The way the embedded documents are stored has changed. The `_cls` attribute is
now only set on embedded documents that are subclasses of a concrete embedded
document. Unless documents are non-strict (i.e. transparently handle unknown
fields, default is strict), the database must be migrated to remove the `_cls`
fields on embedded documents that are not subclasses of a concrete document.

This change is irreversible. It requires the knowledge of the application model
(the document and embedded document classes).

umongo provides dedicated framework specific ``Instance`` subclasses to help on
this.

A simple procedure to build a migration tool is to replace one's ``Instance``
class in the application code with such class and call
``instance.migrate_2_to_3`` on init.

For instance, given following umongo 3 application code

.. code-block:: python

    from umongo.frameworks.pymongo import PyMongoInstance

    instance = PyMongoInstance()

    # Register embedded documents
    [...]


    @instance.register
    class Doc(Document):
        name = fields.StrField()
        # Embed documents
        embedded = fields.EmbeddedField([...])


    instance.set_db(pymongo.MongoClient())

    # This may raise an exception if Doc contains embedded documents
    # as described above
    Doc.find()

the migration can be performed by calling migrate_2_to_3.

.. code-block:: python

    from umongo.frameworks.pymongo import PyMongoMigrationInstance

    instance = PyMongoMigrationInstance()

    # Register embedded documents
    [...]


    @instance.register
    class Doc(Document):
        name = fields.StrField()
        # Embed documents
        embedded = fields.EmbeddedField([...])


    instance.set_db(pymongo.MongoClient())
    instance.migrate_2_to_3()

    # This is safe now that the database is migrated
    Doc.find()

Of course, this needs to be done only once. Although the migration is
idempotent, it wouldn't make sense to keep this in the codebase and execute the
migration on every application startup.

However, it is possible to embed the migration feature in the application code
by defining a dedicated command, like a Flask CLI command for instance.
