import asyncio
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCursor
from pymongo.errors import DuplicateKeyError

from ..builder import BaseBuilder
from ..document import DocumentImplementation
from ..data_proxy import missing
from ..data_objects import Reference
from ..exceptions import NotCreatedError, UpdateError, ValidationError, DeleteError
from ..fields import ReferenceField, ListField, EmbeddedField
from ..query_mapper import map_query

from .tools import cook_find_filter


class WrappedCursor(AsyncIOMotorCursor):

    __slots__ = ('raw_cursor', 'document_cls')

    def __init__(self, document_cls, cursor):
        # Such a cunning plan my lord !
        # We inherit from Cursor but don't call it __init__ because
        # we act as a proxy to the underlying raw_cursor
        WrappedCursor.raw_cursor.__set__(self, cursor)
        WrappedCursor.document_cls.__set__(self, document_cls)

    def __getattr__(self, name):
        return getattr(self.raw_cursor, name)

    def __setattr__(self, name, value):
        return setattr(self.raw_cursor, name, value)

    def clone(self):
        return WrappedCursor(self.document_cls, self.raw_cursor.clone())

    def next_object(self):
        raw = self.raw_cursor.next_object()
        return self.document_cls.build_from_mongo(raw, use_cls=True)

    def each(self, callback):
        def wrapped_callback(result, error):
            if not error and result is not None:
                result = self.document_cls.build_from_mongo(result, use_cls=True)
            return callback(result, error)
        return self.raw_cursor.each(wrapped_callback)

    def to_list(self, length, callback=None):
        raw_future = self.raw_cursor.to_list(length, callback=callback)
        cooked_future = asyncio.Future()
        builder = self.document_cls.build_from_mongo

        def on_raw_done(fut):
            cooked_future.set_result([builder(e, use_cls=True) for e in fut.result()])

        raw_future.add_done_callback(on_raw_done)
        return cooked_future


class MotorAsyncIODocument(DocumentImplementation):

    __slots__ = ()

    opts = DocumentImplementation.opts

    # Cook hooks into coroutines in order to allow them to return
    # either Future or regular return value.

    @asyncio.coroutine
    def __coroutined_pre_insert(self):
        return self.pre_insert()

    @asyncio.coroutine
    def __coroutined_pre_update(self):
        return self.pre_update()

    @asyncio.coroutine
    def __coroutined_pre_delete(self):
        return self.pre_delete()

    @asyncio.coroutine
    def __coroutined_post_insert(self, ret):
        return self.post_insert(ret)

    @asyncio.coroutine
    def __coroutined_post_update(self, ret):
        return self.post_update(ret)

    @asyncio.coroutine
    def __coroutined_post_delete(self, ret):
        return self.post_delete(ret)

    @asyncio.coroutine
    def reload(self):
        """
        Retrieve and replace document's data by the ones in database.

        Raises :class:`umongo.exceptions.NotCreatedError` if the document
        doesn't exist in database.
        """
        if not self.is_created:
            raise NotCreatedError("Document doesn't exists in database")
        ret = yield from self.collection.find_one(self.pk)
        if ret is None:
            raise NotCreatedError("Document doesn't exists in database")
        self._data = self.DataProxy()
        self._data.from_mongo(ret)

    @asyncio.coroutine
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
        :return: Update result dict returned by underlaying driver or
            ObjectId of the inserted document.
        """
        try:
            if self.is_created:
                if self.is_modified():
                    query = conditions or {}
                    query['_id'] = self.pk
                    # pre_update can provide additional query filter and/or
                    # modify the fields' values
                    additional_filter = yield from self.__coroutined_pre_update()
                    if additional_filter:
                        query.update(map_query(additional_filter, self.schema.fields))
                    self.required_validate()
                    yield from self.io_validate(validate_all=io_validate_all)
                    payload = self._data.to_mongo(update=True)
                    ret = yield from self.collection.update(query, payload)
                    if ret.get('ok') != 1 or ret.get('n') != 1:
                        raise UpdateError(ret)
                    yield from self.__coroutined_post_update(ret)
                else:
                    ret = None
            elif conditions:
                raise RuntimeError('Document must already exist in database to use `conditions`.')
            else:
                yield from self.__coroutined_pre_insert()
                self.required_validate()
                yield from self.io_validate(validate_all=io_validate_all)
                payload = self._data.to_mongo(update=False)
                ret = yield from self.collection.insert(payload)
                # TODO: check ret ?
                self._data.set_by_mongo_name('_id', ret)
                self.is_created = True
                yield from self.__coroutined_post_insert(ret)
        except DuplicateKeyError as exc:
            # Need to dig into error message to find faulting index
            errmsg = exc.details['errmsg']
            for index in self.opts.indexes:
                if ('.$%s' % index.document['name'] in errmsg or
                        ' %s ' % index.document['name'] in errmsg):
                    keys = index.document['key'].keys()
                    if len(keys) == 1:
                        key = tuple(keys)[0]
                        msg = self.schema.fields[key].error_messages['unique']
                        raise ValidationError({key: msg})
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

    @asyncio.coroutine
    def delete(self, conditions=None):
        """
        Alias of :meth:`remove` to enforce default api.
        """
        return self.remove(conditions=conditions)

    @asyncio.coroutine
    def remove(self, conditions=None):
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

        :return: Delete result dict returned by underlaying driver.
        """
        if not self.is_created:
            raise NotCreatedError("Document doesn't exists in database")
        query = conditions or {}
        query['_id'] = self.pk
        # pre_delete can provide additional query filter
        additional_filter = yield from self.__coroutined_pre_delete()
        if additional_filter:
            query.update(map_query(additional_filter, self.schema.fields))
        ret = yield from self.collection.remove(query)
        if ret.get('ok') != 1 or ret.get('n') != 1:
            raise DeleteError(ret)
        self.is_created = False
        yield from self.__coroutined_post_delete(ret)
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
    @asyncio.coroutine
    def find_one(cls, spec_or_id=None, *args, **kwargs):
        """
        Find a single document in database.
        """
        # In pymongo<3, `spec_or_id` is for filtering and `filter` is for sorting
        spec_or_id = cook_find_filter(cls, spec_or_id)
        ret = yield from cls.collection.find_one(*args, spec_or_id=spec_or_id, **kwargs)
        if ret is not None:
            ret = cls.build_from_mongo(ret, use_cls=True)
        return ret

    @classmethod
    def find(cls, spec=None, *args, **kwargs):
        """
        Find a list document in database.

        Returns a cursor that provide Documents.
        """
        # In pymongo<3, `spec` is for filtering and `filter` is for sorting
        spec = cook_find_filter(cls, spec)
        return WrappedCursor(cls, cls.collection.find(*args, spec=spec, **kwargs))

    @classmethod
    @asyncio.coroutine
    def ensure_indexes(cls):
        """
        Check&create if needed the Document's indexes in database
        """
        for index in cls.opts.indexes:
            kwargs = index.document.copy()
            keys = [(k, d) for k, d in kwargs.pop('key').items()]
            yield from cls.collection.create_index(keys, **kwargs)


# Run multiple validators and collect all errors in one
@asyncio.coroutine
def _run_validators(validators, field, value):
    errors = []
    tasks = [validator(field, value) for validator in validators]
    results = yield from asyncio.gather(*tasks, return_exceptions=True)
    for i, res in enumerate(results):
        if isinstance(res, ValidationError):
            errors.extend(res.messages)
        elif res:
            raise res
    if errors:
        raise ValidationError(errors)


def _io_validate_data_proxy(schema, data_proxy, partial=None):
    errors = {}
    tasks = []
    tasks_field_name = []
    for name, field in schema.fields.items():
        if partial and name not in partial:
            continue
        data_name = field.attribute or name
        value = data_proxy._data[data_name]
        if value is missing:
            continue
        try:
            if field.io_validate_recursive:
                yield from field.io_validate_recursive(field, value)
            if field.io_validate:
                tasks.append(_run_validators(field.io_validate, field, value))
                tasks_field_name.append(name)
        except ValidationError as ve:
            errors[name] = ve.messages
    results = yield from asyncio.gather(*tasks, return_exceptions=True)
    for i, res in enumerate(results):
        if isinstance(res, ValidationError):
            errors[tasks_field_name[i]] = res.messages
        elif res:
            raise res
    if errors:
        raise ValidationError(errors)


@asyncio.coroutine
def _reference_io_validate(field, value):
    yield from value.fetch(no_data=True)


@asyncio.coroutine
def _list_io_validate(field, value):
    validators = field.container.io_validate
    if not validators or not value:
        return
    tasks = [_run_validators(validators, field.container, e) for e in value]
    results = yield from asyncio.gather(*tasks, return_exceptions=True)
    errors = {}
    for i, res in enumerate(results):
        if isinstance(res, ValidationError):
            errors[i] = res.messages
        elif res:
            raise res
    if errors:
        raise ValidationError(errors)


@asyncio.coroutine
def _embedded_document_io_validate(field, value):
    yield from _io_validate_data_proxy(value.schema, value._data)


class MotorAsyncIOReference(Reference):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._document = None

    @asyncio.coroutine
    def fetch(self, no_data=False):
        if not self._document:
            if self.pk is None:
                raise ReferenceError('Cannot retrieve a None Reference')
            self._document = yield from self.document_cls.find_one(self.pk)
            if not self._document:
                raise ValidationError(self.error_messages['not_found'].format(
                    document=self.document_cls.__name__))
        return self._document


class MotorAsyncIOBuilder(BaseBuilder):

    BASE_DOCUMENT_CLS = MotorAsyncIODocument

    @staticmethod
    def is_compatible_with(db):
        return isinstance(db, AsyncIOMotorDatabase)

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
            field.io_validate = [v if asyncio.iscoroutinefunction(v) else asyncio.coroutine(v)
                                 for v in validators]
        if isinstance(field, ListField):
            field.io_validate_recursive = _list_io_validate
        if isinstance(field, ReferenceField):
            field.io_validate.append(_reference_io_validate)
            field.reference_cls = MotorAsyncIOReference
        if isinstance(field, EmbeddedField):
            field.io_validate_recursive = _embedded_document_io_validate
