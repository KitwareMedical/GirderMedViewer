from trame_dataclass.v2 import StateDataModel, Sync, TypeValidation
from trame_server import Server
from vtk import vtkExtractPolyDataGeometry, vtkSphere

from ....utils import FilterType, SceneObjectSubtype
from ..objects.mesh_object_logic import MeshObjectLogic
from ..objects.scene_object_logic import SceneObject


class StreamlineFilterProperties(StateDataModel):
    radius = Sync(float, 10.0, type_checking=TypeValidation.SKIP)
    center = Sync(list[float], [0.0, 0.0, 0.0])


class StreamlineFilterLogic(MeshObjectLogic):
    def __init__(self, server: Server, scene_object: SceneObject, **kwargs) -> None:
        scene_object.filter_type = FilterType.STREAMLINE
        super().__init__(server, scene_object, **kwargs)

        self.scene_object.object_subtype = SceneObjectSubtype.STREAMLINE

        self.scene_object_filter = StreamlineFilterProperties(self.server)
        self.scene_object.filter_prop_id = self.scene_object_filter._id

        # Extract filter
        self.sphere = vtkSphere()
        self.sphere.SetRadius(self.scene_object_filter.radius)
        self.object_filter = vtkExtractPolyDataGeometry()
        self.object_filter.SetImplicitFunction(self.sphere)
        self.object_filter.ExtractInsideOn()
        self.object_filter.ExtractBoundaryCellsOn()

        self.scene_object_filter.watch(("center", "radius"), self._update_streamline_filter)

    def _update(self):
        self.object_filter.Update()
        self.updated()

    def _update_streamline_filter(self, center: list[float], radius: float) -> None:
        self.sphere.SetCenter(*center)
        self.sphere.SetRadius(radius)
        self._update()

    def load_object_data(self, file_path: str) -> None:
        super().load_object_data(file_path)
        self.object_filter.SetInputData(self.object_data)
        self._update()
        self.object_data = self.object_filter.GetOutput()
