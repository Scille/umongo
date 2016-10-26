from marshmallow import validate as ma_validate

from .abstract import BaseValidator


__all__ = (
    'URL',
    'Email',
    'Range',
    'Length',
    'Equal',
    'Regexp',
    'Predicate',
    'NoneOf',
    'OneOf',
    'ContainsOnly'
)


class URL(BaseValidator, ma_validate.URL):
    pass


class Email(BaseValidator, ma_validate.Email):
    pass


class Range(BaseValidator, ma_validate.Range):
    pass


class Length(BaseValidator, ma_validate.Length):
    pass


class Equal(BaseValidator, ma_validate.Equal):
    pass


class Regexp(BaseValidator, ma_validate.Regexp):
    pass


class Predicate(BaseValidator, ma_validate.Predicate):
    pass


class NoneOf(BaseValidator, ma_validate.NoneOf):
    pass


class OneOf(BaseValidator, ma_validate.OneOf):
    pass


class ContainsOnly(BaseValidator, ma_validate.ContainsOnly):
    pass
