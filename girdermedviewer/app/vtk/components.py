import logging
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from trame.widgets import html, vtk, client
from trame.widgets.vuetify2 import (VContainer, Template, VSlider, VMenu, VCard, VRow, VCol,
                                    VCardText, VTextField)
from ..utils import debounce, Button
from .utils import (
    create_rendering_pipeline,
    get_number_of_slices,
    get_position_from_slice_index,
    get_presets,
    get_reslice_center,
    get_reslice_normals,
    get_reslice_window_level,
    get_slice_index_from_position,
    remove_prop,
    render_mesh_in_3D,
    render_mesh_in_slice,
    render_volume_as_overlay_in_slice,
    render_volume_in_3D,
    render_volume_in_slice,
    reset_reslice,
    reset_3D,
    set_mesh_opacity,
    set_mesh_color,
    set_oblique_visibility,
    set_slice_opacity,
    set_slice_window_level,
    set_reslice_center,
    set_reslice_normal,
    set_reslice_opacity,
    set_reslice_window_level,
    PresetParser
)

logger = logging.getLogger(__name__)


class PositionDialog(VMenu):
    def __init__(self, **kwargs):
        super().__init__(
            v_model=("position_dialog", False),
            close_on_content_click=False,
            close_on_click=False,
            max_width=300,
            offset_x=True,
            left=("main_drawer",),
            offset_overflow=True,
            transition="slide-x-transition",
            **kwargs,
        )
        self.state.position = None
        self.state.normals = None
        client.Style(".v-text-field__prefix {font-weight: 700 !important} "
                     ".v-text-field__details {display: none !important} "
                     ".v-text-field {padding-top: 0px; margin-top: 0px; !important} "
                     ".v-btn:before {opacity: 0 !important} ")
        self._build_ui()

    def _build_ui(self):
        with self:
            with Template(v_slot_activator="{ on: menu }"):
                Button(
                    tooltip="{{ position_dialog ? 'Hide position dialog' : 'Show position dialog' }}",
                    icon_value="mdi-target",
                    icon_color=("position_dialog ? 'primary' : 'black'",),
                    disabled=("Object.keys(selected).length === 0",),
                    v_on="menu",
                )
            with VCard(v_if=("position && Object.keys(selected).length > 0",)), VCardText():
                with VRow(align="center", justify="space-between"):
                    with VCol(
                        v_for=("(field, index) in \
                                [{ prefix: 'X', color: 'red' }, \
                                { prefix: 'Y', color: 'green' }, \
                                { prefix: 'Z', color: 'blue' }]",)
                    ):
                        VTextField(
                            value=("parseFloat(position[index]).toFixed(2)",),
                            input=(self.set_position, "[$event, index]"),
                            prefix=("field.prefix",),
                            color=("field.color",),
                            type="number",
                        )

    def set_position(self, value, index):
        if value:
            old_position = list(self.state.position)
            old_position[int(index)] = float(value)
            self.state.position = tuple(old_position)


class ToolsStrip(html.Div):
    def __init__(self, **kwargs):
        super().__init__(
            classes="bg-grey-darken-4 d-flex flex-column align-center",
            **kwargs,
        )
        self.state.obliques_visibility = True
        client.Style(".v-input--selection-controls__input {margin-right: 0px!important}")

        with self:
            Button(
                tooltip="{{ obliques_visibility ? 'Hide obliques' : 'Show obliques' }}",
                icon_value="{{ obliques_visibility ? 'mdi-eye-remove-outline' : 'mdi-eye-outline' }}",
                click="obliques_visibility = !obliques_visibility",
                disabled=("Object.keys(selected).length === 0",),
            )

            Button(
                tooltip="Reset views",
                icon_value="mdi-camera-flip-outline",
                click=self.ctrl.reset,
                disabled=("Object.keys(selected).length === 0",)
            )

            PositionDialog()


@dataclass
class SliderStateId:
    value_id: str
    min_id: str
    max_id: str
    step_id: str


class ViewGutter(html.Div):
    DEBOUNCED_SLIDER_UPDATE = True

    def __init__(self, view, **kwargs):
        super().__init__(
            classes="gutter",
            style=(
                "position: absolute;"
                "top: 0;"
                "left: 0;"
                "background-color: transparent;"
                "height: 100%;"
            ),
            v_if=("Object.keys(selected).length > 0",),
            **kwargs
        )
        assert view.id is not None
        self.view = view
        with self:
            with html.Div(
                v_if=("Object.keys(selected).length > 0",),
                classes="gutter-content d-flex flex-column fill-height pa-2"
            ):
                Button(
                    tooltip="{{ fullscreen==null ? 'Extend to fullscreen' : 'Exit fullscreen' }}",
                    icon_value="{{ fullscreen==null ? 'mdi-fullscreen' : 'mdi-fullscreen-exit' }}",
                    icon_color="white",
                    click=self.toggle_fullscreen,
                )
                if isinstance(view, SliceView):
                    slider_id = SliderStateId(
                        value_id=f"slider_value_{view.id}",
                        min_id=f"slider_min_{view.id}",
                        max_id=f"slider_max_{view.id}",
                        step_id=f"slider_step_{view.id}",
                    )

                    def _on_slice_view_modified(**kwargs):
                        with self.state as state:
                            range = view.get_slice_range()
                            state.update({
                                slider_id.min_id: range[0],
                                slider_id.max_id: range[1],
                                slider_id.step_id: 1,  # _view.get_slice_step()
                                slider_id.value_id: view.get_slice()
                            })

                    self.state.change("position", "normals")(
                        debounce(0.3, not ViewGutter.DEBOUNCED_SLIDER_UPDATE)(
                            _on_slice_view_modified))

                    VSlider(
                        classes="slice-slider",
                        hide_details=True,
                        vertical=True,
                        theme="dark",
                        dense=True,
                        height="100%",
                        v_model=(slider_id.value_id, view.get_slice()),
                        min=(slider_id.min_id, view.get_slice_range()[0]),
                        max=(slider_id.max_id, view.get_slice_range()[1]),
                        step=(slider_id.step_id, 1),
                        input=(view.set_slice, f"[{slider_id.value_id}]"),
                        # to lower the framerate when animating the slider
                        start=self.ctrl.start_animation,
                        end=self.ctrl.stop_animation,
                        # needed to prevent None triggers
                        v_if=(f'{slider_id.value_id} != null',)
                    )

    def toggle_fullscreen(self):
        self.state.fullscreen = None if self.state.fullscreen else self.view.id


class VtkView(vtk.VtkRemoteView):
    """ Base class for VTK views """
    def __init__(self, ref, **kwargs):
        """ref is also used as id if no id is given. It can be used for CSS styling."""
        renderer, render_window, interactor = create_rendering_pipeline()
        super().__init__(render_window,
                         interactive_quality=80,
                         interactive_ratio=1,
                         id=kwargs.pop("id", None) or ref,
                         ref=ref,  # avoids recreating a view when UI is rebuilt
                         **kwargs)
        self.renderer = renderer
        self.render_window = render_window
        self.interactor = interactor
        self.data = defaultdict(list)
        self.ctrl.view_update.add(self.update)

    def get_data_id(self, data):
        return next((key for key, value in self.data.items() if data in value), None)

    def get_data(self, data_id):
        data = self.data.get(data_id, [])
        return data[0] if len(data) else None

    def get_actors(self, data_id):
        data = [self.data[data_id]] if data_id in self.data else self.data.values()
        return [obj for objs in data for obj in objs if obj.IsA('vtkActor')]

    def register_data(self, data_id, data):
        # Associate data (typically an actor) to data_id so that it can be
        # removed when data_id is unregistered.
        self.data[data_id].append(data)

    def unregister_data(self, data_id, no_render=False, only_data=None):
        """
        :param only_data removes only the provided data if any, all associated if None
        """
        for data in list(self.data[data_id]):
            if only_data is None or data == only_data:
                remove_prop(self.renderer, data)
                self.data[data_id].remove(data)
        if len(self.data[data_id]) == 0:
            self.data.pop(data_id)
        if not no_render:
            self.update()

    def remove_volume(self, data_id, no_render=False, only_data=None):
        return self.unregister_data(data_id, no_render, only_data)

    def remove_mesh(self, data_id, no_render=False, only_data=None):
        return self.unregister_data(data_id, no_render, only_data)

    def set_mesh_opacity(self, data_id, opacity):
        modified = False
        for actor in self.get_actors(data_id):
            modified = set_mesh_opacity(actor, opacity) or modified
        if modified is not False:
            self.update()

    def set_mesh_color(self, data_id, color):
        modified = False
        for actor in self.get_actors(data_id):
            modified = set_mesh_color(actor, color) or modified
        if modified is not False:
            self.update()


class Orientation(Enum):
    SAGITTAL = 0
    CORONAL = 1
    AXIAL = 2


class SliceView(VtkView):
    """ Display volume as a 2D slice along a given axis/orientation """
    _debounced_flush_initialized = False
    DEBOUNCED_FLUSH = False

    def __init__(self, orientation, ref, **kwargs):
        super().__init__(ref=ref, classes=f"slice {orientation.name.lower()}", **kwargs)
        self.orientation = orientation
        if SliceView.DEBOUNCED_FLUSH and SliceView._debounced_flush_initialized is False:  # can't use hasattr here
            SliceView._debounced_flush_initialized = True
            self.server.controller.debounced_flush = debounce(0.3)(self.state.flush)

        self._build_ui()

        self.state.change("position", "normals")(self.on_cursor_changed)
        self.state.change("obliques_visibility")(self.on_obliques_visibility_changed)

        # in addition to self.ctrl.view_update for any view:
        self.ctrl.slice_view_update.add(self.update)
        # If a view is in animation, the other views must also be in animation to
        # be rendered
        self.ctrl.start_animation.add(self.start_animation)
        self.ctrl.stop_animation.add(self.stop_animation)

    def unregister_data(self, data_id, no_render=False, only_data=None):
        super().unregister_data(data_id, no_render=True, only_data=None)
        # we can't have secondary volumes without at least a primary volume
        if not self.has_primary_volume() and self.has_secondary_volume():
            image_slice = self.get_image_slices()[0]
            secondary_data_id = self.get_data_id(image_slice)
            # Replace the secondary volume into a primary volume
            self.add_primary_volume(image_slice.GetMapper().GetDataSetInput(), secondary_data_id)
            super().unregister_data(secondary_data_id, True, only_data=image_slice)

        if not self.has_primary_volume() and self.has_mesh():
            for mesh_slice in self.get_mesh_slices():
                mesh_data_id = self.get_data_id(mesh_slice)
                super().unregister_data(mesh_data_id, True, only_data=mesh_slice)

        if not no_render:
            self.update()

    def flush(self):
        if SliceView.DEBOUNCED_FLUSH:
            self.ctrl.debounced_flush()
        else:
            self.state.flush()

    def get_reslice_image_viewer(self, data_id=None):
        """
        Return the primary volume image viewer if any.
        :param data_id if provided returns only if it matches data_id.
        """
        ids = [data_id] if data_id in self.data else self.data.keys()
        data = [self.get_data(id) for id in ids if self.is_primary_volume(id)]
        return data[0] if len(data) else None

    def get_image_slices(self, data_id=None):
        ids = [data_id] if data_id in self.data else self.data.keys()
        data = [self.get_data(id) for id in ids if self.is_secondary_volume(id)]
        return data

    def get_mesh_slices(self, data_id=None):
        data = [self.data[data_id]] if data_id in self.data else self.data.values()
        return [obj for objs in data for obj in objs if obj.IsA('vtkActor')]

    def add_primary_volume(self, image_data, data_id=None):
        reslice_image_viewer = render_volume_in_slice(
            image_data,
            self.renderer,
            self.orientation.value,
            obliques=self.state.obliques_visibility
        )
        self.register_data(data_id, reslice_image_viewer)

        reslice_cursor_widget = reslice_image_viewer.GetResliceCursorWidget()
        reslice_image_viewer.AddObserver(
            'InteractionEvent', self.on_slice_scroll)
        reslice_cursor_widget.AddObserver(
            'InteractionEvent', self.on_reslice_cursor_interaction)
        reslice_cursor_widget.AddObserver(
            'EndInteractionEvent', self.on_reslice_cursor_end_interaction)
        reslice_image_viewer.GetInteractorStyle().AddObserver(
            'WindowLevelEvent', self.on_window_leveling)

        self.update()

    def add_secondary_volume(self, image_data, data_id=None):
        actor = render_volume_as_overlay_in_slice(
            image_data,
            self.renderer,
            self.orientation.value
        )
        self.register_data(data_id, actor)
        self.update()

    def add_volume(self, image_data, data_id=None):
        if not self.has_primary_volume():
            self.add_primary_volume(image_data, data_id)
            self.on_reslice_cursor_interaction(
                self.get_reslice_image_viewer(), None)
        else:
            self.add_secondary_volume(image_data, data_id)

    def add_mesh(self, poly_data, data_id=None):
        actor = render_mesh_in_slice(
            poly_data,
            self.orientation.value,
            self.renderer
        )
        self.register_data(data_id, actor)
        self.update()

    def is_primary_volume(self, data_id):
        """
        :see-also has_primary_volume, is_secondary_volume, get_reslice_image_viewer
        """
        data = self.get_data(data_id)
        if not data:
            return False
        if data.IsA('vtkResliceImageViewer'):
            return True
        if data.IsA('vtkImageSlice'):
            return False
        return None

    def is_secondary_volume(self, data_id):
        """
        :see-also is_primary_volume, get_image_slices
        """
        data = self.get_data(data_id)
        if not data:
            return False
        if data.IsA('vtkImageSlice'):
            return True
        if data.IsA('vtkResliceImageViewer'):
            return False
        return None

    def has_primary_volume(self):
        return self.get_reslice_image_viewer() is not None

    def has_secondary_volume(self):
        return len(self.get_image_slices()) > 0

    def has_mesh(self):
        return len(self.get_mesh_slices()) > 0

    def reset(self):
        reslice_image_viewer = self.get_reslice_image_viewer()
        if reslice_image_viewer is not None:
            reset_reslice(reslice_image_viewer)
            self.update()

    def on_obliques_visibility_changed(self, obliques_visibility, **kwargs):
        reslice_image_viewer = self.get_reslice_image_viewer()
        if reslice_image_viewer is not None:
            set_oblique_visibility(reslice_image_viewer, obliques_visibility)
            self.update()

    def set_volume_opacity(self, data_id, opacity):
        logger.debug(f"set_volume_opacity({data_id}): {opacity}")
        modified = False
        reslice_image_viewer = self.get_reslice_image_viewer(data_id)
        if reslice_image_viewer is not None:
            modified = set_reslice_opacity(reslice_image_viewer, opacity)
        for slice in self.get_image_slices(data_id):
            modified = set_slice_opacity(slice, opacity) or modified
        if modified:
            self.update()

    def set_volume_window_level(self, data_id, window_level):
        logger.debug(f"set_volume_window_level({data_id}): {window_level}")
        modified = False
        reslice_image_viewer = self.get_reslice_image_viewer(data_id)
        if reslice_image_viewer is not None:
            modified = set_reslice_window_level(reslice_image_viewer, window_level)
        for slice in self.get_image_slices(data_id):
            modified = set_slice_window_level(slice, window_level) or modified
        if modified:
            self.update()

    def set_volume_window_level_min_max(self, data_id, window_level_min_max):
        """
        :see-also set_volume_window_level
        """
        if window_level_min_max is not None:
            window = window_level_min_max[1] - window_level_min_max[0]
            level = (window_level_min_max[0] + window_level_min_max[1]) / 2
            self.set_volume_window_level(data_id, (window, level))

    def on_window_leveling(self, interactor_style, event):
        self.ctrl.window_level_changed_in_view(
            get_reslice_window_level(self.get_reslice_image_viewer()))

    def on_slice_scroll(self, reslice_image_viewer, event):
        """
        Triggered when scrolling the current image.
        There are 2 possible user interactions to modify the cursor:
         - scroll
         - cursor interaction

        :see-also on_reslice_cursor_interaction
        """
        new_position = get_reslice_center(reslice_image_viewer)
        if self.state.position != new_position:
            self.state.position = new_position
        # Because it is called within a co-routine, position is not
        # flushed right away.
        self.flush()

    def on_reslice_cursor_interaction(self, reslice_image_widget, event):
        """
        Triggered when interacting with oblique lines.
        Because it is called within a co-routine, position is not flushed right away.

        There are 2 possible user interactions to modify the cursor:
         - scroll
         - cursor interaction
        :see-also on_slice_scroll
        """
        self.state.update({
            'position': get_reslice_center(reslice_image_widget),
            'normals': get_reslice_normals(reslice_image_widget),
        })
        # Flushing will trigger rendering
        self.flush()

    def on_reslice_cursor_end_interaction(self, reslice_image_widget, event):
        self.state.flush()  # flush state.position

    def on_cursor_changed(self, position, normals, **kwargs):
        if position is not None and normals is not None:
            set_reslice_center(self.get_reslice_image_viewer(), position)
            set_reslice_normal(self.get_reslice_image_viewer(), normals[self.orientation.value], self.orientation.value)
            self.update()

    def get_slice_range(self):
        reslice_image_viewer = self.get_reslice_image_viewer()
        return [0, get_number_of_slices(reslice_image_viewer, self.orientation.value)]

    def get_slice(self):
        reslice_image_viewer = self.get_reslice_image_viewer()
        return get_slice_index_from_position(self.state.position, reslice_image_viewer, self.orientation.value)

    def set_slice(self, slice):
        reslice_image_viewer = self.get_reslice_image_viewer()
        position = get_position_from_slice_index(slice, reslice_image_viewer, self.orientation.value)
        if position is not None and self.state.position != position:
            self.state.position = position
            self.flush()

    def on_window_level_changed(self, window_level, **kwargs):
        logger.debug(f"set_window_level: {window_level}")
        modified = set_reslice_window_level(self.get_reslice_image_viewer(), window_level)
        if modified:
            self.update()

    def _build_ui(self):
        with self:
            ViewGutter(self)


class ThreeDView(VtkView):
    def __init__(self, ref, **kwargs):
        super().__init__(ref, classes="threed", **kwargs)
        self._build_ui()

    def get_volumes(self):
        return [obj for objs in self.data.values() for obj in objs if obj.IsA('vtkVolume')]

    def add_volume(self, image_data, data_id=None):
        volume = render_volume_in_3D(
            image_data,
            self.renderer
        )
        self.register_data(data_id, volume)
        self.update()

    def add_mesh(self, poly_data, data_id=None):
        actor = render_mesh_in_3D(
            poly_data,
            self.renderer
        )
        self.register_data(data_id, actor)
        self.update()

    def reset(self):
        reset_3D(self.renderer)
        self.update()

    def set_volume_preset(self, data_id, preset_name, range):
        logger.debug(f"set_volume_preset({data_id}): {preset_name}, {range}")
        preset = PresetParser(self.state.presets).get_preset_by_name(preset_name)
        volume = self.get_data(data_id)
        if volume is None:
            return
        modified = PresetParser.apply_slicer_preset(preset, volume.GetProperty(), range)
        if modified:
            self.update()

    def _build_ui(self):
        with self:
            ViewGutter(self)


class QuadView(VContainer):
    def __init__(self, **kwargs):
        super().__init__(
            classes="fill-height pa-0",
            fluid=True,
            **kwargs
        )
        self.views = []
        self.state.fullscreen = None
        self.state.presets = get_presets()
        self._build_ui()
        self.ctrl.reset = self.reset
        self.ctrl.remove_data = self.remove_data

    @property
    def twod_views(self):
        return [view for view in self.views if isinstance(view, SliceView)]

    @property
    def threed_views(self):
        return [view for view in self.views if isinstance(view, ThreeDView)]

    def remove_data(self, data_id=None):
        for view in self.views:
            view.unregister_data(data_id)
        self.ctrl.view_update()

    def reset(self):
        for view in self.views:
            view.reset()
        self.ctrl.view_update()

    def _build_ui(self):
        with self:
            with html.Div(
                style=("""{
                       display: 'grid',
                       'grid-template-columns': fullscreen == null ? '1fr 1fr' : 'none',
                       gap: '2px',
                       width: '100%',
                       height: '100%',
                       position: 'relative'
                       }""",),
            ):
                with SliceView(Orientation.SAGITTAL,
                               ref="sag_view",
                               v_if="fullscreen == null || fullscreen == 'sag_view'") as sag_view:
                    self.views.append(sag_view)
                with ThreeDView(ref="threed_view",
                                v_if="fullscreen == null || fullscreen == 'threed_view'") as threed_view:
                    self.views.append(threed_view)
                with SliceView(Orientation.CORONAL, ref="cor_view",
                               v_if="fullscreen == null || fullscreen == 'cor_view'") as cor_view:
                    self.views.append(cor_view)
                with SliceView(Orientation.AXIAL, ref="ax_view",
                               v_if="fullscreen == null || fullscreen == 'ax_view'") as ax_view:
                    self.views.append(ax_view)
