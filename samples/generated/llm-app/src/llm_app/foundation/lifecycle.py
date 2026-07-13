"""Explicit ownership for closeable application resources."""

from contextlib import AbstractContextManager, ExitStack
from types import TracebackType
from typing import Self, TypeVar

T = TypeVar("T")


class ResourceScope:
    """Own resources created by a composition root and close them in reverse order."""

    def __init__(self) -> None:
        self._stack = ExitStack()

    def enter_context(self, resource: AbstractContextManager[T]) -> T:
        return self._stack.enter_context(resource)

    def callback(self, callback: object, *args: object, **kwargs: object) -> None:
        self._stack.callback(callback, *args, **kwargs)  # type: ignore[arg-type]

    def close(self) -> None:
        self._stack.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._stack.__exit__(exc_type, exc_value, traceback)
