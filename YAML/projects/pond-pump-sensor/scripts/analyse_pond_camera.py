#!/usr/bin/env python3
"""
Pond Pump CCTV Vision Analyser - CTRL+ALT+DELusions / @willkennedy78
Use freely without attribution

Captures images from the back garden and summerhouse CCTV cameras,
sends them to Claude AI for vision analysis, and updates Home Assistant
entities with the result. Designed to be run as a background process
triggered by a Home Assistant shell_command.

Setup: copy this file and pond_pump.env to /config/scripts/pond_pump/ on your HA instance.
"""

import os
import sys
import json
import base64
import urllib.request
import urllib.error
import fcntl
import datetime

# ── Config ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(SCRIPT_DIR, 'pond_pump.env')
LOCK_FILE = '/tmp/pond_pump_analysis.lock'

PUMP_ENTITY = 'switch.pond_pump'
STATUS_ENTITY = 'sensor.pond_pump_camera_analysis'
CAMERA_ENTITIES = [
    'camera.back_garden_mainstreamprofile',
    'camera.summerhouse_mainstreamprofile',
]

CLAUDE_MODEL = 'claude-haiku-4-5-20251001'
CLAUDE_MAX_TOKENS = 10

VISION_PROMPT = (
    "These are CCTV camera images of a garden pond with a fountain pump. "
    "Determine if water is actively flowing or spraying from the fountain pump head. "
    "Look for: water jets, spray arcs, or visible turbulent water movement from the pump outlet. "
    "Ignore the static surface of the pond water itself — only active flow from the fountain counts. "
    "Reply with exactly one word: FLOWING if water is visibly coming from the fountain, "
    "or NOT_FLOWING if no active water flow is visible from the fountain. No other text."
)

# ── Helpers ─────────────────────────────────────────────────────────────────────

def load_env(path):
    env = {}
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, val = line.partition('=')
                    env[key.strip()] = val.strip().strip('"\'')
    except FileNotFoundError:
        pass
    return env


def ha_request(url, token, path, method='GET', data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(
        f"{url}/api/{path}",
        data=body,
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read()


def get_pump_state(ha_url, token):
    try:
        raw = ha_request(ha_url, token, f'states/{PUMP_ENTITY}')
        return json.loads(raw).get('state', 'unknown')
    except Exception as exc:
        log(f"pump state error: {exc}")
        return 'unknown'


def fetch_camera_b64(ha_url, token, entity_id):
    try:
        data = ha_request(ha_url, token, f'camera_proxy/{entity_id}')
        if data and len(data) > 1000:
            return base64.b64encode(data).decode()
    except Exception as exc:
        log(f"camera {entity_id} error: {exc}")
    return None


def call_claude(images_b64, api_key):
    content = [
        {
            'type': 'image',
            'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': img},
        }
        for img in images_b64
        if img
    ]
    if not content:
        return 'unknown'

    content.append({'type': 'text', 'text': VISION_PROMPT})

    body = json.dumps({
        'model': CLAUDE_MODEL,
        'max_tokens': CLAUDE_MAX_TOKENS,
        'messages': [{'role': 'user', 'content': content}],
    }).encode()

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=body,
        headers={
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
        },
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
        text = result['content'][0]['text'].strip().upper()
        if 'NOT_FLOWING' in text or 'NOT FLOWING' in text:
            return 'not_flowing'
        if 'FLOWING' in text:
            return 'flowing'
        return 'unknown'


def update_ha_status(ha_url, token, status):
    ha_request(ha_url, token, f'states/{STATUS_ENTITY}', method='POST', data={
        'state': status,
        'attributes': {
            'friendly_name': 'Pond Pump Camera Analysis',
            'icon': 'mdi:cctv',
            'last_analysed': datetime.datetime.now().isoformat(timespec='seconds'),
        },
    })


def log(msg):
    ts = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{ts}] {msg}", file=sys.stderr)


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    env = {**load_env(ENV_FILE), **{k: v for k, v in os.environ.items()
                                     if k in ('HA_URL', 'HA_TOKEN', 'ANTHROPIC_API_KEY')}}

    ha_url = env.get('HA_URL', 'http://localhost:8123').rstrip('/')
    ha_token = env.get('HA_TOKEN', '')
    api_key = env.get('ANTHROPIC_API_KEY', '')

    if not ha_token or not api_key:
        log("ERROR: HA_TOKEN and ANTHROPIC_API_KEY must be set in pond_pump.env")
        sys.exit(1)

    # Prevent concurrent runs
    lock_fh = open(LOCK_FILE, 'w')
    try:
        fcntl.flock(lock_fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log("Another analysis is already running — skipping")
        lock_fh.close()
        return

    try:
        pump_state = get_pump_state(ha_url, ha_token)
        log(f"Pump state: {pump_state}")

        if pump_state != 'on':
            update_ha_status(ha_url, ha_token, 'pump_off')
            log("Pump is off — no analysis needed")
            return

        images = [fetch_camera_b64(ha_url, ha_token, cam) for cam in CAMERA_ENTITIES]
        available = [img for img in images if img]
        log(f"Fetched {len(available)}/{len(CAMERA_ENTITIES)} camera images")

        if not available:
            update_ha_status(ha_url, ha_token, 'unknown')
            log("No camera images available")
            return

        status = call_claude(available, api_key)
        update_ha_status(ha_url, ha_token, status)
        log(f"Analysis result: {status}")

    finally:
        fcntl.flock(lock_fh, fcntl.LOCK_UN)
        lock_fh.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        log(f"Unhandled error: {exc}")
        sys.exit(1)
