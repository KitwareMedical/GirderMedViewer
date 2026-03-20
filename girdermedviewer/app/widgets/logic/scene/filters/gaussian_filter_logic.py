from trame_dataclass.v2 import StateDataModel, Sync, TypeValidation

from ....utils import create_gaussian_filter
from ..objects.volume_object_logic import VolumeObjectLogic


class GaussianFilterProperties(StateDataModel):
    sigma = Sync(float, 1.0, type_checking=TypeValidation.SKIP)


class GaussianFilterLogic(VolumeObjectLogic):
    def __init__(
        self,
        original_logic: VolumeObjectLogic,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.scene_object_filter = GaussianFilterProperties(self.server)
        self.scene_object.filter_prop_id = self.scene_object_filter._id
        self.soft_input_id = original_logic._id
        self.object_filter = create_gaussian_filter(original_logic.object_data)
        self._load_object_data()

        self.scene_object_filter.watch(("sigma",), self._update_sigma, eager=True)

    def update(self):
        self.object_filter.Update()
        self.updated()

    def _load_object_data(self):
        self.object_filter.Update()
        self.object_data = self.object_filter.GetOutput()
        self._init_display_properties()

    def _update_sigma(self, sigma: int) -> None:
        self.object_filter.SetStandardDeviation(sigma)
        self.update()
