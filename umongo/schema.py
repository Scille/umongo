from .abstract import BaseSchema


__all__ = ('Schema', 'EmbeddedSchema', 'on_need_add_id_field', 'add_child_field')


def on_need_add_id_field(bases, fields):
    """
    If the given fields make no reference to `_id`, add an `id` field
    (type ObjectId, dump_only=True, attribute=`_id`) to handle it
    """

    def find_id_field(fields):
        for name, field in fields.items():
            if (name == '_id' and not field.attribute) or field.attribute == '_id':
                return name, field

    # Search among parents for the id field
    for base in bases:
        schema = base()
        if find_id_field(schema.fields):
            return

    # Search amongo our own fields
    if not find_id_field(fields):
        # No id field found, add a default one
        from .fields import ObjectIdField
        fields['id'] = ObjectIdField(attribute='_id', dump_only=True)


def add_child_field(name, fields):
    from .fields import StrField
    fields['cls'] = StrField(attribute='_cls', missing=name, dump_only=True)


class Schema(BaseSchema):
    """
    Base schema class used by :class:`umongo.Document`
    """

    pass


class EmbeddedSchema(BaseSchema):
    """
    Base schema class used by :class:`umongo.EmbeddedDocument`
    """

    pass
