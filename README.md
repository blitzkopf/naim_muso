# naim_muso

[![GitHub Release][releases-shield]][releases]
[![GitHub Activity][commits-shield]][commits]
[![License][license-shield]](LICENSE)

![Project Maintenance][maintenance-shield]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

_Home Assistant Integration to integrate with [naim muso][naim] media player._

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

<!---->

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