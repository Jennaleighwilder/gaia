"""GAIA Sirens — independent watchers, each owning one atmospheric element."""

from .base_siren import BaseSiren, SirenAudit, SirenResult
from .moisture_siren import MoistureSiren
from .pressure_siren import PressureSiren
from .rotation_siren import RotationSiren
from .lightning_siren import LightningSiren
from .column_siren import ColumnSiren
from .stream_siren import StreamSiren
from .soil_siren import SoilSiren
from .fire_siren import FireSiren

ALL_SIRENS = [
    MoistureSiren(),
    PressureSiren(),
    RotationSiren(),
    LightningSiren(),
    ColumnSiren(),
    StreamSiren(),
    SoilSiren(),
    FireSiren(),
]
