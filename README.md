# naim_muso

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

![Project Maintenance][maintenance-shield]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

_Home Assistant Integration to integrate with [naim muso][naim] generation 1 media player._

## Installation via HACS
The preferred type of installation is via [HACS](https://hacs.xyz). This way, you'll get updates when there are new versions.

1. Add [https://github.com/blitzkopf/naim_muso][naim_muso] to HACS under: HACS → Integrations → 3 dots(top right) → Custom repositories.
1. Select Naim Mu-so under HACS → Integrations, or search for it if it not on the front page.


## Installation
This is the hard way, HACS above is easier, at least after you have HACS set up.

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
1. If you do not have a `custom_components` directory (folder) there, you need to create it.
1. In the `custom_components` directory (folder) create a new folder called `naim_muso`.
1. Download _all_ the files from the `custom_components/naim_muso/` directory (folder) in this repository.
1. Place the files you downloaded in the new directory (folder) you created.
1. Restart Home Assistant
1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Integration blueprint"

## Configuration is done in the UI

## Using the Integration
When the muso device is found it will show up with controls for on/off, volume +/-, source selection
and if the source selected is iRadio you will be able to browse the preset radio stations from the app.

What is specifically not working is playing arbitrary media, but you can actually play media using
the DLNA integration. But the DLNA integration is unable to turn the muso on so you will need to do
that with this integration.

It is also possible to control the muso through scripts and scenes.

Here is an example script to turn the device on and select digital input.
You have to find the entity_id of your device, using device_id will not work
because the DLNA medial player has the same device_id.

```yaml
alias: Stofan Digital script
sequence:
  - action: media_player.turn_on
    metadata: {}
    data: {}
    target:
      entity_id: media_player.stofan_2
  - action: media_player.select_source
    metadata: {}
    data:
      source: Digital
    target:
      entity_id: media_player.stofan_2
description: ""
icon: mdi:toslink
```

Here is a scene doing similar things, you could also use the UI to create as scene.

```yaml
- id: '1723583194866'
  name: Stofan Digital
  entities:
    media_player.stofan_2:
      friendly_name: Stofan
      supported_features: 135044
      entity_picture_local:
      source_list:
      - iRadio
      - Multiroom
      - UPnP
      - USB/iPod
      - Bluetooth
      - Airplay
      - Spotify
      - TIDAL
      - Analogue
      - Digital
      volume_level: 0.14
      source: Digital
      state: 'on'
  icon: mdi:toslink
  metadata:
    media_player.stofan_2:
      entity_only: true
```

<!---->
## muso Generation 2
This integration will only work with a generation 1 muso, the generation 2 muso uses a totally
different protocol.

As generation 2 uses a simple REST API it is possible to control some parts of it with the
rest_command integration. You will need to change the IP-address, and using a fixed IP-address is probably best.
```yaml
rest_command:
  naim_on:
    url: "http://192.168.1.52:15081/power?system=on"
    method: put
  naim_off:
    url: "http://192.168.1.52:15081/power?system=lona"
    method: put
  naim_dig:
    url: "http://192.168.1.52:15081/inputs/dig?cmd=select"
    method: get
  naim_ana:
    url: "http://192.168.1.52:15081/inputs/ana?cmd=select"
    method: get
  naim_vol:
    url: "http://192.168.1.52:15081/levels/room?volume=30"
    method: put
```

## Contributions are welcome!

If you want to contribute to this please read the [Contribution guidelines](CONTRIBUTING.md)

***

[naim]: https://www.naimaudio.com/
[commits-shield]: https://img.shields.io/github/commit-activity/y/blitzkopf/naim_muso.svg?style=for-the-badge
[commits]: https://github.com/blitzkopf/naim_muso/commits/main
[discord]: https://discord.gg/Qa5fW2R
[discord-shield]: https://img.shields.io/discord/330944238910963714.svg?style=for-the-badge
[exampleimg]: example.png
[forum-shield]: https://img.shields.io/badge/community-forum-brightgreen.svg?style=for-the-badge
[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/blitzkopf/naim_muso.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/badge/maintainer-Yngvi%20Þór%20Sigurjónsson%20%40blitzkopf-blue.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/blitzkopf/naim_muso.svg?style=for-the-badge
[releases]: https://github.com/blitzkopf/naim_muso/releases