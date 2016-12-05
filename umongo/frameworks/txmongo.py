from txmongo.database import Database
from twisted.internet.defer import (
    inlineCallbacks, Deferred, DeferredList, returnValue, maybeDeferred)
from txmongo import filter as qf
from pymongo.errors import DuplicateKeyError

from ..builder import BaseBuilder
from ..document import DocumentImplementation
from ..data_proxy import missing
from ..data_objects import Reference
from ..exceptions import NotCreatedError, UpdateError, DeleteError, ValidationError
from ..fields import ReferenceField, ListField, EmbeddedField
from ..query_mapper import map_query

from .tools import cook_find_filter


class TxMongoDocument(DocumentImplementation):

    __slots__ = ()

    opts = DocumentImplementation.opts

    @inlineCallbacks
    def reload(self):
        """
        Retrieve and replace document's data by the ones in database.

        Raises :class:`umongo.exceptions.NotCreatedError` if the document
        doesn't exist in database.
        """
        if not self.is_created:
            raise NotCreatedError("Document doesn't exists in database")
        ret = yield self.collection.find_one(self.pk)
        if ret is None:
            raise NotCreatedError("Document doesn't exists in database")
        self._data = self.DataProxy()
        self._data.from_mongo(ret)

    @inlineCallbacks
    def commit(self, io_validate_all=False, conditions=None):
        """
        Commit the document in database.
        If the document doesn't already exist it will be inserted, otherwise
        it will be updated.

        :param io_validate_all:
        :param conditions: only perform commit if matching record in db
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
                    additional_filter = yield maybeDeferred(self.pre_update)
                    if additional_filter:
                        query.update(map_query(additional_filter, self.schema.fields))
                    self.required_validate()
                    yield self.io_validate(validate_all=io_validate_all)
                    payload = self._data.to_mongo(update=True)
                    ret = yield self.collection.update_one(query, payload)
                    if ret.matched_count != 1:
                        raise UpdateError(ret)
                    yield maybeDeferred(self.post_update, ret)
                else:
                    ret = None
            elif conditions:
                raise RuntimeError('Document must already exist in database to use `conditions`.')
            else:
                yield maybeDeferred(self.pre_insert)
                self.required_validate()
                yield self.io_validate(validate_all=io_validate_all)
                payload = self._data.to_mongo(update=False)
                ret = yield self.collection.insert_one(payload)
                # TODO: check ret ?
                self._data.set_by_mongo_name('_id', ret.inserted_id)
                self.is_created = True
                yield maybeDeferred(self.post_insert, ret)
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
        self._data.clear_modified()
        return ret

    @inlineCallbacks
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
        additional_filter = yield maybeDeferred(self.pre_delete)
        if additional_filter:
            query.update(map_query(additional_filter, self.schema.fields))
        ret = yield self.collection.delete_one(query)
        if ret.deleted_count != 1:
            raise DeleteError(ret)
        self.is_created = False
        yield maybeDeferred(self.post_delete, ret)
        return ret

    def io_validate(self, validate_all=False):
        """
        Run the io_validators of the document's fields.

        :param validate_all: If False only run the io_validators of the
            fields that have been modified.
        """
        if validate_all:
            return _io_validate_data_proxy(self.schema, self._data)
        else:
            return _io_validate_data_proxy(
                self.schema, self._data, partial=self._data.get_modified_fields())

    @classmethod
    @inlineCallbacks
    def find_one(cls, spec=None, *args, **kwargs):
        """
        Find a single document in database.
        """
        # In txmongo, `spec` is for filtering and `filter` is for sorting
        spec = cook_find_filter(cls, spec)
        ret = yield cls.collection.find_one(*args, spec=spec, **kwargs)
        if ret is not None:
            ret = cls.build_from_mongo(ret, use_cls=True)
        return ret

    @classmethod
    @inlineCallbacks
    def find(cls, spec=None, *args, **kwargs):
        """
        Find a list document in database.

        Returns a cursor that provide Documents.
        """
        # In txmongo, `spec` is for filtering and `filter` is for sorting
        spec = cook_find_filter(cls, spec)
        raw_cursor_or_list = yield cls.collection.find(*args, spec=spec, **kwargs)
        if isinstance(raw_cursor_or_list, tuple):

            def wrap_raw_results(result):
                cursor = result[1]
                if cursor is not None:
                    cursor.addCallback(wrap_raw_results)
                return ([cls.build_from_mongo(e, use_cls=True) for e in result[0]], cursor)

            return wrap_raw_results(raw_cursor_or_list)
        else:
            return [cls.build_from_mongo(e, use_cls=True) for e in raw_cursor_or_list]

    @classmethod
    def count(cls, spec=None, **kwargs):
        """
        Get the number of documents in this collection.
        """
        # In txmongo, `spec` is for filtering and `filter` is for sorting
        spec = cook_find_filter(cls, spec)
        return cls.collection.count(spec=spec, **kwargs)

    @classmethod
    @inlineCallbacks
    def ensure_indexes(cls):
        """
        Check&create if needed the Document's indexes in database
        """
        for index in cls.opts.indexes:
            kwargs = index.document.copy()
            keys = kwargs.pop('key')
            index = qf.sort([(k, d) for k, d in keys.items()])
            yield cls.collection.create_index(index, **kwargs)


def _errback_factory(errors, field=None):

    def errback(err):
        if isinstance(err.value, ValidationError):
            if field is not None:
                errors[field] = err.value.messages
            else:
                errors.extend(err.value.messages)
        else:
            raise err.value

    return errback


# Run multiple validators and collect all errors in one
@inlineCallbacks
def _run_validators(validators, field, value):
    errors = []
    defers = []
    for validator in validators:
        try:
            defer = validator(field, value)
        except ValidationError as ve:
            errors.extend(ve.messages)
        else:
            assert isinstance(defer, Deferred), 'io_validate functions must return a Deferred'
            defer.addErrback(_errback_factory(errors))
            defers.append(defer)
    yield DeferredList(defers)
    if errors:
        raise ValidationError(errors)


@inlineCallbacks
def _io_validate_data_proxy(schema, data_proxy, partial=None):
    errors = {}
    defers = []
    for name, field in schema.fields.items():
        if partial and name not in partial:
            continue
        data_name = field.attribute or name
        value = data_proxy._data[data_name]
        if value is missing:
            continue
        try:
            if field.io_validate_recursive:
                yield field.io_validate_recursive(field, value)
            if field.io_validate:
                defer = _run_validators(field.io_validate, field, value)
                defer.addErrback(_errback_factory(errors, name))
                defers.append(defer)
        except ValidationError as ve:
            errors[name] = ve.messages
    yield DeferredList(defers)
    if errors:
        raise ValidationError(errors)


def _reference_io_validate(field, value):
    return value.fetch(no_data=True)


@inlineCallbacks
def _list_io_validate(field, value):
    validators = field.container.io_validate
    if not validators or not value:
        return
    errors = {}
    defers = []
    for i, e in enumerate(value):
        defer = _run_validators(validators, field.container, e)
        defer.addErrback(_errback_factory(errors, i))
        defers.append(defer)
    yield DeferredList(defers)
    if errors:
        raise ValidationError(errors)


def _embedded_document_io_validate(field, value):
    return _io_validate_data_proxy(value.schema, value._data)


class TxMongoReference(Reference):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._document = None

    @inlineCallbacks
    def fetch(self, no_data=False):
        if not self._document:
            if self.pk is None:
                raise ReferenceError('Cannot retrieve a None Reference')
            self._document = yield self.document_cls.find_one(self.pk)
            if not self._document:
                raise ValidationError(self.error_messages['not_found'].format(
                    document=self.document_cls.__name__))
        returnValue(self._document)


class TxMongoBuilder(BaseBuilder):

    BASE_DOCUMENT_CLS = TxMongoDocument

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
                validators = list(validators)
            else:
                validators = [validators]
            field.io_validate = validators
        if isinstance(field, ListField):
            field.io_validate_recursive = _list_io_validate
        if isinstance(field, ReferenceField):
            field.io_validate.append(_reference_io_validate)
            field.reference_cls = TxMongoReference
        if isinstance(field, EmbeddedField):
            field.io_validate_recursive = _embedded_document_io_validate
