.. _api:

=============
API Reference
=============

.. module:: umongo

Instance
========

.. autoclass:: umongo.instance.BaseInstance
    :inherited-members:

.. autoclass:: umongo.Instance

.. autoclass:: umongo.instance.LazyLoaderInstance
  :members:

.. autoclass:: umongo.PyMongoInstance

.. autoclass:: umongo.TxMongoInstance

.. autoclass:: umongo.MotorAsyncIOInstance

.. autoclass:: umongo.MongoMockInstance

Document
========

.. autoclass:: umongo.Document

.. autoclass:: umongo.document.DocumentTemplate

.. autoclass:: umongo.document.DocumentOpts

.. autoclass:: umongo.document.DocumentImplementation
    :inherited-members:

.. _api_abstracts:

Abstracts
=========

.. autoclass:: umongo.abstract.BaseSchema
  :members:

.. autoclass:: umongo.abstract.BaseField
  :members:
  :undoc-members:

.. autoclass:: umongo.abstract.BaseValidator
  :members:

.. autoclass:: umongo.abstract.BaseDataObject
  :members:
  :undoc-members:

.. _api_fields:

Fields
======

.. automodule:: umongo.fields
  :members:
  :undoc-members:

.. _api_data_objects:

Data objects
============

.. automodule:: umongo.data_objects
  :members:
  :undoc-members:

.. _api_marshmallow_intergration:

Marshmallow integration
=======================

.. automodule:: umongo.marshmallow_bonus
  :members:

.. _api_exceptions:

Exceptions
==========

.. automodule:: umongo.exceptions
  :members:
  :undoc-members:
