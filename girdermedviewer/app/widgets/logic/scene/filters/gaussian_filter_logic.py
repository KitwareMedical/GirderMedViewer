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
        self.original_logic = original_logic
        self.object_filter = create_gaussian_filter(original_logic.object_data)
        self._load_object_data()

        self.scene_object_filter.watch(("sigma",), self._update_sigma, eager=True)

    def update(self):
        self.object_filter.Update()
        for view in self.views:
            view.update()

    def _load_object_data(self):
        self.object_data = self.object_filter.GetOutput()
        self.object_filter.Update()

    def _update_sigma(self, sigma: int) -> None:
        self.object_filter.SetStandardDeviation(sigma)
        self.update()
