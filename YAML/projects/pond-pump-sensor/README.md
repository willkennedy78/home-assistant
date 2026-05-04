# Pond Pump CCTV Vision Sensor

**CTRL+ALT+DELusions / @willkennedy78 — Use freely without attribution**

Monitors the garden pond fountain pump using AI vision analysis of the back garden
and summerhouse CCTV cameras. Creates a fault sensor that triggers when the pump
is switched on but no water flow is detected, and sends a notification alert.

---

## How it works

1. When `switch.pond_pump` turns **on**, Home Assistant triggers the analysis script
   30 seconds later (allowing the pump to prime).
2. Every 3 minutes while the pump is on, the script runs again.
3. The script captures snapshots from both cameras and sends them to Claude AI,
   which determines whether water is visibly flowing from the fountain.
4. The result is written back to `sensor.pond_pump_camera_analysis` via the HA REST API.
5. If the pump has been on for ≥5 minutes with no detected flow,
   `binary_sensor.pond_pump_fault` turns on and a notification is sent.

---

## Entities created

| Entity | Description |
|---|---|
| `sensor.pond_pump_camera_analysis` | Raw analysis result: `flowing`, `not_flowing`, `pump_off`, or `unknown` |
| `binary_sensor.pond_pump_water_flowing` | `on` when water flow is detected |
| `binary_sensor.pond_pump_fault` | `on` when pump is running but no flow detected |

---

## Prerequisites

- Anthropic API key (get one at https://console.anthropic.com)
- A Home Assistant long-lived access token
- Python 3 available on your HA host (standard on HA OS / Supervised)
- Both `camera.back_garden_mainstreamprofile` and `camera.summerhouse_mainstreamprofile`
  working and accessible

---

## Installation

### 1. Copy the script to your HA config directory

```bash
mkdir -p /config/scripts/pond_pump
cp scripts/analyse_pond_camera.py /config/scripts/pond_pump/
chmod +x /config/scripts/pond_pump/analyse_pond_camera.py
```

### 2. Create the credentials file

Create `/config/scripts/pond_pump/pond_pump.env`:

```
# Home Assistant URL (use localhost if script runs on the same machine)
HA_URL=http://localhost:8123

# Long-lived access token — create one in your HA profile under Security
HA_TOKEN=your_long_lived_token_here

# Anthropic API key
ANTHROPIC_API_KEY=sk-ant-your_key_here
```

> Keep this file private — do not commit it to version control.

### 3. Add the package to configuration.yaml

In your `configuration.yaml`, make sure packages are enabled. If not already present:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Then copy `packages/pond_pump_sensor.yaml` to your HA `packages/` directory:

```bash
cp packages/pond_pump_sensor.yaml /config/packages/
```

### 4. Set your notification target

Edit `/config/packages/pond_pump_sensor.yaml` and replace `notify.notify` in both
automation actions with your actual notification service, for example:

- `notify.mobile_app_your_phone` — HA Companion app
- `notify.alexa_media_echo` — Alexa via Alexa Media Player integration

### 5. Restart Home Assistant

After restarting, the entities will appear. You can test by switching the pump on
and watching `sensor.pond_pump_camera_analysis` update within ~45 seconds.

---

## Tuning

| Setting | Where | Default | Notes |
|---|---|---|---|
| Analysis frequency | `pond_pump_sensor.yaml` → periodic automation | Every 3 min | Adjust `minutes: /3` |
| Fault delay | `pond_pump_sensor.yaml` → fault alert automation | 5 min | Adjust `minutes: 5` |
| Pump startup wait | `pond_pump_sensor.yaml` → on-start automation | 30 s | Adjust `seconds: 30` |
| AI model | `analyse_pond_camera.py` → `CLAUDE_MODEL` | `claude-haiku-4-5-20251001` | Switch to `claude-sonnet-4-6` for better accuracy |
| Camera entities | `analyse_pond_camera.py` → `CAMERA_ENTITIES` | Back garden + Summerhouse | Add/remove cameras as needed |

---

## Cost estimate

Using `claude-haiku-4-5-20251001` with two camera images every 3 minutes:

- ~20 analysis calls per hour of pump runtime
- Approximately **£0.01–0.03 per hour** depending on image size
- A typical day with 8 hours pump runtime ≈ **£0.08–0.24/day**

Switch to `claude-haiku-4-5-20251001` (already default) for lowest cost.
Switch to `claude-sonnet-4-6` if detection accuracy needs improving.

---

## Troubleshooting

**`sensor.pond_pump_camera_analysis` stays `unknown`**
- Check `/config/scripts/pond_pump/pond_pump.log` for errors
- Verify `pond_pump.env` has correct credentials
- Confirm the script is executable: `chmod +x /config/scripts/pond_pump/analyse_pond_camera.py`

**Always shows `not_flowing` even when pump is working**
- Check that both cameras can serve snapshots — test with:
  `curl -H "Authorization: Bearer <TOKEN>" http://localhost:8123/api/camera_proxy/camera.back_garden_mainstreamprofile -o test.jpg`
- The fountain may not be clearly visible — adjust camera angle or switch to `claude-sonnet-4-6`

**Multiple runs overlapping**
- The script uses a lockfile at `/tmp/pond_pump_analysis.lock` to prevent this
- If the lock gets stuck after a crash: `rm /tmp/pond_pump_analysis.lock`
