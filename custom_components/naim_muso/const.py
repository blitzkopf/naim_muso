"""Constants for the naim Mu-so controller integration."""
import logging
from typing import Final

LOGGER = logging.getLogger(__package__)

UPNP_ST = "urn:schemas-upnp-org:device:MediaRenderer:1"

DOMAIN: Final = "naim_muso"
CONF_LISTEN_PORT: Final = "listen_port"
CONF_CALLBACK_URL_OVERRIDE: Final = "callback_url_override"
CONF_POLL_AVAILABILITY: Final = "poll_availability"
CONF_BROWSE_UNFILTERED: Final = "browse_unfiltered"

DEFAULT_NAME: Final = "Naim Mu-so speaker"

DATA_NAIM_MUSO_DISCOVERY_MANAGER = "naim_muso_discovery_manager"
