import logging
import math
import os
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from vtk import reference as vtk_reference
from vtk import (
    vtkActor,
    vtkArrowSource,
    vtkBoundingBox,
    vtkBox,
    vtkColorSeries,
    vtkCutter,
    vtkGlyph3DMapper,
    vtkImageData,
    vtkImageGaussianSmooth,
    vtkImageReslice,
    vtkImageResliceMapper,
    vtkImageSlice,
    vtkMath,
    vtkMatrix4x4,
    vtkMetaImageReader,
    vtkNIFTIImageReader,
    vtkNrrdReader,
    vtkPolyDataMapper,
    vtkResliceCursor,
    vtkResliceCursorLineRepresentation,
    vtkResliceCursorRepresentation,
    vtkResliceCursorWidget,
    vtkSmartVolumeMapper,
    vtkSTLReader,
    vtkTransform,
    vtkTransformFilter,
    vtkVolume,
    vtkVolumeProperty,
    vtkXMLImageDataReader,
    vtkXMLPolyDataReader,
)
from vtkmodules.all import (
    vtkCommand,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
    vtkResliceImageViewer,
    vtkWidgetEvent,
)

logger = logging.getLogger(__name__)


# FIXME do not use global variable
# dict[axis:vtkResliceImageViewer]
viewers = {}


def set_oblique_visibility(reslice_image_viewer, visible):
    reslice_cursor_widget = reslice_image_viewer.GetResliceCursorWidget()
    cursor_rep = vtkResliceCursorLineRepresentation.SafeDownCast(reslice_cursor_widget.GetRepresentation())
    reslice_cursor_actor = cursor_rep.GetResliceCursorActor()
    for axis in range(3):
        reslice_cursor_actor.GetCenterlineProperty(axis).SetOpacity(1.0 if visible else 0.0)
    reslice_cursor_widget.SetProcessEvents(visible)


def get_reslice_cursor(reslice_object) -> vtkResliceCursor | None:
    """
    Return the vtkResliceCursor from a vtkResliceImageViewer,
    a vtkResliceCursorWidget or a vtkResliceCursorRepresentation.
    :rtype vtkResliceCursor | None:
    """
    if isinstance(reslice_object, vtkResliceImageViewer):
        reslice_object = reslice_object.GetResliceCursor()
    if isinstance(reslice_object, vtkResliceCursorWidget):
        reslice_object = reslice_object.GetResliceCursorRepresentation()
    if isinstance(reslice_object, vtkResliceCursorRepresentation):
        reslice_object = reslice_object.GetResliceCursor()
    assert reslice_object is None or reslice_object.IsA("vtkResliceCursor")
    return reslice_object


def get_reslice_cursor_representation(reslice_object) -> vtkResliceCursorRepresentation | None:
    """
    Return the vtkResliceCursorRepresentation from vtkResliceImageViewer or a vtkResliceCursorWidget.
    :rtype vtkResliceCursorRepresentation | None:
    """
    if isinstance(reslice_object, vtkResliceImageViewer):
        reslice_object = reslice_object.GetResliceCursorWidget()
    if isinstance(reslice_object, vtkResliceCursorWidget):
        reslice_object = reslice_object.GetResliceCursorRepresentation()
    assert reslice_object is None or reslice_object.IsA("vtkResliceCursorRepresentation")
    return reslice_object


def get_image_data(object: vtkResliceImageViewer | vtkImageSlice) -> vtkImageData | None:
    if isinstance(object, vtkResliceImageViewer):
        return object.GetInput()
    if isinstance(object, vtkImageSlice):
        return object.GetMapper().GetInput()
    return None


def get_closest_point_in_bounds(bounds, point):
    return tuple([max(bounds[i], min(point[i // 2], bounds[i + 1])) for i in range(0, len(bounds), 2)])


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
    if not vtkBoundingBox(reslice_cursor.image.bounds).ContainsPoint(new_center):
        new_center = get_closest_point_in_bounds(reslice_cursor.image.bounds, new_center)
    reslice_cursor.SetCenter(new_center)
    return True


def set_reslice_normal(reslice_object, new_normal, axis):
    if reslice_object is None:
        return False
    reslice_cursor = get_reslice_cursor(reslice_object)
    axis_name = "X" if axis == 0 else "Y" if axis == 1 else "Z"
    normal = getattr(reslice_cursor, f"Get{axis_name}Axis")()
    if normal == new_normal:
        return False
    getattr(reslice_cursor, f"Set{axis_name}Axis")(new_normal)
    return True


def set_reslice_window_level(reslice_image_viewer, new_window_level):
    if reslice_image_viewer is None:
        return False
    if (
        reslice_image_viewer.GetColorWindow() == new_window_level[0]
        and reslice_image_viewer.GetColorLevel() == new_window_level[1]
    ):
        return False
    reslice_image_viewer.SetColorWindow(new_window_level[0])
    reslice_image_viewer.SetColorLevel(new_window_level[1])
    return True


def get_reslice_window_level(reslice_image_viewer):
    """
    :param interactor_style reslice_image_viewer.GetInteractorStyle()
    """
    return (reslice_image_viewer.GetColorWindow(), reslice_image_viewer.GetColorLevel())


def set_reslice_visibility(reslice_image_viewer: vtkResliceImageViewer, visible: bool) -> bool:
    alpha = (float(visible), float(visible))
    lut = reslice_image_viewer.GetWindowLevel().GetLookupTable()
    if lut.GetAlphaRange() == alpha:
        return False
    lut.SetAlphaRange(*alpha)
    lut.Build()
    return True


def set_reslice_opacity(_reslice_image_viewer, opacity):
    if opacity != 1:
        logger.warning("not implemented")
    return False
    # reslice_representation = get_reslice_cursor_representation(reslice_image_viewer)
    # if reslice_representation is None:
    #     return False
    # reslice_actor = reslice_representation.GetImageActor() => should be GetTexturedActor
    # reslice_property = reslice_actor.GetProperty()
    # if reslice_property.GetOpacity() == opacity:
    #     return False
    # reslice_property.SetOpacity(opacity)
    # return True


def reset_reslice(reslice_image_viewer):
    reslice_cursor = get_reslice_cursor(reslice_image_viewer)
    image_data = get_image_data(reslice_image_viewer)
    if image_data is not None:
        center = image_data.center
        reslice_cursor.SetCenter(center)
    # reslice_image_viewer.GetResliceCursorWidget().ResetResliceCursor()
    reslice_cursor.GetPlane(0).SetNormal(-1, 0, 0)
    reslice_cursor.SetXViewUp(0, 0, 1)
    reslice_cursor.GetPlane(1).SetNormal(0, 1, 0)
    reslice_cursor.SetYViewUp(0, 0, 1)
    reslice_cursor.GetPlane(2).SetNormal(0, 0, -1)
    reslice_cursor.SetZViewUp(0, 1, 0)

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
    image_data = get_image_data(reslice_image_viewer)
    bounds = image_data.GetBounds()
    if center is None or not vtkBoundingBox(bounds).ContainsPoint(center):
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
    vtkBox.IntersectWithInfiniteLine(bounds, center_minus_normal, center_plus_normal, t1, t2, x1, x2, p1, p2)
    image_data.GetSpacing()
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
    spacing = get_image_data(reslice_image_viewer).GetSpacing()
    return get_index(start, end, spacing)


def get_slice_index_from_position(position, reslice_image_viewer, axis):
    """Position must be in the reslice range, else the current reslice position is used."""
    if reslice_image_viewer is None:
        return None
    start, _ = get_reslice_range(reslice_image_viewer, axis, position)
    spacing = get_image_data(reslice_image_viewer).GetSpacing()
    return get_index(start, position, spacing)


def get_position_from_slice_index(index, reslice_image_viewer, axis):
    """Position must be on the line defined by start and end."""
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
        start[2] + index * dir[2] / slice_count,
    ]


def get_reslice_image_viewer(axis=-1) -> vtkResliceImageViewer:
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
    cursor_rep = vtkResliceCursorLineRepresentation.SafeDownCast(reslice_cursor_widget.GetRepresentation())

    # (Oblique): Make all vtkResliceImageViewer instance share the same
    reslice_image_viewer.SetResliceCursor(get_reslice_image_viewer(-1).GetResliceCursor())

    set_reslice_visibility(reslice_image_viewer, True)
    reset_reslice(reslice_image_viewer)

    for i in range(3):
        cursor_rep.GetResliceCursorActor().GetCenterlineProperty(i).SetLineWidth(4)
        cursor_rep.GetResliceCursorActor().GetCenterlineProperty(i).RenderLinesAsTubesOn()
        cursor_rep.GetResliceCursorActor().GetCenterlineProperty(i).SetRepresentationToWireframe()
        cursor_rep.GetResliceCursorActor().GetThickSlabProperty(i).SetRepresentationToWireframe()
    cursor_rep.GetResliceCursorActor().GetCursorAlgorithm().SetReslicePlaneNormal(axis)

    # (Oblique) Keep orthogonality between axis
    reslice_cursor_widget.GetEventTranslator().RemoveTranslation(vtkCommand.LeftButtonPressEvent)
    reslice_cursor_widget.GetEventTranslator().SetTranslation(vtkCommand.LeftButtonPressEvent, vtkWidgetEvent.Rotate)
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

    set_slice_opacity(image_slice, opacity)

    # vtkResliceImageViewer computes the default color window/level.
    # here we need to do it manually
    range = image_data.GetScalarRange()
    set_slice_window_level(image_slice, [(range[1] - range[0]) / 2.0, (range[0] + range[1]) / 2.0])

    renderer.AddActor(image_slice)

    # Fit volume to viewport
    renderer.ResetCameraScreenSpace(0.8)

    return image_slice


def set_slice_visibility(image_slice: vtkImageSlice, visible: bool) -> bool:
    if image_slice is None:
        return False
    if image_slice.GetVisibility() == visible:
        return False
    image_slice.SetVisibility(visible)
    return True


def render_volume_as_vector_field(image_data, renderer, axis=2):
    reslice_image_viewer = get_reslice_image_viewer(axis)
    reslice_cursor = get_reslice_cursor(reslice_image_viewer)

    point_data = image_data.GetPointData()
    for i in range(point_data.GetNumberOfArrays()):
        logger.info("array: %s", point_data.GetArray(i).GetName())

    cutter = vtkCutter()
    cutter.SetInputData(image_data)
    cutter.SetCutFunction(reslice_cursor.GetPlane(axis))

    arrow = vtkArrowSource()
    arrow.SetTipLength(0.3)
    arrow.SetTipRadius(0.1)
    arrow.SetShaftRadius(0.03)

    imageMapper = vtkImageResliceMapper()
    imageMapper.SetInputData(image_data)
    imageMapper.SetSlicePlane(reslice_cursor.GetPlane(axis))

    glyph_mapper = vtkGlyph3DMapper()
    glyph_mapper.SetInputConnection(cutter.GetOutputPort())
    glyph_mapper.SetSourceConnection(arrow.GetOutputPort())

    glyph_mapper.SetOrientationArray("Scalars")
    # glyph_mapper.SetScaleArray("Vectors")
    # glyph_mapper.SetScaleModeToScaleByVector()
    # glyph_mapper.SetScaleFactor(0.2)
    glyph_mapper.OrientOn()

    bounds = glyph_mapper.GetBounds()
    logger.info('glyph bounds: %s', bounds)

    glyph_actor = vtkActor()
    glyph_actor.SetMapper(glyph_mapper)

    renderer.AddActor(glyph_actor)

    # Fit volume to viewport
    # renderer.ResetCameraScreenSpace(0.8)

    return glyph_actor


def set_actor_visibility(image_slice_or_actor: vtkActor | vtkImageSlice, visibility: bool) -> bool:
    """
    Set the visibility of a vtkActor or a vtkImageSlice.
    Return true if the visibility was changed, false otherwise.
    @see set_actor_opacity
    """
    if image_slice_or_actor is None:
        return False
    if hasattr(image_slice_or_actor, "GetResliceCursorWidget"):
        image_slice_or_actor = image_slice_or_actor.GetResliceCursorWidget().GetRepresentation()
    if image_slice_or_actor.GetVisibility() == visibility:
        return False
    image_slice_or_actor.SetVisibility(visibility)
    return True


def set_actor_opacity(image_slice_or_actor: vtkActor | vtkImageSlice, opacity: float) -> bool:
    if image_slice_or_actor is None:
        return False
    if image_slice_or_actor.GetProperty().GetOpacity() == opacity:
        return False
    image_slice_or_actor.GetProperty().SetOpacity(opacity)
    return True


def set_slice_opacity(image_slice: vtkImageSlice, opacity: float) -> bool:
    return set_actor_opacity(image_slice, opacity)


def set_slice_window_level(image_slice, window_level):
    if image_slice is None:
        return False
    if (
        image_slice.GetProperty().GetColorWindow() == window_level[0]
        and image_slice.GetProperty().GetColorLevel() == window_level[1]
    ):
        return False
    image_slice.GetProperty().SetColorWindow(window_level[0])
    image_slice.GetProperty().SetColorLevel(window_level[1])
    return True


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


def set_mesh_visibility(actor: vtkActor, visible):
    if actor.GetVisibility() == visible:
        return False
    actor.SetVisibility(visible)
    return True


def set_mesh_opacity(actor, opacity):
    return set_actor_opacity(actor, opacity)


def set_mesh_solid_color(actor, color):
    old_scalar_visibilty = actor.GetMapper().GetScalarVisibility()
    old_color = actor.GetProperty().GetColor()
    if old_color == color and not old_scalar_visibilty:
        return False
    actor.GetMapper().SetScalarVisibility(False)
    actor.GetProperty().SetColor(color)
    return True


def reset_3D(renderer):
    bounds = renderer.ComputeVisiblePropBounds()
    center = [0, 0, 0]
    vtkBoundingBox(bounds).GetCenter(center)
    renderer.GetActiveCamera().SetFocalPoint(center)
    renderer.GetActiveCamera().SetPosition((bounds[1], bounds[2], center[2]))
    renderer.GetActiveCamera().SetViewUp(0, 0, 1)
    renderer.ResetCameraScreenSpace(0.8)


def set_volume_visibility(volume: vtkVolume, visible: bool) -> bool:
    if volume.GetVisibility() == visible:
        return False
    volume.SetVisibility(visible)
    return True


def render_volume_in_3D(image_data, renderer):
    volume_mapper = vtkSmartVolumeMapper()
    volume_mapper.SetInputData(image_data)

    # FIXME: does not work for all dataset
    volume_property = vtkVolumeProperty()
    volume_property.ShadeOn()
    volume_property.SetInterpolationTypeToLinear()

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
    elif isinstance(prop, vtkActor | vtkImageSlice):
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

    return renderer, render_window


def supported_volume_extensions():
    return (".nii", ".nii.gz", ".nrrd", ".mha", ".zip", ".vti")


def supported_mesh_extensions():
    return (".stl", ".vtp")


def find_subfolder_with_most_files(directory):
    """
    Convenient function to search the subfolder with the most files.
    The returned subfolder can be the input directory.
    :param directory:  the directory to scan
    :type directory: string
    :return: the folder with the most files in it
    :rtype: string
    """
    max_files = 0
    folder_with_max_files = None

    # Walk through the directory
    for subdir, _dirs, files in os.walk(directory):
        num_files = len(files)
        if num_files > max_files:
            max_files = num_files
            folder_with_max_files = subdir

    return folder_with_max_files


def create_gaussian_filter(original_image):
    gaussian_smooth = vtkImageGaussianSmooth()
    gaussian_smooth.SetInputData(original_image)

    return gaussian_smooth


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

    if file_path.endswith(".nrrd"):
        reader = vtkNrrdReader()
        reader.SetFileName(file_path)
        reader.Update()
        return reader.GetOutput()

    if file_path.endswith(".mha"):
        reader = vtkMetaImageReader()
        reader.SetFileName(file_path)
        reader.Update()
        return reader.GetOutput()

    if file_path.endswith(".zip"):
        from dicomexporter import exporter  # pip install ".[dicom]"

        with TemporaryDirectory() as temp_dir, ZipFile(file_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)
            folder = find_subfolder_with_most_files(temp_dir)
            image_data, _ = exporter.readDICOMVolume(folder)
            return image_data

    if file_path.endswith(".vti"):
        reader = vtkXMLImageDataReader()
        reader.SetFileName(file_path)
        reader.Update()
        return reader.GetOutput()

    raise Exception(f"File format is not handled for {file_path}")


def load_mesh(file_path):
    """Read a file and return a vtkPolyData object"""
    logger.info(f"Loading mesh {file_path}")

    def invert_xy(reader):
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

    if file_path.endswith(".stl"):
        reader = vtkSTLReader()
        reader.SetFileName(file_path)
        reader.Update()
        return invert_xy(reader)

    if file_path.endswith(".vtp"):
        reader = vtkXMLPolyDataReader()
        reader.SetFileName(file_path)
        reader.Update()
        return invert_xy(reader)

    raise Exception(f"File format is not handled for {file_path}")


color_series = vtkColorSeries()
last_color_scheme = vtkColorSeries.BREWER_QUALITATIVE_SET1
color_series.SetColorScheme(vtkColorSeries.BREWER_QUALITATIVE_SET1)
last_color = 0


def get_random_color():
    global last_color_scheme  # noqa: PLW0603
    global last_color  # noqa: PLW0603
    if last_color >= color_series.GetNumberOfColors():
        color_series.SetColorScheme(last_color_scheme)
        last_color_scheme += 1
        last_color = 0
    color = color_series.GetColor(last_color)
    last_color += 1
    return "#{:02x}{:02x}{:02x}".format(*color)
