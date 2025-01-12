import logging
import sys

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

# Callback class used to refresh all views.
class ResliceImageViewerCallback(object):
    def __init__(self, renderers):
        self.renderers = renderers

    def __call__(self, caller, ev):
        # Find caller to synchronize Window/Level in Axis-aligned mode
        caller_id = -1
        for i in range(len(self.renderers)):
            if (
                vtkInteractorStyleImage.SafeDownCast(caller) ==
                self.renderers[i].GetInteractorStyle()
            ):
                caller_id = i
                break

        for i in range(len(self.renderers)):
            # (Axis-aligned): Window/Level must be synchronized to
            if caller_id != -1 and caller_id != i:
                self.renderers[i].SetColorWindow(
                    self.renderers[caller_id].GetColorWindow()
                )
                self.renderers[i].SetColorLevel(
                    self.renderers[caller_id].GetColorLevel()
                )
            # Refresh all views
            self.renderers[i].Render()

viewers = []
viewer_callback = ResliceImageViewerCallback(viewers)

def render_slice(image_data, renderer, axis = 2, obliques=True):
    render_window = renderer.GetRenderWindow()
    interactor = render_window.GetInteractor()

    reslice_image_viewer = vtkResliceImageViewer()
    viewers.append(reslice_image_viewer)
    reslice_image_viewer.SetRenderer(renderer)
    reslice_image_viewer.SetRenderWindow(render_window)
    reslice_image_viewer.SetupInteractor(interactor)
    # FIXME: should not be needed
    render_window.reslice_image = reslice_image_viewer
    reslice_image_viewer.SetInputData(image_data)

    # Set the reslice mode and axis
    # viewers[axis].SetResliceModeToOblique()
    reslice_image_viewer.SetSliceOrientation(axis)  # 0=X, 1=Y, 2=Z
    reslice_image_viewer.SetThickMode(0)

    # (Oblique) Get widget representation
    cursor_rep = vtkResliceCursorLineRepresentation.SafeDownCast(
        reslice_image_viewer.GetResliceCursorWidget().GetRepresentation()
    )
    reslice_image_viewer.cursor_rep = cursor_rep

    # vtkResliceImageViewer instance share share the same lookup table
    reslice_image_viewer.SetLookupTable(viewers[0].GetLookupTable())

    # (Oblique): Make all vtkResliceImageViewer instance share the same
    reslice_image_viewer.SetResliceCursor(viewers[0].GetResliceCursor())
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
    reslice_image_viewer.GetResliceCursorWidget()\
        .GetEventTranslator()\
        .RemoveTranslation(
            vtkCommand.LeftButtonPressEvent
        )
    reslice_image_viewer.GetResliceCursorWidget() \
        .GetEventTranslator() \
        .SetTranslation(
            vtkCommand.LeftButtonPressEvent, vtkWidgetEvent.Rotate
        )
    # Update all views on events
    reslice_image_viewer.GetResliceCursorWidget().AddObserver(
        'AnyEvent',
        viewer_callback
    )
    reslice_image_viewer.AddObserver('AnyEvent', viewer_callback)
    reslice_image_viewer.GetInteractorStyle().AddObserver(
        'WindowLevelEvent',
        viewer_callback
    )

    # Oblique
    reslice_image_viewer.SetResliceModeToOblique()
    reslice_image_viewer.GetResliceCursorWidget().AddObserver(
        'ResliceAxesChangedEvent', viewer_callback
    )
    reslice_image_viewer.GetResliceCursorWidget().AddObserver(
        'WindowLevelEvent', viewer_callback
    )
    reslice_image_viewer.GetResliceCursorWidget().AddObserver(
        'ResliceThicknessChangedEvent', viewer_callback
    )
    reslice_image_viewer.GetResliceCursorWidget().AddObserver(
        'ResetCursorEvent', viewer_callback
    )
    reslice_image_viewer.AddObserver(
        'SliceChangedEvent', viewer_callback
    )

    if not obliques:
        for i in range(3):
            cursor_rep.GetResliceCursorActor() \
                .GetCenterlineProperty(i) \
                .SetOpacity(0.0)
        reslice_image_viewer.GetResliceCursorWidget().ProcessEventsOff()

    # Reset camera and render.
    renderer.ResetCameraScreenSpace(0.8)
    reslice_image_viewer.Render()

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
    render_window = renderer.GetRenderWindow()
    render_window.reslice_image = None

    renderer.ResetCameraScreenSpace(0.8)
    render_window.Render()


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
