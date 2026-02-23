from typing import Any

from trame.widgets.client import Style
from trame.widgets.html import Div, Span
from trame.widgets.vuetify3 import VAvatar, VBtn, VIcon, VTooltip


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
        # loading: bool = False,
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
            kwargs["size"] = kwargs.get("size", "small")
            kwargs["variant"] = kwargs.get("variant", "text")
        else:
            kwargs["rounded"] = True
            kwargs["color"] = color
            kwargs["variant"] = kwargs.get("variant", "tonal" if color == "primary" else "outlined")

        text_transform = "uppercase" if kwargs.get("block", False) else text_transform or "none"
        kwargs["style"] = " ".join([kwargs.get("style", ""), f"text-transform: {text_transform};"])

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


class GlobalStyle(Style):
    def __init__(self):
        super().__init__(
            ".connection-form { display: flex } "
            ".position-selector .v-text-field__prefix {font-weight: 700 !important} "
            ".position-selector .v-input__details {display: none !important} "
            ".position-selector .v-input__control { width: 120px; } "
            ".item-card .v-expansion-panel-text__wrapper { padding: 0 !important }"
            ".item-card .v-expansion-panel--active>.v-expansion-panel-title,.v-expansion-panel-title { "
            "height: 64px !important }"
            ".girder-browser { width: 100% }; "
            "flex-direction: column; }"
            ".file-manager { overflow: auto; max-height: 50%}"
            ".metadata-list { display: flex; flex-wrap: wrap; }"
            ".metadata-item { width: 50%; }"
            ".metadata-content { display: flex; flex-direction: row; justify-content: space-between; "
            "align-items: center; gap:8px; }"
            ".metadata-ellipsis { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }"
            ".quad-view { display: 'grid'; 'grid-template-columns': fullscreen == null ? '1fr 1fr' : 'none'; "
            "gap: '2px'; width: '100%'; height: '100%'; position: 'relative'; }"
            ".tools-strip {display: flex; flex-direction: column; align-items: center; width: 50px;"
            ".view-gutter {position: absolute;  top: 0; left: 0; background-color: transparent; height: 100%;"
            ".view-gutter-content { display: flex; flex-direction: column; height: 100%; padding: 8px; }"
        )
