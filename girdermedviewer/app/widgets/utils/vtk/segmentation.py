import math
from enum import IntEnum

import numpy as np
import vtkmodules.util.numpy_support as vtknp
from numpy.typing import NDArray
from vtkmodules.vtkCommonCore import VTK_UNSIGNED_CHAR, vtkCommand, vtkPoints
from vtkmodules.vtkCommonDataModel import vtkImageData, vtkPlane, vtkPolyData
from vtkmodules.vtkCommonExecutionModel import vtkAlgorithmOutput, vtkPolyDataAlgorithm
from vtkmodules.vtkCommonMath import vtkMatrix4x4
from vtkmodules.vtkCommonTransforms import vtkTransform
from vtkmodules.vtkFiltersCore import vtkCutter, vtkGlyph3D, vtkPolyDataNormals
from vtkmodules.vtkFiltersGeneral import vtkTransformPolyDataFilter
from vtkmodules.vtkFiltersModeling import vtkFillHolesFilter
from vtkmodules.vtkFiltersSources import vtkCylinderSource, vtkSphereSource
from vtkmodules.vtkImagingStencil import (
    vtkImageStencilToImage,
    vtkPolyDataToImageStencil,
)
from vtkmodules.vtkInteractionImage import vtkResliceImageViewer
from vtkmodules.vtkInteractionWidgets import vtkResliceCursor, vtkResliceCursorWidget
from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkPolyDataMapper,
    vtkProp,
    vtkProperty,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
)

from girdermedviewer.app.widgets.utils.vtk.vtk_utils import realign_axes


def _vtk_image_to_np(image: vtkImageData) -> np.ndarray:
    """Get a numpy view of a vtkImageData
    Remember to call image.Update() once the changes are done.
    This takes care of reversing the dims (numpy is col-major, vtk is row-major)
    """
    dims = tuple(reversed(image.GetDimensions()))
    return vtknp.vtk_to_numpy(image.GetPointData().GetScalars()).reshape(dims)


def _clamp_extent(extent: list[int], limits: list[int]) -> list[int]:
    """Prevents segfaults"""
    return [
        max(extent[0], limits[0]),
        min(extent[1], limits[1]),
        max(extent[2], limits[2]),
        min(extent[3], limits[3]),
        max(extent[4], limits[4]),
        min(extent[5], limits[5]),
    ]


def _subextent_to_slices(extent: list[int], subextent: list[int]) -> tuple[slice, slice, slice]:
    """Convert a vtkImageData subextent to NumPy slices"""
    return (
        slice(
            subextent[4] - extent[4],
            subextent[4] - extent[4] + (subextent[5] - subextent[4] + 1),
        ),
        slice(
            subextent[2] - extent[2],
            subextent[2] - extent[2] + (subextent[3] - subextent[2] + 1),
        ),
        slice(
            subextent[0] - extent[0],
            subextent[0] - extent[0] + (subextent[1] - subextent[0] + 1),
        ),
    )


class LabelMapOperation(IntEnum):
    Erase = 0
    Set = 1


class LabelMapOverwriteMode(IntEnum):
    # Areas added to selected segment will be removed from all other segments. (no overlap)
    AllSegments = 0
    # Areas added to selected segment will not be removed from any segments. (overlap with all other segments)
    Never = 1


class LabelMapEditor:
    """
    Edits a labelmap
    """

    def __init__(
        self,
    ) -> None:
        self._labelmap = None
        self._active_segment = None
        self._operation = LabelMapOperation.Set
        self._overwrite_mode = LabelMapOverwriteMode.AllSegments

    @property
    def labelmap(self) -> vtkImageData:
        return self._labelmap

    @labelmap.setter
    def labelmap(self, image_data: vtkImageData) -> None:
        self._labelmap = image_data

    @property
    def active_segment(self) -> int:
        return self._active_segment

    @active_segment.setter
    def active_segment(self, id: int) -> None:
        self._active_segment = id

    @property
    def operation(self) -> LabelMapOperation:
        return self._operation

    @operation.setter
    def operation(self, op: LabelMapOperation) -> None:
        self._operation = op

    @property
    def overwrite_mode(self) -> LabelMapOverwriteMode:
        return self._overwrite_mode

    @overwrite_mode.setter
    def overwrite_mode(self, mode: LabelMapOverwriteMode) -> None:
        self._overwrite_mode = mode

    def _get_world_to_ijk_no_origin(self):
        output = vtkMatrix4x4()
        output.DeepCopy(self._get_world_to_ijk())
        output.SetElement(0, 3, 0)
        output.SetElement(1, 3, 0)
        output.SetElement(2, 3, 0)
        return output

    def _get_world_to_ijk(self):
        return self._labelmap.GetPhysicalToIndexMatrix()

    def apply_glyph(self, poly: vtkPolyData, world_locations: vtkPoints) -> None:
        """Apply poly at every world locations
        poly: in world origin coordinates
        world locations: each location where glyph will be applieds at
        """
        # Rotate poly to later be translated in ijk coordinates for each world_locations
        world_to_ijk_transform_matrix = self._get_world_to_ijk_no_origin()
        world_origin_to_modifier_labelmap_ijk_transform = vtkTransform()
        world_origin_to_modifier_labelmap_ijk_transform.Concatenate(world_to_ijk_transform_matrix)
        world_origin_to_modifier_labelmap_ijk_transformer = vtkTransformPolyDataFilter()
        world_origin_to_modifier_labelmap_ijk_transformer.SetTransform(world_origin_to_modifier_labelmap_ijk_transform)
        world_origin_to_modifier_labelmap_ijk_transformer.SetInputData(poly)
        world_origin_to_modifier_labelmap_ijk_transformer.Update()

        # Pre-rotated polydata
        brush_model: vtkPolyData = world_origin_to_modifier_labelmap_ijk_transformer.GetOutput()

        modifier_labelmap = self._poly_to_modifier_labelmap(brush_model)
        original_extent = modifier_labelmap.GetExtent()
        np_modifier_labelmap = _vtk_image_to_np(modifier_labelmap) != 0

        points_ijk = self._world_points_to_ijk(world_locations)
        for i in range(points_ijk.GetNumberOfPoints()):
            position = points_ijk.GetPoint(i)
            # translate the modifier labelmap in IJK coords
            extent = [
                original_extent[0] + int(position[0]),
                original_extent[1] + int(position[0]),
                original_extent[2] + int(position[1]),
                original_extent[3] + int(position[1]),
                original_extent[4] + int(position[2]),
                original_extent[5] + int(position[2]),
            ]
            self.apply_binary_labelmap(np_modifier_labelmap, extent)

    def apply_binary_labelmap(self, modifier_labelmap: NDArray[np.bool], base_modifier_extent: list[int]):
        # modifier_labelmap: in source ijk coordinates
        common_extent = list(self._labelmap.GetExtent())
        # clamp modifier extent to common extent so we don't draw outside the segmentation!
        modifier_extent = _clamp_extent(base_modifier_extent, common_extent)

        np_labelmap = _vtk_image_to_np(self._labelmap)
        labelmap_slices = _subextent_to_slices(common_extent, modifier_extent)
        modifier_labelmap_slices = _subextent_to_slices(base_modifier_extent, modifier_extent)

        if any(s.stop - s.start <= 0 for s in labelmap_slices) or any(
            s.stop - s.start <= 0 for s in modifier_labelmap_slices
        ):
            # nothing to do, affected labelmap area is empty or out of labelmap range
            return

        label_value = self._active_segment if self._operation == LabelMapOperation.Set else 0
        active_label_value = self._active_segment

        ## Apply effect
        self._apply_modifier_labelmap_to_labelmap(
            np_labelmap[labelmap_slices],
            modifier_labelmap[modifier_labelmap_slices],
            label_value,
            active_label_value,
            self._overwrite_mode,
        )

        self._labelmap.Modified()

    def clear_segment(self, labelmap: vtkImageData, id: int):
        """Set to 0 all values equal to current segment id"""
        labelmap_array = _vtk_image_to_np(labelmap)
        modifier_labelmap = labelmap_array == id
        self._apply_modifier_labelmap_to_labelmap(
            labelmap_array,
            modifier_labelmap,
            0,
            id,
            LabelMapOverwriteMode.AllSegments,  # AllSegment is faster and fine in this case
        )
        labelmap.Modified()

    def _apply_modifier_labelmap_to_labelmap(
        self,
        labelmap: np.ndarray,
        modifier: NDArray[np.bool],
        label_value: int,
        active_label_value: int,
        rule: LabelMapOverwriteMode,
    ) -> None:
        if rule == LabelMapOverwriteMode.AllSegments:
            labelmap[modifier] = label_value
        elif rule == LabelMapOverwriteMode.Never:
            # When erasing (label_value == 0) we only affect current segment
            # Otherwise, we only affect empty spaces (labelmap == 0)
            empty_label_mask = labelmap == 0 if label_value != 0 else labelmap == active_label_value
            labelmap[modifier & empty_label_mask] = label_value

    def _poly_to_modifier_labelmap(self, poly: vtkPolyData) -> vtkImageData:
        filler = vtkFillHolesFilter()
        filler.SetInputData(poly)
        filler.SetHoleSize(4096.0)
        filler.Update()
        filled_poly = filler.GetOutput()

        bounds = filled_poly.GetBounds()
        extent = [
            math.floor(bounds[0]) - 1,
            math.ceil(bounds[1]) + 1,
            math.floor(bounds[2]) - 1,
            math.ceil(bounds[3]) + 1,
            math.floor(bounds[4]) - 1,
            math.ceil(bounds[5]) + 1,
        ]
        brush_poly_data_to_stencil = vtkPolyDataToImageStencil()
        brush_poly_data_to_stencil.SetInputData(filled_poly)
        brush_poly_data_to_stencil.SetOutputSpacing(1.0, 1.0, 1.0)
        brush_poly_data_to_stencil.SetOutputWholeExtent(extent)

        stencilToImage = vtkImageStencilToImage()
        stencilToImage.SetInputConnection(brush_poly_data_to_stencil.GetOutputPort())
        stencilToImage.SetInsideValue(1.0)
        stencilToImage.SetOutsideValue(0.0)
        stencilToImage.SetOutputScalarType(VTK_UNSIGNED_CHAR)
        stencilToImage.Update()

        return stencilToImage.GetOutput()

    def _world_points_to_ijk(self, points: vtkPoints) -> vtkPoints:
        world_to_ijk_transform_matrix = self._get_world_to_ijk()
        world_to_ijk_transform = vtkTransform()
        world_to_ijk_transform.Identity()
        world_to_ijk_transform.Concatenate(world_to_ijk_transform_matrix)

        ijk_points = vtkPoints()
        world_to_ijk_transform.TransformPoints(points, ijk_points)

        return ijk_points


class BrushShape(IntEnum):
    Sphere = 0
    Cylinder = 1


class BrushModel:
    def __init__(self, shape: BrushShape) -> None:
        self._sphere_source = vtkSphereSource()
        self.set_sphere_parameters(8.0, 32, 32)
        self._cylinder_source = vtkCylinderSource()
        self.set_cylinder_parameters(8.0, 32, 1.1)

        self._brush_to_world_origin_transform = vtkTransform()
        self._brush_to_world_origin_transformer = vtkTransformPolyDataFilter()
        self._brush_to_world_origin_transformer.SetTransform(self._brush_to_world_origin_transform)

        self._brush_poly_data_normals = vtkPolyDataNormals()
        self._brush_poly_data_normals.SetInputConnection(self._brush_to_world_origin_transformer.GetOutputPort())
        self._brush_poly_data_normals.AutoOrientNormalsOn()

        self._world_origin_to_world_transform = vtkTransform()
        self._world_origin_to_world_transformer = vtkTransformPolyDataFilter()
        self._world_origin_to_world_transformer.SetTransform(self._world_origin_to_world_transform)
        self._world_origin_to_world_transformer.SetInputConnection(self._brush_poly_data_normals.GetOutputPort())

        self._shape = None  # force shape update
        self.shape = shape

    @property
    def brush_to_world_origin_transform(self) -> vtkTransform:
        return self._brush_to_world_origin_transform

    @property
    def world_origin_to_world_transform(self) -> vtkTransform:
        return self._world_origin_to_world_transform

    @property
    def shape(self) -> BrushShape:
        return self._shape

    @shape.setter
    def shape(self, shape: BrushShape):
        if self._shape == shape:
            return

        self._shape = shape
        self._brush_to_world_origin_transform.Identity()
        if shape == BrushShape.Sphere:
            self._brush_to_world_origin_transformer.SetInputConnection(self._sphere_source.GetOutputPort())
        elif shape == BrushShape.Cylinder:
            self._brush_to_world_origin_transformer.SetInputConnection(self._cylinder_source.GetOutputPort())
        else:
            raise Exception(f"Invalid shape value {shape}")

    def set_sphere_parameters(self, radius: float, phi_resolution: int, theta_resolution: int):
        self._sphere_source.SetPhiResolution(phi_resolution)
        self._sphere_source.SetThetaResolution(theta_resolution)
        self._sphere_source.SetRadius(radius)

    def set_cylinder_parameters(self, radius: float, resolution: int, height: float):
        self._cylinder_source.SetResolution(resolution)
        self._cylinder_source.SetHeight(height)
        self._cylinder_source.SetRadius(radius)

    def get_output_port(self) -> vtkAlgorithmOutput:
        """Return output port of transformed brush model"""
        return self._world_origin_to_world_transformer.GetOutputPort()

    def get_untransformed_output_port(self) -> vtkAlgorithmOutput:
        """Return output port of untransformed brush model. Useful for feedback actors"""
        return self._brush_poly_data_normals.GetOutputPort()


class Brush2D:
    """Display a vtkPolyData on a Slice
    This takes a vtkPolyData(Algorithm output port) as input and expect it to be pre transformed in world position
    """

    def __init__(self):
        self._slice_plane = vtkPlane()

        self._brush_cutter = vtkCutter()
        self._brush_cutter.SetCutFunction(self._slice_plane)
        self._brush_cutter.SetGenerateCutScalars(0)

        self._world_to_slice_transform = vtkTransform()
        self._brush_world_to_slice_transformer = vtkTransformPolyDataFilter()
        self._brush_world_to_slice_transformer.SetTransform(self._world_to_slice_transform)
        self._brush_world_to_slice_transformer.SetInputConnection(self._brush_cutter.GetOutputPort())

        self._brush_mapper = vtkPolyDataMapper()
        self._brush_mapper.SetInputConnection(self._brush_world_to_slice_transformer.GetOutputPort())
        self._brush_actor = vtkActor()
        self._brush_actor.SetMapper(self._brush_mapper)
        self._brush_actor.VisibilityOff()

    def set_input_connection(self, input: vtkAlgorithmOutput):
        """Specify input polydata to use as brush"""
        self._brush_cutter.SetInputConnection(input)

    def get_prop(self) -> vtkProp:
        """Return brush prop.
        Can be used to add or remove the brush from the renderer, configure rendering properties (visibility, color, ...)
        """
        return self._brush_actor

    def get_property(self) -> vtkProperty:
        return self._brush_actor.GetProperty()

    def get_visibility(self) -> bool:
        return self._brush_actor.GetVisibility() != 0

    def set_visibility(self, visibility: bool) -> None:
        return self._brush_actor.SetVisibility(int(visibility))

    def update_slice_position(self, slice_to_world: vtkMatrix4x4):
        """This must be called every time the current slice changes in the slice node"""
        self._slice_plane.SetNormal(
            slice_to_world.GetElement(0, 2),
            slice_to_world.GetElement(1, 2),
            slice_to_world.GetElement(2, 2),
        )
        self._slice_plane.SetOrigin(
            slice_to_world.GetElement(0, 3),
            slice_to_world.GetElement(1, 3),
            slice_to_world.GetElement(2, 3),
        )


class SegmentPaintEffect2D:
    """Setup a segmentation effect in a vtkResliceImageViewer"""

    def __init__(self, viewer: vtkResliceImageViewer, editor: LabelMapEditor, brush_model: BrushModel, layer = 2):
        self._viewer = viewer
        self._editor = editor
        self._widget: vtkResliceCursorWidget = self._viewer.GetResliceCursorWidget()
        self._cursor: vtkResliceCursor = self._viewer.GetResliceCursor()
        self._brush_model = brush_model

        window: vtkRenderWindow = self._viewer.GetRenderWindow()
        if window.GetNumberOfLayers() < layer + 1:
            window.SetNumberOfLayers(layer + 1)
            main_renderer = window.GetRenderers().GetFirstRenderer()
            self._overlay_renderer = vtkRenderer()
            self._overlay_renderer.SetActiveCamera(main_renderer.GetActiveCamera())
            self._overlay_renderer.SetLayer(layer)
            window.AddRenderer(self._overlay_renderer)
        else:
            self._overlay_renderer: vtkRenderer = window.GetRenderers().GetItemAsObject(layer)

        # logical brush
        self._brush = Brush2D()
        self._brush.set_input_connection(brush_model.get_output_port())
        self._brush.get_property().SetAmbient(1)
        self._brush.get_property().SetAmbientColor(0.0, 1.0, 0.0)

        # Feedback brush
        feedback_points_poly_data = vtkPolyData()
        feedback_glyph_filter = vtkGlyph3D()
        feedback_glyph_filter.SetInputData(feedback_points_poly_data)
        feedback_glyph_filter.SetSourceConnection(brush_model.get_untransformed_output_port())
        self._brush_feedback = Brush2D()
        self._brush_feedback.set_input_connection(feedback_glyph_filter.GetOutputPort())
        self._brush_feedback.get_property().SetAmbient(1)
        self._brush_feedback.get_property().SetAmbientColor(0.0, 0.0, 1.0)

        self._brush_enabled = False
        self._paint_coordinates_world = vtkPoints()
        self._painting = False

        feedback_points_poly_data.SetPoints(self.paint_coordinates_world)

        self._interactor: vtkRenderWindowInteractor = self._viewer.GetInteractor()

        self._all_commands: list[int] = []
        self.disable_brush()  # disabled by default
        self._on_slice_changed(None, None)

    @property
    def viewer(self) -> vtkResliceImageViewer:
        return self._viewer

    @property
    def editor(self) -> LabelMapEditor:
        return self._editor

    @property
    def brush_model(self) -> BrushModel:
        return self._brush_model

    @property
    def paint_coordinates_world(self) -> vtkPoints:
        return self._paint_coordinates_world

    def add_point_to_selection(self, position: tuple[float, float, float]) -> None:
        self._paint_coordinates_world.InsertNextPoint(position)
        self._paint_coordinates_world.Modified()

    def enable_brush(self) -> None:
        self._connect_all()
        self._brush.set_visibility(True)
        self._brush_enabled = True
        self._overlay_renderer.AddViewProp(self._brush.get_prop())
        self._overlay_renderer.AddViewProp(self._brush_feedback.get_prop())
        # We can not dynamically swap between viewer's reslice modes,
        # this does the same but with the oblique pipeline.
        # This won't affect the center of the reslice.
        realign_axes(self._viewer)

    def disable_brush(self) -> None:
        if self.is_painting():
            self.stop_painting()
        self._disconnect_all()
        self._brush.set_visibility(False)
        self._brush_enabled = False
        self._overlay_renderer.RemoveViewProp(self._brush.get_prop())
        self._overlay_renderer.RemoveViewProp(self._brush_feedback.get_prop())

    def is_brush_enabled(self) -> bool:
        return self._brush_enabled

    def start_painting(self) -> None:
        self._brush_feedback.set_visibility(True)
        self._painting = True

    def stop_painting(self) -> None:
        self._brush_feedback.set_visibility(False)
        self._painting = False
        if self._paint_coordinates_world.GetNumberOfPoints() > 0:
            self.commit()

    def is_painting(self) -> bool:
        return self._painting

    def commit(self) -> None:
        try:
            algo: vtkPolyDataAlgorithm = self._brush_model.get_untransformed_output_port().GetProducer()
            algo.Update()
            self._editor.apply_glyph(algo.GetOutput(), self._paint_coordinates_world)
        except:
            raise
        finally:  # ensure points are always cleared
            self._paint_coordinates_world.SetNumberOfPoints(0)  # clear points

    def _get_slice_to_world(self) -> vtkMatrix4x4:
        return self._widget.GetResliceCursorRepresentation().GetResliceAxes()

    def _connect_all(self):
        if len(self._all_commands) > 0:
            return  # already connected

        self._slice_changed_command_id = self._viewer.AddObserver(vtkCommand.InteractionEvent, self._on_slice_changed)
        self._left_pressed_command_id = self._interactor.AddObserver(
            vtkCommand.LeftButtonPressEvent, self._on_left_pressed, 1.0
        )
        self._left_released_command_id = self._interactor.AddObserver(
            vtkCommand.LeftButtonReleaseEvent, self._on_left_released, 1.0
        )
        self._mouse_moved_command_id = self._interactor.AddObserver(vtkCommand.MouseMoveEvent, self._on_mouse_move)
        self._all_commands: list[int] = [
            self._slice_changed_command_id,
            self._left_pressed_command_id,
            self._left_released_command_id,
            self._mouse_moved_command_id,
        ]

    def _disconnect_all(self):
        for id in self._all_commands:
            self._interactor.RemoveObserver(id)
        self._slice_changed_command_id = -1
        self._left_pressed_command_id = -1
        self._left_released_command_id = -1
        self._mouse_moved_command_id = -1
        self._all_commands: list[int] = []

    def _on_slice_changed(self, _caller: vtkResliceImageViewer, _ev: str) -> None:
        self._update_brush()

    def _on_left_pressed(self, caller: vtkRenderWindowInteractor, _ev: str) -> bool:
        if self.is_brush_enabled():
            self.start_painting()
            # swallow event
            caller.GetCommand(self._left_pressed_command_id).AbortFlagOn()

    def _on_left_released(self, _caller: vtkRenderWindowInteractor, _ev: str) -> bool:
        if self.is_painting():
            self.stop_painting()

    def _on_mouse_move(self, _caller: vtkRenderWindowInteractor, _ev: str) -> bool:
        self._update_brush()

    def _update_brush(self):
        if self.is_brush_enabled():
            world_pos = self._viewport_to_world(*self._interactor.GetLastEventPosition())
            self._update_brush_position(world_pos)
            slice_to_world = self._get_slice_to_world()
            self._brush.update_slice_position(slice_to_world)
            self._brush_feedback.update_slice_position(slice_to_world)
            if self.is_painting():
                self.add_point_to_selection(world_pos)

    def _viewport_to_world(self, display_x, display_y) -> tuple[float, float, float]:
        match self._viewer.GetSliceOrientation():
            case vtkResliceImageViewer.SLICE_ORIENTATION_YZ:
                display_z = self._viewer.GetResliceCursor().GetCenter()[0]
                renderer = self._viewer.GetRenderer()
                renderer.SetDisplayPoint(display_x, display_y, 0.0)
                renderer.DisplayToWorld()
                world_point = renderer.GetWorldPoint()
                if self._brush_model.shape == BrushShape.Cylinder:
                    display_z += 0.5
                return (display_z, world_point[1], world_point[2])
            case vtkResliceImageViewer.SLICE_ORIENTATION_XZ:
                display_z = self._viewer.GetResliceCursor().GetCenter()[1]
                renderer = self._viewer.GetRenderer()
                renderer.SetDisplayPoint(display_x, display_y, 0.0)
                renderer.DisplayToWorld()
                world_point = renderer.GetWorldPoint()
                if self._brush_model.shape == BrushShape.Cylinder:
                    display_z += 0.5
                return (world_point[0], display_z, world_point[2])
            case vtkResliceImageViewer.SLICE_ORIENTATION_XY:
                display_z = self._viewer.GetResliceCursor().GetCenter()[2]
                renderer = self._viewer.GetRenderer()
                renderer.SetDisplayPoint(display_x, display_y, display_z)
                renderer.DisplayToWorld()
                world_point = renderer.GetWorldPoint()
                if self._brush_model.shape == BrushShape.Cylinder:
                    display_z -= 0.5
                return (world_point[0], world_point[1], display_z)
            case _:
                raise RuntimeError(f"Invalid orientation for viewer {self._viewer}")

    def _update_brush_position(self, world_pos: tuple[float, float, float]):
        # brush is rotated to the slice widget plane
        brush_to_world_origin_transform_matrix = vtkMatrix4x4()
        brush_to_world_origin_transform_matrix.DeepCopy(self._get_slice_to_world())
        brush_to_world_origin_transform_matrix.SetElement(0, 3, 0)
        brush_to_world_origin_transform_matrix.SetElement(1, 3, 0)
        brush_to_world_origin_transform_matrix.SetElement(2, 3, 0)

        # cylinder's long axis is the Y axis, we need to rotate it to Z axis
        self._brush_model.brush_to_world_origin_transform.Identity()
        self._brush_model.brush_to_world_origin_transform.Concatenate(brush_to_world_origin_transform_matrix)
        self._brush_model.brush_to_world_origin_transform.RotateX(90)

        self._brush_model.world_origin_to_world_transform.Identity()
        self._brush_model.world_origin_to_world_transform.Translate(world_pos)
