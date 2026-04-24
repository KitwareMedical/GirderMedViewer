from trame_dataclass.v2 import StateDataModel, Sync, TypeValidation
from undo_stack import Signal
from vtk import vtkExtractPolyDataGeometry, vtkSphere, vtkTubeFilter

from ....utils import FilterType, SceneObjectSubtype, get_aligned_poly_data, load_mesh
from ..objects.mesh_object_logic import MeshObjectLogic


class StreamlineFilterProperties(StateDataModel):
    thickness = Sync(float, 0.5, type_checking=TypeValidation.SKIP)
    radius = Sync(float, 10.0, type_checking=TypeValidation.SKIP)
    center = Sync(list[float], [0.0, 0.0, 0.0])


class StreamlineFilterLogic(MeshObjectLogic):
    filter_updated = Signal()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, filter_type=FilterType.STREAMLINE, **kwargs)
        self.scene_object.object_subtype = SceneObjectSubtype.STREAMLINE
        self.scene_object_filter = StreamlineFilterProperties(self.server)
        self.scene_object.filter_prop_id = self.scene_object_filter._id

        # Extract filter
        self.sphere = vtkSphere()
        self.sphere.SetRadius(self.scene_object_filter.radius)
        self.extract_filter = vtkExtractPolyDataGeometry()
        self.extract_filter.SetImplicitFunction(self.sphere)

        # Tube filter
        self.tube_filter = vtkTubeFilter()
        self.tube_filter.SetRadius(self.scene_object_filter.thickness)
        self.tube_filter.SetNumberOfSides(20)
        self.tube_filter.CappingOn()

        self.scene_object_filter.watch(("center", "radius", "thickness"), self._update_streamline_filter)

    def _update(self):
        self.tube_filter.Update()
        self.filter_updated()

    def _update_streamline_filter(self, center: list[float], radius: float, thickness: float) -> None:
        self.sphere.SetCenter(*center)
        self.sphere.SetRadius(radius)
        self.tube_filter.SetRadius(thickness)
        self._update()

    def align_data(self, center: tuple[float]) -> None:
        self.original_data = get_aligned_poly_data(self.original_data, center)
        self.scene_object_filter.center = list(center)

    def init_filter(self) -> None:
        self.extract_filter.SetInputData(self.original_data)
        self.extract_filter.ExtractInsideOn()
        self.extract_filter.ExtractBoundaryCellsOn()
        self.tube_filter.SetInputConnection(self.extract_filter.GetOutputPort())
        self._update()
        self.object_data = self.tube_filter.GetOutput()

    def load_object_data(self, file_path: str) -> None:
        self.original_data = load_mesh(file_path)
        self._populate_data_arrays(self.original_data)
