# JBL One Soundbar Integration for Unfolded Circle Remote 2/3

Control your **JBL soundbars** (the ones supported by the **JBL One** app) directly from your Unfolded Circle Remote 2 or Remote 3. Power, volume, mute, play/pause, source switching, sound modes, EQ presets, and rear-speaker battery monitoring - controlled **entirely locally** over your network with **no JBL account or cloud login** required.

![JBL](https://img.shields.io/badge/JBL-One%20Soundbar-FF3300)
[![GitHub Release](https://img.shields.io/github/v/release/mase1981/uc-intg-jbl-one?style=flat-square)](https://github.com/mase1981/uc-intg-jbl-one/releases)
![License](https://img.shields.io/badge/license-MPL--2.0-blue?style=flat-square)
[![GitHub issues](https://img.shields.io/github/issues/mase1981/uc-intg-jbl-one?style=flat-square)](https://github.com/mase1981/uc-intg-jbl-one/issues)
[![Community Forum](https://img.shields.io/badge/community-forum-blue?style=flat-square)](https://unfolded.community/)
[![Discord](https://badgen.net/discord/online-members/zGVYf58)](https://discord.gg/zGVYf58)
![GitHub Downloads (all assets, all releases)](https://img.shields.io/github/downloads/mase1981/uc-intg-jbl-one/total?style=flat-square)
[![Buy Me A Coffee](https://img.shields.io/badge/buy%20me%20a%20coffee-donate-yellow.svg?style=flat-square)](https://buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-donate-blue.svg?style=flat-square)](https://paypal.me/mmiyara)
[![Github Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-30363D?&logo=GitHub-Sponsors&logoColor=EA4AAA&style=flat-square)](https://github.com/sponsors/mase1981)

## Supported Devices

JBL soundbars that work with the **JBL One** app, on the local network, including: **Bar 300, Bar 500, Bar 700, Bar 800, Bar 1000, Bar 1300, Bar 1300X**, and **Authentics 200 / 300 / 500**. Both the older firmware (3-band EQ) and JBL One 3.0+ firmware (7-band EQ with presets) are supported.

## Features

- **🔊 Media player** - power on/off, set volume, volume up/down, mute, play/pause, and source selection (HDMI, TV, Bluetooth) as a speaker media player.
- **🎛️ Full remote entity** - all soundbar functions as simple commands for Activities: power, volume, mute, play/pause, Smart Mode (surround), Bass Boost, Atmos level, Calibration, Moment, Rear, source switching, Night Mode, and Pure Voice, with physical button mapping and ready-made button pages.
- **🎚️ Switches** - Night Mode, Smart Mode, and Pure Voice as toggle switches (created only when your model supports them).
- **🎵 EQ preset selector** - pick from your soundbar's EQ presets (JBL One 3.0+ firmware).
- **🔋 Rear-speaker battery sensors** - battery level for detachable rear speakers (models that have them).
- **ℹ️ Info sensors** - model and firmware version.
- **🔒 Fully local** - direct LAN control, no JBL account and no cloud in the loop.
- **Multi-device** - add each JBL soundbar on your network.

---
## ❤️ Support Development ❤️

If you find this integration useful, consider supporting development:

[![GitHub Sponsors](https://img.shields.io/badge/Sponsor-GitHub-pink?style=for-the-badge&logo=github)](https://github.com/sponsors/mase1981)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://www.buymeacoffee.com/meirmiyara)
[![PayPal](https://img.shields.io/badge/PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white)](https://paypal.me/mmiyara)

Your support helps maintain this integration. Thank you! ❤️
---

## How It Works

JBL One soundbars are built on the Harman/LinkPlay platform and expose a local control API. This integration speaks that protocol directly:

- **No account, no cloud** - control runs entirely over your local network. Nothing is sent to JBL's servers.
- **Automatic discovery** - soundbars are found on the network automatically; nothing needs to be paired or entered.
- **State follows the soundbar** - power, volume, mute, and now-playing state are polled from the device.

> Because power is a toggle on the JBL protocol, the integration reads the soundbar's state back after sending commands. On **Authentics** models the "power off" command is suppressed, because those models cannot be powered back on remotely once switched off.

## Requirements

- A JBL One-compatible soundbar on the same network as your Remote.
- The soundbar powered on and connected to your network.
- Unfolded Circle Remote 2 / 3 with firmware supporting custom integrations.

## Installation

### Option 1: Remote Web Interface (Recommended)

1. Download the latest `uc-intg-jbl-one-<version>.tar.gz` from the [**Releases**](https://github.com/mase1981/uc-intg-jbl-one/releases) page.
2. Open your Remote's web interface (`http://your-remote-ip`).
3. Go to **Settings -> Integrations -> Add Integration -> Install Custom** and upload the `.tar.gz`.

### Option 2: Docker (Advanced Users)

**Image**: `ghcr.io/mase1981/uc-intg-jbl-one:latest`

**Docker Compose:**
```yaml
services:
  uc-intg-jbl-one:
    image: ghcr.io/mase1981/uc-intg-jbl-one:latest
    container_name: uc-intg-jbl-one
    network_mode: host
    volumes:
      - ./config:/config
    environment:
      - UC_CONFIG_HOME=/config
      - UC_INTEGRATION_HTTP_PORT=9090
      - UC_INTEGRATION_INTERFACE=0.0.0.0
      - PYTHONPATH=/app
    restart: unless-stopped
```

**Docker Run:**
```bash
docker run -d --name uc-intg-jbl-one --restart unless-stopped --network host -v $(pwd)/config:/config -e UC_CONFIG_HOME=/config -e UC_INTEGRATION_INTERFACE=0.0.0.0 -e UC_INTEGRATION_HTTP_PORT=9090 -e PYTHONPATH=/app ghcr.io/mase1981/uc-intg-jbl-one:latest
```

## Configuration

1. Make sure your JBL soundbar is **powered on** and on the same network as the Remote.
2. Start setup. Your soundbars are **discovered automatically**; if you have more than one, pick the soundbar to add. If discovery finds nothing, **enter the soundbar's IP address** manually.
3. Repeat setup to add additional soundbars.

For each device the integration creates:

| Entity | Purpose |
|--------|---------|
| **Media player** (`<name>`) | Power, volume, mute, play/pause, and source selection. |
| **Remote** (`<name> Remote`) | Full button surface (power, volume, sound modes, sources, Night Mode, Pure Voice) as simple commands for Activities, with button pages. |
| **Switches** | Night Mode, Smart Mode, Pure Voice (when supported by the model). |
| **Select** | EQ preset (JBL One 3.0+ firmware). |
| **Sensors** | Model, firmware, and rear-speaker battery (when present). |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| "No JBL soundbars were found" | Ensure the soundbar is powered on and on the same network/subnet as the Remote, then re-run setup and enter the IP manually. |
| Soundbar shows as unavailable after changing networks | The integration tries to re-find the soundbar by its device ID automatically; if it does not recover, re-run setup with the new IP. |
| Cannot power an Authentics model back on | Those models cannot be powered on remotely; the integration suppresses "power off" for them to avoid this. |
| Some switches (Night Mode, etc.) are missing | Those toggles only appear when your soundbar model reports supporting them. |
| No EQ preset selector | EQ presets are only available on JBL One 3.0+ firmware. |

## Credits

- **Developer**: Meir Miyara
- **JBL / LinkPlay local protocol**: based on the community [JBL_Soundbar](https://github.com/MrBearPresident/JBL_Soundbar) Home Assistant integration.
- **Unfolded Circle**: Remote 2/3 integration framework ([ucapi](https://github.com/unfoldedcircle/integration-python-library) / [ucapi-framework](https://github.com/JackJPowell/ucapi-framework)).

## License

Mozilla Public License 2.0 (MPL-2.0) - see the LICENSE file.

## Support & Community

- **GitHub Issues**: [Report bugs and request features](https://github.com/mase1981/uc-intg-jbl-one/issues)
- **UC Community Forum**: [General discussion and support](https://unfolded.community/)
- **Developer**: [Meir Miyara](https://www.linkedin.com/in/meirmiyara)

---

**Made with ❤️ for the Unfolded Circle Community**

**Thank You**: Meir Miyara
