from dataclasses import dataclass, field


@dataclass
class SceneState:
    scene_id: str | None = None
    active_primary_volume_id: str | None = None
    primary_volume_ids: list[str] = field(default_factory=list)
