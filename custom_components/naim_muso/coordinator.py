
from datetime import timedelta

import asyncio
from urllib.parse import urlparse
from asyncio import Task
from async_upnp_client.utils import async_get_local_ip
from async_upnp_client.exceptions import UpnpError


from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID, CONF_MAC, CONF_TYPE, CONF_URL

from homeassistant.exceptions import HomeAssistantError

from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from naimco import NaimCo, NaimState

from .const import (
    LOGGER as _LOGGER,
)
from .data import get_domain_data


def catch_comm_error(func):
    async def wrapper(*args, **kwargs):
        self = args[0]
        if not isinstance(self, MusoCoordinator):
            raise HomeAssistantError(
                "Illegal use of decorator, 'self' is not instance of NaimMediaPlayer")
        if self._tasks and self._tasks.done():
            # await self._device_disconnect()

            ex = self._tasks.exception()
            self._tasks = None
            if ex:
                raise HomeAssistantError(ex)
            raise HomeAssistantError("Runner task finished, disconnecting")
        if not self._device:
            _LOGGER.info("trying to reconnect!")
            try:
                await self._device_connect(self.location)
            except UpnpError as err:
                _LOGGER.debug("Couldn't connect immediately: %r", err)
        try:
            return await func(*args, **kwargs)
        except Exception as ex:
            _LOGGER.warn(
                f"{func.__name__} failed to communuicate with Mu-so {ex}\n")
            raise
    return wrapper


class MusoCoordinator(DataUpdateCoordinator):
    """Naim Mu-so custom coordinator."""
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
    # _attr_should_poll = True

    # Name of the current sound mode, not supported by DLNA
    # _attr_sound_mode = None

    _device: NaimCo | None = None

    _tasks: Task | None = None

    # def __init__(self, device: NaimCo) -> None:
    #     """Store the naimco device used to control naim device."""
    #     self._device = device

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize Mu-so coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            # Name of the data. For logging purposes.
            name=config_entry.title,
            # Polling interval. Will only be polled if there are subscribers.
            update_interval=timedelta(seconds=10),
            # update_method=self._async_update_data,
            # Set always_update to `False` if the data returned from the
            # api can be compared via `__eq__` to avoid duplicate updates
            # being dispatched to listeners
            always_update=True
        )
        """Initialize DLNA DMR entity."""
        self.udn = config_entry.data[CONF_DEVICE_ID],
        self.device_type = config_entry.data[CONF_TYPE]
        self._attr_name = config_entry.title
        # self._event_addr = EventListenAddr(None, event_port, event_callback_url)
        # self.poll_availability = poll_availability
        self.location = config_entry.data[CONF_URL]
        self.mac_address = config_entry.data[CONF_MAC]
        # self.browse_unfiltered = browse_unfiltered
        self._device_lock = asyncio.Lock()

    async def _async_setup(self):
        """Set up the coordinator

        This is the place to set up your coordinator,
        or to load data, that only needs to be loaded once.

        This method will be called automatically during
        coordinator.async_config_entry_first_refresh.
        """

        # Try to connect to the last known location, but don't worry if not available
        if not self._device:
            try:
                await self._device_connect(self.location)
            except UpnpError as err:
                _LOGGER.debug("Couldn't connect immediately: %r", err)

    # @catch_comm_error
    async def _async_update_data(self):
        """Fetch data from API endpoint.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        # try:
        #     # Note: asyncio.TimeoutError and aiohttp.ClientError are already
        #     # handled by the data update coordinator.
        #     async with async_timeout.timeout(10):
        #         # Grab active context variables to limit data required to be fetched from API
        #         # Note: using context is not required if there is no need or ability to limit
        #         # data retrieved from API.
        #         listening_idx = set(self.async_contexts())
        #         return await self.my_api.fetch_data(listening_idx)
        # except ApiAuthError as err:
        #     # Raising ConfigEntryAuthFailed will cancel future updates
        #     # and start a config flow with SOURCE_REAUTH (async_step_reauth)
        #     raise ConfigEntryAuthFailed from err
        # except ApiError as err:
        #     raise UpdateFailed(f"Error communicating with API: {err}")
        _LOGGER.debug("Coordinator Updating data")
        try:
            await self._device.update_data()
        except Exception as e:
            _LOGGER.debug("Error updating data: %r", e)
            raise UpdateFailed(f"Error communicating with Mu-so: {e}")
        # await asyncio.sleep(0.1)
        return self._device.state

    @property
    def unique_id(self) -> str:
        """Report the UDN (Unique Device Name) as this entity's unique ID."""
        return self.udn[0]

    @property
    def usn(self) -> str:
        """Get the USN based on the UDN (Unique Device Name) and device type."""
        return f"{self.udn}::{self.device_type}"

    @property
    def device(self):
        # if not self._device:
        #     raise ConfigEntryNotReady("device not connected")
        return self._device

    async def _device_connect(self, location: str) -> None:
        """Connect to the device now that it's available."""
        _LOGGER.debug("Connecting to device at %s", location)

        async with self._device_lock:
            if self._device:
                _LOGGER.debug(
                    "Trying to connect when device already connected")
                return

            domain_data = get_domain_data(self.hass)
            _LOGGER.debug(f"domain_data {domain_data}")

            # Connect to the base UPNP device
            upnp_device = await domain_data.upnp_factory.async_create_device(location)
            _LOGGER.debug(f"upnp_device {upnp_device}")
            _LOGGER.debug(f"upnp_device {upnp_device.device_info.url}")
            hostname = urlparse(upnp_device.device_info.url).hostname
            _LOGGER.debug(f"hostname {hostname}")

            # # Create/get event handler that is reachable by the device, using
            # # the connection's local IP to listen only on the relevant interface
            # _, event_ip = await async_get_local_ip(location, self.hass.loop)
            # self._event_addr = self._event_addr._replace(host=event_ip)
            # event_handler = await domain_data.async_get_event_notifier(
            #     self._event_addr, self.hass
            # )

            # # Create profile wrapper
            # self._device = DmrDevice(upnp_device, event_handler)
            _, ip_address = await async_get_local_ip(location, self.hass.loop)
            _LOGGER.debug(f"location {location} ip_address {ip_address}")
            self._device = NaimCo(hostname, self.devices_update_callback)
            self.location = location
            await self._device.startup(timeout=10)
            # Using the hass async_create_task will hang,
            # self.hass.async_create_task(self._device.runner_task())

            # await self._device.controller.send_command("GetViewState")
            # await self._device.controller.nvm.send_command("GETVIEWSTATE")
            # await self._device.controller.nvm.send_command("GETPREAMP")
            # await self._device.controller.nvm.send_command("GETSTANDBYSTATUS")
            # await self._device.controller.nvm.send_command("GETINPUTBLK")
            # await self._device.controller.nvm.send_command("PRODUCT")
            # await self._device.controller.nvm.send_command("GETROOMNAME")
            # await self._device.controller.nvm.send_command("GETSERIALNUM")

    async def _device_disconnect(self) -> None:
        """Destroy connections to the device now that it's not available.

        Also call when removing this entity from hass to clean up connections.
        """
        async with self._device_lock:
            if self._tasks:
                _LOGGER.debug("Cancelling tasks")
                self._tasks.cancel()
                self._tasks = None

            if not self._device:
                _LOGGER.debug("Disconnecting from device that's not connected")
                return

            _LOGGER.debug("Disconnecting from %s", self._device.name)
            # self._device.on_event = None
            old_device = self._device
            self._device = None
            # await old_device.async_unsubscribe_services()
            await old_device.shutdown()

        # domain_data = get_domain_data(self.hass)
        # await domain_data.async_release_event_notifier(self._event_addr)

    async def devices_update_callback(self, state: NaimState):
        """Receive callback from api with device update."""
        self.async_set_updated_data(state)

    # async def runner_task(self):
    #     try:
    #         await self._device.runner_task()
    #         # ConnectionResetError
    #     except Exception as e:
    #         _LOGGER.info(f"Runner task failed! {e}")
    #         await self._device_disconnect()
    #         raise

    # async def keep_alive_task(self, interval: int):
    #     try:
    #         await self._device.controller.keep_alive(interval)
    #         # ConnectionResetError
    #     except Exception as e:
    #         _LOGGER.info(f"Keep alive task failed! {e}")
    #         # await self._device_disconnect()
    #         raise
