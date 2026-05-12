import json
import logging
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, TypeVar

from trame.assets.local import LocalFileManager
from trame_dataclass.v2 import FieldEncoder, ServerOnly, StateDataModel, Sync
from vtk import (
    vtkActor,
    vtkColorTransferFunction,
    vtkDataArray,
    vtkImageSlice,
    vtkPiecewiseFunction,
    vtkResliceImageViewer,
    vtkVolumeProperty,
)
from vtkmodules.vtkCommonCore import vtkLookupTable

from .resources import resources_path

logger = logging.getLogger(__name__)


class MeshColoringMode(Enum):
    SOLID = 0
    ARRAY = 1

    @staticmethod
    def encoder(object: Enum):
        return object.value

    @classmethod
    def decoder(cls, value: Any):
        return cls(value)


class VolumeColoringMode(Enum):
    PRESET = 0
    NORMALS = 1

    @staticmethod
    def encoder(object: Enum):
        return object.value

    @classmethod
    def decoder(cls, value: Any):
        return cls(value)


class DataArrayType(Enum):
    POINT = "point"
    CELL = "cell"
    UNDEFINED = None

    @staticmethod
    def encoder(object: Enum):
        return object.value

    @classmethod
    def decoder(cls, value: Any):
        return cls(value)


class DataArray(StateDataModel):
    title = Sync(str)
    data = ServerOnly(vtkDataArray | None, None)
    type = Sync(
        DataArrayType,
        DataArrayType.UNDEFINED,
        convert=FieldEncoder(DataArrayType.encoder, DataArrayType.decoder),
    )
    array_min_max = Sync(list[float])
    number_of_components = Sync(int, 0)
    coloring_mode = Sync(MeshColoringMode, convert=FieldEncoder(MeshColoringMode.encoder, MeshColoringMode.decoder))
    props = Sync(dict[str, str | int])

    def __init__(self, server, **kwargs):
        super().__init__(server, **kwargs)
        self.coloring_mode = MeshColoringMode.SOLID if self.number_of_components == 0 else MeshColoringMode.ARRAY
        self.props = {"number_of_components": self.number_of_components}


class Preset(StateDataModel):
    title = Sync(str)
    props = Sync(dict[str, str], {})


PresetColorPoints = list[tuple[float, float, float, float]]
PresetOpacityPoints = list[tuple[float, float]]
T = TypeVar("T")


@dataclass
class PresetInfo:
    name: str
    points: PresetColorPoints
    opacity_points: PresetOpacityPoints | None = None
    ambient: float | None = None
    diffuse: float | None = None
    specular: float | None = None
    specular_power: int | None = None
    shade: int | None = None
    interpolation: int | None = None


class PresetParser(ABC):
    def __init__(self, presets_file: Path, icons_folder: Path | None):
        self.presets: list[PresetInfo] = self.parse_slicer_presets(presets_file)
        self.icons_folder = icons_folder

    def get_preset_names(self) -> list[str]:
        return [preset.name for preset in self.presets]

    def get_preset_by_name(self, name: str) -> Preset | None:
        return next((p for p in self.presets if p.name == name), None)

    def get_presets_icons_url(self, icon_ext: str = ".png") -> list[tuple[str, str]]:
        if not self.icons_folder:
            return [(name, None) for name in self.get_preset_names()]
        presets = [(name, f"{name}{icon_ext}") for name in self.get_preset_names()]
        local_asset = LocalFileManager(self.icons_folder.resolve().as_posix())
        return [
            (
                preset_name,
                local_asset.url(preset_name, preset_icon_path)
                if self.icons_folder.joinpath(preset_icon_path).is_file()
                else None,
            )
            for preset_name, preset_icon_path in presets
        ]

    @abstractmethod
    def parse_slicer_presets(self, presets_file_path: Path) -> list[PresetInfo]:
        pass


class ColorPresetParser(PresetParser):
    def __init__(self, presets_file: Path, icons_folder: Path):
        super().__init__(presets_file, icons_folder)

    def _array_to_function(self, klass: type[T], add_method: str, xrgbs: PresetColorPoints, is_inverted: bool) -> T:
        transfer_function = klass()
        min_x = xrgbs[0][0]
        max_x = xrgbs[-1][0]
        points = []
        for x, r, g, b in xrgbs:
            scalar = max_x - (x - min_x) if is_inverted else x
            points.append((scalar, r, g, b))
        points.sort(key=lambda p: p[0])  # Ensure increasing order
        for scalar, r, g, b in points:
            getattr(transfer_function, add_method)(scalar, r, g, b)
        return transfer_function

    def _populate_lut_from_transfer_function(self, transfer_function: vtkColorTransferFunction, lut: vtkLookupTable):
        number_of_values = lut.GetNumberOfTableValues()
        for i in range(number_of_values):
            t = i / (number_of_values - 1)
            r, g, b = transfer_function.GetColor(t)
            lut.SetTableValue(i, r, g, b, 1.0)

    def parse_slicer_presets(self, presets_file_path: Path) -> list[PresetInfo]:
        with presets_file_path.open("r") as f:
            data = json.load(f)
        return [PresetInfo(d["name"], d["points"]) for d in data["colormaps"]]

    def apply_preset_to_slice(self, slice: vtkImageSlice, preset: PresetInfo, is_inverted: bool) -> bool:
        if slice.GetMapper().GetInput().GetPointData().GetNumberOfComponents() > 1:
            return False

        color_transfer_function = self._array_to_function(
            vtkColorTransferFunction, "AddRGBPoint", preset.points, is_inverted
        )
        lut = vtkLookupTable()
        lut.SetNumberOfTableValues(256)
        lut.Build()
        self._populate_lut_from_transfer_function(color_transfer_function, lut)
        slice.GetProperty().SetLookupTable(lut)
        return True

    def apply_preset_to_reslice(self, reslice: vtkResliceImageViewer, preset: PresetInfo, is_inverted: bool) -> bool:
        color_transfer_function = self._array_to_function(
            vtkColorTransferFunction, "AddRGBPoint", preset.points, is_inverted
        )
        lut = reslice.GetLookupTable()
        self._populate_lut_from_transfer_function(color_transfer_function, lut)
        return True

    def apply_preset_to_mesh(
        self,
        actor: vtkActor,
        data_array_obj: DataArray,
        preset: PresetInfo,
        preset_range: list[float],
        is_inverted: bool,
    ) -> bool:
        color_transfer_function = self._array_to_function(
            vtkColorTransferFunction, "AddRGBPoint", preset.points, is_inverted
        )
        mapper = actor.GetMapper()

        mapper.SelectColorArray(data_array_obj.title)
        mapper.SetColorModeToMapScalars()
        mapper.SetLookupTable(color_transfer_function)
        mapper.SetScalarVisibility(True)

        if not data_array_obj.data:
            logger.info(f"Array {data_array_obj.title} not found.")
            return False

        min_val = max(data_array_obj.array_min_max[0], preset_range[0])
        max_val = min(data_array_obj.array_min_max[1], preset_range[1])

        mapper.SetScalarRange(min_val, max_val)
        mapper.SetUseLookupTableScalarRange(True)

        return True


class VolumePresetParser(PresetParser):
    def __init__(self, presets_file: Path, icons_folder: Path):
        super().__init__(presets_file, icons_folder)

    def _array_to_function(
        self,
        klass: type[T],
        add_method: str,
        point_array: PresetColorPoints | PresetOpacityPoints,
        array_range: list[float],
        number_of_components: int,
    ) -> T:
        transfer_function = klass()
        if array_range is not None:
            orig_range = (point_array[0], point_array[-number_of_components])
            orig_size = orig_range[1] - orig_range[0]
            array_range_size = array_range[1] - array_range[0]
        for i in range(0, len(point_array), number_of_components):
            node = point_array[i : i + number_of_components]
            if array_range is not None:
                node[0] = array_range[0] + array_range_size * (node[0] - orig_range[0]) / orig_size
            getattr(transfer_function, add_method)(*node)
        return transfer_function

    def _same_arrays(
        self,
        array_1: PresetColorPoints | PresetOpacityPoints,
        array_2: PresetColorPoints | PresetOpacityPoints,
        number_of_components: int,
    ):
        array_1_size = array_1[0]
        array_2_size = array_2[0]
        if array_1_size != array_2_size:
            return False
        chunks1 = [
            lst[1:number_of_components] for lst in zip(*[iter(array_1[1:])] * number_of_components, strict=False)
        ]
        chunks2 = [
            lst[1:number_of_components] for lst in zip(*[iter(array_2[1:])] * number_of_components, strict=False)
        ]

        # Compare corresponding chunks
        return [c1 == c2 for c1, c2 in zip(chunks1, chunks2, strict=False)]

    def _string_to_array(self, string_of_numbers: str) -> PresetColorPoints | PresetOpacityPoints:
        point_array = list(map(float, string_of_numbers.split()))
        number_of_expected_values = point_array.pop(0)
        assert number_of_expected_values == len(point_array)
        return point_array

    def _array_to_color_transfer_function(self, xrgbs: PresetColorPoints, array_range: list[float, float]):
        return self._array_to_function(vtkColorTransferFunction, "AddRGBPoint", xrgbs, array_range, 4)

    def _array_to_opacity_function(self, opacity_points: PresetOpacityPoints, array_range: list[float, float]):
        return self._array_to_function(vtkPiecewiseFunction, "AddPoint", opacity_points, array_range, 2)

    def _opacity_function_to_array(self, opacity_function) -> PresetOpacityPoints:
        """
        :see-also array_to_opacity_function
        """
        size = opacity_function.GetSize()
        node = [0, 0, 0, 0]
        xrgbs = [2 * size]
        for i in range(size):
            opacity_function.GetNodeValue(i, node)
            xrgbs += node[0:2]
        return xrgbs

    def _color_transfer_function_to_array(self, color_transfer_function) -> PresetColorPoints:
        """
        :see-also array_to_color_transfer_function
        """
        size = color_transfer_function.GetSize()
        node = [0, 0, 0, 0, 0, 0]
        xrgbs = [4 * size]
        for i in range(size):
            color_transfer_function.GetNodeValue(i, node)
            xrgbs += node[0:4]
        return xrgbs

    def _has_preset(self, preset: PresetInfo, volume_property, range: list[float]):
        """
        Returns true if the volume_property already has the preset applied.
        """
        if range is not None and volume_property.GetRGBTransferFunction().GetRange() != range:
            return False
        colors = self._color_transfer_function_to_array(volume_property.GetRGBTransferFunction())
        if not self._same_arrays(colors, preset.points, 4):
            return False

        opacities = self._opacity_function_to_array(volume_property.GetScalarOpacity())
        return self._same_arrays(opacities, preset.opacity_points, 2)

    def parse_slicer_presets(self, presets_file_path: Path) -> list[PresetInfo]:
        tree = ET.parse(presets_file_path)
        root = tree.getroot()

        presets = []
        for vp in root.findall("VolumeProperty"):
            preset = {}
            for attr, value in vp.attrib.items():
                preset[attr] = value

            presets.append(preset)
        return [
            PresetInfo(
                name=preset.get("name"),
                points=self._string_to_array(preset.get("colorTransfer")),
                opacity_points=self._string_to_array(preset.get("scalarOpacity")),
                ambient=float(preset.get("ambient")) if preset.get("ambient") else None,
                diffuse=float(preset.get("diffuse")) if preset.get("diffuse") else None,
                specular=float(preset.get("specular")) if preset.get("specular") else None,
                specular_power=int(preset.get("specularPower")) if preset.get("specularPower") else None,
                shade=int(preset.get("shade")) if preset.get("shade") else None,
                interpolation=int(preset.get("interpolation")) if preset.get("interpolation") else None,
            )
            for preset in presets
        ]

    def apply_preset(self, volume_property: vtkVolumeProperty, preset: PresetInfo, array_range: list[float, float]):
        if self._has_preset(preset, volume_property, array_range):
            return False
        volume_property.SetColor(self._array_to_color_transfer_function(preset.points, array_range))
        volume_property.SetScalarOpacity(self._array_to_opacity_function(preset.opacity_points, array_range))
        if preset.ambient is not None:
            volume_property.SetAmbient(preset.ambient)
        if preset.diffuse is not None:
            volume_property.SetDiffuse(preset.diffuse)
        if preset.specular is not None:
            volume_property.SetSpecular(preset.specular)
        if preset.specular_power is not None:
            volume_property.SetSpecularPower(preset.specular_power)
        if preset.shade is not None:
            volume_property.SetShade(preset.shade)
        if preset.interpolation is not None:
            volume_property.SetInterpolationType(preset.interpolation)
        return True


def get_volume_preset_parser() -> VolumePresetParser:
    presets_file = resources_path() / "3d_presets.xml"
    presets_icons_folder = resources_path() / "presets_icons" / "3d"
    return VolumePresetParser(presets_file, presets_icons_folder)


def get_color_preset_parser() -> ColorPresetParser:
    presets_file = resources_path() / "2d_presets.json"
    presets_icons_folder = resources_path() / "presets_icons" / "2d"
    return ColorPresetParser(presets_file, presets_icons_folder)
