from collections.abc import Callable
from typing import Any, Generic, TypeVar

from trame_server import Server
from trame_server.state import State
from trame_server.utils.typed_state import TypedState

T = TypeVar("T")


class BaseLogic(Generic[T]):
    def __init__(self, server: Server, state_type: type[T] | None, state_namespace: str = ""):
        self._server = server
        self._typed_state: TypedState[T] | None = (
            TypedState(self.state, state_type, namespace=state_namespace) if state_type else None
        )

    @property
    def server(self) -> Server:
        return self._server

    @property
    def state(self) -> State:
        return self._server.state

    @property
    def ctrl(self) -> State:
        return self._server.controller

    @property
    def name(self) -> T:
        return self._typed_state.name if self._typed_state else None

    @property
    def data(self) -> T:
        return self._typed_state.data if self._typed_state else None

    def bind_changes(self, change_dict: dict[Any | list[Any] | tuple[Any], Callable]):
        if self._typed_state:
            self._typed_state.bind_changes(change_dict)

    def set_ui(self, ui: Any) -> Any:
        pass
