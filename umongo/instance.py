from .exceptions import (
    NotRegisteredDocumentError, AlreadyRegisteredDocumentError, NoDBDefinedError)
from .document import DocumentTemplate, DocumentImplementation
from .template import get_template


class BaseInstance:
    """
    Base class for instance.

    Instances aims at collecting and implementing :class:`umongo.template.Template`::

        # Doc is a template, cannot use it for the moment
        class Doc(DocumentTemplate):
            pass

        instance = Instance()
        # doc_cls is the instance's implementation of Doc
        doc_cls = instance.register(Doc)
        # Implementations are registered as attribute into the instance
        instance.Doc is doc_cls
        # Now we can work with the implementations
        doc_cls.find()

    .. note::
        Instance registration is divided between :class:`umongo.Document` and
        :class:`umongo.EmbeddedDocument`.
    """

    BUILDER_CLS = None

    def __init__(self, templates=()):
        assert self.BUILDER_CLS, 'BUILDER_CLS must be defined.'
        self.builder = self.BUILDER_CLS(self)
        self._doc_lookup = {}
        self._embedded_lookup = {}
        for template in templates:
            self.register(template)

    @property
    def db(self):
        """Database used within the instance."""
        raise NotImplementedError

    def retrieve_document(self, name_or_template):
        """
        Retrieve a :class:`umongo.document.DocumentImplementation` registered into this
        instance from it name or it template class (i.e. :class:`umongo.Document`).
        """
        if not isinstance(name_or_template, str):
            name_or_template = name_or_template.__name__
        if name_or_template not in self._doc_lookup:
            raise NotRegisteredDocumentError(
                'Unknown document class `%s`' % name_or_template)
        return self._doc_lookup[name_or_template]

    def retrieve_embedded_document(self, name_or_template):
        """
        Retrieve a :class:`umongo.embedded_document.EmbeddedDocumentImplementation`
        registered into this instance from it name or it template class
        (i.e. :class:`umongo.EmbeddedDocument`).
        """
        if not isinstance(name_or_template, str):
            name_or_template = name_or_template.__name__
        if name_or_template not in self._embedded_lookup:
            raise NotRegisteredDocumentError(
                'Unknown embedded document class `%s`' % name_or_template)
        return self._embedded_lookup[name_or_template]

    def register(self, template, as_attribute=True):
        """
        Generate an :class:`umongo.template.Implementation` from the given
        :class:`umongo.template.Template` for this instance.

        :param template: :class:`umongo.template.Template` to implement
        :param as_attribute:
            Make the generated :class:`umongo.template.Implementation` available
            as this instance's attribute.

        :return: The :class:`umongo.template.Implementation` generated

        .. note::
            This method can be used as a decorator. This is useful when you
            only have a single instance to work with to directly use the
            class you defined::

                @instance.register
                class MyEmbedded(EmbeddedDocument):
                    pass

                @instance.register
                class MyDoc(Document):
                    emb = fields.EmbeddedField(MyEmbedded)

                MyDoc.find()

        """
        # Retrieve the template if another implementation has been provided instead
        template = get_template(template)
        if issubclass(template, DocumentTemplate):
            implementation = self._register_doc(template)
        else:  # EmbeddedDocumentTemplate
            implementation = self._register_embedded_doc(template)
        if as_attribute:
            setattr(self, implementation.__name__, implementation)
        return implementation

    def _register_doc(self, template):
        implementation = self.builder.build_document_from_template(template)
        if hasattr(self, implementation.__name__):
            raise AlreadyRegisteredDocumentError(
                'Document `%s` already registered' % implementation.__name__)
        self._doc_lookup[implementation.__name__] = implementation
        return implementation

    def _register_embedded_doc(self, template):
        implementation = self.builder.build_embedded_document_from_template(template)
        if hasattr(self, implementation.__name__):
            raise AlreadyRegisteredDocumentError(
                'EmbeddedDocument `%s` already registered' % implementation.__name__)
        self._embedded_lookup[implementation.__name__] = implementation
        return implementation


class Instance(BaseInstance):
    """
    Automatically configured instance according to the type of
    the provided database.
    """

    def __init__(self, db, templates=()):
        self._db = db
        # Dynamically find a builder compatible with the db
        from .frameworks import find_builder_from_db
        self.BUILDER_CLS = find_builder_from_db(db)
        super().__init__(templates=templates)

    @property
    def db(self):
        return self._db


class LazyLoaderInstance(BaseInstance):
    """
    Base class for instance with database lazy loading.

    .. note::
        This class should not be used directly but instead overloaded.
        See :class:`umongo.PyMongoInstance` for example.

    """

    def __init__(self, templates=(), auto_indexes=False):
        self._db = None
        super().__init__(templates=templates)
        self.auto_indexes = auto_indexes

    @property
    def db(self):
        if not self._db:
            raise NoDBDefinedError('init must be called to define a db')
        return self._db

    def init(self, db):
        """
        Set the database to use whithin this instance.

        For all documents already registered when init is called, indexes
        are ensured if either this Instance was instantiated with auto_indexes=True,
        or the document itself has auto_indexes=True in its Meta class.

        .. note::
            The documents registered in the instance cannot be used
            before this function is called.
        """
        assert self.BUILDER_CLS.is_compatible_with(db)
        self._db = db
        self.ensure_indexes(self.auto_indexes)

    def ensure_indexes(self, auto_indexes=False):
        for implementation in self._doc_lookup.values():
            if auto_indexes or implementation.opts.auto_indexes:
                implementation.ensure_indexes()
