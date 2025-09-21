import marshmallow as ma

from .exceptions import DocumentDefinitionError
from .expose_missing import RemoveMissingSchema
from .i18n import N_
from .i18n import gettext as _

__all__ = (
    "BaseDataObject",
    "BaseField",
    "BaseMarshmallowSchema",
    "BaseSchema",
    "BaseValidator",
)


class I18nErrorDict(dict):
    def __getitem__(self, name):
        raw_msg = dict.__getitem__(self, name)
        return _(raw_msg)


class BaseMarshmallowSchema(RemoveMissingSchema):
    """Base schema for pure marshmallow schemas"""


class BaseSchema(ma.Schema):
    """All schema used in umongo should inherit from this base schema"""

    # This class attribute is overriden by the builder upon registration
    # to let the template set the base marshmallow schema class.
    # It may be overriden in Template classes.
    MA_BASE_SCHEMA_CLS = BaseMarshmallowSchema

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_messages = I18nErrorDict(self.error_messages)
        self._ma_schema = None

    def map_to_field(self, func):
        """Apply a function to every field in the schema

        >>> def func(mongo_path, path, field):
        ...     pass
        """
        for name, field in self.fields.items():
            mongo_path = field.attribute or name
            func(mongo_path, name, field)
            if hasattr(field, "map_to_field"):
                field.map_to_field(mongo_path, name, func)

    def as_marshmallow_schema(self):
        """Return a pure-marshmallow version of this schema class"""
        # Use a cache to avoid generating several times the same schema
        if self._ma_schema is not None:
            return self._ma_schema

        # Create schema if not found in cache
        nmspc = {
            name: field.as_marshmallow_field() for name, field in self.fields.items()
        }
        name = "Marshmallow%s" % type(self).__name__
        m_schema = type(name, (self.MA_BASE_SCHEMA_CLS,), nmspc)
        # Add i18n support to the schema
        # We can't use I18nErrorDict here because __getitem__ is not called
        # when error_messages is updated with _default_error_messages.
        m_schema._default_error_messages = {
            k: _(v) for k, v in m_schema._default_error_messages.items()
        }
        self._ma_schema = m_schema
        return m_schema


class BaseField(ma.fields.Field):
    """All fields used in umongo should inherit from this base field.

    ==============================   ===============
    Enabled flags                    resulting index
    ==============================   ===============
    <no flags>
    allow_none
    required
    required, allow_none
    required, unique, allow_none     unique
    unique                           unique, sparse
    unique, required                 unique
    unique, allow_none               unique, sparse
    ==============================   ===============

    .. note:: Even with allow_none flag, the unique flag will refuse duplicated
        `null` value. Consider unsetting the field with `del` instead.
    """

    default_error_messages = {
        "unique": N_("Field value must be unique."),
        "unique_compound": N_("Values of fields {fields} must be unique together."),
    }

    MARSHMALLOW_ARGS_PREFIX = "marshmallow_"

    def __init__(self, *args, io_validate=None, unique=False, instance=None, **kwargs):
        if "missing" in kwargs:
            raise DocumentDefinitionError(
                "uMongo doesn't use `missing` argument, use `default` "
                "instead and `marshmallow_load_default`/`marshmallow_dump_default` "
                "to tell `as_marshmallow_field` to use a custom value when "
                "generating pure Marshmallow field.",
            )
        if "default" in kwargs:
            kwargs["load_default"] = kwargs["dump_default"] = kwargs.pop("default")

        # Store attributes prefixed with marshmallow_ to use them when
        # creating pure marshmallow Schema
        self._ma_kwargs = {
            key[len(self.MARSHMALLOW_ARGS_PREFIX) :]: val
            for key, val in kwargs.items()
            if key.startswith(self.MARSHMALLOW_ARGS_PREFIX)
        }
        kwargs = {
            key: val
            for key, val in kwargs.items()
            if not key.startswith(self.MARSHMALLOW_ARGS_PREFIX)
        }

        super().__init__(*args, **kwargs)

        self._ma_kwargs.setdefault("dump_default", self.dump_default)
        self._ma_kwargs.setdefault("load_default", self.dump_default)

        # Overwrite error_messages to handle i18n translation
        self.error_messages = I18nErrorDict(self.error_messages)
        # `io_validate` will be run after `io_validate_resursive`
        # only if this one doesn't returns errors. This is useful for
        # list and embedded fields.
        self.io_validate = io_validate
        self.io_validate_recursive = None
        self.unique = unique
        self.instance = instance

    def __repr__(self):
        return (
            f"<fields.{self.__class__.__name__}(default={self.load_default!r}, "
            f"attribute={self.attribute!r}, "
            f"validate={self.validate}, required={self.required}, "
            f"load_only={self.load_only}, dump_only={self.dump_only}, "
            f"allow_none={self.allow_none}, "
            f"error_messages={self.error_messages}, "
            f"io_validate={self.io_validate}, "
            f"io_validate_recursive={self.io_validate_recursive}, "
            f"unique={self.unique}, "
            f"marshmallow_kwargs={self._ma_kwargs!r}, "
            f"instance={self.instance})>"
        )

    def _validate_missing(self, value):
        # Overwrite marshmallow.Field._validate_missing given it also checks
        # for missing required fields (this is done at commit time in umongo
        # using `DataProxy.required_validate`).
        if value is None and getattr(self, "allow_none", False) is False:
            self.fail("null")

    def serialize_to_mongo(self, obj):
        if obj is None and getattr(self, "allow_none", False) is True:
            return None
        if obj is ma.missing:
            return ma.missing
        return self._serialize_to_mongo(obj)

    # def serialize_to_mongo_update(self, path, obj):
    #     return self._serialize_to_mongo(attr, obj=obj, update=update)

    def deserialize_from_mongo(self, value):
        if value is None and getattr(self, "allow_none", False) is True:
            return None
        return self._deserialize_from_mongo(value)

    def _serialize_to_mongo(self, obj):
        return obj

    def _deserialize_from_mongo(self, value):
        return value

    def _extract_marshmallow_field_params(self):
        params = {
            attribute: getattr(self, attribute)
            for attribute in (
                "validate",
                "required",
                "allow_none",
                "load_only",
                "dump_only",
                "error_messages",
            )
        }
        # Override uMongo attributes with marshmallow_ prefixed attributes
        params.update(self._ma_kwargs)
        return params

    def as_marshmallow_field(self):  # noqa: RET503 (no explicit return)
        """Return a pure-marshmallow version of this field"""
        field_kwargs = self._extract_marshmallow_field_params()
        # Retrieve the marshmallow class we inherit from
        for m_class in type(self).mro():
            if not issubclass(m_class, BaseField) and issubclass(
                m_class,
                ma.fields.Field,
            ):
                m_field = m_class(**field_kwargs, metadata=self.metadata)
                # Add i18n support to the field
                m_field.error_messages = I18nErrorDict(m_field.error_messages)
                return m_field
        # Cannot escape the loop given BaseField itself inherits marshmallow's Field


class BaseValidator(ma.validate.Validator):
    """All validators in umongo should inherit from this base validator."""

    def __init__(self, *args, **kwargs):
        self._error = None
        super().__init__(*args, **kwargs)

    @property
    def error(self):
        return _(self._error)

    @error.setter
    def error(self, value):
        self._error = value


class BaseDataObject:
    """All data objects in umongo should inherit from this base data object."""

    def is_modified(self):
        raise NotImplementedError

    def clear_modified(self):
        raise NotImplementedError

    @classmethod
    def build_from_mongo(cls, data):
        doc = cls()
        doc.from_mongo(data)
        return doc

    def from_mongo(self, data):
        return self(data)

    def to_mongo(self, update=False):
        return self

    def dump(self):
        return self
