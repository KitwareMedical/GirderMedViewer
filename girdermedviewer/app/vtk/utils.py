import logging
import math

from vtkmodules.all import (
    vtkCommand,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkResliceImageViewer,
    vtkInteractorStyleImage,
    vtkWidgetEvent
)
from vtk import (
    reference as vtk_reference,
    vtkActor,
    vtkBoundingBox,
    vtkBox,
    vtkColorTransferFunction,
    vtkCutter,
    vtkImageReslice,
    vtkImageResliceMapper,
    vtkImageSlice,
    vtkMath,
    vtkMatrix4x4,
    vtkNIFTIImageReader,
    vtkPiecewiseFunction,
    vtkPolyDataMapper,
    vtkResliceCursorLineRepresentation,
    vtkResliceCursorRepresentation,
    vtkResliceCursorWidget,
    vtkSmartVolumeMapper,
    vtkSTLReader,
    vtkTransform,
    vtkTransformFilter,
    vtkVolume,
    vtkVolumeProperty,
)

logger = logging.getLogger(__name__)


# FIXME do not use global variable
# dict[axis:vtkResliceImageViewer]
viewers = dict()


def set_oblique_visibility(reslice_image_viewer, visible):
    reslice_cursor_widget = reslice_image_viewer.GetResliceCursorWidget()
    cursor_rep = vtkResliceCursorLineRepresentation.SafeDownCast(
        reslice_cursor_widget.GetRepresentation())
    reslice_cursor_actor = cursor_rep.GetResliceCursorActor()
    for axis in range(3):
        reslice_cursor_actor.GetCenterlineProperty(axis) \
            .SetOpacity(1.0 if visible else 0.0)
    reslice_cursor_widget.SetProcessEvents(visible)


def get_reslice_cursor(reslice_object):
    """
    Return the point where the 3 planes intersect.
    :rtype tuple[float, float, float]
    """
    if isinstance(reslice_object, vtkResliceImageViewer):
        reslice_object = reslice_object.GetResliceCursor()
    if isinstance(reslice_object, vtkResliceCursorWidget):
        reslice_object = reslice_object.GetResliceCursorRepresentation()
    if isinstance(reslice_object, vtkResliceCursorRepresentation):
        reslice_object = reslice_object.GetResliceCursor()
    assert reslice_object is None or reslice_object.IsA('vtkResliceCursor')
    return reslice_object


def get_reslice_center(reslice_object):
    """
    Return the point where the 3 planes intersect.
    :rtype tuple[float, float, float]
    """
    return get_reslice_cursor(reslice_object).center


def set_reslice_center(reslice_object, new_center):
    if reslice_object is None:
        return False
    reslice_cursor = get_reslice_cursor(reslice_object)
    center = reslice_cursor.GetCenter()
    if center == new_center:
        return False
    reslice_cursor.SetCenter(new_center)
    return True


def set_reslice_normal(reslice_object, new_normal, axis):
    if reslice_object is None:
        return False
    reslice_cursor = get_reslice_cursor(reslice_object)
    axis_name = 'X' if axis == 0 else 'Y' if axis == 1 else 'Z'
    normal = getattr(reslice_cursor, f"Get{axis_name}Axis")()
    if normal == new_normal:
        return False
    getattr(reslice_cursor, f"Set{axis_name}Axis")(new_normal)
    return True


def set_window_level(reslice_image_viewer, new_window_level):
    if reslice_image_viewer is None:
        return False
    if (reslice_image_viewer.GetColorWindow() == new_window_level[0] and
            reslice_image_viewer.GetColorLevel() == new_window_level[1]):
        return False
    reslice_image_viewer.SetColorWindow(new_window_level[0])
    reslice_image_viewer.SetColorLevel(new_window_level[1])
    return True


def reset_reslice(reslice_image_viewer):
    center = reslice_image_viewer.input.center
    reslice_image_viewer.GetResliceCursor().SetCenter(center)
    reslice_image_viewer.GetResliceCursorWidget().ResetResliceCursor()
    reslice_image_viewer.GetRenderer().ResetCameraScreenSpace(0.8)


def get_reslice_normals(reslice_object):
    """
    Return the 3 plane normals as a tuple of tuples.
    :rtype tuple[tuple[float, float, float],
                 tuple[float, float, float],
                 tuple[float, float, float]]
    """
    reslice_cursor = get_reslice_cursor(reslice_object)
    return (
        reslice_cursor.x_axis,
        reslice_cursor.y_axis,
        reslice_cursor.z_axis,
    )


def get_reslice_normal(reslice_image_viewer, axis):
    return get_reslice_normals(reslice_image_viewer)[axis]


def get_reslice_range(reslice_image_viewer, axis, center=None):
    if reslice_image_viewer is None:
        return None
    bounds = reslice_image_viewer.GetInput().GetBounds()
    if center is None:
        center = get_reslice_center(reslice_image_viewer)
    normal = list(get_reslice_normal(reslice_image_viewer, axis))
    vtkMath.MultiplyScalar(normal, 1000000.0)
    center_plus_normal = [0, 0, 0]
    vtkMath.Add(center, normal, center_plus_normal)
    center_minus_normal = [0, 0, 0]
    vtkMath.Subtract(center, normal, center_minus_normal)
    t1 = vtk_reference(0)
    t2 = vtk_reference(0)
    x1 = [0, 0, 0]
    x2 = [0, 0, 0]
    p1 = vtk_reference(0)
    p2 = vtk_reference(0)
    vtkBox.IntersectWithInfiniteLine(
        bounds,
        center_minus_normal, center_plus_normal,
        t1, t2, x1, x2, p1, p2)
    reslice_image_viewer.GetInput().GetSpacing()
    return x1, x2


def get_index(p1, p2, spacing):
    v = [
        (p2[0] - p1[0]) / spacing[0],
        (p2[1] - p1[1]) / spacing[1],
        (p2[2] - p1[2]) / spacing[2],
    ]
    return math.ceil(vtkMath.Norm(v))


def get_number_of_slices(reslice_image_viewer, axis):
    if reslice_image_viewer is None:
        return 0
    start, end = get_reslice_range(reslice_image_viewer, axis)
    spacing = reslice_image_viewer.GetInput().GetSpacing()
    return get_index(start, end, spacing)


def get_slice_index_from_position(position, reslice_image_viewer, axis):
    """Position must be on the line defined by stard and end."""
    if reslice_image_viewer is None:
        return None
    start, end = get_reslice_range(reslice_image_viewer, axis, position)
    spacing = reslice_image_viewer.GetInput().GetSpacing()
    return get_index(start, position, spacing)


def get_position_from_slice_index(index, reslice_image_viewer, axis):
    """Position must be on the line defined by stard and end."""
    if reslice_image_viewer is None:
        return None
    start, end = get_reslice_range(reslice_image_viewer, axis)
    slice_count = get_number_of_slices(reslice_image_viewer, axis)
    if slice_count == 0:
        return None
    dir = [end[0] - start[0], end[1] - start[1], end[2] - start[2]]
    return [
        start[0] + index * dir[0] / slice_count,
        start[1] + index * dir[1] / slice_count,
        start[2] + index * dir[2] / slice_count
    ]


def get_reslice_image_viewer(axis=-1):
    """
    Returns a matching reslice image viewer or create it if it does not exist.
    If axis is -1, it returns the firstly added reslice image viewer
    or create an axial (2) reslice image viewer if none exist.
    """
    if axis == -1:
        try:
            return next(iter(viewers.values()))
        except StopIteration:
            # no Reslice Image Viewer has been created for data_id
            axis = 2
    if axis in viewers:
        return viewers[axis]

    reslice_image_viewer = vtkResliceImageViewer()
    # is it the firstly created image viewer ?
    if len(viewers) == 0:
        reslice_cursor = get_reslice_cursor(reslice_image_viewer)
        reslice_cursor.GetPlane(0).SetNormal(-1, 0, 0)
        reslice_cursor.SetXViewUp(0, 0, -1)
        reslice_cursor.GetPlane(1).SetNormal(0, 1, 0)
        reslice_cursor.SetYViewUp(0, 0, -1)
        reslice_cursor.GetPlane(2).SetNormal(0, 0, -1)
        reslice_cursor.SetZViewUp(0, -1, 0)

    viewers[axis] = reslice_image_viewer

    return reslice_image_viewer


def render_volume_in_slice(image_data, renderer, axis=2, obliques=True):
    render_window = renderer.GetRenderWindow()
    interactor = render_window.GetInteractor()

    reslice_image_viewer = get_reslice_image_viewer(axis)

    reslice_image_viewer.SetRenderer(renderer)
    reslice_image_viewer.SetRenderWindow(render_window)
    reslice_image_viewer.SetupInteractor(interactor)
    reslice_image_viewer.SetInputData(image_data)

    # Set the reslice mode and axis
    # viewers[axis].SetResliceModeToOblique()
    reslice_image_viewer.SetSliceOrientation(axis)  # 0=X, 1=Y, 2=Z
    reslice_image_viewer.SetThickMode(0)

    reslice_cursor_widget = reslice_image_viewer.GetResliceCursorWidget()

    # (Oblique) Get widget representation
    cursor_rep = vtkResliceCursorLineRepresentation.SafeDownCast(
        reslice_cursor_widget.GetRepresentation()
    )

    # vtkResliceImageViewer instances share the same lookup table
    reslice_image_viewer.SetLookupTable(get_reslice_image_viewer(-1).GetLookupTable())

    # (Oblique): Make all vtkResliceImageViewer instance share the same
    reslice_image_viewer.SetResliceCursor(get_reslice_image_viewer(-1).GetResliceCursor())
    for i in range(3):
        cursor_rep.GetResliceCursorActor() \
            .GetCenterlineProperty(i) \
            .SetLineWidth(4)
        cursor_rep.GetResliceCursorActor() \
            .GetCenterlineProperty(i)\
            .RenderLinesAsTubesOn()
        cursor_rep.GetResliceCursorActor() \
            .GetCenterlineProperty(i) \
            .SetRepresentationToWireframe()
        cursor_rep.GetResliceCursorActor() \
            .GetThickSlabProperty(i) \
            .SetRepresentationToWireframe()
    cursor_rep.GetResliceCursorActor() \
        .GetCursorAlgorithm() \
        .SetReslicePlaneNormal(axis)

    # (Oblique) Keep orthogonality between axis
    reslice_cursor_widget \
        .GetEventTranslator() \
        .RemoveTranslation(
            vtkCommand.LeftButtonPressEvent
        )
    reslice_cursor_widget \
        .GetEventTranslator() \
        .SetTranslation(
            vtkCommand.LeftButtonPressEvent, vtkWidgetEvent.Rotate
        )
    # Oblique
    reslice_image_viewer.SetResliceModeToOblique()

    if not obliques:
        set_oblique_visibility(reslice_image_viewer, obliques)

    # Fit volume to viewport
    renderer.ResetCameraScreenSpace(0.8)

    return reslice_image_viewer


def render_volume_as_overlay_in_slice(image_data, renderer, axis=2, opacity=0.8):
    reslice_image_viewer = get_reslice_image_viewer(axis)
    reslice_cursor = get_reslice_cursor(reslice_image_viewer)

    imageMapper = vtkImageResliceMapper()
    imageMapper.SetInputData(image_data)
    imageMapper.SetSlicePlane(reslice_cursor.GetPlane(axis))

    image_slice = vtkImageSlice()
    image_slice.SetMapper(imageMapper)
    slice_property = image_slice.GetProperty()
    # actor.GetProperty().SetLookupTable(ColorTransferFunction)
    slice_property.SetInterpolationTypeToNearest()
    slice_property.SetOpacity(opacity)

    # vtkResliceImageViewer computes the default color window/level.
    # here we need to do it manually
    range = image_data.GetScalarRange()
    slice_property.SetColorWindow(range[1] - range[0])
    slice_property.SetColorLevel((range[0] + range[1]) / 2.0)

    renderer.AddActor(image_slice)

    # Fit volume to viewport
    renderer.ResetCameraScreenSpace(0.8)

    return image_slice


def render_mesh_in_slice(poly_data, axis, renderer):
    reslice_image_viewer = get_reslice_image_viewer(axis)
    reslice_cursor = get_reslice_cursor(reslice_image_viewer)

    cutter = vtkCutter()
    cutter.SetInputData(poly_data)
    cutter.SetCutFunction(reslice_cursor.GetPlane(axis))

    mapper = vtkPolyDataMapper()
    mapper.SetInputConnection(cutter.GetOutputPort())

    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(1, 0, 0)

    renderer.AddActor(actor)
    renderer.ResetCameraScreenSpace(0.8)

    return actor


def reset_3D(renderer):
    bounds = renderer.ComputeVisiblePropBounds()
    center = [0, 0, 0]
    vtkBoundingBox(bounds).GetCenter(center)
    renderer.GetActiveCamera().SetFocalPoint(center)
    renderer.GetActiveCamera().SetPosition(
        (bounds[1], bounds[2], center[2])
    )
    renderer.GetActiveCamera().SetViewUp(0, 0, 1)
    renderer.ResetCameraScreenSpace(0.8)


def render_volume_in_3D(image_data, renderer):
    volume_mapper = vtkSmartVolumeMapper()
    volume_mapper.SetInputData(image_data)

    # FIXME: does not work for all dataset
    volume_property = vtkVolumeProperty()
    volume_property.ShadeOn()
    volume_property.SetInterpolationTypeToLinear()

    color_function = vtkColorTransferFunction()
    color_function.AddRGBPoint(0, 0.0, 0.0, 0.0)  # Black
    color_function.AddRGBPoint(100, 1.0, 0.5, 0.3)  # Orange
    color_function.AddRGBPoint(255, 1.0, 1.0, 1.0)  # White

    opacity_function = vtkPiecewiseFunction()
    opacity_function.AddPoint(0, 0.0)  # Transparent
    opacity_function.AddPoint(100, 0.5)  # Semi-transparent
    opacity_function.AddPoint(255, 1.0)  # Opaque

    volume_property.SetColor(color_function)
    volume_property.SetScalarOpacity(opacity_function)

    volume = vtkVolume()
    volume.SetMapper(volume_mapper)
    volume.SetProperty(volume_property)

    renderer.AddVolume(volume)
    reset_3D(renderer)

    return volume


def render_mesh_in_3D(poly_data, renderer):
    mapper = vtkPolyDataMapper()
    mapper.SetInputData(poly_data)

    actor = vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(1, 0, 0)

    renderer.AddActor(actor)
    renderer.ResetCameraScreenSpace(0.8)

    return actor


def remove_prop(renderer, prop):
    if isinstance(prop, vtkVolume):
        renderer.RemoveVolume(prop)
    elif isinstance(prop, vtkActor) or isinstance(prop, vtkImageSlice):
        renderer.RemoveActor(prop)
    elif isinstance(prop, vtkResliceImageViewer):
        prop.SetupInteractor(None)
        # FIXME: check for leak
        # prop.SetRenderer(None)
        # prop.SetRenderWindow(None)
    else:
        raise Exception(f"Can't remove prop {prop}")


def create_rendering_pipeline():
    renderer = vtkRenderer()
    render_window = vtkRenderWindow()
    render_window.ShowWindowOff()
    interactor = vtkRenderWindowInteractor()

    render_window.AddRenderer(renderer)
    interactor.SetRenderWindow(render_window)
    interactor.GetInteractorStyle().SetCurrentStyleToTrackballCamera()

    renderer.ResetCamera()

    return renderer, render_window, interactor


def load_volume(file_path):
    """Read a file and return a vtkImageData object"""
    logger.info(f"Loading volume {file_path}")
    if file_path.endswith((".nii", ".nii.gz")):
        reader = vtkNIFTIImageReader()
        reader.SetFileName(file_path)
        reader.Update()

        if reader.GetSFormMatrix() is None:
            return reader.GetOutput()

        transform = vtkTransform()
        transform.SetMatrix(reader.GetSFormMatrix())
        transform.Inverse()

        reslice = vtkImageReslice()
        reslice.SetInputConnection(reader.GetOutputPort())
        reslice.SetResliceTransform(transform)
        reslice.SetInterpolationModeToLinear()
        reslice.AutoCropOutputOn()
        reslice.TransformInputSamplingOff()
        reslice.Update()

        return reslice.GetOutput()

    raise Exception("File format is not handled for {}".format(file_path))


def load_mesh(file_path):
    """Read a file and return a vtkPolyData object"""
    logger.info(f"Loading mesh {file_path}")
    if file_path.endswith(".stl"):
        reader = vtkSTLReader()
        reader.SetFileName(file_path)
        reader.Update()

        matrix = vtkMatrix4x4()
        matrix.SetElement(0, 0, -1)
        matrix.SetElement(1, 1, -1)

        transform = vtkTransform()
        transform.SetMatrix(matrix)
        transform.Inverse()

        transform_filter = vtkTransformFilter()
        transform_filter.SetInputConnection(reader.GetOutputPort())
        transform_filter.SetTransform(transform)
        transform_filter.Update()

        return transform_filter.GetOutput()

    raise Exception("File format is not handled for {}".format(file_path))
