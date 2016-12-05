from pymongo.database import Database
from pymongo.cursor import Cursor
from pymongo.errors import DuplicateKeyError

from ..builder import BaseBuilder
from ..document import DocumentImplementation
from ..data_proxy import missing
from ..data_objects import Reference
from ..exceptions import NotCreatedError, UpdateError, DeleteError, ValidationError
from ..fields import ReferenceField, ListField, EmbeddedField
from ..query_mapper import map_query

from .tools import cook_find_filter


class WrappedCursor(Cursor):

    __slots__ = ('raw_cursor', 'document_cls')

    def __init__(self, document_cls, cursor, *args, **kwargs):
        # Such a cunning plan my lord !
        # We inherit from Cursor but don't call it __init__ because
        # we act as a proxy to the underlying raw_cursor
        WrappedCursor.raw_cursor.__set__(self, cursor)
        WrappedCursor.document_cls.__set__(self, document_cls)

    def __getattr__(self, name):
        return getattr(self.raw_cursor, name)

    def __setattr__(self, name, value):
        return setattr(self.raw_cursor, name, value)

    def __getitem__(self, index):
        if isinstance(index, slice):
            elems = self.raw_cursor[index]
            return (self.document_cls.build_from_mongo(elem, use_cls=True)
                    for elem in elems)
        elem = self.raw_cursor[index]
        return self.document_cls.build_from_mongo(elem, use_cls=True)

    def __next__(self):
        elem = next(self.raw_cursor)
        return self.document_cls.build_from_mongo(elem, use_cls=True)

    def __iter__(self):
        for elem in self.raw_cursor:
            yield self.document_cls.build_from_mongo(elem, use_cls=True)


class PyMongoDocument(DocumentImplementation):

    __slots__ = ()

    opts = DocumentImplementation.opts

    def reload(self):
        """
        Retrieve and replace document's data by the ones in database.

        Raises :class:`umongo.exceptions.NotCreatedError` if the document
        doesn't exist in database.
        """
        if not self.is_created:
            raise NotCreatedError("Document doesn't exists in database")
        ret = self.collection.find_one(self.pk)
        if ret is None:
            raise NotCreatedError("Document doesn't exists in database")
        self._data = self.DataProxy()
        self._data.from_mongo(ret)

    def commit(self, io_validate_all=False, conditions=None):
        """
        Commit the document in database.
        If the document doesn't already exist it will be inserted, otherwise
        it will be updated.

        :param io_validate_all: Validate all field instead of only changed ones.
        :param conditions: Only perform commit if matching record in db
            satisfies condition(s) (e.g. version number).
            Raises :class:`umongo.exceptions.UpdateError` if the
            conditions are not satisfied.
        :return: A :class:`pymongo.results.UpdateResult` or
            :class:`pymongo.results.InsertOneResult` depending of the operation.
        """
        try:
            if self.is_created:
                if self.is_modified():
                    query = conditions or {}
                    query['_id'] = self.pk
                    # pre_update can provide additional query filter and/or
                    # modify the fields' values
                    additional_filter = self.pre_update()
                    if additional_filter:
                        query.update(map_query(additional_filter, self.schema.fields))
                    self.required_validate()
                    self.io_validate(validate_all=io_validate_all)
                    payload = self._data.to_mongo(update=True)
                    ret = self.collection.update_one(query, payload)
                    if ret.matched_count != 1:
                        raise UpdateError(ret)
                    self.post_update(ret)
                else:
                    ret = None
            elif conditions:
                raise RuntimeError('Document must already exist in database to use `conditions`.')
            else:
                self.pre_insert()
                self.required_validate()
                self.io_validate(validate_all=io_validate_all)
                payload = self._data.to_mongo(update=False)
                ret = self.collection.insert_one(payload)
                # TODO: check ret ?
                self._data.set_by_mongo_name('_id', ret.inserted_id)
                self.is_created = True
                self.post_insert(ret)
        except DuplicateKeyError as exc:
            # Need to dig into error message to find faulting index
            errmsg = exc.details['errmsg']
            for index in self.opts.indexes:
                if ('.$%s' % index.document['name'] in errmsg or
                        ' %s ' % index.document['name'] in errmsg):
                    keys = index.document['key'].keys()
                    if len(keys) == 1:
                        msg = self.schema.fields[keys[0]].error_messages['unique']
                        raise ValidationError({keys[0]: msg})
                    else:
                        fields = self.schema.fields
                        # Compound index (sort value to make testing easier)
                        keys = sorted(keys)
                        raise ValidationError({k: fields[k].error_messages[
                            'unique_compound'].format(fields=keys) for k in keys})
            # Unknown index, cannot wrap the error so just reraise it
            raise
        self._data.clear_modified()
        return ret

    def delete(self, conditions=None):
        """
        Remove the document from database.

        :param conditions: Only perform delete if matching record in db
            satisfies condition(s) (e.g. version number).
            Raises :class:`umongo.exceptions.DeleteError` if the
            conditions are not satisfied.
        Raises :class:`umongo.exceptions.NotCreatedError` if the document
        is not created (i.e. ``doc.is_created`` is False)
        Raises :class:`umongo.exceptions.DeleteError` if the document
        doesn't exist in database.

        :return: A :class:`pymongo.results.DeleteResult`
        """
        if not self.is_created:
            raise NotCreatedError("Document doesn't exists in database")
        query = conditions or {}
        query['_id'] = self.pk
        # pre_delete can provide additional query filter
        additional_filter = self.pre_delete()
        if additional_filter:
            query.update(map_query(additional_filter, self.schema.fields))
        ret = self.collection.delete_one(query)
        if ret.deleted_count != 1:
            raise DeleteError(ret)
        self.is_created = False
        self.post_delete(ret)
        return ret

    def io_validate(self, validate_all=False):
        """
        Run the io_validators of the document's fields.

        :param validate_all: If False only run the io_validators of the
            fields that have been modified.
        """
        if validate_all:
            _io_validate_data_proxy(self.schema, self._data)
        else:
            _io_validate_data_proxy(
                self.schema, self._data, partial=self._data.get_modified_fields())

    @classmethod
    def find_one(cls, filter=None, *args, **kwargs):
        """
        Find a single document in database.
        """
        filter = cook_find_filter(cls, filter)
        ret = cls.collection.find_one(*args, filter=filter, **kwargs)
        if ret is not None:
            ret = cls.build_from_mongo(ret, use_cls=True)
        return ret

    @classmethod
    def find(cls, filter=None, *args, **kwargs):
        """
        Find a list document in database.

        Returns a cursor that provide Documents.
        """
        filter = cook_find_filter(cls, filter)
        raw_cursor = cls.collection.find(*args, filter=filter, **kwargs)
        return WrappedCursor(cls, raw_cursor)

    @classmethod
    def ensure_indexes(cls):
        """
        Check&create if needed the Document's indexes in database
        """
        if cls.opts.indexes:
            cls.collection.create_indexes(cls.opts.indexes)


# Run multiple validators and collect all errors in one
def _run_validators(validators, field, value):
    if not hasattr(validators, '__iter__'):
        validators(field, value)
    else:
        errors = []
        for validator in validators:
            try:
                validator(field, value)
            except ValidationError as ve:
                errors.extend(ve.messages)
        if errors:
            raise ValidationError(errors)


def _io_validate_data_proxy(schema, data_proxy, partial=None):
    errors = {}
    for name, field in schema.fields.items():
        if partial and (partial is True or name not in partial):
            continue
        data_name = field.attribute or name
        value = data_proxy._data[data_name]
        if value is missing:
            continue
        try:
            if field.io_validate_recursive:
                field.io_validate_recursive(field, value)
            if field.io_validate:
                _run_validators(field.io_validate, field, value)
        except ValidationError as ve:
            errors[name] = ve.messages
    if errors:
        raise ValidationError(errors)


def _reference_io_validate(field, value):
    value.fetch(no_data=True)


def _list_io_validate(field, value):
    errors = {}
    validators = field.container.io_validate
    if not validators:
        return
    for i, e in enumerate(value):
        try:
            _run_validators(validators, field.container, e)
        except ValidationError as ev:
            errors[i] = ev.messages
    if errors:
        raise ValidationError(errors)


def _embedded_document_io_validate(field, value):
    _io_validate_data_proxy(value.schema, value._data)


class PyMongoReference(Reference):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._document = None

    def fetch(self, no_data=False):
        if not self._document:
            if self.pk is None:
                raise ReferenceError('Cannot retrieve a None Reference')
            self._document = self.document_cls.find_one(self.pk)
            if not self._document:
                raise ValidationError(self.error_messages['not_found'].format(
                    document=self.document_cls.__name__))
        return self._document


class PyMongoBuilder(BaseBuilder):

    BASE_DOCUMENT_CLS = PyMongoDocument

    @staticmethod
    def is_compatible_with(db):
        return isinstance(db, Database)

    def _patch_field(self, field):
        super()._patch_field(field)

        validators = field.io_validate
        if not validators:
            field.io_validate = []
        else:
            if hasattr(validators, '__iter__'):
                field.io_validate = list(validators)
            else:
                field.io_validate = [validators]
        if isinstance(field, ListField):
            field.io_validate_recursive = _list_io_validate
        if isinstance(field, ReferenceField):
            field.io_validate.append(_reference_io_validate)
            field.reference_cls = PyMongoReference
        if isinstance(field, EmbeddedField):
            field.io_validate_recursive = _embedded_document_io_validate
