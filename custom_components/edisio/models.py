"""The Device model table: what each kind of Device is called and what it reports."""
from dataclasses import dataclass
from typing import Any, Dict

CONF_DEVICE_MODEL = "device_model"


@dataclass(frozen=True)
class DeviceModel:
    key: str  # stored per Device in the options
    model_code: str  # the Model code the Device sends in every packet
    product_name: str  # the model shown in the HA device registry
    default_name_prefix: str  # default Device name is "<prefix> <Radio ID>"
    has_buttons: bool  # reports Button presses (events and Button sensors)
    has_opening: bool  # reports Open/Closed


WALL_PLATE = DeviceModel("wall_plate", "01", "EBP8", "Edisio EBP8-B", has_buttons=True, has_opening=False)
OPENING_SENSOR = DeviceModel(
    "opening_sensor", "09", "Opening sensor", "Edisio Opening sensor", has_buttons=False, has_opening=True
)

DEVICE_MODELS: Dict[str, DeviceModel] = {m.key: m for m in (WALL_PLATE, OPENING_SENSOR)}


def device_model(device_cfg: Dict[str, Any]) -> DeviceModel:
    """The Device model stored for a Device; a Device with none stored is a Wall plate."""
    return DEVICE_MODELS.get(device_cfg.get(CONF_DEVICE_MODEL), WALL_PLATE)
