import logging

from trame_dataclass.v2 import StateDataModel, Sync, get_instance
from trame_server import Server

from ....ui import VtkView
from ....utils import (
    DataArray,
    DataArrayType,
    MeshColoringMode,
    SceneObjectType,
    debounce,
    get_random_color,
    load_mesh,
)
from .scene_object_logic import SceneObject, SceneObjectLogic, TwoDColor

logger = logging.getLogger(__name__)


class ArrayColor(StateDataModel):
    name = Sync(str, "Grayscale")
    is_inverted = Sync(bool, False)
    array_range = Sync(list[float], list)


class MeshDisplay(StateDataModel):
    data_arrays = Sync(list[DataArray], list, has_dataclass=True)
    active_array_id = Sync(str)
    solid_color = Sync(str)
    array_color = Sync(ArrayColor, has_dataclass=True)
    opacity = Sync(float, 1.0)


class MeshObjectLogic(SceneObjectLogic):
    def __init__(self, server: Server, scene_object: SceneObject, views: list[VtkView]) -> None:
        super().__init__(server, scene_object, views)
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

        self.display.watch(("opacity",), self._update_opacity)
        self.display.watch(("active_array_id",), self._update_active_array)
        self.display.watch(("solid_color",), self._update_solid_coloring)
        self.display.array_color.watch(
            (
                "name",
                "is_inverted",
                "array_range",
            ),
            self._update_array_coloring,
        )

    @debounce(0.05)
    def _update_opacity(self, opacity: float) -> None:
        for view in self.views:
            view.set_mesh_opacity(self.scene_object._id, opacity)

    @debounce(0.05)
    def _update_solid_coloring(self, solid_color: str) -> None:
        hex = solid_color.lstrip("#")
        color_tuple = tuple(float(int(hex[i : i + 2], 16)) / 255.0 for i in (0, 2, 4))
        for view in self.views:
            view.set_mesh_solid_color(self.scene_object._id, color_tuple)

    @debounce(0.05)
    def _update_array_coloring(self, name: str, is_inverted: bool, scalar_range: list[float]) -> None:
        for view in self.views:
            view.set_mesh_array_color(
                self.scene_object._id,
                self.active_array,
                name,
                is_inverted,
                scalar_range,
            )

        # TODO handle invert

    @debounce(0.05)
    def _update_active_array(self, active_array_id: str) -> None:
        self.active_array = get_instance(active_array_id)
        assert isinstance(self.active_array, DataArray)
        if self.active_array.coloring_mode == MeshColoringMode.SOLID:
            self._update_solid_coloring(self.display.solid_color)

        elif self.active_array.coloring_mode == MeshColoringMode.ARRAY:
            self.display.array_color.array_range = self.active_array.array_min_max

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

    def load(self, file_path: str) -> None:
        self.object_data = load_mesh(file_path)

        self._populate_data_arrays()

        # TODO provide self.display to views to load proper configuration
        self.load_to_view()

        self.scene_object.gui.loading = False
