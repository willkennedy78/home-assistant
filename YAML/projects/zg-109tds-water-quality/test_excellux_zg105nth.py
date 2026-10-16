"""Offline tests for the ZG-105NTH custom quirk.

Run from a zha-device-handlers checkout (uses its conftest fixtures):
    cp test_excellux_zg105nth.py <zha-device-handlers>/tests/
    QUIRK_PATH_NTH=/path/to/excellux_zg105nth.py pytest tests/test_excellux_zg105nth.py
"""

import importlib.util
import os
import pathlib
import struct
from unittest import mock

from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement

from tests.common import wait_for_zigpy_tasks
import zhaquirks
from zhaquirks.builder.device import QuirkV2Factory
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.mcu import TuyaMCUCluster

zhaquirks.setup()

QUIRK = os.environ.get(
    "QUIRK_PATH_NTH", str(pathlib.Path(__file__).with_name("excellux_zg105nth.py"))
)
_spec = importlib.util.spec_from_file_location("excellux_zg105nth", QUIRK)
quirk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(quirk)

TUYA_HDR = b"\x09\xe0\x02\x0b\x33"
WRITE_HDR_LEN = 5

# Real signature: EF00 is a client (output) cluster only.
REAL_CLUSTERS = {
    1: {
        PowerConfiguration.cluster_id: ClusterType.Server,
        TemperatureMeasurement.cluster_id: ClusterType.Server,
        RelativeHumidity.cluster_id: ClusterType.Server,
        TUYA_CLUSTER_ID: ClusterType.Client,
    }
}


def dp_value(dp: int, value: int) -> bytes:
    """Encode a Tuya VALUE (int32) datapoint."""
    return struct.pack(">BBHi", dp, 0x02, 4, value)


def dp_enum(dp: int, value: int) -> bytes:
    """Encode a Tuya ENUM datapoint."""
    return struct.pack(">BBHB", dp, 0x04, 1, value)


def handle(ep, *dps: bytes) -> foundation.Status:
    """Feed a Tuya get_data frame into the MCU cluster."""
    _, data = ep.tuya_manufacturer.deserialize(TUYA_HDR + b"".join(dps))
    return ep.tuya_manufacturer.handle_get_data(data.data)


def _device(factory, manuf="NTCHT01"):
    return factory(manuf, "Excellux", cluster_ids=REAL_CLUSTERS)


def test_mcu_cluster_added_as_server(zigpy_device_from_v2_quirk):
    """The output-only EF00 still gets a server-side MCU cluster to receive DPs."""
    ep = _device(zigpy_device_from_v2_quirk).endpoints[1]
    assert isinstance(ep.in_clusters[TUYA_CLUSTER_ID], TuyaMCUCluster)
    # native clusters are left alone
    assert type(ep.in_clusters[TemperatureMeasurement.cluster_id]) is (
        TemperatureMeasurement
    )


def test_whitelabels_match(zigpy_device_from_v2_quirk):
    """NTCHT02 / NTCHT03 resolve to the same quirk."""
    for manuf in ("NTCHT02", "NTCHT03"):
        ep = _device(zigpy_device_from_v2_quirk, manuf).endpoints[1]
        assert isinstance(ep.in_clusters[TUYA_CLUSTER_ID], TuyaMCUCluster)


def test_reports_decode(zigpy_device_from_v2_quirk):
    """Probe and air temperatures decode separately; duplicates are acknowledged."""
    ep = _device(zigpy_device_from_v2_quirk).endpoints[1]
    status = handle(
        ep,
        dp_value(1, 266),  # probe 26.6 °C
        dp_value(4, 74),  # battery (stored, no entity)
        dp_value(5, 2252),  # air 22.52 °C
        dp_value(118, 6622),  # humidity (stored, no entity)
        dp_enum(112, 2),  # probe high
        dp_value(101, 600),
        dp_value(108, -3),
    )
    assert status == foundation.Status.SUCCESS
    mcu = ep.tuya_manufacturer
    assert mcu.get("probe_temperature") == 266
    assert mcu.get("air_temperature") == 2252
    assert mcu.get("probe_temperature_warning") == quirk.LowHighWarning.High
    assert mcu.get("sampling_interval") == 600
    assert mcu.get("probe_temperature_calibration") == -3

    assert handle(ep, dp_value(1, -55)) == foundation.Status.SUCCESS
    assert mcu.get("probe_temperature") == -55


async def test_writes_encode(zigpy_device_from_v2_quirk):
    """Config writes go out as the correct DP and Tuya data type."""
    mcu = _device(zigpy_device_from_v2_quirk).endpoints[1].tuya_manufacturer
    cases = [
        ({"sampling_interval": 300}, dp_value(101, 300)),
        ({"probe_temperature_calibration": -15}, dp_value(108, -15)),
    ]
    with mock.patch.object(
        mcu.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as req:
        for attrs, expected in cases:
            await mcu.write_attributes(attrs)
            await wait_for_zigpy_tasks()
            assert req.call_args.kwargs["data"][WRITE_HDR_LEN:] == expected


def test_translation_keys_consistent():
    """No translation key clashes with any other loaded quirk (incl. ZG-109TDS)."""
    seen: dict[str, set[str]] = {}
    definitions = [
        e.zha_device_factory.quirk_definition
        for e in DEVICE_REGISTRY
        if isinstance(e.zha_device_factory, QuirkV2Factory)
    ]
    mine_loaded = [
        d
        for d in definitions
        if any(m.translation_key == "probe_temperature" for m in d.entity_metadata)
    ]
    assert mine_loaded, "ZG-105NTH quirk not in the live registry"
    for d in definitions:
        for m in d.entity_metadata:
            if m.translation_key and not m.translation_placeholders:
                seen.setdefault(m.translation_key, set()).add(m.fallback_name)
    clashes = {k: v for k, v in seen.items() if len(v) > 1}
    mine = {
        "probe_temperature",
        "air_temperature",
        "probe_temperature_warning",
        "probe_temperature_calibration",
        "probe_temperature_v0",
        "probe_temperature_v1",
        "water_temperature_warning",
        "water_temperature_calibration",
    }
    assert not (mine & clashes.keys()), clashes
