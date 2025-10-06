"""umongo Document"""

from copy import deepcopy

import marshmallow as ma
from marshmallow import (
    post_dump,
    post_load,
    pre_dump,
    pre_load,  # republishing
    validates_schema,
)

from bson import DBRef

from .data_objects import Reference
from .embedded_document import EmbeddedDocumentImplementation
from .exceptions import (
    AbstractDocumentError,
    AlreadyCreatedError,
    NoDBDefinedError,
    NotCreatedError,
)
from .indexes import parse_index
from .template import MetaImplementation, Template

__all__ = (
    "Document",
    "DocumentImplementation",
    "DocumentOpts",
    "DocumentTemplate",
    "MetaDocumentImplementation",
    "post_dump",
    "post_load",
    "pre_dump",
    "pre_load",
    "validates_schema",
)


class DocumentTemplate(Template):
    """Base class to define a umongo document.

    .. note::
        Once defined, this class must be registered inside a
        :class:`umongo.instance.BaseInstance` to obtain it corresponding
        :class:`umongo.document.DocumentImplementation`.
    .. note::
        You can provide marshmallow tags (e.g. `marshmallow.pre_load`
        or `marshmallow.post_dump`) to this class that will be passed
        to the marshmallow schema internally used for this document.
    """


Document = DocumentTemplate
"Shortcut to DocumentTemplate"


class DocumentOpts:
    """Configuration for a document.

    Should be passed as a Meta class to the :class:`Document`

    .. code-block:: python

        @instance.register
        class Doc(Document):
            class Meta:
                abstract = True


        assert Doc.opts.abstract == True


    ==================== ====================== ===========
    attribute            configurable in Meta   description
    ==================== ====================== ===========
    template             no                     Origine template of the Document
    instance             no                     Implementation's instance
    abstract             yes                    Document has no collection
                                                and can only be inherited
    collection_name      yes                    Name of the collection to store
                                                the document into
    is_child             no                     Document inherits a non-abstract
                                                document
    strict               yes                    Don't accept unknown fields from mongo
                                                (default: True)
    indexes              yes                    List of custom indexes
    offspring            no                     List of Documents inheriting this one
    ==================== ====================== ===========
    """

    def __repr__(self):
        return (
            f"<{self.__class__.__name__}("
            f"instance={self.instance}, "
            f"template={self.template}, "
            f"abstract={self.abstract}, "
            f"collection_name={self.collection_name}, "
            f"is_child={self.is_child}, "
            f"strict={self.strict}, "
            f"indexes={self.indexes}, "
            f"offspring={self.offspring})>"
        )

    def __init__(
        self,
        instance,
        template,
        collection_name=None,
        abstract=False,
        indexes=None,
        is_child=True,
        strict=True,
        offspring=None,
    ):
        self.instance = instance
        self.template = template
        self.collection_name = collection_name if not abstract else None
        self.abstract = abstract
        self.indexes = indexes or []
        self.is_child = is_child
        self.strict = strict
        self.offspring = set(offspring) if offspring else set()


class MetaDocumentImplementation(MetaImplementation):
    def __init__(cls, *args, **kwargs):
        cls._indexes = None

    @property
    def collection(cls):
        """Return the collection used by this document class"""
        if cls.opts.abstract:
            raise NoDBDefinedError("Abstract document has no collection")
        if cls.opts.instance.db is None:
            raise NoDBDefinedError("Instance must be initialized first")
        return cls.opts.instance.db[cls.opts.collection_name]

    @property
    def indexes(cls):
        """Retrieve all indexes (custom defined in meta class, by inheritances
        and unique attributes in fields)
        """
        if cls._indexes is None:
            idxs = []
            is_child = cls.opts.is_child

            # First collect parent indexes (including inherited field's unique indexes)
            for base in cls.mro():
                if (
                    base is not cls
                    and issubclass(base, DocumentImplementation)
                    and
                    # Skip base framework doc classes
                    hasattr(base, "schema")
                ):
                    idxs += base.indexes

            # Then get our own custom indexes
            if hasattr(cls, "Meta") and hasattr(cls.Meta, "indexes"):
                custom_indexes = [
                    parse_index(x, base_compound_field="_cls" if is_child else None)
                    for x in cls.Meta.indexes
                ]
                idxs += custom_indexes

            # Add _cls to indexes
            if is_child:
                idxs.append(parse_index("_cls"))

            # Finally parse our own fields (i.e. not inherited) for unique indexes
            def parse_field(mongo_path, path, field):
                if field.unique:
                    index = {"unique": True, "key": [mongo_path]}
                    if not field.required or field.allow_none:
                        index["sparse"] = True
                    if is_child:
                        index["key"].append("_cls")
                    idxs.append(parse_index(index))

            for name, field in cls.schema.fields.items():
                parse_field(name or field.attribute, name, field)
                if hasattr(field, "map_to_field"):
                    field.map_to_field(name or field.attribute, name, parse_field)

            cls._indexes = idxs

        return cls._indexes


class DocumentImplementation(
    EmbeddedDocumentImplementation,
    metaclass=MetaDocumentImplementation,
):
    """Represent a document once it has been implemented inside a
    :class:`umongo.instance.BaseInstance`.

    .. note:: This class should not be used directly, it should be inherited by
              concrete implementations such as
              :class:`umongo.frameworks.pymongo.PyMongoDocument`
    """

    __slots__ = ("_data", "is_created")
    opts = DocumentOpts(None, DocumentTemplate, abstract=True)

    def __init__(self, **kwargs):
        if self.opts.abstract:
            raise AbstractDocumentError("Cannot instantiate an abstract Document")
        self.is_created = False
        super().__init__(**kwargs)

    def __repr__(self):
        return (
            f"<object Document {self.__module__}.{self.__class__.__name__}"
            f"({dict(self._data.items())})>"
        )

    def __eq__(self, other):
        if self.pk is None:
            return self is other
        if isinstance(other, self.__class__) and other.pk is not None:
            return self.pk == other.pk
        if isinstance(other, DBRef):
            return other.collection == self.collection.name and other.id == self.pk
        if isinstance(other, Reference):
            return isinstance(self, other.document_cls) and self.pk == other.pk
        return NotImplemented

    def clone(self):
        """Return a copy of this Document as a new Document instance

        All fields are deep-copied except the _id field.
        """
        new = self.__class__()
        data = deepcopy(self._data._data)
        # Replace ID with new ID ("missing" unless a default value is provided)
        data["_id"] = new._data._data["_id"]
        new._data._data = data
        new._data._modified_data = set(data.keys())
        return new

    @property
    def collection(self):
        """Return the collection used by this document class"""
        # Cannot implicitly access to the class's property
        return type(self).collection

    @property
    def pk(self):
        """Return the document's primary key (i.e. ``_id`` in mongo notation) or
        None if not available yet

        .. warning:: Use ``is_created`` field instead to test if the document
                     has already been commited to database given ``_id``
                     field could be generated before insertion
        """
        value = self._data.get(self.pk_field)
        return value if value is not ma.missing else None

    @property
    def dbref(self):
        """Return a pymongo DBRef instance related to the document"""
        if not self.is_created:
            raise NotCreatedError(
                "Must create the document before having access to DBRef",
            )
        return DBRef(collection=self.collection.name, id=self.pk)

    @classmethod
    def build_from_mongo(cls, data, use_cls=False):
        """Create a document instance from MongoDB data

        :param data: data as retrieved from MongoDB
        :param use_cls: if the data contains a ``_cls`` field,
            use it determine the Document class to instanciate
        """
        # If a _cls is specified, we have to use this document class
        if use_cls and "_cls" in data:
            cls = cls.opts.instance.retrieve_document(data["_cls"])
        doc = cls()
        doc.from_mongo(data)
        return doc

    def from_mongo(self, data):
        """Update the document with the MongoDB data

        :param data: data as retrieved from MongoDB
        """
        self._data.from_mongo(data)
        self.is_created = True

    def to_mongo(self, update=False):
        """Return the document as a dict compatible with MongoDB driver.

        :param update: if True the return dict should be used as an
                       update payload instead of containing the entire document
        """
        if update and not self.is_created:
            raise NotCreatedError("Must create the document before using update")
        return self._data.to_mongo(update=update)

    def update(self, data):
        """Update the document with the given data."""
        if self.is_created and self.pk_field in data:
            raise AlreadyCreatedError("Can't modify id of a created document")
        self._data.update(data)

    def dump(self):
        """Dump the document."""
        return self._data.dump()

    def is_modified(self):
        """Returns True if and only if the document was modified since last commit."""
        return not self.is_created or self._data.is_modified()

    # Data-proxy accessor shortcuts

    def __setitem__(self, name, value):
        if self.is_created and name == self.pk_field:
            raise AlreadyCreatedError("Can't modify id of a created document")
        super().__setitem__(name, value)

    def __delitem__(self, name):
        if self.is_created and name == self.pk_field:
            raise AlreadyCreatedError("Can't modify id of a created document")
        super().__delitem__(name)

    def __setattr__(self, name, value):
        if name in self._fields:
            if self.is_created and name == self.pk_field:
                raise AlreadyCreatedError("Can't modify id of a created document")
            self._data.set(name, value)
        else:
            super().__setattr__(name, value)

    def __delattr__(self, name):
        if name in self._fields:
            if self.is_created and name == self.pk_field:
                raise AlreadyCreatedError("Can't modify pk of a created document")
            self._data.delete(name)
        else:
            super().__delattr__(name)

    # Callbacks

    def pre_insert(self):
        """Overload this method to get a callback before document insertion.

        .. note:: If you use an async driver, this callback can be asynchronous.
        """

    def pre_update(self):
        """Overload this method to get a callback before document update.
        :return: Additional filters dict that will be used for the query to
        select the document to update.

        .. note:: If you use an async driver, this callback can be asynchronous.
        """

    def pre_delete(self):
        """Overload this method to get a callback before document deletion.
        :return: Additional filters dict that will be used for the query to
        select the document to update.

        .. note:: If you use an async driver, this callback can be asynchronous.
        """

    def post_insert(self, ret):
        """Overload this method to get a callback after document insertion.
        :param ret: Pymongo response sent by the database.

        .. note:: If you use an async driver, this callback can be asynchronous.
        """

    def post_update(self, ret):
        """Overload this method to get a callback after document update.
        :param ret: Pymongo response sent by the database.

        .. note:: If you use an async driver, this callback can be asynchronous.
        """

    def post_delete(self, ret):
        """Overload this method to get a callback after document deletion.
        :param ret: Pymongo response sent by the database.

        .. note:: If you use an async driver, this callback can be asynchronous.
        """
