from time import monotonic
from typing import Dict, Tuple

# A Button repeats its packet every ~24 ms while held, and a short press sends a burst of
# 4 packets within ~70 ms (capture edisio-s4h.2). Packets closer together than this gap
# belong to the same physical press.
PRESS_GAP = 0.15


class PressFilter:
    """Collapses the repeated packets of one physical press into a single event."""

    def __init__(self) -> None:
        self._last_seen: Dict[Tuple[str, str, str], float] = {}

    def is_repeat(self, device_id: str, button: str, cmd: str) -> bool:
        key = (device_id, button, cmd)
        now = monotonic()
        previous = self._last_seen.get(key)
        self._last_seen[key] = now
        return previous is not None and now - previous < PRESS_GAP
