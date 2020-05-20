"""umongo EmbeddedDocument"""
import marshmallow as ma

from .document import Implementation, Template
from .data_objects import BaseDataObject
from .exceptions import AbstractDocumentError


__all__ = (
    'EmbeddedDocumentTemplate',
    'EmbeddedDocument',
    'EmbeddedDocumentOpts',
    'EmbeddedDocumentImplementation'
)


class EmbeddedDocumentTemplate(Template):
    """
    Base class to define a umongo embedded document.

    .. note::
        Once defined, this class must be registered inside a
        :class:`umongo.instance.BaseInstance` to obtain it corresponding
        :class:`umongo.embedded_document.EmbeddedDocumentImplementation`.
    """
    MA_BASE_SCHEMA_CLS = ma.Schema


EmbeddedDocument = EmbeddedDocumentTemplate
"Shortcut to EmbeddedDocumentTemplate"


class EmbeddedDocumentOpts:
    """
    Configuration for an :class:`umongo.embedded_document.EmbeddedDocument`.

    Should be passed as a Meta class to the :class:`Document`

    .. code-block:: python

        @instance.register
        class MyEmbeddedDoc(EmbeddedDocument):
            class Meta:
                abstract = True

        assert MyEmbeddedDoc.opts.abstract == True


    ==================== ====================== ===========
    attribute            configurable in Meta   description
    ==================== ====================== ===========
    template             no                     Origin template of the embedded document
    instance             no                     Implementation's instance
    abstract             yes                    Embedded document can only be inherited
    is_child             no                     Embedded document inherit of a non-abstract
                                                embedded document
    strict               yes                    Don't accept unknown fields from mongo
                                                (default: True)
    offspring            no                     List of embedded documents inheriting this one
    ==================== ====================== ===========
    """
    def __repr__(self):
        return ('<{ClassName}('
                'instance={self.instance}, '
                'template={self.template}, '
                'abstract={self.abstract}, '
                'is_child={self.is_child}, '
                'strict={self.strict}, '
                'offspring={self.offspring})>'
                .format(ClassName=self.__class__.__name__, self=self))

    def __init__(self, instance, template, abstract=False,
                 is_child=False, strict=True, offspring=None):
        self.instance = instance
        self.template = template
        self.abstract = abstract
        self.is_child = is_child
        self.strict = strict
        self.offspring = set(offspring) if offspring else set()


class EmbeddedDocumentImplementation(Implementation, BaseDataObject):
    """
    Represent an embedded document once it has been implemented inside a
    :class:`umongo.instance.BaseInstance`.
    """

    __slots__ = ('_data', )
    __real_attributes = None
    opts = EmbeddedDocumentOpts(None, EmbeddedDocumentTemplate, abstract=True)

    def __init__(self, **kwargs):
        super().__init__()
        if self.opts.abstract:
            raise AbstractDocumentError("Cannot instantiate an abstract EmbeddedDocument")
        self._data = self.DataProxy(kwargs)

    def __repr__(self):
        return '<object EmbeddedDocument %s.%s(%s)>' % (
            self.__module__, self.__class__.__name__, dict(self._data.items()))

    def __eq__(self, other):
        if isinstance(other, dict):
            return self._data == other
        if hasattr(other, '_data'):
            return self._data == other._data
        return NotImplemented

    def is_modified(self):
        return self._data.is_modified()

    def clear_modified(self):
        self._data.clear_modified()

    def required_validate(self):
        self._data.required_validate()

    @classmethod
    def build_from_mongo(cls, data, use_cls=True):
        """
        Create an embedded document instance from MongoDB data

        :param data: data as retrieved from MongoDB
        :param use_cls: if the data contains a ``_cls`` field,
            use it determine the EmbeddedDocument class to instanciate
        """
        # If a _cls is specified, we have to use this document class
        if use_cls and '_cls' in data:
            cls = cls.opts.instance.retrieve_embedded_document(data['_cls'])
        doc = cls()
        doc.from_mongo(data)
        return doc

    def from_mongo(self, data):
        self._data.from_mongo(data)

    def to_mongo(self, update=False):
        return self._data.to_mongo(update=update)

    def update(self, data):
        """
        Update the embedded document with the given data.
        """
        return self._data.update(data)

    def dump(self):
        """
        Dump the embedded document.
        """
        return self._data.dump()

    def items(self):
        return self._data.items()

    # Data-proxy accessor shortcuts

    def __getitem__(self, name):
        value = self._data.get(name)
        return value if value is not ma.missing else None

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
        if name[:2] == name[-2:] == '__':
            raise AttributeError(name)
        value = self._data.get(name, to_raise=AttributeError)
        return value if value is not ma.missing else None

    def __delattr__(self, name):
        if not self.__real_attributes:
            type(self).__real_attributes = dir(self)
        if name in self.__real_attributes:
            object.__delattr__(self, name)
        else:
            self._data.delete(name, to_raise=AttributeError)
