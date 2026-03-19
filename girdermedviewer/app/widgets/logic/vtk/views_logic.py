from trame_server.core import Server
from undo_stack import Signal

from ...logic.base_logic import BaseLogic
from ...ui import ViewsState, ViewsUI, ViewType
from ...utils import (
    get_color_preset_parser,
    get_volume_preset_parser,
)
from .views.slice_view_logic import SliceViewLogic
from .views.threed_view_logic import ThreeDViewLogic
from .views.view_logic import ViewLogic


class ViewsLogic(BaseLogic[ViewsState]):
    window_level_changed = Signal()

    def __init__(self, server: Server):
        super().__init__(server, ViewsState)
        self.view_logics: dict[ViewType, ViewLogic] = {}
        self.ctrl.reset = self.reset

        self.volume_preset_parser = get_volume_preset_parser()
        self.color_preset_parser = get_color_preset_parser()

        for view_type in ViewType:
            view_logic_type = ThreeDViewLogic if view_type == ViewType.THREED else SliceViewLogic
            self.view_logics[view_type] = view_logic_type(
                server=self.server,
                view_type=view_type,
                volume_preset_parser=self.volume_preset_parser,
                color_preset_parser=self.color_preset_parser,
            )
            self.view_logics[view_type].window_level_changed.connect(self.window_level_changed)

    def set_ui(self, ui: ViewsUI):
        self.update_views = ui.update_views
        for view_type, view_ui in ui.view_uis.items():
            view_logic = self.view_logics.get(view_type)
            if view_logic is not None:
                view_logic.set_ui(view_ui)

    def reset(self):
        for view_logic in self.view_logics.values():
            view_logic.reset()
        self.update_views()
