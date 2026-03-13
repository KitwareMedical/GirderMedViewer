from trame.widgets import html
from trame.widgets import vuetify3 as v3


class Selector(v3.VSelect):
    def __init__(self, **kwargs):
        super().__init__(flat=True, hide_details=True, variant="solo-filled", density="comfortable", **kwargs)


class PresetSelector(Selector):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self:
            with (
                v3.Template(v_slot_item="{ props }"),
                v3.VListItem(v_bind="props"),
                v3.Template(v_slot_prepend=""),
            ):
                v3.VImg(v_if=("props.data",), src=("props.data",), height=64, width=64, classes="mr-2")

            with v3.Template(v_slot_selection="{item}"):
                v3.VImg(v_if=("item.props.data",), src=("item.props.data",), height=32, width=32, classes="mr-2")
                html.Span("{{ item.title }}")


class PropertyRangeSlider(v3.VRangeSlider):
    def __init__(self, range_min_max: str, **kwargs):
        super().__init__(
            min=(f"{range_min_max}[0]",),
            max=(f"{range_min_max}[1]",),
            step=kwargs.pop("step", 1e-3),
            hide_details=True,
            thumb_size=16,
            track_size=2,
            **kwargs,
        )


class PropertySlider(v3.VSlider):
    def __init__(self, **kwargs):
        super().__init__(
            step=kwargs.pop("step", 1e-3),
            hide_details=True,
            thumb_size=16,
            track_size=2,
            **kwargs,
        )
