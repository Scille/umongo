from marshmallow import ValidationError, missing

from .abstract import BaseDataObject
from .exceptions import FieldNotLoadedError


__all__ = ('DataProxy', 'missing')


class DataProxy:

    __slots__ = ('partial', '_schema', '_fields', '_data',
                 '_modified_data', '_fields_from_mongo_key')

    def __init__(self, schema, data=None):
        self.partial = False
        self._schema = schema
        self._fields = schema.fields
        self._data = {}
        self._modified_data = set()
        fields_from_mongo_key = {}
        for k, v in self._fields.items():
            if v.attribute:
                k = v.attribute
            fields_from_mongo_key[k] = v
        self._fields_from_mongo_key = fields_from_mongo_key
        self.load(data if data else {})

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
            mongo_data['$unset'] = sorted(unset_data)
        return mongo_data or None

    def from_mongo(self, data, partial=False):
        self._data = {}
        for k, v in data.items():
            field = self._fields_from_mongo_key[k]
            self._data[k] = field.deserialize_from_mongo(v)
        self._add_missing_fields()
        self.clear_modified()
        self.partial = partial

    def dump(self, schema=None):
        schema = schema or self._schema
        data, err = schema.dump(self._data)
        if err:
            raise ValidationError(err)
        return data

    def _mark_as_modified(self, key):
        self._modified_data.add(key)

    def update(self, data, schema=None, reset_missings=False):
        schema = schema or self._schema
        # Always use marshmallow partial load to skip required checks
        loaded_data, err = schema.load(data, partial=True)
        if err:
            raise ValidationError(err)
        self._data.update(loaded_data)

        # Set missing values to missing
        if reset_missings:
            loadable_fields = set(
                [k for k, v in schema.fields.items() if not v.dump_only])
            missing_keys = loadable_fields - set(data)
            for key in missing_keys:
                self._data[key] = missing

        for key in loaded_data:
            self._mark_as_modified(key)

    def load(self, data, partial=False, schema=None):
        schema = schema or self._schema
        # Always use marshmallow partial load to skip required checks
        loaded_data, err = schema.load(data, partial=True)
        if err:
            raise ValidationError(err)
        self._data = loaded_data
        self._add_missing_fields()
        self.clear_modified()
        self.partial = partial

    def get_by_mongo_name(self, name):
        value = self._data[name]
        if value is missing:
            if self.partial:
                raise FieldNotLoadedError(name)
            else:
                return None
        return value

    def set_by_mongo_name(self, name, value):
        self._data[name] = value
        self._mark_as_modified(name)

    def delete_by_mongo_name(self, name):
        self.set_by_mongo_name(name, missing)

    def get(self, name, to_raise=KeyError):
        if name not in self._fields:
            raise to_raise(name)
        field = self._fields[name]
        name = field.attribute or name
        value = self._data[name]
        if value is missing:
            if self.partial:
                raise FieldNotLoadedError(name)
            elif field.default is not missing:
                return field.default
            else:
                return None
        return value

    def set(self, name, value, to_raise=KeyError):
        if name not in self._fields:
            raise to_raise(name)
        field = self._fields[name]
        name = field.attribute or name
        value = field._deserialize(value, name, None)
        field._validate(value)
        self._data[name] = value
        self._mark_as_modified(name)

    def delete(self, name, to_raise=KeyError):
        if name not in self._fields:
            raise to_raise(name)
        name = self._fields[name].attribute or name
        if self._data[name] is missing:
            raise to_raise(name)
        self._data[name] = missing
        self._mark_as_modified(name)

    def __repr__(self):
        return "<DataProxy(%s)>" % self._data

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

    def _add_missing_fields(self):
        # TODO: we should be able to do that by configuring marshmallow...
        for name, field in self._fields.items():
            name = field.attribute or name
            if name not in self._data:
                if callable(field.missing):
                    self._data[name] = field.missing()
                else:
                    self._data[name] = field.missing
