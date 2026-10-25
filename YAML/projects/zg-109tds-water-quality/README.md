# ZG-109TDS Water Quality Sensor — ZHA Custom Quirk

**CTRL+ALT+DELusions / @willkennedy78 — Use freely without attribution**

A quirks v2 definition for the Excellux / Gleco **ZG-109TDS** 7-in-1 water quality
probe (Tuya MCU, cluster `0xEF00`). Without it, ZHA pairs the device and shows
nothing useful, because every reading arrives as an opaque Tuya datapoint.

No upstream ZHA quirk exists as of zha-device-handlers `1d6598c` (Oct 2026). The
datapoint map comes from the Zigbee2MQTT converter, which has supported the
device for a while.

---

## Files

| File | Purpose |
|---|---|
| `excellux_zg109tds.py` | The quirk. Copy it into your custom quirks folder. |
| `test_excellux_zg109tds.py` | Offline tests: DP decoding, write encoding, translation-key clashes. |
| `excellux_zg105nth.py` | Companion quirk for the Excellux ZG-105NTH / ZG-106NTH / EZ-L01NTH probe thermometer (`NTCHT01/02/03`), used as a reference water-temperature probe. |
| `test_excellux_zg105nth.py` | Offline tests for the probe thermometer quirk, built on its real signature. |

---

## Install

1. **Check the signature first.** Go to *Settings → Devices → (the sensor) → Zigbee
   info*. The quirk matches **manufacturer `DTS1XM9`, model `Excellux`**, the
   fingerprint Z2M uses. If yours reports `TS0601` / `_TZE2xx_…`, add a line to
   the builder chain:

   ```python
   .applies_to("_TZE284_xxxxxxxx", "TS0601")
   ```

2. Enable custom quirks in `configuration.yaml`, if they aren't already on:

   ```yaml
   zha:
     custom_quirks_path: /config/custom_zha_quirks/
   ```

3. Copy `excellux_zg109tds.py` into `/config/custom_zha_quirks/`.
4. Restart Home Assistant. Reloading the ZHA integration is not enough, because
   quirks are only read at startup.
5. Confirm under *Zigbee info* that **Quirk** shows `excellux_zg109tds…`.
6. Wake the device by pressing its button so it reports. It's a sleepy end device,
   so the entities stay *unknown* until its first sampling cycle.

If it was paired before you added the quirk, a restart is normally enough. If any
entities stay missing, remove the device and re-pair it.

---

## Entities

**Enabled by default (15):**

| Entity | Source | Notes |
|---|---|---|
| Temperature | DP1 | **Water probe** temperature, on the standard temperature cluster |
| Battery | DP4 | |
| Electrical conductivity | DP127 | µS/cm, standard ZCL EC cluster |
| Humidity | DP118 | On-board air humidity |
| Total dissolved solids | DP124 | ppm |
| Salinity | DP131 | ‰ |
| Specific gravity | DP132 | Unitless, e.g. `1.001` |
| Air temperature | DP5 | On-board air temperature |
| Water temp / TDS / EC warning | DP112/126/130 | Diagnostic: `Normal` / `Low` / `High` |
| Water mode | DP133 | Select: `Freshwater` / `Seawater` |
| Sampling interval | DP101 | 5–1200 s |
| Water temperature calibration | DP108 | ±2 °C |
| TDS alarm threshold | DP125 | ppm |

**Disabled by default (12):** air temperature and humidity warnings, air and
humidity calibration, and every v0/v1 low/high limit. These only drive the
device's own warning datapoints. HA automations against the measurements are
the better place for alerting, since they're auditable and versioned and don't
sit in a battery-powered probe's NVRAM. Enable them if you want the device-side
flags anyway.

### Design decisions

- **The probe temperature takes the standard temperature cluster.** That makes
  `sensor.<device>_temperature` the water temperature, which is the reading you
  actually bought this for. The air temperature is the custom one.
- **Battery has no size/voltage asserted.** I couldn't verify the cell type, so
  it doesn't claim one rather than claim a wrong one. Percentage only.
- **No `ReportingConfig`.** Tuya MCU devices push datapoints. The device is a
  sleepy end device, so `skip_configuration()` avoids a futile bind/configure
  on join.

---

## Testing

The tests run offline against a zha-device-handlers checkout and its fixtures:

```bash
git clone --depth 1 https://github.com/zigpy/zha-device-handlers.git
cd zha-device-handlers && python -m venv .venv && .venv/bin/pip install -e . pytest pytest-asyncio
cp /path/to/test_excellux_zg109tds.py tests/
QUIRK_PATH=/path/to/excellux_zg109tds.py .venv/bin/pytest tests/test_excellux_zg109tds.py
```

They cover:
- Decoding of every measurement DP, including scale and negative temperatures.
- Write encoding for the value and enum types (DP 101, 108, 125, 133), checked byte for byte.
- The entity count, and that no translation key clashes with an existing upstream quirk.

**On-device checks (to do once it's paired):**
1. Cross-check the TDS/EC readings against a handheld meter in a known solution.
   A 1413 µS/cm calibration buffer is the standard.
2. Change *Sampling interval*, press the button, and confirm the cadence changes.
   This is the end-to-end test of the write path.
3. Toggle *Water mode* and check that salinity and SG shift as expected.

---

## Failure modes

| Symptom | Likely cause |
|---|---|
| Quirk not applied | Signature mismatch. Check the manufacturer/model, add `.applies_to()`. |
| Values 10× or 100× off | Firmware variant with a different scale. Adjust `scale`, `divisor` or `multiplier` for that DP. |
| EC entity missing | Older ZHA without the EC cluster entity. Swap it for a `tuya_sensor` on DP127. |
| Writes ignored | The device is asleep. Press the button within a few seconds of writing. |
| `ImportError` on load | Very old HA. The quirk falls back to `zigpy.quirks.v2.homeassistant` imports, but the v2 builder still needs HA ≥ 2024.x. |

---

## Companion: ZG-105NTH probe thermometer

The ZG-109TDS probe reads about 5 °C high (side by side with its own air sensor
indoors: +5.2 °C, steady over four hours). A second probe is used as a reference.

That device (`NTCHT01` / `Excellux`) advertises Tuya cluster `0xEF00` only as an
**output** cluster, so out of the box ZHA never receives its datapoints. It does
send native ZCL temperature and humidity reports, and which physical sensor
those come from isn't documented. The quirk therefore:

- adds a server-side Tuya MCU cluster so the datapoints arrive;
- exposes **Probe temperature** (DP1) and **Air temperature** (DP5) as separate
  sensors, and leaves the native temperature cluster untouched, so the two
  sources cannot overwrite each other;
- stores DP4 (battery) and DP118 (humidity) without entities, because they
  duplicate native reports, so frames are still acknowledged as `SUCCESS`.

Once it's live, compare the native temperature with DP1 and DP5. Whichever it
matches is the duplicate, and can be disabled in Home Assistant.

## Upstreaming

The quirk passes upstream's `ruff` config and the shared translation-key test,
so it's close to PR-ready for `zhaquirks/tuya/tuya_sensor.py`. Before that it
needs the try/except import shim removed, the test moved into
`tests/test_tuya_sensor.py`, and the device's real signature confirmed.
