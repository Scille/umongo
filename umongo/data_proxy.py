from marshmallow import ValidationError, missing

from .abstract import BaseDataObject
from .exceptions import FieldNotLoadedError
from .i18n import gettext as _


__all__ = ('data_proxy_factory', 'missing')


class BaseDataProxy:

    __slots__ = ('not_loaded_fields', '_data', '_modified_data')
    schema = None
    _fields = None
    _fields_from_mongo_key = None

    def __init__(self, data=None):
        self.not_loaded_fields = set()
        # Inside data proxy, data are stored in mongo world representation
        self._modified_data = set()
        self.load(data or {})

    @property
    def partial(self):
        # TODO: rename to `is_partialy_loaded` ?
        return bool(self.not_loaded_fields)

    def to_mongo(self, update=False):
        if update:
            return self._to_mongo_update()
        else:
            return self._to_mongo()

    def _to_mongo(self):
        mongo_data = {}
        for k, v in self._data.items():
            field = self._fields_from_mongo_key[k]
            v = field.serialize_to_mongo(v)
            if v is not missing:
                mongo_data[k] = v
        return mongo_data

    def _to_mongo_update(self):
        mongo_data = {}
        set_data = {}
        unset_data = []
        for name, field in self._fields.items():
            name = field.attribute or name
            v = self._data[name]
            if name in self._modified_data or (
                    isinstance(v, BaseDataObject) and v.is_modified()):
                v = field.serialize_to_mongo(v)
                if v is missing:
                    unset_data.append(name)
                else:
                    set_data[name] = v
        if set_data:
            mongo_data['$set'] = set_data
        if unset_data:
            mongo_data['$unset'] = {k: "" for k in unset_data}
        return mongo_data or None

    def from_mongo(self, data, partial=False):
        self._data = {}
        for k, v in data.items():
            field = self._fields_from_mongo_key[k]
            self._data[k] = field.deserialize_from_mongo(v)
        if partial:
            self._collect_partial_fields(data.keys(), as_mongo_fields=True)
        else:
            self.not_loaded_fields.clear()
        self.clear_modified()
        self._add_missing_fields()

    def dump(self):
        data, err = self.schema.dump(self._data)
        if err:
            raise ValidationError(err)
        return data

    def _mark_as_modified(self, key):
        self._modified_data.add(key)

    def update(self, data):
        # Always use marshmallow partial load to skip required checks
        loaded_data, err = self.schema.load(data, partial=True)
        if err:
            raise ValidationError(err)
        self._data.update(loaded_data)
        if self.not_loaded_fields:
            for k in loaded_data:
                self.not_loaded_fields.discard(self._fields_from_mongo_key[k])
        for key in loaded_data:
            self._mark_as_modified(key)

    def load(self, data, partial=False):
        # Always use marshmallow partial load to skip required checks
        loaded_data, err = self.schema.load(data, partial=True)
        if err:
            raise ValidationError(err)
        self._data = loaded_data
        # Map the modified fields list on the the loaded data
        self.clear_modified()
        for key in loaded_data:
            self._mark_as_modified(key)
        if partial:
            self._collect_partial_fields(data)
        else:
            self.not_loaded_fields.clear()
        # Must be done last given it modify `loaded_data`
        self._add_missing_fields()

    def get_by_mongo_name(self, name):
        value = self._data[name]
        if self._fields_from_mongo_key[name] in self.not_loaded_fields:
            raise FieldNotLoadedError(name)
        return value

    def set_by_mongo_name(self, name, value):
        self._data[name] = value
        if self._fields_from_mongo_key[name] in self.not_loaded_fields:
            raise FieldNotLoadedError(name)
        self._mark_as_modified(name)

    def delete_by_mongo_name(self, name):
        self.set_by_mongo_name(name, missing)

    def _get_field(self, name, to_raise):
        if name not in self._fields:
            raise to_raise(name)
        field = self._fields[name]
        if field in self.not_loaded_fields:
            raise FieldNotLoadedError(name)
        name = field.attribute or name
        return name, field

    def get(self, name, to_raise=KeyError):
        name, field = self._get_field(name, to_raise)
        value = self._data[name]
        if value is missing and field.default is not missing:
            return field.default
        return value

    def set(self, name, value, to_raise=KeyError):
        name, field = self._get_field(name, to_raise)
        value = field._deserialize(value, name, None)
        if value is not None or not getattr(field, 'allow_none', False):
            field._validate(value)
        self._data[name] = value
        self._mark_as_modified(name)

    def delete(self, name, to_raise=KeyError):
        name, _ = self._get_field(name, to_raise)
        self._data[name] = missing
        self._mark_as_modified(name)

    def __repr__(self):
        # Display data in oo world format
        return "<%s(%s)>" % (self.__class__.__name__, dict(self.items()))

    def __eq__(self, other):
        if isinstance(other, dict):
            return self._data == other
        else:
            return self._data == other._data

    def get_modified_fields_by_mongo_name(self):
        return self._modified_data

    def get_modified_fields(self):
        modified = []
        for name, field in self._fields.items():
            value_name = field.attribute or name
            if value_name in self._modified_data:
                modified.append(name)
        return modified

    def clear_modified(self):
        self._modified_data.clear()
        for v in self._data.values():
            if isinstance(v, BaseDataObject):
                v.clear_modified()

    def is_modified(self):
        return (bool(self._modified_data) or
            any(isinstance(v, BaseDataObject) and v.is_modified()
                for v in self._data.values()))

    def _collect_partial_fields(self, loaded_fields, as_mongo_fields=False):
        if as_mongo_fields:
            self.not_loaded_fields = set(
                self._fields_from_mongo_key[k]
                for k in self._fields_from_mongo_key.keys() - set(loaded_fields))
        else:
            self.not_loaded_fields = set(
                self._fields[k] for k in self._fields.keys() - set(loaded_fields))

    def _add_missing_fields(self):
        # TODO: we should be able to do that by configuring marshmallow...
        for name, field in self._fields.items():
            mongo_name = field.attribute or name
            if mongo_name not in self._data:
                if callable(field.missing):
                    self._data[mongo_name] = field.missing()
                else:
                    self._data[mongo_name] = field.missing

    def required_validate(self):
        errors = {}
        for name, field in self.schema.fields.items():
            value = self._data[field.attribute or name]
            if field.required and value is missing:
                errors[name] = [_("Missing data for required field.")]
            elif hasattr(field, '_required_validate'):
                try:
                    field._required_validate(value)
                except ValidationError as exc:
                    errors[name] = exc.messages
        if errors:
            raise ValidationError(errors)

    # Standards iterators providing oo and mongo worlds views

    def items(self):
        return ((key, self._data[field.attribute or key])
                 for key, field in self._fields.items())

    def items_by_mongo_name(self):
        return self._data.items()

    def keys(self):
        return (field.attribute or key for key, field in self._fields.items())

    def keys_by_mongo_name(self):
        return self._data.keys()

    def values(self):
        return self._data.values()


def data_proxy_factory(basename, schema):
    """
    Generate a DataProxy from the given schema.

    This way all generic informations (like schema and fields lookups)
    are kept inside the  DataProxy class and it instances are just flyweights.
    """

    cls_name = "%sDataProxy" % basename

    nmspc = {
        '__slots__': (),
        'schema': schema,
        '_fields': schema.fields,
        '_fields_from_mongo_key': {v.attribute or k: v for k, v in schema.fields.items()}
    }

    data_proxy_cls = type(cls_name, (BaseDataProxy, ), nmspc)
    return data_proxy_cls
