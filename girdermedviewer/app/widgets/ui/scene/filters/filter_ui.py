from trame.widgets import html
from undo_stack import Signal

from ....utils import Button, FilterType, SceneObjectType
from .gaussian_filter_ui import GaussianFilterUI
from .segmentation_filter_ui import SegmentationFilterUI


class FilterToolbarUI(html.Div):
    filter_clicked = Signal(str, FilterType)

    def __init__(self, obj_id: str, obj_type: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._obj_id = obj_id
        self._obj_type = obj_type

        self._build_ui()

    def _build_ui(self):
        with self:
            self._build_filter_button(FilterType.GAUSSIAN_BLUR, SceneObjectType.VOLUME, icon="mdi-blur")
            self._build_filter_button(FilterType.SEGMENTATION, SceneObjectType.VOLUME, icon="mdi-shape")

    def _build_filter_button(self, filter_type: FilterType, scene_object_type: SceneObjectType, **kwargs):
        def _filter_clicked(obj_id):
            self.filter_clicked(obj_id, filter_type)

        Button(
            v_if=(self._is_obj_type(scene_object_type)),
            tooltip=filter_type.value,
            click=(_filter_clicked, f"[{self._obj_id}]"),
            **kwargs,
        )

    def _is_obj_type(self, scene_object_type: SceneObjectType) -> str:
        return f"{self._obj_type} == '{scene_object_type.value}'"


class FilterUI(html.Div):
    def __init__(self, obj_id: str, obj_filter_type: str, obj_filter_prop: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._obj_id = obj_id
        self._filter_type = obj_filter_type
        self._filter_prop = obj_filter_prop
        self._build_ui()

    def _build_ui(self) -> None:
        with self:
            self.gaussian_filter = GaussianFilterUI(
                v_if=(self._is_filter_active(FilterType.GAUSSIAN_BLUR),),
                obj_filter_prop=self._filter_prop,
            )

            self.segmentation_filter = SegmentationFilterUI(
                v_if=(self._is_filter_active(FilterType.SEGMENTATION),),
                obj_id=self._obj_id,
                obj_filter_prop=self._filter_prop,
            )

    def _is_filter_active(self, filter_type: FilterType) -> str:
        return f"{self._filter_type} == '{filter_type.value}'"
