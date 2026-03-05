from typing import Any

from trame.widgets.client import Style
from trame.widgets.html import Div, Span
from trame.widgets.vuetify3 import (
    VAvatar,
    VBtn,
    VColorPicker,
    VIcon,
    VNumberInput,
    VProgressCircular,
    VTextField,
    VTooltip,
)


class Text(Div):
    def __init__(
        self, text: str, icon: str | None = None, icon_size: int | None = None, uppercase: bool = False, **kwargs
    ) -> None:
        kwargs["classes"] = " ".join([kwargs.get("classes", ""), "text-uppercase" if uppercase else ""])
        super().__init__(**kwargs)

        with self:
            if icon is not None:
                VIcon(classes="mr-1", icon=icon, size=icon_size)
            Span(text)


class Button(VBtn):
    def __init__(
        self,
        avatar_text: str | None = None,
        text_transform: str | tuple[Any] | None = None,
        tooltip: str | tuple[Any] | None = None,
        tooltip_location: str = "right",
        **kwargs,
    ) -> None:
        icon = kwargs.pop("icon", None)
        text = kwargs.pop("text", None)
        color = kwargs.pop("color", None)

        if avatar_text is not None:
            kwargs["icon"] = True
            kwargs["size"] = kwargs.get("size", "large")
            kwargs["variant"] = kwargs.get("variant", "tonal")
        elif icon:
            kwargs["icon"] = True
            kwargs["variant"] = kwargs.get("variant", "text")
        else:
            kwargs["rounded"] = True
            kwargs["color"] = color
            kwargs["variant"] = kwargs.get("variant", "tonal" if color == "primary" else "outlined")

        text_transform = "uppercase" if kwargs.get("block", False) else text_transform or "none"
        kwargs["style"] = " ".join([kwargs.get("style", ""), f"text-transform: {text_transform};"])
        kwargs["__events"] = [*kwargs.get("__events", []), ("click_stop", "click.stop")]

        super().__init__(**kwargs)

        with self:
            if text and not isinstance(text, bool):
                Text(text=text)
            if icon and not isinstance(icon, bool):
                VIcon(icon=icon, color=color)
            if avatar_text:
                with VAvatar(color=color):
                    Text(avatar_text)
            if tooltip:
                VTooltip(
                    activator="parent",
                    close_delay=100,
                    location=tooltip_location,
                    open_delay=500,
                    text=tooltip,
                )


class LoadingButton(Button):
    def __init__(self, **kwargs):
        kwargs["icon"] = kwargs.get("icon", True)
        kwargs["variant"] = kwargs.get("variant", "text")
        super().__init__(**kwargs)
        with self:
            VProgressCircular(
                indeterminate=True,
                size=20,
                width=3,
            )
class ColorPicker(VColorPicker):
    def __init__(self, **kwargs):
        super().__init__(
            elevation=kwargs.pop("elevation", 0),
            mode=kwargs.pop("mode", "rgb"),
            style=kwargs.pop("style", "width: 100%;"),
            **kwargs,
        )


class TextField(VTextField):
    def __init__(self, **kwargs):
        super().__init__(
            variant="solo",
            hide_details=True,
            flat=True,
            bg_color="transparent",
            **kwargs,
        )


class LayerIcon(VIcon):
    def __init__(self, inactive: bool = False, gap: bool = False, **kwargs):
        kwargs["icon"] = kwargs.pop("icon", "mdi-square")
        kwargs["classes"] = kwargs.pop("classes", "layer-icon")
        if inactive:
            kwargs["classes"] += " layer-icon--inactive"
        if gap:
            kwargs["classes"] += " layer-icon--gap"
        super().__init__(**kwargs)


class LayerButton(Button):
    def __init__(self, main_layer: str | tuple[str], **kwargs):
        super().__init__(icon=True, variant="text", **kwargs)
        with self, Div(classes="layer-btn"):
            with Div(classes="layer-bottom"):
                LayerIcon(v_if=main_layer)
                LayerIcon(v_else=True, inactive=True)
            with Div(classes="layer-top"):
                LayerIcon(gap=True)
            with Div(classes="layer-top"):
                LayerIcon(v_if=main_layer, inactive=True)
                LayerIcon(v_else=True)


class NumberInput(VNumberInput):
    def __init__(self, **kwargs):
        super().__init__(
            control_variant=kwargs.pop("control_variant", "stacked"),
            density=kwargs.pop("density", "compact"),
            flat=kwargs.pop("flat", True),
            hide_details=kwargs.pop("hide_details", True),
            inset=kwargs.pop("inset", True),
            **kwargs,
        )


class GlobalStyle(Style):
    def __init__(self):
        super().__init__(
            ".display-property { gap: 12px; display: flex; flex-direction: column; } "
            ".display-property-divider { margin-top: 12px; margin-bottom: 12px; } "
            ".display-property-setting { gap: 12px; display: flex; flex-direction: row; align-items: center; } "
            ".drawer .v-navigation-drawer__content { display: flex; flex-direction: column; padding: 12px; justify-content: space-between;} "
            ".fullscreen-view { width: 100% !important; height: 100% !important; }"
            ".girder-browser { width: 100%; } "
            ".item-card .v-expansion-panel--active>.v-expansion-panel-title,.v-expansion-panel-title { height: 64px !important }"
            ".item-card .v-expansion-panel-text__wrapper { padding: 0 !important; }"
            ".item-card-title { gap: 16px; } "
            ".layer-btn { position: relative; height: 24px; width: 24px; transform: rotateX(45deg); } "
            ".layer-bottom { position: absolute; top: 4px; left: -1px; } "
            ".layer-top { position: absolute; top: -4px; left: -1px; } "
            ".layer-icon { transform: rotate(45deg); } "
            ".layer-icon--inactive { opacity: 0.4 !important; } "
            ".layer-icon--gap { color: rgb(var(--v-theme-surface)); } "
            ".metadata-content { display: flex; flex-direction: row; justify-content: space-between; align-items: center; gap:8px; }"
            ".metadata-ellipsis { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }"
            ".metadata-item { width: 50%; }"
            ".metadata-list { display: flex; flex-wrap: wrap; }"
            ".point-selector { display: flex; justify-content: space-between; align-items: center; gap: 8px; }"
            ".position-selector .v-input__details { display: none !important; } "
            ".position-selector .v-text-field__prefix { font-weight: 700 !important; } "
            ".quad-view { display: flex; gap: 2px; width: 100%; height: 100%; flex-direction: row; flex-wrap: wrap; }"
            ".scene-drawer { overflow: auto; } "
            ".segment-item .v-list-item__prepend { display: grid; }"
            ".text-header { font-size: 1.125rem; font-weight: 300; line-height: 1.75; letter-spacing: 0.0125em; }"
            ".text-subtitle { font-size: 1rem; font-weight: 500; line-height: 1.75; letter-spacing:  0.009375em; }"
            ".tool-card { padding: 0px; }"
            ".tools-strip { display: flex; flex-direction: column; align-items: center; width: 50px; }"
            ".v-btn-group .v-btn:first-child { border-end-start-radius: 24px; border-start-start-radius: 24px; } "
            ".v-btn-group .v-btn:last-child { border-start-end-radius: 24px; border-end-end-radius: 24px; } "
            ".v-window { overflow: unset; } "
            ".view { min-width: calc(50% - 1px); width: unset !important; height: unset !important; }"
            ".view-gutter { position: absolute;  top: 0; left: 0; background-color: transparent; height: 100%; }"
            ".view-gutter-content { display: flex; flex-direction: column; height: 100%; padding: 8px; }"
        )
