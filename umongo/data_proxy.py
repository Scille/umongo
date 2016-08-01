from marshmallow import ValidationError, missing

from .abstract import BaseDataObject
from .exceptions import FieldNotLoadedError


__all__ = ('DataProxy', 'missing')


class DataProxy:

    __slots__ = ('not_loaded_fields', '_schema', '_fields', '_data',
                 '_modified_data', '_fields_from_mongo_key')

    def __init__(self, schema, data=None):
        self.not_loaded_fields = ()
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

    @property
    def partial(self):
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
        self._add_missing_fields()
        self.clear_modified()

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

        # Use marshmallow partial load to skip required checks
        # unless reset_missings is True
        loaded_data, err = schema.load(data, partial=(not reset_missings))
        if err:
            raise ValidationError(err)
        self._data.update(loaded_data)
        for key in loaded_data:
            self._mark_as_modified(key)

        # Delete missing fields unless dump_only or with a default value
        if reset_missings:
            deletable_fields = set(
                [k for k, v in schema.fields.items()
                 if not v.dump_only and v.missing is missing])
            missing_keys = deletable_fields - set(data)
            for key in missing_keys:
                self.delete(key)

    def load(self, data, partial=False, schema=None):
        schema = schema or self._schema
        # Always use marshmallow partial load to skip required checks
        loaded_data, err = schema.load(data, partial=True)
        if err:
            raise ValidationError(err)
        self._data = loaded_data
        if partial:
            self._collect_partial_fields(data)
        self._add_missing_fields()
        self.clear_modified()

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
        field._validate(value)
        self._data[name] = value
        self._mark_as_modified(name)

    def delete(self, name, to_raise=KeyError):
        name, _ = self._get_field(name, to_raise)
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
