"""
Start Nyx MetabolicDaemon alongside GAIA — continuous gather → process → birth loop.

Liminal state persists under <project>/runs/nyx_liminal/ (not /tmp) so restarts
can germinate from spore and continue the lineage.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


def start_metabolic_daemon(
    root: Path,
    *,
    cache: Any | None = None,
    background: bool = True,
) -> Optional[Any]:
    """
    Attach the bacterial-metabolism loop to optional GAIADataCache (weather/fire/seismic).

    If background=True (default), starts a daemon thread — use from gaia_daemon.
    If background=False, returns the instance only; caller should run_forever() on the main thread.

    Returns the MetabolicDaemon instance on success, or None if Nyx is unavailable.
    """
    liminal = root / "runs" / "nyx_liminal"
    liminal.mkdir(parents=True, exist_ok=True)

    try:
        from nyx.metabolism import MetabolicDaemon

        daemon = MetabolicDaemon(liminal_path=str(liminal))
        daemon.register_gaia_sources(cache=cache)
        if background:
            daemon.start_background()
        logger.info(
            "Nyx MetabolicDaemon %s (liminal=%s, cache=%s)",
            "started in background" if background else "ready (foreground)",
            liminal,
            "live" if cache is not None else "standalone APIs",
        )
        return daemon
    except Exception as e:
        logger.warning("Nyx metabolism not available (non-critical): %s", e)
        return None
