from .document import Implementation, Template
from .data_objects import BaseDataObject
from .data_proxy import DataProxy


class EmbeddedDocumentTemplate(Template):
    """
    Base class to define a umongo embedded document.

    .. note::
        Once defined, this class must be registered inside a
        :class:`umongo.instance.BaseInstance` to obtain it corresponding
        :class:`umongo.embedded_document.EmbeddedDocumentImplementation`.
    """
    pass


EmbeddedDocument = EmbeddedDocumentTemplate
"Shortcut to EmbeddedDocumentTemplate"


class EmbeddedDocumentOpts:
    """
    Configuration for an :class:`umongo.embedded_document.EmbeddedDocument`.
    """

    def __repr__(self):
        return ('<{ClassName}(instance={self.instance}, template={self.template})>'
                .format(ClassName=self.__class__.__name__, self=self))

    def __init__(self, instance, template):
        self.instance = instance
        self.template = template


class EmbeddedDocumentImplementation(Implementation, BaseDataObject):
    """
    Represent an embedded document once it has been implemented inside a
    :class:`umongo.instance.BaseInstance`.
    """

    __slots__ = ('_callback', '_data', '_modified')
    opts = EmbeddedDocumentOpts(None, EmbeddedDocumentTemplate)

    def __init__(self, **kwargs):
        schema = self.Schema()
        self._modified = False
        self._data = DataProxy(schema, kwargs)

    def __repr__(self):
        return '<object EmbeddedDocument %s.%s(%s)>' % (
            self.__module__, self.__class__.__name__, self._data._data)

    def __eq__(self, other):
        if isinstance(other, dict):
            return self._data == other
        else:
            return self._data == other._data

    def is_modified(self):
        return self._modified

    def set_modified(self):
        self._modified = True

    def clear_modified(self):
        self._modified = False
        self._data.clear_modified()

    def from_mongo(self, data):
        self._data.from_mongo(data)

    def to_mongo(self, update=False):
        return self._data.to_mongo(update=update)

    def dump(self):
        return self._data.dump()

    def update(self, data, schema=None, reset_missings=False):
        return self._data.update(data, schema=schema, reset_missings=reset_missings)

    # Data-proxy accessor shortcuts

    def __getitem__(self, name):
        return self._data.get(name)

    def __delitem__(self, name):
        self.set_modified()
        self._data.delete(name)

    def __setitem__(self, name, value):
        self.set_modified()
        self._data.set(name, value)

    def __setattr__(self, name, value):
        if name in EmbeddedDocumentImplementation.__dict__:
            EmbeddedDocumentImplementation.__dict__[name].__set__(self, value)
        else:
            self.set_modified()
            self._data.set(name, value)

    def __getattr__(self, name):
        return self._data.get(name)

    def __delattr__(self, name):
        self.set_modified()
        self._data.delete(name)
