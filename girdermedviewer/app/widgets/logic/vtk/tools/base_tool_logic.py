from abc import ABC, abstractmethod

from trame_server import Server

from ...base_logic import BaseLogic, T
from ..views_logic import ViewsLogic


class BaseToolLogic(BaseLogic[T], ABC):
    def __init__(self, server: Server, views_logic: ViewsLogic, state_type: type[T] | None, state_namespace: str = ""):
        super().__init__(server, state_type, state_namespace)
        self._views_logic = views_logic

    @abstractmethod
    def set_enabled(self, enabled: bool) -> None:
        pass
