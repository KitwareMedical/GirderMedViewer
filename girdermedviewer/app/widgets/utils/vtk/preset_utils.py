import json
import logging
import xml.etree.ElementTree as ET
from abc import abstractmethod
from pathlib import Path

from trame.assets.local import LocalFileManager
from trame_dataclass.v2 import StateDataModel, Sync
from vtk import (
    vtkActor,
    vtkColorTransferFunction,
    vtkPiecewiseFunction,
)

from .resources import resources_path

logger = logging.getLogger(__name__)


class Preset(StateDataModel):
    title = Sync(str)
    props = Sync(dict[str, str], {})


class PresetParser:
    def __init__(self, presets_file: Path, icons_folder: Path):
        self.presets = self.parse_slicer_presets(presets_file)
        self.icons_folder = icons_folder

    def get_preset_names(self):
        return [preset.get("name") for preset in self.presets]

    def get_preset_by_name(self, name: str):
        return next((p for p in self.presets if p.get("name") == name), None)

    def get_presets_icons_url(self, icon_ext: str = ".png") -> list[tuple[str, str]]:
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
    def parse_slicer_presets(self, presets_file_path: Path):
        pass


class ColorPresetParser(PresetParser):
    def __init__(self, presets_file: Path, icons_folder: Path):
        super().__init__(presets_file, icons_folder)

    def _array_to_function(self, xrgbs, klass, add_method):
        transfer_function = klass()
        for point in xrgbs:
            scalar, r, g, b = point
            getattr(transfer_function, add_method)(scalar, r, g, b)

        return transfer_function

    def parse_slicer_presets(self, presets_file_path: Path) -> list[dict[str, str]]:
        with presets_file_path.open("r") as f:
            data = json.load(f)
        return data["colormaps"]

    def apply_preset_to_volume(self, preset, object_property, is_inverted):
        color_transfer_function = self._array_to_function(preset.get("points"), vtkColorTransferFunction, "AddRGBPoint")
        lut = object_property.GetLookupTable()
        number_of_values = lut.GetNumberOfTableValues()
        for i in range(number_of_values):
            x = i / (number_of_values - 1)
            x = 1.0 - x if is_inverted else x
            r, g, b = color_transfer_function.GetColor(x)
            lut.SetTableValue(i, r, g, b, 1.0)
        return True

    def apply_preset_to_mesh_scalars(self, preset, actor: vtkActor):
        color_transfer_function = self._array_to_function(preset.get("points"), vtkColorTransferFunction, "AddRGBPoint")
        mapper = actor.GetMapper()
        polydata = mapper.GetInput()
        point_scalars = polydata.GetPointData().GetScalars()
        cell_scalars = polydata.GetCellData().GetScalars()

        if not point_scalars and not cell_scalars:
            return False

        mapper.SetScalarVisibility(True)
        mapper.SetScalarModeToUsePointData()

        mapper.SetLookupTable(color_transfer_function)
        if point_scalars:
            mapper.SetScalarRange(**point_scalars.GetRange())
        else:
            mapper.SetScalarRange(**cell_scalars.GetRange())

        mapper.Modified()
        return True

    def apply_preset_to_mesh_vectors(self, preset, actor: vtkActor):
        color_transfer_function = self._array_to_function(preset.get("points"), vtkColorTransferFunction, "AddRGBPoint")
        mapper = actor.GetMapper()
        polydata = mapper.GetInput()
        point_scalars = polydata.GetPointData().GetScalars()
        cell_scalars = polydata.GetCellData().GetScalars()

        if not point_scalars and not cell_scalars:
            return False

        mapper.SetScalarVisibility(True)
        mapper.SetScalarModeToUsePointData()

        mapper.SetLookupTable(color_transfer_function)
        if point_scalars:
            mapper.SetScalarRange(**point_scalars.GetRange())
        else:
            mapper.SetScalarRange(**cell_scalars.GetRange())

        mapper.Modified()
        return True


class VolumePresetParser(PresetParser):
    def __init__(self, presets_file: Path, icons_folder: Path):
        super().__init__(presets_file, icons_folder)

    def _same_arrays(self, array_1, array_2, number_of_components):
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

    def _string_to_array(self, string_of_numbers: str) -> list[float]:
        return list(map(float, string_of_numbers.split()))

    def _string_to_color_transfer_function(self, string_of_numbers, range=None):
        xrgbs = self._string_to_array(string_of_numbers)
        return self._array_to_color_transfer_function(xrgbs, range)

    def _array_to_color_transfer_function(self, xrgbs, range=None):
        return self._array_to_function(xrgbs, range, vtkColorTransferFunction, "AddRGBPoint", 4)

    def _array_to_function(self, xrgbs, array_range, klass, add_method, number_of_components):
        number_of_expected_values = xrgbs.pop(0)
        assert number_of_expected_values == len(xrgbs)
        transfer_function = klass()
        if array_range is not None:
            orig_range = (xrgbs[0], xrgbs[-number_of_components])
            orig_size = orig_range[1] - orig_range[0]
            array_range_size = array_range[1] - array_range[0]
        for i in range(0, len(xrgbs), number_of_components):
            node = xrgbs[i : i + number_of_components]
            if range is not None:
                node[0] = array_range[0] + array_range_size * (node[0] - orig_range[0]) / orig_size
            getattr(transfer_function, add_method)(*node)
        return transfer_function

    def _color_transfer_function_to_array(self, color_transfer_function):
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

    def _string_to_opacity_function(self, string_of_numbers, range=None):
        opacities = self._string_to_array(string_of_numbers)
        return self._array_to_opacity_function(opacities, range)

    def _array_to_opacity_function(self, opacities, range=None):
        return self._array_to_function(opacities, range, vtkPiecewiseFunction, "AddPoint", 2)

    def _opacity_function_to_array(self, opacity_function):
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

    def _has_preset(self, preset: dict[str, str], volume_property, range=None):
        """
        Returns true if the volume_property already has the preset applied.
        """
        if range is not None and volume_property.GetRGBTransferFunction().GetRange() != range:
            return False
        colors = self._color_transfer_function_to_array(volume_property.GetRGBTransferFunction())
        preset_colors = self._string_to_array(preset.get("colorTransfer"))
        if not self._same_arrays(colors, preset_colors, 4):
            return False

        opacities = self._opacity_function_to_array(volume_property.GetScalarOpacity())
        preset_opacities = self._string_to_array(preset.get("scalarOpacity"))
        return self._same_arrays(opacities, preset_opacities, 2)

    def parse_slicer_presets(self, presets_file_path: Path) -> list[dict[str, str]]:
        tree = ET.parse(presets_file_path)
        root = tree.getroot()

        presets = []
        for vp in root.findall("VolumeProperty"):
            preset = {}
            for attr, value in vp.attrib.items():
                preset[attr] = value

            presets.append(preset)

        return presets

    def apply_preset(
        self, preset: dict[str, str], volume_property, range: list[float, float] | tuple[float, float] | None = None
    ):
        if self._has_preset(preset, volume_property, range):
            return False
        color_transfer_function = self._string_to_color_transfer_function(preset.get("colorTransfer"), range)
        volume_property.SetColor(color_transfer_function)
        opacity_function = self._string_to_opacity_function(preset.get("scalarOpacity"), range)
        volume_property.SetScalarOpacity(opacity_function)
        if "ambient" in preset:
            volume_property.SetAmbient(float(preset.get("ambient")))
        if "diffuse" in preset:
            volume_property.SetDiffuse(float(preset.get("diffuse")))
        if "specular" in preset:
            volume_property.SetSpecular(float(preset.get("specular")))
        if "specularPower" in preset:
            volume_property.SetSpecularPower(float(preset.get("specularPower")))
        if "shade" in preset:
            volume_property.SetShade(int(preset.get("shade")))
        if "interpolation" in preset:
            volume_property.SetInterpolationType(int(preset.get("interpolation")))
        return True


def get_volume_preset_parser() -> VolumePresetParser:
    presets_file = resources_path() / "3d_presets.xml"
    presets_icons_folder = resources_path() / "presets_icons" / "3d"
    return VolumePresetParser(presets_file, presets_icons_folder)


def get_color_preset_parser() -> ColorPresetParser:
    presets_file = resources_path() / "2d_presets.json"
    presets_icons_folder = resources_path() / "presets_icons" / "2d"
    return ColorPresetParser(presets_file, presets_icons_folder)
