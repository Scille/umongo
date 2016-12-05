from datetime import datetime
from dateutil.tz import tzutc

from marshmallow import ValidationError, Schema as MaSchema, missing
from marshmallow import fields as ma_fields, validates_schema
import bson

from .i18n import gettext as _


__all__ = (
    'schema_validator_check_unknown_fields',
    'schema_from_umongo_get_attribute',
    'SchemaFromUmongo',

    'StrictDateTime',
    'ObjectId',
    'Reference',
    'GenericReference'
)


# Bonus: schema helpers !


def schema_validator_check_unknown_fields(self, data, original_data):
    """
    Schema validator, raise ValidationError for unknown fields in a
    marshmallow schema.

    example::

        class MySchema(marshsmallow.Schema):
            # method's name is not important
            __check_unknown_fields = validates_schema(pass_original=True)(
                schema_validator_check_unknown_fields)

            # Define the rest of your schema
            ...

    ..note:: Unknown fields with `missing` value will be ignored
    """
    # Just skip if dummy data have been passed to the schema
    if not isinstance(original_data, dict):
        return
    loadable_fields = [k for k, v in self.fields.items() if not v.dump_only]
    unknown_fields = {key for key, value in original_data.items()
                      if value is not missing and key not in loadable_fields}
    if unknown_fields:
        raise ValidationError([_('Unknown field name {field}.').format(field=field)
                               for field in unknown_fields])


def schema_from_umongo_get_attribute(self, attr, obj, default):
    """
    Overwrite default `Schema.get_attribute` method by this one to access
        umongo missing fields instead of returning `None`.

    example::

        class MySchema(marshsmallow.Schema):
            get_attribute = schema_from_umongo_get_attribute

            # Define the rest of your schema
            ...

    """
    ret = MaSchema.get_attribute(self, attr, obj, default)
    if ret is None and ret is not default and attr in obj.schema.fields:
        raw_ret = obj._data.get(attr)
        return default if raw_ret is missing else raw_ret
    else:
        return ret


class SchemaFromUmongo(MaSchema):
    """
    Custom :class:`marshmallow.Schema` subclass providing unknown fields
    checking and custom get_attribute for umongo documents.

    .. note: It is not mandatory to use this schema with umongo document.
        This is just a helper providing usefull behaviors.
    """

    __check_unknown_fields = validates_schema(pass_original=True)(
        schema_validator_check_unknown_fields)
    get_attribute = schema_from_umongo_get_attribute


# Bonus: new fields !

class StrictDateTime(ma_fields.DateTime):
    """
    Marshmallow DateTime field with extra parameter to control
    whether dates should be loaded as tz_aware or not
    """

    def __init__(self, load_as_tz_aware=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_as_tz_aware = load_as_tz_aware

    def _deserialize(self, value, attr, data):
        if isinstance(value, datetime):
            date = value
        else:
            date = super()._deserialize(value, attr, data)
        if self.load_as_tz_aware:
            # If datetime is TZ naive, set UTC timezone
            if date.tzinfo is None or date.tzinfo.utcoffset(date) is None:
                date = date.replace(tzinfo=tzutc())
        else:
            # If datetime is TZ aware, convert it to UTC and remove TZ info
            if date.tzinfo is not None and date.tzinfo.utcoffset(date) is not None:
                date = date.astimezone(tzutc())
            date = date.replace(tzinfo=None)
        return date


class ObjectId(ma_fields.Field):
    """
    Marshmallow field for :class:`bson.ObjectId`
    """

    def _serialize(self, value, attr, obj):
        if value is None:
            return None
        return str(value)

    def _deserialize(self, value, attr, data):
        if value is None:
            return None
        try:
            return bson.ObjectId(value)
        except bson.errors.InvalidId:
            raise ValidationError(_('Invalid ObjectId.'))


class Reference(ObjectId):
    """
    Marshmallow field for :class:`umongo.fields.ReferenceField`
    """

    def __init__(self, *args, mongo_world=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.mongo_world = mongo_world

    def _serialize(self, value, attr, obj):
        if value is None:
            return None
        if self.mongo_world:
            # In mongo world, value is a regular ObjectId
            return str(value)
        else:
            # In OO world, value is a :class:`umongo.data_object.Reference`
            return str(value.pk)


class GenericReference(ma_fields.Field):
    """
    Marshmallow field for :class:`umongo.fields.GenericReferenceField`
    """

    def __init__(self, *args, mongo_world=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.mongo_world = mongo_world

    def _serialize(self, value, attr, obj):
        if value is None:
            return None
        if self.mongo_world:
            # In mongo world, value a dict of cls and id
            return {'id': str(value['_id']), 'cls': value['_cls']}
        else:
            # In OO world, value is a :class:`umongo.data_object.Reference`
            return {'id': str(value.pk), 'cls': value.document_cls.__name__}

    def _deserialize(self, value, attr, data):
        if value is None:
            return None
        if not isinstance(value, dict):
            raise ValidationError(_("Invalid value for generic reference field."))
        if value.keys() != {'cls', 'id'}:
            raise ValidationError(_("Generic reference must have `id` and `cls` fields."))
        try:
            _id = bson.ObjectId(value['id'])
        except ValueError:
            raise ValidationError(_("Invalid `id` field."))
        if self.mongo_world:
            return {'_cls': value['cls'], '_id': _id}
        else:
            return {'cls': value['cls'], 'id': _id}
