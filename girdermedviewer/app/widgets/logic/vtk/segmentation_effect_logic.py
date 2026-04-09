import logging

from trame_dataclass.v2 import StateDataModel, Sync
from trame_server import Server
from undo_stack import Signal

from ...ui import SegmentationEffectState
from ...utils import SegmentationEffectType
from ..base_logic import BaseLogic

logger = logging.getLogger(__name__)


class PaintEraseEffectProperties(StateDataModel):
    brush_size = Sync(float, 15)
    use_sphere_brush = Sync(bool, True)


class SegmentationEffectLogic(BaseLogic[SegmentationEffectState]):
    roi_updated = Signal()

    def __init__(self, server: Server) -> None:
        super().__init__(server, SegmentationEffectState)
        self.paint_erase_effect_prop = PaintEraseEffectProperties(self.server)

        self.bind_changes({self.name.active_effect: self._update_active_effect})
        self.paint_erase_effect_prop.watch(("brush_size",), self._update_brush_size)
        self.paint_erase_effect_prop.watch(("use_sphere_brush",), self._update_use_sphere_brush)

    def _update_active_effect(self, active_effect: SegmentationEffectType):
        if active_effect == SegmentationEffectType.PAINT:  # noqa: SIM114
            self.data.active_effect_prop_id = self.paint_erase_effect_prop._id
            # Access brush size or sphere brush with self.paint_erase_effect_prop.[brush_size | use_sphere_brush]
            # TODO: trigger paintbrush mode

        elif active_effect == SegmentationEffectType.ERASE:
            self.data.active_effect_prop_id = self.paint_erase_effect_prop._id
            # TODO: trigger erase mode

        else:
            self.data.active_effect_prop_id = None

    def _update_brush_size(self, _brush_size: float) -> None:
        # TODO: may have nothing to do here
        pass

    def _update_use_sphere_brush(self, _use_sphere_brush: bool) -> None:
        # TODO: may have nothing to do here
        pass
