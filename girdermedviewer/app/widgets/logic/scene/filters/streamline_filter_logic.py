from trame_dataclass.v2 import StateDataModel, Sync, TypeValidation
from undo_stack import Signal
from vtk import vtkExtractPolyDataGeometry, vtkSphere

from ....utils import FilterType, get_aligned_poly_data, load_mesh
from ..objects.mesh_object_logic import MeshObjectLogic


class StreamlineFilterProperties(StateDataModel):
    density = Sync(float, 0.5)
    radius = Sync(float, 1.0, type_checking=TypeValidation.SKIP)
    center = Sync(list[float], [0.0, 0.0, 0.0])


class StreamlineFilterLogic(MeshObjectLogic):
    filter_updated = Signal()

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, filter_type=FilterType.STREAMLINE, **kwargs)
        self.scene_object_filter = StreamlineFilterProperties(self.server)
        self.scene_object.filter_prop_id = self.scene_object_filter._id
        self.sphere = vtkSphere()
        self.object_filter = vtkExtractPolyDataGeometry()
        self.object_filter.SetImplicitFunction(self.sphere)

        self.scene_object_filter.watch(("center", "radius"), self._update_sphere)

    def _update(self):
        self.object_filter.Update()
        self.filter_updated()

    def _update_sphere(self, center: list[float], radius: float) -> None:
        self.sphere.SetCenter(*center)
        self.sphere.SetRadius(radius)
        self._update()

    def align_data(self, center: tuple[float]) -> None:
        self.original_data = get_aligned_poly_data(self.original_data, center)
        self.scene_object_filter.center = list(center)

    def init_filter(self) -> None:
        self.object_filter.SetInputData(self.original_data)
        self.object_filter.ExtractInsideOn()
        self.object_filter.ExtractBoundaryCellsOn()
        self.object_filter.Update()
        self.object_data = self.object_filter.GetOutput()

    def load_object_data(self, file_path: str) -> None:
        self.original_data = load_mesh(file_path)
        self._populate_data_arrays(self.original_data)
