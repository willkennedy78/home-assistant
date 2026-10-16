"""Excellux ZG-105NTH / ZG-106NTH / EZ-L01NTH probe thermometer (Tuya MCU).

External NTC probe plus on-board air temperature and humidity. Datapoint map
taken from the Zigbee2MQTT converter (zigbee-herdsman-converters,
src/devices/tuya.ts, model "ZG-105NTH").

The device advertises 0xEF00 as a client (output) cluster only, so without a
quirk ZHA never sees the Tuya datapoints, including the probe. It also sends
native ZCL temperature/humidity reports; those are left untouched and the
probe and air temperatures are exposed as separate, explicitly named sensors
so the two sources cannot overwrite each other.

Drop into the ZHA custom quirks directory and restart Home Assistant.
"""

import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.builder import (
    PERCENTAGE,
    EntityPlatform,
    EntityType,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder

READ_ONLY = foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report


class LowHighWarning(t.enum8):
    """Threshold state against the device-side v0/v1 limits."""

    Normal = 0x00
    Low = 0x01
    High = 0x02


(
    # Basic cluster reports manufacturer="NTCHT01", model="Excellux" (confirmed
    # on a real unit, Oct 2026). NTCHT02 = ZG-106NTH, NTCHT03 = EZ-L01NTH (LCD).
    TuyaQuirkBuilder("NTCHT01", "Excellux")
    .applies_to("NTCHT02", "Excellux")
    .applies_to("NTCHT03", "Excellux")
    .friendly_name(manufacturer="Excellux", model="ZG-105NTH")
    # --- Measurements -------------------------------------------------------
    .tuya_sensor(
        dp_id=1,
        attribute_name="probe_temperature",
        type=t.int32s,
        divisor=10,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="probe_temperature",
        fallback_name="Probe temperature",
    )
    .tuya_sensor(
        dp_id=5,
        attribute_name="air_temperature",
        type=t.int32s,
        divisor=100,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="air_temperature",
        fallback_name="Air temperature",
    )
    # --- Device-side alarm states -------------------------------------------
    .tuya_enum(
        dp_id=112,
        attribute_name="probe_temperature_warning",
        enum_class=LowHighWarning,
        access=READ_ONLY,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="probe_temperature_warning",
        fallback_name="Probe temperature warning",
    )
    .tuya_enum(
        dp_id=117,
        attribute_name="temperature_warning",
        enum_class=LowHighWarning,
        access=READ_ONLY,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="air_temperature_warning",
        fallback_name="Air temperature warning",
    )
    .tuya_enum(
        dp_id=122,
        attribute_name="humidity_warning",
        enum_class=LowHighWarning,
        access=READ_ONLY,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        translation_key="humidity_warning",
        fallback_name="Humidity warning",
    )
    # --- Configuration ------------------------------------------------------
    .tuya_number(
        dp_id=101,
        attribute_name="sampling_interval",
        type=t.uint32_t,
        min_value=5,
        max_value=1200,
        step=5,
        unit=UnitOfTime.SECONDS,
        translation_key="sampling_interval",
        fallback_name="Sampling interval",
    )
    .tuya_number(
        dp_id=108,
        attribute_name="probe_temperature_calibration",
        type=t.int32s,
        min_value=-2,
        max_value=2,
        step=0.1,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="probe_temperature_calibration",
        fallback_name="Probe temperature calibration",
    )
    .tuya_number(
        dp_id=114,
        attribute_name="temperature_calibration",
        type=t.int32s,
        min_value=-2,
        max_value=2,
        step=0.01,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        initially_disabled=True,
        translation_key="air_temperature_calibration",
        fallback_name="Air temperature calibration",
    )
    .tuya_number(
        dp_id=119,
        attribute_name="humidity_calibration",
        type=t.int32s,
        min_value=-10,
        max_value=10,
        step=0.01,
        multiplier=0.01,
        unit=PERCENTAGE,
        initially_disabled=True,
        translation_key="humidity_calibration",
        fallback_name="Humidity calibration",
    )
    .tuya_number(
        dp_id=109,
        attribute_name="probe_temperature_v0",
        type=t.int32s,
        min_value=-40,
        max_value=125,
        step=0.1,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        initially_disabled=True,
        translation_key="probe_temperature_v0",
        fallback_name="Probe temperature limit 1",
    )
    .tuya_number(
        dp_id=110,
        attribute_name="probe_temperature_v1",
        type=t.int32s,
        min_value=-40,
        max_value=125,
        step=0.1,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        initially_disabled=True,
        translation_key="probe_temperature_v1",
        fallback_name="Probe temperature limit 2",
    )
    .tuya_number(
        dp_id=115,
        attribute_name="temperature_v0",
        type=t.int32s,
        min_value=-40,
        max_value=85,
        step=0.01,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        initially_disabled=True,
        translation_key="air_temperature_v0",
        fallback_name="Air temperature limit 1",
    )
    .tuya_number(
        dp_id=116,
        attribute_name="temperature_v1",
        type=t.int32s,
        min_value=-40,
        max_value=85,
        step=0.01,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        initially_disabled=True,
        translation_key="air_temperature_v1",
        fallback_name="Air temperature limit 2",
    )
    .tuya_number(
        dp_id=120,
        attribute_name="humidity_v0",
        type=t.int32s,
        min_value=0,
        max_value=100,
        step=0.01,
        multiplier=0.01,
        unit=PERCENTAGE,
        initially_disabled=True,
        translation_key="humidity_v0",
        fallback_name="Humidity limit 1",
    )
    .tuya_number(
        dp_id=121,
        attribute_name="humidity_v1",
        type=t.int32s,
        min_value=0,
        max_value=100,
        step=0.01,
        multiplier=0.01,
        unit=PERCENTAGE,
        initially_disabled=True,
        translation_key="humidity_v1",
        fallback_name="Humidity limit 2",
    )
    # DP4 (battery) and DP118 (humidity) duplicate the native PowerConfiguration
    # and RelativeHumidity reports. Store them without entities so frames that
    # carry them are still acknowledged as SUCCESS.
    .tuya_dp_attribute(dp_id=4, attribute_name="tuya_battery", type=t.uint32_t)
    .tuya_dp_attribute(dp_id=118, attribute_name="tuya_humidity", type=t.uint32_t)
    .tuya_enchantment()
    .skip_configuration()
    .add_to_registry()
)
