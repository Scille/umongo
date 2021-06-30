import typing as t

TDocument = t.TypeVar("TDocument", bound="Document")


class Document:
    @classmethod
    def find(
        cls: t.Type[TDocument],
        filter: t.Optional[t.Dict[str, t.Any]],
        *args: t.Any,
        **kwargs: t.Any
    ) -> t.List[TDocument]:
        ...
