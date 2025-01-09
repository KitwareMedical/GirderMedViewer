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
    vtkSmartVolumeMapper,
    vtkVolumeProperty,
    vtkColorTransferFunction,
    vtkPiecewiseFunction,
    vtkVolume,
    vtkResliceCursorLineRepresentation,
)


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


def render_slices(image_data, renderers, render_windows, interactors):
    viewers = []
    viewer_callback = ResliceImageViewerCallback(viewers)
    for axis in range(3):
        viewers.append(vtkResliceImageViewer())
        viewers[axis].SetRenderer(renderers[axis])
        viewers[axis].SetRenderWindow(render_windows[axis])
        viewers[axis].SetupInteractor(interactors[axis])

        viewers[axis].SetInputData(image_data)

        # Set the reslice mode and axis
        viewers[axis].SetResliceModeToAxisAligned()
        viewers[axis].SetSliceOrientation(axis)  # 0=X, 1=Y, 2=Z

        viewers[axis].SetThickMode(0)

        # (Oblique) Get widget representation
        cursor_rep = vtkResliceCursorLineRepresentation.SafeDownCast(
            viewers[axis].GetResliceCursorWidget().GetRepresentation()
        )

        # vtkResliceImageViewer instance share share the same lookup table
        viewers[axis].SetLookupTable(viewers[0].GetLookupTable())

        # (Oblique): Make all vtkResliceImageViewer instance share the same
        viewers[axis].SetResliceCursor(viewers[0].GetResliceCursor())
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
        viewers[axis].GetResliceCursorWidget()\
            .GetEventTranslator()\
            .RemoveTranslation(
                vtkCommand.LeftButtonPressEvent
            )
        viewers[axis].GetResliceCursorWidget() \
            .GetEventTranslator() \
            .SetTranslation(
                vtkCommand.LeftButtonPressEvent, vtkWidgetEvent.Rotate
            )
        # Update all views on events
        viewers[axis].GetResliceCursorWidget().AddObserver(
            'AnyEvent',
            viewer_callback
        )
        viewers[axis].AddObserver('AnyEvent', viewer_callback)
        viewers[axis].GetInteractorStyle().AddObserver(
            'WindowLevelEvent',
            viewer_callback
        )

        # Oblique
        viewers[axis].SetResliceModeToOblique()
        viewers[axis].GetResliceCursorWidget().AddObserver(
          'ResliceAxesChangedEvent', viewer_callback
        )
        viewers[axis].GetResliceCursorWidget().AddObserver(
          'WindowLevelEvent', viewer_callback
        )
        viewers[axis].GetResliceCursorWidget().AddObserver(
          'ResliceThicknessChangedEvent', viewer_callback
        )
        viewers[axis].GetResliceCursorWidget().AddObserver(
          'ResetCursorEvent', viewer_callback
        )
        viewers[axis].AddObserver(
          'SliceChangedEvent', viewer_callback
        )

        # Reset camera and render.
        viewers[axis].GetRenderer().ResetCameraScreenSpace(0.8)
        viewers[axis].Render()


def render_3D(image_data, renderer, render_window):
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

        renderers.append(renderer)
        render_windows.append(render_window)
        interactors.append(interactor)

    return renderers, render_windows, interactors
