"""Pure marshmallow fields used in umongo"""
import bson
import marshmallow as ma
from .template import get_template

from bson import ObjectId as BsonObjectId

from .i18n import gettext as _


__all__ = (
    'ObjectId',
    'Reference',
    'GenericReference'
)


class ObjectId(ma.fields.Field):
    """Marshmallow field for :class:`bson.objectid.ObjectId`"""

    def _serialize(self, value, attr, obj):
        if value is None:
            return None
        return str(value)

    def _deserialize(self, value, attr, data, **kwargs):
        try:
            return bson.ObjectId(value)
        except (TypeError, bson.errors.InvalidId):
            raise ma.ValidationError(_('Invalid ObjectId.'))


class Reference(ma.fields.Field):
    """Marshmallow field for :class:`umongo.fields.ReferenceField`"""

    def _serialize(self, value, attr, obj):
        if value is None:
            return None
        # In OO world, value is a :class:`umongo.data_object.Reference`
        # or an ObjectId before being loaded into a Document
        if isinstance(value, bson.ObjectId):
            return str(value)
        return str(value.pk)

    def _get_pk_template(self):
        if not self._pk_template:
            if isinstance(self.document, str):
                document_template = get_template(self.document_cls)
            else:
                document_template = self.document
            if hasattr(document_template, self.document_cls.pk_field):
                self._pk_template = getattr(document_template, self.document_cls.pk_field)
            else:
                self._pk_template = ObjectId
        return self._pk_template

    def _deserialize(self, value, attr, data, **kwargs):
        try:
            return self._get_pk_template()._deserialize(self, value, attr, data, **kwargs)
        except (TypeError, bson.errors.InvalidId):
            raise ma.ValidationError(_('Invalid Reference.'))


class GenericReference(ma.fields.Field):
    """Marshmallow field for :class:`umongo.fields.GenericReferenceField`"""

    def _serialize(self, value, attr, obj):
        if value is None:
            return None
        # In OO world, value is a :class:`umongo.data_object.Reference`
        # or a dict before being loaded into a Document
        if isinstance(value, dict):
            return {'id': str(value['id']), 'cls': value['cls']}
        return {'id': str(value.pk), 'cls': value.document_cls.__name__}

    def _deserialize(self, value, attr, data, **kwargs):
        if not isinstance(value, dict):
            raise ma.ValidationError(_("Invalid value for generic reference field."))
        if value.keys() != {'cls', 'id'}:
            raise ma.ValidationError(_("Generic reference must have `id` and `cls` fields."))
        try:
            _id = bson.ObjectId(value['id'])
        except ValueError:
            raise ma.ValidationError(_("Invalid `id` field."))
        return {'cls': value['cls'], 'id': _id}
