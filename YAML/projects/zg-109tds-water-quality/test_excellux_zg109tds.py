"""Offline tests for the ZG-109TDS custom quirk.

Run from a zha-device-handlers checkout (uses its conftest fixtures):
    cp test_excellux_zg109tds.py <zha-device-handlers>/tests/
    QUIRK_PATH=/path/to/excellux_zg109tds.py pytest tests/test_excellux_zg109tds.py
"""

import importlib.util
import os
import pathlib
import struct
from unittest import mock

from zha.quirks import DEVICE_REGISTRY
from zigpy.zcl import foundation

from tests.common import wait_for_zigpy_tasks
from tests.test_quirks_v2 import ALL_QUIRK_V2
import zhaquirks
from zhaquirks.builder.device import QuirkV2Factory
from zhaquirks.tuya.mcu import TuyaMCUCluster

zhaquirks.setup()

QUIRK = os.environ.get(
    "QUIRK_PATH", str(pathlib.Path(__file__).with_name("excellux_zg109tds.py"))
)
_spec = importlib.util.spec_from_file_location("excellux_zg109tds", QUIRK)
quirk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(quirk)


MANUF, MODEL = "DTS1XM9", "Excellux"
TUYA_HDR = b"\x09\xe0\x02\x0b\x33"  # ZCL hdr + Tuya status/seq
WRITE_HDR_LEN = 5


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


def _definition():
    entries = [
        e.zha_device_factory.quirk_definition
        for e in DEVICE_REGISTRY
        if isinstance(e.zha_device_factory, QuirkV2Factory)
        and any(m.manufacturer == MANUF for m in e.device_match.applies_to)
    ]
    assert len(entries) == 1
    return entries[0]


def test_reports_decode(zigpy_device_from_v2_quirk):
    """Every measurement DP lands on the right attribute with the right scale."""
    ep = zigpy_device_from_v2_quirk(MANUF, MODEL).endpoints[1]
    assert isinstance(ep.tuya_manufacturer, TuyaMCUCluster)

    status = handle(
        ep,
        dp_value(1, 183),  # probe 18.3 °C
        dp_value(4, 87),  # battery 87 %
        dp_value(5, 2154),  # air 21.54 °C
        dp_value(118, 6123),  # RH 61.23 %
        dp_value(124, 312),  # TDS 312 ppm
        dp_value(127, 624),  # EC 624 µS/cm
        dp_value(131, 3),  # salinity 0.3 ‰
        dp_value(132, 1001),  # SG 1.001
        dp_enum(126, 1),  # TDS high
        dp_enum(133, 1),  # seawater
        dp_value(108, -5),  # probe calibration -0.5 °C
        dp_value(101, 300),  # sampling 300 s
    )
    assert status == foundation.Status.SUCCESS

    mcu = ep.tuya_manufacturer
    assert ep.temperature.get("measured_value") == 1830
    assert ep.power.get("battery_percentage_remaining") == 174
    assert ep.humidity.get("measured_value") == 6123
    assert ep.electrical_conductivity.get("measured_value") == 624
    assert mcu.get("air_temperature") == 2154
    assert mcu.get("tds") == 312
    assert mcu.get("salinity") == 3
    assert mcu.get("specific_gravity") == 1001
    assert mcu.get("tds_warning") == quirk.HighWarning.High
    assert mcu.get("water_mode") == quirk.WaterMode.Seawater
    assert mcu.get("probe_temperature_calibration") == -5
    assert mcu.get("sampling_interval") == 300

    assert handle(ep, dp_value(1, -21)) == foundation.Status.SUCCESS
    assert ep.temperature.get("measured_value") == -210


async def test_writes_encode(zigpy_device_from_v2_quirk):
    """Config writes go out as the correct DP and Tuya data type."""
    mcu = zigpy_device_from_v2_quirk(MANUF, MODEL).endpoints[1].tuya_manufacturer
    cases = [
        ({"sampling_interval": 600}, dp_value(101, 600)),
        ({"water_mode": quirk.WaterMode.Freshwater}, dp_enum(133, 0)),
        ({"probe_temperature_calibration": -12}, dp_value(108, -12)),
        ({"tds_alarm_threshold": 500}, dp_value(125, 500)),
    ]
    with mock.patch.object(
        mcu.endpoint, "request", return_value=foundation.Status.SUCCESS
    ) as req:
        for attrs, expected in cases:
            await mcu.write_attributes(attrs)
            await wait_for_zigpy_tasks()
            assert req.call_args.kwargs["data"][WRITE_HDR_LEN:] == expected


def test_entities_and_translation_keys():
    """Entity set is as designed and no translation key clashes upstream."""
    definition = _definition()
    metadata = definition.entity_metadata
    assert len(metadata) == 23
    assert sum(not m.initially_disabled for m in metadata) == 11

    upstream: dict[str, set[str]] = {}
    for _, other in ALL_QUIRK_V2:
        for m in other.entity_metadata:
            if m.translation_key and not m.translation_placeholders:
                upstream.setdefault(m.translation_key, set()).add(m.fallback_name)
    for m in metadata:
        names = upstream.get(m.translation_key, set())
        assert names <= {m.fallback_name}, (m.translation_key, names)
