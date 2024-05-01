"""Naim Mu-so Media Player."""
import asyncio
import contextlib

from typing import Any

from naimco import NaimCo

from async_upnp_client.exceptions import UpnpError
from async_upnp_client.utils import async_get_local_ip
from custom_components.naim_muso.data import get_domain_data
from urllib.parse import urlparse



from homeassistant import config_entries
from homeassistant.components import ssdp

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    BrowseMedia,
    MediaClass,
    MediaType,
    MediaPlayerEnqueue
)
from homeassistant.const import CONF_DEVICE_ID, CONF_MAC, CONF_TYPE, CONF_URL

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    LOGGER as _LOGGER,
    CONF_POLL_AVAILABILITY,
    CONF_BROWSE_UNFILTERED,
    CONF_LISTEN_PORT,
    CONF_CALLBACK_URL_OVERRIDE,

)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DlnaDmrEntity from a config entry."""
    _LOGGER.debug("media_player.async_setup_entry %s (%s)", entry.entry_id, entry.title)

    # print(f"entry {entry}")
    # device = NaimCo(entry.data["host"])
    # await device.startup()
    # _ = asyncio.create_task(device.run_connection(10))
    # await device.controller.send_command("GetViewState")
    # await device.controller.nvm.send_command("GETVIEWSTATE")
    # await device.controller.nvm.send_command("GETPREAMP")
    # await device.controller.nvm.send_command("GETSTANDBYSTATUS")
    # await device.controller.nvm.send_command("GETINPUTBLK")
    # await device.controller.nvm.send_command("PRODUCT")
    # await device.controller.nvm.send_command("GETROOMNAME")
    # await device.controller.nvm.send_command("GETSERIALNUM")

    # Create our own device-wrapping entity
    entity = NaimMediaPlayer(
        udn=entry.data[CONF_DEVICE_ID],
        device_type=entry.data[CONF_TYPE],
        name=entry.title,
        # event_port=entry.options.get(CONF_LISTEN_PORT) or 0,
        # event_callback_url=entry.options.get(CONF_CALLBACK_URL_OVERRIDE),
        # poll_availability=entry.options.get(CONF_POLL_AVAILABILITY, False),
        location=entry.data[CONF_URL],
        mac_address=entry.data.get(CONF_MAC),
        #browse_unfiltered=entry.options.get(CONF_BROWSE_UNFILTERED, False),
    )

    async_add_entities([entity])


class NaimMediaPlayer(MediaPlayerEntity):
    """NaimMediaPlayer to interface with naim Mu-so."""
    udn: str
    device_type: str

    # Last known URL for the device, used when adding this entity to hass to try
    # to connect before SSDP has rediscovered it, or when SSDP discovery fails.
    location: str
    # Should the async_browse_media function *not* filter out incompatible media?
    browse_unfiltered: bool

    _device_lock: asyncio.Lock  # Held when connecting or disconnecting the device
    check_available: bool = False
    _ssdp_connect_failed: bool = False

    # Track BOOTID in SSDP advertisements for device changes
    _bootid: int | None = None

    # DMR devices need polling for track position information. async_update will
    # determine whether further device polling is required.
    #_attr_should_poll = True

    # Name of the current sound mode, not supported by DLNA
    #_attr_sound_mode = None

    _device: NaimCo | None = None

    # def __init__(self, device: NaimCo) -> None:
    #     """Store the naimco device used to control naim device."""
    #     self._device = device

    def __init__(
        self,
        udn: str,
        device_type: str,
        name: str,
        #event_port: int,
        #event_callback_url: str | None,
        #poll_availability: bool,
        location: str,
        mac_address: str | None,
        #browse_unfiltered: bool,
    ) -> None:
        """Initialize DLNA DMR entity."""
        self.udn = udn
        self.device_type = device_type
        self._attr_name = name
        #self._event_addr = EventListenAddr(None, event_port, event_callback_url)
        #self.poll_availability = poll_availability
        self.location = location
        self.mac_address = mac_address
        #self.browse_unfiltered = browse_unfiltered
        self._device_lock = asyncio.Lock()

    async def async_added_to_hass(self) -> None:
        """Handle addition."""
        print("async_added_to_hass ")
        # Update this entity when the associated config entry is modified
        if self.registry_entry and self.registry_entry.config_entry_id:
            config_entry = self.hass.config_entries.async_get_entry(
                self.registry_entry.config_entry_id
            )
            assert config_entry is not None
            self.async_on_remove(
                config_entry.add_update_listener(self.async_config_update_listener)
            )

        # Try to connect to the last known location, but don't worry if not available
        if not self._device:
            try:
                await self._device_connect(self.location)
            except UpnpError as err:
                _LOGGER.debug("Couldn't connect immediately: %r", err)

        # Get SSDP notifications for only this device
        self.async_on_remove(
            await ssdp.async_register_callback(
                self.hass, self.async_ssdp_callback, {"USN": self.usn}
            )
        )

        # # async_upnp_client.SsdpListener only reports byebye once for each *UDN*
        # # (device name) which often is not the USN (service within the device)
        # # that we're interested in. So also listen for byebye advertisements for
        # # the UDN, which is reported in the _udn field of the combined_headers.
        # self.async_on_remove(
        #     await ssdp.async_register_callback(
        #         self.hass,
        #         self.async_ssdp_callback,
        #         {"_udn": self.udn, "NTS": NotificationSubType.SSDP_BYEBYE},
        #     )
        # )
        print(f"added to hass  {self.registry_entry}")

    async def async_will_remove_from_hass(self) -> None:
        """Handle removal."""
        await self._device_disconnect()

    async def async_ssdp_callback(
        self, info: ssdp.SsdpServiceInfo, change: ssdp.SsdpChange
    ) -> None:
        """Handle notification from SSDP of device state change."""
        _LOGGER.debug(
            "SSDP %s notification of device %s at %s",
            change,
            info.ssdp_usn,
            info.ssdp_location,
        )

        try:
            bootid_str = info.ssdp_headers[ssdp.ATTR_SSDP_BOOTID]
            bootid: int | None = int(bootid_str, 10)
        except (KeyError, ValueError):
            bootid = None

        if change == ssdp.SsdpChange.UPDATE:
            # This is an announcement that bootid is about to change
            if self._bootid is not None and self._bootid == bootid:
                # Store the new value (because our old value matches) so that we
                # can ignore subsequent ssdp:alive messages
                with contextlib.suppress(KeyError, ValueError):
                    next_bootid_str = info.ssdp_headers[ssdp.ATTR_SSDP_NEXTBOOTID]
                    self._bootid = int(next_bootid_str, 10)
            # Nothing left to do until ssdp:alive comes through
            return

        if self._bootid is not None and self._bootid != bootid:
            # Device has rebooted
            # Maybe connection will succeed now
            self._ssdp_connect_failed = False
            if self._device:
                # Drop existing connection and maybe reconnect
                await self._device_disconnect()
        self._bootid = bootid

        if change == ssdp.SsdpChange.BYEBYE:
            # Device is going away
            if self._device:
                # Disconnect from gone device
                await self._device_disconnect()
            # Maybe the next alive message will result in a successful connection
            self._ssdp_connect_failed = False

        if (
            change == ssdp.SsdpChange.ALIVE
            and not self._device
            and not self._ssdp_connect_failed
        ):
            assert info.ssdp_location
            location = info.ssdp_location
            try:
                await self._device_connect(location)
            except UpnpError as err:
                self._ssdp_connect_failed = True
                _LOGGER.warning(
                    "Failed connecting to recently alive device at %s: %r",
                    location,
                    err,
                )

        # Device could have been de/re-connected, state probably changed
        self.async_write_ha_state()
    async def async_config_update_listener(
        self, hass: HomeAssistant, entry: config_entries.ConfigEntry
    ) -> None:
        """Handle options update by modifying self in-place."""
        _LOGGER.debug(
            "Updating: %s with data=%s and options=%s",
            self.name,
            entry.data,
            entry.options,
        )
        self.location = entry.data[CONF_URL]
        self.poll_availability = entry.options.get(CONF_POLL_AVAILABILITY, False)
        self.browse_unfiltered = entry.options.get(CONF_BROWSE_UNFILTERED, False)

        new_mac_address = entry.data.get(CONF_MAC)
        if new_mac_address != self.mac_address:
            self.mac_address = new_mac_address
            self._update_device_registry(set_mac=True)

        new_port = entry.options.get(CONF_LISTEN_PORT) or 0
        new_callback_url = entry.options.get(CONF_CALLBACK_URL_OVERRIDE)

        if (
            new_port == self._event_addr.port
            and new_callback_url == self._event_addr.callback_url
        ):
            return

        # Changes to eventing requires a device reconnect for it to update correctly
        await self._device_disconnect()
        # Update _event_addr after disconnecting, to stop the right event listener
        self._event_addr = self._event_addr._replace(
            port=new_port, callback_url=new_callback_url
        )
        try:
            await self._device_connect(self.location)
        except UpnpError as err:
            _LOGGER.warning("Couldn't (re)connect after config change: %r", err)

        # Device was de/re-connected, state might have changed
        self.async_write_ha_state()

    async def _device_connect(self, location: str) -> None:
        """Connect to the device now that it's available."""
        _LOGGER.debug("Connecting to device at %s", location)

        async with self._device_lock:
            if self._device:
                _LOGGER.debug("Trying to connect when device already connected")
                return

            domain_data = get_domain_data(self.hass)
            print(f"domain_data {domain_data}")

            # Connect to the base UPNP device
            upnp_device = await domain_data.upnp_factory.async_create_device(location)
            print(f"upnp_device {upnp_device}")
            print(f"upnp_device {upnp_device.device_info.url}")
            hostname = urlparse(upnp_device.device_info.url).hostname
            print(f"hostname {hostname}")

            # # Create/get event handler that is reachable by the device, using
            # # the connection's local IP to listen only on the relevant interface
            # _, event_ip = await async_get_local_ip(location, self.hass.loop)
            # self._event_addr = self._event_addr._replace(host=event_ip)
            # event_handler = await domain_data.async_get_event_notifier(
            #     self._event_addr, self.hass
            # )

            # # Create profile wrapper
            # self._device = DmrDevice(upnp_device, event_handler)
            _,ip_address = await async_get_local_ip(location, self.hass.loop)
            print(f"location {location} ip_address {ip_address}")
            self._device = NaimCo(hostname)
            self.location = location
            await self._device.startup(10)
            #_ = asyncio.create_task(self._device.run_connection(10))
            await self._device.controller.send_command("GetViewState")
            await self._device.controller.nvm.send_command("GETVIEWSTATE")
            await self._device.controller.nvm.send_command("GETPREAMP")
            await self._device.controller.nvm.send_command("GETSTANDBYSTATUS")
            await self._device.controller.nvm.send_command("GETINPUTBLK")
            await self._device.controller.nvm.send_command("PRODUCT")
            await self._device.controller.nvm.send_command("GETROOMNAME")
            await self._device.controller.nvm.send_command("GETSERIALNUM")

            # Subscribe to event notifications
            # try:
            #     self._device.on_event = self._on_event
            #     await self._device.async_subscribe_services(auto_resubscribe=True)
            # except UpnpResponseError as err:
            #     # Device rejected subscription request. This is OK, variables
            #     # will be polled instead.
            #     _LOGGER.debug("Device rejected subscription: %r", err)
            # except UpnpError as err:
            #     # Don't leave the device half-constructed
            #     self._device.on_event = None
            #     self._device = None
            #     await domain_data.async_release_event_notifier(self._event_addr)
            #     _LOGGER.debug("Error while subscribing during device connect: %r", err)
            #     raise

        self._update_device_registry()

    def _update_device_registry(self, set_mac: bool = False) -> None:
        """Update the device registry with new information about the DMR."""
        print(f"self._device {self._device}")
        if not self._device:
            return  # Can't get all the required information without a connection
        print(f"self.registry_entry {self.registry_entry}")
        if not self.registry_entry or not self.registry_entry.config_entry_id:
            return  # No config registry entry to link to
        print(f"self.registry_entry.device_id {self.registry_entry.device_id}")
        if self.registry_entry.device_id and not set_mac:
            return  # No new information
        print(f"self.registry_entry.device_id {self.registry_entry.device_id}")
        connections = set()
        # Connections based on the root device's UDN, and the DMR embedded
        # device's UDN. They may be the same, if the DMR is the root device.
        connections.add(
            (
                dr.CONNECTION_UPNP,
                #self._device.profile_device.root_device.udn,
                self.udn,
            )
        )
        #connections.add((dr.CONNECTION_UPNP, self._device.udn))
        connections.add((dr.CONNECTION_UPNP, self.udn))

        if self.mac_address:
            # Connection based on MAC address, if known
            connections.add(
                # Device MAC is obtained from the config entry, which uses getmac
                (dr.CONNECTION_NETWORK_MAC, self.mac_address)
            )

        # Create linked HA DeviceEntry now the information is known.
        dev_reg = dr.async_get(self.hass)
        device_entry = dev_reg.async_get_or_create(
            config_entry_id=self.registry_entry.config_entry_id,
            connections=connections,
            #default_manufacturer=self._device.manufacturer,
            default_manufacturer='Naim Audio Ltd.',
            #default_model=self._device.model_name,
            default_model='Mu-so',
            #default_name=self._device.name,
            default_name=self._attr_name,
        )

        # Update entity registry to link to the device
        ent_reg = er.async_get(self.hass)
        ent_reg.async_get_or_create(
            self.registry_entry.domain,
            self.registry_entry.platform,
            self.unique_id,
            device_id=device_entry.id,
        )
    async def _device_disconnect(self) -> None:
        """Destroy connections to the device now that it's not available.

        Also call when removing this entity from hass to clean up connections.
        """
        async with self._device_lock:
            if not self._device:
                _LOGGER.debug("Disconnecting from device that's not connected")
                return

            _LOGGER.debug("Disconnecting from %s", self._device.name)
            #self._device.on_event = None
            old_device = self._device
            self._device = None
            #await old_device.async_unsubscribe_services()
            await old_device.shutdown()

        domain_data = get_domain_data(self.hass)
        await domain_data.async_release_event_notifier(self._event_addr)

    @property
    def unique_id(self) -> str:
        """Report the UDN (Unique Device Name) as this entity's unique ID."""
        return self.udn

    @property
    def usn(self) -> str:
        """Get the USN based on the UDN (Unique Device Name) and device type."""
        return f"{self.udn}::{self.device_type}"

    # @property
    # def device_info(self) -> DeviceInfo:
    #     """Return the device info."""
    #     return DeviceInfo(
    #         identifiers={
    #             # Serial numbers are unique identifiers within a specific domain
    #             (DOMAIN, self._device.serialnum)
    #         },
    #         name=self._attr_name,
    #         manufacturer='Naim Audio Ltd.', # self.light.manufacturername,
    #         model='Mu-so', # self.light.productname,
    #         #sw_version=self.light.swversion,
    #         #via_device=(hue.DOMAIN, self.api.bridgeid),
    #     )

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Flag media player features that are supported at this moment.

        Supported features may change as the device enters different states.
        """
        if not self._device:
            return MediaPlayerEntityFeature(0)

        supported_features = (
            MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.SELECT_SOURCE
            | MediaPlayerEntityFeature.BROWSE_MEDIA
            | MediaPlayerEntityFeature.PLAY_MEDIA
        )
        return supported_features

    async def async_update(self) -> None:
        """Retrieve the latest data."""
        # TOD O: these should be moved into the naimco package.
        # Leave them here until the thing stabilize.
        await self._device.controller.send_command("GetViewState")
        await self._device.controller.nvm.send_command("GETVIEWSTATE")
        await self._device.controller.nvm.send_command("GETPREAMP")
        await self._device.controller.nvm.send_command("GETSTANDBYSTATUS")
        await self._device.controller.nvm.send_command("GETINPUTBLK")
        await self._device.controller.nvm.send_command("PRODUCT")
        await self._device.controller.nvm.send_command("GETROOMNAME")
        await self._device.controller.nvm.send_command("GETSERIALNUM")
        await self._device.controller.nvm.send_command('GETTOTALPRESETS')

        await self._device.controller.send_command("GetNowPlaying")

    async def async_turn_on(self) -> None:
        """Turn the media player off."""
        await self._device.on()

    async def async_turn_off(self) -> None:
        """Turn the media player off."""
        await self._device.off()

    async def async_volume_up(self) -> None:
        """Turn volume up for media player.

        This method is a coroutine.
        """
        await self._device.volume_up()

    async def async_volume_down(self) -> None:
        """Turn volume down for media player.

        This method is a coroutine.
        """
        await self._device.volume_down()

    async def async_set_volume_level(self, volume: float) -> None:
        """Set volume level, range 0..1."""
        await self._device.set_volume(int(100 * volume))

    @property
    def volume_level(self) -> float | None:
        """Volume level of the media player (0..1)."""
        vol = self._device.volume
        if vol:
            return int(self._device.volume) / 100.0
        return None

    @property
    def state(self) -> MediaPlayerState | None:
        """State of the player."""

        if not self._device or not self.available:
            return None
        try:
            stbystate = self._device.standbystatus.get("state")
        except AttributeError:
            return None
        if stbystate == "ON":
            return MediaPlayerState.OFF
        if stbystate == "OFF":
            return MediaPlayerState.ON
        ## TOD O: There are other states to consider
        return MediaPlayerState.IDLE

    @property
    def source(self) -> str | None:
        """Get the currently selected input."""
        if not self._device or not self.available:
            return None
        return self._device.inputs.get(self._device.input, None)

    @property
    def source_list(self) -> list[str] | None:
        """Get a list of inputs available."""
        if not self._device or not self.available:
            return None
        inputs = self._device.inputs
        _LOGGER.debug("Source_list inputs: %s", inputs)
        return list(inputs.values())

    async def async_select_source(self, source: str) -> None:
        """Select input source."""
        inputs = self._device.inputs
        for index, name in inputs.items():
            if name == source:
                await self._device.select_input(index)

    async def async_browse_media(
        self, media_content_type: str | None = None, media_content_id: str | None = None
    ) -> BrowseMedia:
        """ Browse available media, only radio presets for the moment"""
        seq = []
        for key,value in self._device.presets.items():
            seq.append(BrowseMedia(media_class=MediaClass.CHANNEL,media_content_id=f"radio/{key}",
                           media_content_type=MediaType.CHANNEL,title=value,
                           can_play=True,can_expand=False))
        return BrowseMedia(media_class=MediaClass.CHANNEL,media_content_id="presets",
                           media_content_type=MediaType.CHANNEL,title="Presets",
                           can_play=False,can_expand=True,
                           children=seq,children_media_class=MediaClass.CHANNEL)
    async def async_play_media(
        self,
        media_type: str,
        media_id: str,
        enqueue: MediaPlayerEnqueue | None = None,
        announce: bool | None = None, **kwargs: Any
    ) -> None:
        """Play a piece of media. Only working with iRadio presets for now"""
        (_dummy,station)=media_id.split("/")
        await self._device.select_preset(station)


    @property
    def media_image_url(self) -> str | None:
        """Image url of current playing media."""
        return self._device.media_image_url

    @property
    def media_image_remotely_accessible(self) -> bool:
        """If the image url is remotely accessible."""
        # it depends on what it playing, leave it at True for now
        return True

    @property
    def media_title(self) -> str | None:
        """Title of current playing media."""
        return self._device.media_title

    @property
    def media_artist(self) -> str | None:
        """Artist of current playing media, music track only."""
        return self._device.media_artist

    @property
    def media_album_name(self) -> str | None:
        """Album name of current playing media, music track only."""
        return self._device.media_album_name

    # @property
    # def media_album_artist(self) -> str | None:
    #     """Album artist of current playing media, music track only."""
    #     return self._attr_media_album_artist

    # @property
    # def media_track(self) -> int | None:
    #     """Track number of current playing media, music track only."""
    #     return self._attr_media_track

    # @property
    # def media_series_title(self) -> str | None:
    #     """Title of series of current playing media, TV show only."""
    #     return self._attr_media_series_title

    # @property
    # def media_season(self) -> str | None:
    #     """Season of current playing media, TV show only."""
    #     return self._attr_media_season

    # @property
    # def media_episode(self) -> str | None:
    #     """Episode of current playing media, TV show only."""
    #     return self._attr_media_episode

    # @property
    # def media_channel(self) -> str | None:
    #     """Channel currently playing."""
    #     return self._attr_media_channel

    # @property
    # def media_playlist(self) -> str | None:
    #     """Title of Playlist currently playing."""
    #     return self._attr_media_playlist
