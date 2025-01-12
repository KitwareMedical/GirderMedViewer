import logging
import sys
from collections import defaultdict

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
    vtkColorTransferFunction,
    vtkNIFTIImageReader,
    vtkSmartVolumeMapper,
    vtkVolumeProperty,
    vtkPiecewiseFunction,
    vtkVolume,
    vtkResliceCursorLineRepresentation,
)

logging.basicConfig(stream=sys.stdout)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# FIXME do not use global variable
# key = data_id, value= list of vtkResliceImageViewer
viewers = defaultdict(list)
# key = data_id, value=ResliceImageViewerCallback
viewer_callbacks = {}

# Callback class used to refresh all views.
class ResliceImageViewerCallback(object):
    def __init__(self, renderers):
        self.renderers = renderers

    def get_renderer(self, caller):
        # Find caller to synchronize Window/Level in Axis-aligned mode
        caller_id = -1
        for i in range(len(self.renderers)):
            if (
                vtkInteractorStyleImage.SafeDownCast(caller) ==
                self.renderers[i].GetInteractorStyle()
            ):
                caller_id = i
                break
        return self.renderers[caller_id] if caller_id != -1 else None

    def __call__(self, caller, ev):
        calling_renderer = self.get_renderer(caller)
        if calling_renderer is None:
            return

        for renderer in self.renderers:
            # (Axis-aligned): Window/Level must be synchronized to
            if calling_renderer == renderer:
                continue
            renderer.SetColorWindow(calling_renderer.GetColorWindow())
            renderer.SetColorLevel(calling_renderer.GetColorLevel())

            renderer.Render()


def set_oblique_visibility(reslice_image_viewer, visible):
    reslice_cursor_widget = reslice_image_viewer.GetResliceCursorWidget()
    cursor_rep = vtkResliceCursorLineRepresentation.SafeDownCast(
        reslice_cursor_widget.GetRepresentation())
    reslice_cursor_actor = cursor_rep.GetResliceCursorActor()
    for axis in range(3):
        reslice_cursor_actor.GetCenterlineProperty(axis) \
            .SetOpacity(1.0 if visible else 0.0)
    reslice_cursor_widget.SetProcessEvents(visible)

def render_slice(data_id, image_data, renderer, axis=2, obliques=True):
    render_window = renderer.GetRenderWindow()
    interactor = render_window.GetInteractor()

    reslice_image_viewer = vtkResliceImageViewer()
    viewers[data_id].append(reslice_image_viewer)

    if data_id not in viewer_callbacks:
        viewer_callback = ResliceImageViewerCallback(viewers[data_id])
        viewer_callbacks[data_id] = viewer_callback
    else:
        viewer_callback = viewer_callbacks[data_id]

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

    # vtkResliceImageViewer instance share share the same lookup table
    reslice_image_viewer.SetLookupTable(viewers[data_id][0].GetLookupTable())

    # (Oblique): Make all vtkResliceImageViewer instance share the same
    reslice_image_viewer.SetResliceCursor(viewers[data_id][0].GetResliceCursor())
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
    # Update all views on events
    reslice_cursor_widget.AddObserver('AnyEvent', viewer_callback)
    reslice_image_viewer.AddObserver('AnyEvent', viewer_callback)
    reslice_image_viewer.GetInteractorStyle().AddObserver(
        'WindowLevelEvent',
        viewer_callback
    )

    # Oblique
    reslice_image_viewer.SetResliceModeToOblique()
    reslice_cursor_widget.AddObserver(
        'ResliceAxesChangedEvent', viewer_callback
    )
    reslice_cursor_widget.AddObserver(
        'WindowLevelEvent', viewer_callback
    )
    reslice_cursor_widget.AddObserver(
        'ResliceThicknessChangedEvent', viewer_callback
    )
    reslice_cursor_widget.AddObserver(
        'ResetCursorEvent', viewer_callback
    )
    reslice_image_viewer.AddObserver(
        'SliceChangedEvent', viewer_callback
    )

    if not obliques:
        set_oblique_visibility(reslice_image_viewer, obliques)

    # Fit volume to viewport
    renderer.ResetCameraScreenSpace(0.8)

    return reslice_image_viewer


def render_3D(image_data, renderer):
    volume_mapper = vtkSmartVolumeMapper()
    volume_mapper.SetInputData(image_data)

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

    renderer.ResetCameraScreenSpace(0.8)

    return volume


def create_rendering_pipeline(n_views):
    renderers, render_windows, interactors = [], [], []
    for _ in range(n_views):
        renderer = vtkRenderer()
        render_window = vtkRenderWindow()
        interactor = vtkRenderWindowInteractor()

        render_window.AddRenderer(renderer)
        interactor.SetRenderWindow(render_window)
        interactor.GetInteractorStyle().SetCurrentStyleToTrackballCamera()

        renderer.ResetCamera()
        render_window.Render()
        interactor.Render()

        renderers.append(renderer)
        render_windows.append(render_window)
        interactors.append(interactor)

    return renderers, render_windows, interactors


def load_file(file_path):
    logger.debug(f"Loading file {file_path}")
    if file_path.endswith((".nii", ".nii.gz")):
        reader = vtkNIFTIImageReader()
        reader.SetFileName(file_path)
        reader.Update()
        return reader.GetOutput()

    # TODO Handle dicom, vti, mesh

    raise Exception("File format is not handled for {}".format(file_path))
