from bson import DBRef

from .abstract import BaseDataObject, I18nErrorDict


__all__ = ('List', 'Reference')


class List(BaseDataObject, list):

    def __init__(self, container_field, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.container_field = container_field

    def __setitem__(self, key, obj):
        obj = self.container_field.deserialize(obj)
        super().__setitem__(key, obj)
        self._modified = True

    def append(self, obj):
        obj = self.container_field.deserialize(obj)
        ret = super().append(obj)
        self.set_modified()
        return ret

    def pop(self, *args, **kwargs):
        ret = super().pop(*args, **kwargs)
        self.set_modified()
        return ret

    def clear(self, *args, **kwargs):
        ret = super().clear(*args, **kwargs)
        self.set_modified()
        return ret

    def remove(self, *args, **kwargs):
        ret = super().remove(*args, **kwargs)
        self.set_modified()
        return ret

    def reverse(self, *args, **kwargs):
        ret = super().reverse(*args, **kwargs)
        self.set_modified()
        return ret

    def sort(self, *args, **kwargs):
        ret = super().sort(*args, **kwargs)
        self.set_modified()
        return ret

    def extend(self, iterable):
        iterable = [self.container_field.deserialize(obj) for obj in iterable]
        ret = super().extend(iterable)
        self.set_modified()
        return ret

    def __repr__(self):
        return '<object %s.%s(%s)>' % (
            self.__module__, self.__class__.__name__, list(self))

    def is_modified(self):
        if self._modified:
            return True
        if len(self) and isinstance(self[0], BaseDataObject):
            # Recursive handling needed
            return next((True for obj in self if obj.is_modified() is True), False)

    def clear_modified(self):
        self._modified = False
        if len(self) and isinstance(self[0], BaseDataObject):
            # Recursive handling needed
            for obj in self:
                obj.clear_modified()


# TODO: Dict is to much raw: you need to use `set_modified` by hand !
class Dict(BaseDataObject, dict):
    pass


class Reference:

    error_messages = I18nErrorDict(not_found='Reference not found for document {document}.')

    def __init__(self, document_cls, pk):

        # Attribute getter/setter/deleter are overridden to provide
        # direct access to referenced document. We must use __dict__
        # directly to get around those.
        self.__dict__['document_cls'] = document_cls
        self.__dict__['pk'] = pk
        self.__dict__['_document'] = None

    def fetch(self, no_data=False):
        """
        Retrieve from the database the referenced document

        :param no_data: if True, the caller is only interested in whether or
            not the document is present in database. This means the
            implementation may not retrieve document's data to save bandwidth.
        """
        raise NotImplementedError
    # TODO replace no_data by `exists` function

    def __repr__(self):
        return '<object %s.%s(document=%s, pk=%r)>' % (
            self.__module__, self.__class__.__name__, self.document_cls.__name__, self.pk)

    def __eq__(self, other):
        if isinstance(other, self.document_cls):
            return other.pk == self.pk
        elif isinstance(other, Reference):
            return self.pk == other.pk and self.document_cls == other.document_cls
        elif isinstance(other, DBRef):
            return self.pk == other.id and self.document_cls.collection.name == other.collection
        return NotImplemented

    def __getitem__(self, name):
        return self.fetch()[name]

    def __setitem__(self, name, value):
        self.fetch()[name] = value

    def __delitem__(self, name):
        del self.fetch()[name]

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        return getattr(self.fetch(), name)

    def __setattr__(self, name, value):
        if name in self.__dict__:
            self.__dict__[name] = value
        else:
            setattr(self.fetch(), name)

    def __delattr__(self, name):
        if name in self.__dict__:
            del self.__dict__[name]
        else:
            delattr(self.fetch(), name)
