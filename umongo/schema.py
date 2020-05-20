"""Schema used in Document"""
import marshmallow as ma

from .abstract import BaseSchema
from .i18n import gettext as _


__all__ = (
    'Schema',
    'schema_from_umongo_get_attribute',
    'SchemaFromUmongo',
)


def schema_from_umongo_get_attribute(self, obj, attr, default):
    """
    Overwrite default `Schema.get_attribute` method by this one to access
        umongo missing fields instead of returning `None`.

    example::

        class MySchema(marshsmallow.Schema):
            get_attribute = schema_from_umongo_get_attribute

            # Define the rest of your schema
            ...

    """
    ret = ma.Schema.get_attribute(self, obj, attr, default)
    if ret is None and ret is not default and attr in obj.schema.fields:
        raw_ret = obj._data.get(attr)
        return default if raw_ret is ma.missing else raw_ret
    return ret


class SchemaFromUmongo(ma.Schema):
    """
    Custom :class:`marshmallow.Schema` subclass providing unknown fields
    checking and custom get_attribute for umongo documents.

    .. note: It is not mandatory to use this schema with umongo document.
        This is just a helper providing usefull behaviors.
    """
    get_attribute = schema_from_umongo_get_attribute


class Schema(BaseSchema):
    """Schema used in Document"""

    _marshmallow_schemas_cache = {}

    def as_marshmallow_schema(self, *, mongo_world=False):
        """
        Return a pure-marshmallow version of this schema class.

        :param mongo_world: If True the schema will work against the mongo world
            instead of the OO world (default: False).
        """
        # Use a cache to avoid generating several times the same schema
        cache_key = (self.__class__, self.MA_BASE_SCHEMA_CLS, mongo_world)
        if cache_key in self._marshmallow_schemas_cache:
            return self._marshmallow_schemas_cache[cache_key]

        # Create schema if not found in cache
        nmspc = {
            name: field.as_marshmallow_field(mongo_world=mongo_world)
            for name, field in self.fields.items()
        }
        name = 'Marshmallow%s' % type(self).__name__
        # By default OO world returns `missing` fields as `None`,
        # disable this behavior here to let marshmallow deal with it
        if not mongo_world:
            nmspc['get_attribute'] = schema_from_umongo_get_attribute
        m_schema = type(name, (self.MA_BASE_SCHEMA_CLS, ), nmspc)
        # Add i18n support to the schema
        # We can't use I18nErrorDict here because __getitem__ is not called
        # when error_messages is updated with _default_error_messages.
        m_schema._default_error_messages = {
            k: _(v) for k, v in m_schema._default_error_messages.items()}
        self._marshmallow_schemas_cache[cache_key] = m_schema
        return m_schema
