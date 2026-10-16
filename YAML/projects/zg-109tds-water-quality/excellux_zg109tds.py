"""Excellux / Gleco ZG-109TDS 7-in-1 water quality sensor (Tuya MCU, 0xEF00).

Probe temperature, EC, TDS, salinity, specific gravity, plus on-board air
temperature and humidity. Datapoint map taken from the Zigbee2MQTT converter
(zigbee-herdsman-converters, src/devices/tuya.ts, model "ZG-109TDS").

Drop into the ZHA custom quirks directory and restart Home Assistant.
"""

import zigpy.types as t
from zigpy.zcl import foundation

try:  # zhaquirks >= 2026.x: constants live behind the zhaquirks.builder facade
    from zhaquirks.builder import (
        CONCENTRATION_PARTS_PER_MILLION,
        PERCENTAGE,
        EntityPlatform,
        EntityType,
        SensorDeviceClass,
        SensorStateClass,
        UnitOfConductivity,
        UnitOfTemperature,
        UnitOfTime,
    )
except ImportError:  # older installs: constants still in zigpy
    from zigpy.quirks.v2.homeassistant import (
        CONCENTRATION_PARTS_PER_MILLION,
        PERCENTAGE,
        EntityPlatform,
        EntityType,
        UnitOfConductivity,
        UnitOfTemperature,
        UnitOfTime,
    )
    from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass

from zhaquirks.tuya import TuyaPowerConfigurationCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder

READ_ONLY = foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report


class WaterMode(t.enum8):
    """Measurement medium; changes the salinity/SG compensation."""

    Freshwater = 0x00
    Seawater = 0x01


class LowHighWarning(t.enum8):
    """Threshold state against the device-side v0/v1 limits."""

    Normal = 0x00
    Low = 0x01
    High = 0x02


class HighWarning(t.enum8):
    """TDS has only an upper threshold."""

    Normal = 0x00
    High = 0x01


(
    # Z2M fingerprint is modelID="Excellux", manufacturerName="DTS1XM9", i.e.
    # zigpy (manufacturer, model) = ("DTS1XM9", "Excellux"). If your unit reports
    # TS0601 / _TZE..., add an .applies_to() line with those values.
    TuyaQuirkBuilder("DTS1XM9", "Excellux")
    .friendly_name(manufacturer="Excellux", model="ZG-109TDS")
    # --- Primary measurements ------------------------------------------------
    # DP1: water probe temperature, 0.1 °C -> ZCL 0.01 °C
    .tuya_temperature(dp_id=1, scale=10)
    # DP4: battery %, ZCL wants half-percent; no battery metadata asserted
    .tuya_battery(dp_id=4, power_cfg=TuyaPowerConfigurationCluster)
    # DP127: EC in µS/cm, maps 1:1 onto the ZCL Electrical Conductivity cluster
    .tuya_electrical_conductivity(dp_id=127)
    .tuya_sensor(
        dp_id=124,
        attribute_name="tds",
        type=t.uint32_t,
        state_class=SensorStateClass.MEASUREMENT,
        unit=CONCENTRATION_PARTS_PER_MILLION,
        translation_key="tds",
        fallback_name="Total dissolved solids",
    )
    .tuya_sensor(
        dp_id=131,
        attribute_name="salinity",
        type=t.uint32_t,
        divisor=10,
        state_class=SensorStateClass.MEASUREMENT,
        unit="‰",
        translation_key="salinity",
        fallback_name="Salinity",
    )
    .tuya_sensor(
        dp_id=132,
        attribute_name="specific_gravity",
        type=t.uint32_t,
        divisor=1000,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="specific_gravity",
        fallback_name="Specific gravity",
    )
    # DP5 / DP118: on-board air temperature and humidity, both 0.01 units
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
    .tuya_humidity(dp_id=118, scale=1)
    # --- Device-side alarm states ---------------------------------------------
    .tuya_enum(
        dp_id=112,
        attribute_name="probe_temperature_warning",
        enum_class=LowHighWarning,
        access=READ_ONLY,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="probe_temperature_warning",
        fallback_name="Water temperature warning",
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
    .tuya_enum(
        dp_id=126,
        attribute_name="tds_warning",
        enum_class=HighWarning,
        access=READ_ONLY,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="tds_warning",
        fallback_name="TDS warning",
    )
    .tuya_enum(
        dp_id=130,
        attribute_name="ec_warning",
        enum_class=LowHighWarning,
        access=READ_ONLY,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="ec_warning",
        fallback_name="EC warning",
    )
    # --- Configuration ----------------------------------------------------------
    .tuya_enum(
        dp_id=133,
        attribute_name="water_mode",
        enum_class=WaterMode,
        translation_key="water_mode",
        fallback_name="Water mode",
    )
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
        fallback_name="Water temperature calibration",
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
        dp_id=125,
        attribute_name="tds_alarm_threshold",
        type=t.uint32_t,
        min_value=0,
        max_value=13000,
        step=1,
        unit=CONCENTRATION_PARTS_PER_MILLION,
        translation_key="tds_alarm_threshold",
        fallback_name="TDS alarm threshold",
    )
    # Low/high (v0/v1) alarm limits. Disabled by default: HA automations are the
    # better place for alerting; these only drive the device-side warning DPs.
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
        fallback_name="Water temperature limit 1",
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
        fallback_name="Water temperature limit 2",
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
    .tuya_number(
        dp_id=128,
        attribute_name="ec_v0",
        type=t.uint32_t,
        min_value=0,
        max_value=20000,
        step=1,
        unit=UnitOfConductivity.MICROSIEMENS_PER_CM,
        initially_disabled=True,
        translation_key="ec_v0",
        fallback_name="EC limit 1",
    )
    .tuya_number(
        dp_id=129,
        attribute_name="ec_v1",
        type=t.uint32_t,
        min_value=0,
        max_value=20000,
        step=1,
        unit=UnitOfConductivity.MICROSIEMENS_PER_CM,
        initially_disabled=True,
        translation_key="ec_v1",
        fallback_name="EC limit 2",
    )
    .tuya_enchantment()
    .skip_configuration()
    .add_to_registry()
)
