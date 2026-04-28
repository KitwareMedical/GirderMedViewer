import logging

from trame_dataclass.v2 import StateDataModel, Sync

from ....utils import (
    DataArray,
    DataArrayType,
    SceneObjectType,
    get_random_color,
    load_mesh,
)
from .scene_object_logic import SceneObjectDisplay, SceneObjectLogic, TwoDColor

logger = logging.getLogger(__name__)


class ArrayColor(StateDataModel):
    name = Sync(str, "Grayscale")
    is_inverted = Sync(bool, False)
    array_range = Sync(list[float], list)


class MeshDisplay(SceneObjectDisplay):
    data_arrays = Sync(list[DataArray], list, has_dataclass=True)
    active_array_id = Sync(str)
    solid_color = Sync(str)
    array_color = Sync(ArrayColor, has_dataclass=True)


class MeshObjectLogic(SceneObjectLogic):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.scene_object.object_type = SceneObjectType.MESH
        self.active_array = DataArray(self.server, title="Solid color")
        self.display = MeshDisplay(
            self.server,
            data_arrays=[self.active_array],
            active_array_id=self.active_array._id,
            solid_color=get_random_color(),
            color_preset=TwoDColor(self.server),
            array_color=ArrayColor(self.server),
        )
        self.scene_object.display = self.display._id
        self.scene_object.flush()

    def load_object_data(self, file_path: str) -> None:
        self.object_data = load_mesh(file_path)
        self._populate_data_arrays()

    def _create_data_array(self, arr, arr_type: DataArrayType) -> DataArray:
        n_components = arr.GetNumberOfComponents()
        if n_components == 1:
            array_min_max = list(arr.GetRange(0))  # Scalar range
        else:
            array_min_max = list(arr.GetRange(-1))  # Magnitude range
        return DataArray(
            self.server,
            title=arr.GetName(),
            data=arr,
            type=arr_type,
            number_of_components=n_components,
            array_min_max=array_min_max,
        )

    def _populate_data_arrays(self) -> None:
        data_arrays = []
        point_data = self.object_data.GetPointData()
        for i in range(point_data.GetNumberOfArrays()):
            arr = point_data.GetArray(i)
            data_arrays.append(self._create_data_array(arr, DataArrayType.POINT))

        cell_data = self.object_data.GetCellData()
        for i in range(cell_data.GetNumberOfArrays()):
            arr = cell_data.GetArray(i)
            data_arrays.append(self._create_data_array(arr, DataArrayType.CELL))

        self.display.data_arrays = [*self.display.data_arrays, *data_arrays]
