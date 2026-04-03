from dataclasses import dataclass, field
from enum import Enum


class ViewType(Enum):
    SAGITTAL = "sag"
    THREED = "threed"
    CORONAL = "cor"
    AXIAL = "ax"


@dataclass
class SliderState:
    value: int | None = None
    min_value: int | None = None
    max_value: int | None = None


@dataclass
class ViewsState:
    position: tuple[float] | None = None
    normals: tuple[tuple[float]] | None = None
    is_viewer_disabled: bool = True
    are_sliders_visible: bool = False
    are_obliques_visible: bool = False
    is_position_menu_visible: bool = False
    fullscreen: ViewType | None = None


@dataclass
class ViewState:
    slider_state: SliderState = field(default_factory=SliderState)
