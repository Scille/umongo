from bson import DBRef

from marshmallow import pre_load, post_load, pre_dump, post_dump, validates_schema  # republishing

from .abstract import BaseDataObject
from .data_proxy import missing
from .exceptions import (NotCreatedError, NoDBDefinedError,
                         AbstractDocumentError, DocumentDefinitionError)
from .template import Implementation, Template, MetaImplementation


__all__ = (
    'DocumentTemplate',
    'Document',
    'DocumentOpts',
    'MetaDocumentImplementation',
    'DocumentImplementation',
    'pre_load',
    'post_load',
    'pre_dump',
    'post_dump',
    'validates_schema'
)


class DocumentTemplate(Template):
    """
    Base class to define a umongo document.

    .. note::
        Once defined, this class must be registered inside a
        :class:`umongo.instance.BaseInstance` to obtain it corresponding
        :class:`umongo.document.DocumentImplementation`.
    .. note::
        You can provide marshmallow tags (e.g. `marshmallow.pre_load`
        or `marshmallow.post_dump`) to this class that will be passed
        to the marshmallow schema internally used for this document.
    """
    pass


Document = DocumentTemplate
"Shortcut to DocumentTemplate"


class DocumentOpts:
    """
    Configuration for a document.

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
    allow_inheritance    yes                    Allow the document to be subclassed
    collection_name      yes                    Name of the collection to store
                                                the document into
    is_child             no                     Document inherit of a non-abstract document
    indexes              yes                    List of custom indexes
    offspring            no                     List of Documents inheriting this one
    ==================== ====================== ===========

    """

    def __repr__(self):
        return ('<{ClassName}('
                'instance={self.instance}, '
                'template={self.template}, '
                'abstract={self.abstract}, '
                'allow_inheritance={self.allow_inheritance}, '
                'collection_name={self.collection_name}, '
                'is_child={self.is_child}, '
                'indexes={self.indexes}, '
                'offspring={self.offspring})>'
                .format(ClassName=self.__class__.__name__, self=self))

    def __init__(self, instance, template, collection_name=None, abstract=False,
                 allow_inheritance=None, indexes=None, is_child=False, offspring=None):
        self.instance = instance
        self.template = template
        self.collection_name = collection_name if not abstract else None
        self.abstract = abstract
        self.allow_inheritance = abstract if allow_inheritance is None else allow_inheritance
        self.indexes = indexes or []
        self.is_child = is_child
        self.offspring = set(offspring) if offspring else set()
        if self.abstract and not self.allow_inheritance:
            raise DocumentDefinitionError("Abstract document cannot disable inheritance")


class MetaDocumentImplementation(MetaImplementation):

    @property
    def collection(cls):
        """
        Return the collection used by this document class
        """
        if cls.opts.abstract:
            raise NoDBDefinedError('Abstract document has no collection')
        if not cls.opts.instance.db:
            raise NoDBDefinedError('Instance must be initialized first')
        return cls.opts.instance.db[cls.opts.collection_name]


class DocumentImplementation(BaseDataObject, Implementation, metaclass=MetaDocumentImplementation):
    """
    Represent a document once it has been implemented inside a
    :class:`umongo.instance.BaseInstance`.

    .. note:: This class should not be used directly, it should be inherited by
              concrete implementations such as :class:`umongo.frameworks.pymongo.PyMongoDocument`
    """

    __slots__ = ('is_created', '_data')
    __real_attributes = None
    opts = DocumentOpts(None, DocumentTemplate, abstract=True)

    def __init__(self, **kwargs):
        super().__init__()
        if self.opts.abstract:
            raise AbstractDocumentError("Cannot instantiate an abstract Document")
        self.is_created = False
        "Return True if the document has been commited to database"  # is_created's docstring
        self._data = self.DataProxy(kwargs if kwargs else None)

    def __repr__(self):
        return '<object Document %s.%s(%s)>' % (
            self.__module__, self.__class__.__name__, dict(self._data.items()))

    def __eq__(self, other):
        from .data_objects import Reference
        if self.pk is None:
            return self is other
        elif isinstance(other, self.__class__) and other.pk is not None:
            return self.pk == other.pk
        elif isinstance(other, DBRef):
            return other.collection == self.collection.name and other.id == self.pk
        elif isinstance(other, Reference):
            return isinstance(self, other.document_cls) and self.pk == other.pk
        return NotImplemented

    @property
    def collection(self):
        """
        Return the collection used by this document class
        """
        # Cannot implicitly access to the class's property
        return type(self).collection

    @property
    def pk(self):
        """
        Return the document's primary key (i.e. ``_id`` in mongo notation) or
        None if not available yet

        .. warning:: Use ``is_created`` field instead to test if the document
                     has already been commited to database given ``_id``
                     field could be generated before insertion
        """
        value = self._data.get_by_mongo_name('_id')
        return value if value is not missing else None

    @property
    def dbref(self):
        """
        Return a pymongo DBRef instance related to the document
        """
        if not self.is_created:
            raise NotCreatedError('Must create the document before'
                                  ' having access to DBRef')
        return DBRef(collection=self.collection.name, id=self.pk)

    @classmethod
    def build_from_mongo(cls, data, partial=False, use_cls=False):
        """
        Create a document instance from MongoDB data

        :param data: data as retrieved from MongoDB
        :param use_cls: if the data contains a ``_cls`` field,
            use it determine the Document class to instanciate
        """
        # If a _cls is specified, we have to use this document class
        if use_cls and '_cls' in data:
            cls = cls.opts.instance.retrieve_document(data['_cls'])
        doc = cls()
        doc.from_mongo(data, partial=partial)
        return doc

    def from_mongo(self, data, partial=False):
        """
        Update the document with the MongoDB data

        :param data: data as retrieved from MongoDB
        """
        # TODO: handle partial
        self._data.from_mongo(data, partial=partial)
        self.is_created = True

    def to_mongo(self, update=False):
        """
        Return the document as a dict compatible with MongoDB driver.

        :param update: if True the return dict should be used as an
                       update payload instead of containing the entire document
        """
        if update and not self.is_created:
            raise NotCreatedError('Must create the document before'
                                  ' using update')
        return self._data.to_mongo(update=update)

    def update(self, data):
        """
        Update the document with the given data.
        """
        self._data.update(data)

    def dump(self):
        """
        Dump the document.
        """
        return self._data.dump()

    def clear_modified(self):
        """
        Reset the list of document's modified items.
        """
        self._data.clear_modified()

    def is_modified(self):
        """
        Returns True if and only if the document was modified since last commit.
        """
        return not self.is_created or self._data.is_modified()

    def required_validate(self):
        self._data.required_validate()

    def items(self):
        return self._data.items()

    # Data-proxy accessor shortcuts

    def __getitem__(self, name):
        value = self._data.get(name)
        return value if value is not missing else None

    def __delitem__(self, name):
        self._data.delete(name)

    def __setitem__(self, name, value):
        self._data.set(name, value)

    def __setattr__(self, name, value):
        # Try to retrieve name among class's attributes and __slots__
        if not self.__real_attributes:
            # `dir(self)` result only depend on self's class so we can
            # compute it once and store it inside the class
            type(self).__real_attributes = dir(self)
        if name in self.__real_attributes:
            object.__setattr__(self, name, value)
        else:
            self._data.set(name, value, to_raise=AttributeError)

    def __getattr__(self, name):
        value = self._data.get(name, to_raise=AttributeError)
        return value if value is not missing else None

    def __delattr__(self, name):
        self._data.delete(name, to_raise=AttributeError)

    # Callbacks

    def pre_insert(self):
        """
        Overload this method to get a callback before document insertion.

        .. note:: If you use an async driver, this callback can return a defer/future.
        """
        pass

    def pre_update(self):
        """
        Overload this method to get a callback before document update.
        :return: Additional filters dict that will be used for the query to
            select the document to update.

        .. note:: If you use an async driver, this callback can return a defer/future.
        """
        pass

    def pre_delete(self):
        """
        Overload this method to get a callback before document deletion.
        :return: Additional filters dict that will be used for the query to
            select the document to update.

        .. note:: If you use an async driver, this callback can return a defer/future.
        """
        pass

    def post_insert(self, ret):
        """
        Overload this method to get a callback after document insertion.
        :param ret: Pymongo response sent by the database.

        .. note:: If you use an async driver, this callback can return a defer/future.
        """
        pass

    def post_update(self, ret):
        """
        Overload this method to get a callback after document update.
        :param ret: Pymongo response sent by the database.

        .. note:: If you use an async driver, this callback can return a defer/future.
        """
        pass

    def post_delete(self, ret):
        """
        Overload this method to get a callback after document deletion.
        :param ret: Pymongo response sent by the database.

        .. note:: If you use an async driver, this callback can return a defer/future.
        """
        pass
