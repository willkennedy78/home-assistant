# Pond Pump CCTV Vision Sensor

**CTRL+ALT+DELusions / @willkennedy78 — Use freely without attribution**

Monitors the garden pond fountain pump using AI vision analysis of the back garden
and summerhouse CCTV cameras via the **LLMVision** HACS integration. Creates a
fault sensor that triggers when the pump is on but no water flow is detected, and
sends a notification alert.

---

## How it works

1. When `switch.pond_pump` turns **on**, analysis fires after 30 seconds (allows the pump to prime).
2. Every 3 minutes while the pump is on, a re-analysis runs.
3. The `script.pond_pump_analyse_cameras` script calls `llmvision.image_analyzer`
   with both camera entity IDs — LLMVision handles snapshotting and the AI call.
4. The script parses the response (`FLOWING` / `NOT_FLOWING`) and writes it to
   `input_text.pond_pump_camera_status`.
5. If the pump has been on for ≥ 5 minutes with no detected flow,
   `binary_sensor.pond_pump_fault` turns on and a notification fires.

---

## Entities created

| Entity | Description |
|---|---|
| `input_text.pond_pump_camera_status` | Latest analysis result: `flowing`, `not_flowing`, `pump_off`, or `unknown` |
| `binary_sensor.pond_pump_water_flowing` | `on` when water flow is detected |
| `binary_sensor.pond_pump_fault` | `on` when pump is running but no flow detected |

---

## Prerequisites

- [LLMVision](https://github.com/valentinfrlch/ha-llmvision) installed via HACS
- An AI provider configured in LLMVision (Anthropic, OpenAI, Google, or Ollama)
- Both `camera.back_garden_mainstreamprofile` and `camera.summerhouse_mainstreamprofile` working

---

## Installation

### 1. Install LLMVision via HACS

In Home Assistant → HACS → Integrations, search for **LLMVision** and install it.
Then go to Settings → Devices & Services → Add Integration → LLMVision and
configure your preferred AI provider and API key.

### 2. Add the package to configuration.yaml

Ensure packages are enabled in your `configuration.yaml`:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Copy `packages/pond_pump_sensor.yaml` to your HA `packages/` directory:

```bash
cp packages/pond_pump_sensor.yaml /config/packages/
```

### 3. Set your notification target

Edit `/config/packages/pond_pump_sensor.yaml` and replace `notify.notify` in
both alert automations with your actual notification service, for example:

- `notify.mobile_app_your_phone` — HA Companion app
- `notify.alexa_media_echo` — Alexa via Alexa Media Player integration

### 4. Restart Home Assistant

After restarting, the entities will appear. Test by switching the pump on and
watching `input_text.pond_pump_camera_status` update within ~45 seconds.

---

## Switching to Ollama (local model)

When you have Ollama running with a vision-capable model, update the script
action in `pond_pump_sensor.yaml`:

```yaml
- action: llmvision.image_analyzer
  data:
    provider: Ollama
    model: llava           # or moondream, llava-phi3, minicpm-v, etc.
    message: ...
```

Make sure the Ollama provider is configured in the LLMVision integration settings
and that your chosen model supports image input.

---

## Tuning

| Setting | Where | Default | Notes |
|---|---|---|---|
| AI provider | `pond_pump_sensor.yaml` → script `provider:` | `Anthropic` | See LLMVision docs for valid values |
| Model | `pond_pump_sensor.yaml` → script `model:` | `claude-haiku-4-5-20251001` | Any vision-capable model |
| Analysis frequency | Periodic automation `minutes: /3` | Every 3 min | Reduce for lower API usage |
| Fault delay | Fault alert automation `minutes: 5` | 5 min | Increase to reduce false alerts |
| Pump startup wait | On-start automation `seconds: 30` | 30 s | Increase if pump is slow to prime |
| Camera entities | Script `image_entity:` list | Back garden + Summerhouse | Add/remove cameras as needed |

---

## Troubleshooting

**`input_text.pond_pump_camera_status` stays `unknown`**
- Check that `script.pond_pump_analyse_cameras` ran — look in HA's logbook
- Verify LLMVision is configured with a working provider in Settings → Devices & Services
- Call the script manually: Developer Tools → Actions → `script.pond_pump_analyse_cameras`

**Always shows `not_flowing` even when pump is working**
- The fountain may not be clearly visible in the camera angle
- Try switching to `claude-sonnet-4-6` for better accuracy
- Check camera snapshots are working: Developer Tools → Actions → `camera.snapshot`

**Script runs are being skipped**
- `mode: single` + `max_exceeded: silent` prevents overlapping runs; this is expected
- If stuck, navigate to Developer Tools → States and check `script.pond_pump_analyse_cameras`
  is not showing `on` permanently (which would indicate a hung run)
