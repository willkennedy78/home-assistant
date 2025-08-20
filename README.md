## Starling Bank "Kite Spaces" - API Sensor + Home Assistant Dashboard.

Will Kennedy - CTRL+ALT+DELusions - will@shwok.com.  Anonymisation and packaging peformed by AI

I wanted to capture the balance of each of my kids' Starling Kite spaces so they could be displayed on our HA dashboard.  Eventually I hope this will be a motivator to save.

This is a tidy, anonymised example showing how to read a Starling primary account balance and two children's spending spaces into Home Assistant, then display a small colour‑coded card per child.

Colours are sensible for my tweenage daughters: **< £5 = green**, **£5–£10 = amber**, **> £10 = red**. you may wish to tweak the values accordingly.

## Package Contents

- `packages/starling_bank.yaml` – REST sensors and template sensors
- `dashboards/starling_cards.yaml` – Lovelace example using `custom:button-card`
- `secrets.yaml.template` – copy‑paste starter for your own secrets

## Quick start
## You will need to sign up for a Starling Developer account to gain access to the Open Banking API.  Sign up at https://developer.starlingbank.com/ 
## Additionally you will need to configure oAuth for your application and then exchange this for a service token and secret you can use to access your API endpoint.  I suggest you only grant your token read privileges!!
1. Copy `packages/starling_bank.yaml` into your Home Assistant **packages** folder (or merge into your config).
2. Copy `dashboards/starling_cards.yaml` into your dashboards (or paste via Raw editor).
3. Copy `secrets.yaml.template` into your `secrets.yaml` and fill in your real values.
4. In `packages/starling_bank.yaml`, replace:
   - `ACCOUNT_UID` with your real account UID
   - `SPACE_UID_CHILD_A` / `SPACE_UID_CHILD_B` with your space UIDs
5. Restart Home Assistant (or reload templates/sensors if you know your way around).

## Security & housekeeping

- **Do not** commit real tokens or UIDs. Keep your `secrets.yaml` local.
- Use a Starling token with the **least** privileges required. 
- Rotate tokens now and again. Belt and braces.
- Keep polling polite (`scan_interval`) so you don’t hammer anything.

## Notes on responses

Some Starling tenants return `feedItems` for spending space detail; others might present a `transactions` array. The templates defensively check **either**. If your payload looks different, adjust the template blocks accordingly (they’re commented).

## Credits

This is supplied as is, with no attribution necessary or warranty implied.  If I can help with any challenges, please let me know.  

Get more like this at https://blog.shwok.com

