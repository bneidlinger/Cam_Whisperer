"""Integration catalog for VMS platforms.

This module normalizes the capabilities exposed by each VMS integration so the
app can enable the right tooling (discovery, snapshots, optimization controls)
per platform.
"""

from typing import Any, Dict, List

from integrations.genetec_client import GenetecClient
from integrations.hanwha_wave_client import HanwhaWAVEClient
from integrations.rhombus_client import RhombusClient
from integrations.verkada_client import VerkadaClient


def get_vms_integration_catalog() -> List[Dict[str, Any]]:
    """Return normalized integration profiles for all supported VMS platforms."""

    catalog: List[Dict[str, Any]] = [
        HanwhaWAVEClient.integration_profile(),
        VerkadaClient.integration_profile(),
        RhombusClient.integration_profile(),
    ]

    # Genetec remains gated behind DAP membership, but exposing the profile
    # keeps the UI experience consistent.
    catalog.append(GenetecClient.integration_profile())

    return catalog


__all__ = ["get_vms_integration_catalog"]
