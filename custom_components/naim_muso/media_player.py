"""Naim Mu-so Media Player."""


from typing import Any
import datetime

from naimco import NaimCo

from homeassistant import config_entries

from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    BrowseMedia,
    MediaPlayerEnqueue,
    MediaType
)

from homeassistant.core import HomeAssistant, callback

from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from .base_entity import BaseEntity

from .const import LOGGER as _LOGGER
from . import media_browser


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DlnaDmrEntity from a config entry."""
    _LOGGER.debug("media_player.async_setup_entry %s (%s)",
                  entry.entry_id, entry.title)

    # Create our own device-wrapping entity
    entity = NaimMediaPlayer(
        coordinator=entry.runtime_data.coordinator,
        parameter=None
    )

    async_add_entities([entity])


class NaimMediaPlayer(BaseEntity, MediaPlayerEntity):
    """NaimMediaPlayer to interface with naim Mu-so."""
    _attr_name = None

    # def __init__(self, coordinator):
    #     """Pass coordinator to CoordinatorEntity."""
    #     super().__init__(coordinator)
    #     self._attr_unique_id = coordinator.unique_id
    #     _LOGGER.debug("NaimMediaPlayer.__init__ unique_id %s",
    #                   self._attr_unique_id)

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update sensor with latest data from coordinator."""
        # This method is called by your DataUpdateCoordinator when a successful update runs.
        # self.device = self.coordinator.get_device_by_id(
        #    self.device.device_type, self.device_id
        # )
        # _LOGGER.debug("handle coordinator_update : %s", self._device.name)
        self.async_write_ha_state()

    # async def async_will_remove_from_hass(self) -> None:
    #     """Handle removal."""
    #     await self._device_disconnect()

    @property
    def _device(self) -> NaimCo | None:
        return self.coordinator._device

    @property
    def available(self) -> bool:
        """Device available if we have a connection to it"""
        if self._device:
            return True
        else:
            return False

    # @property
    # def unique_id(self) -> str:
    #     self.coordinator.unique_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return self.coordinator.device_info

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Flag media player features that are supported at this moment.

        Supported features may change as the device enters different states.
        """
        if not self.coordinator._device:
            return MediaPlayerEntityFeature(0)

        supported_features = (
            MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.SELECT_SOURCE
            | MediaPlayerEntityFeature.BROWSE_MEDIA
            | MediaPlayerEntityFeature.PLAY_MEDIA
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.NEXT_TRACK
            | MediaPlayerEntityFeature.PREVIOUS_TRACK
            | MediaPlayerEntityFeature.SEEK
        )
        return supported_features

    async def async_turn_on(self) -> None:
        """Turn the media player off."""
        await self._device.on()

    async def async_turn_off(self) -> None:
        """Turn the media player off."""
        await self._device.off()

    async def async_media_stop(self) -> None:
        """Stop media playing."""
        await self._device.stop()

    async def async_media_pause(self) -> None:
        """Pause media playing."""
        await self._device.pause()

    async def async_media_play(self) -> None:
        """Play media."""
        await self._device.play()

    async def async_media_next_track(self) -> None:
        """Send next track command."""
        await self._device.nexttrack()

    async def async_media_previous_track(self) -> None:
        """Send next track command."""
        await self._device.prevtrack()

    async def async_mute_volume(self, mute: bool) -> None:
        """Mute the volume."""
        await self._device.mute(mute)

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
    def is_volume_muted(self) -> bool | None:
        """Boolean if volume is currently muted."""
        return self._device.is_muted

    @property
    def state(self) -> MediaPlayerState | None:
        """State of the player. Is it on or off?"""
        stbystate = None
        if not self._device or not self.available:
            return None
        try:
            stbystate = self._device.standbystatus.get("state")
            if stbystate == "ON":
                return MediaPlayerState.OFF
                # return MediaPlayerState.STANDBY
        except AttributeError:
            # return None
            pass
        if self._device.state.bufferstate and int(self._device.state.bufferstate) < 20:
            return MediaPlayerState.BUFFERING
        if self._device.state.viewstate and self._device.state.viewstate.get("phase") == "PAUSE":
            return MediaPlayerState.PAUSED
        if self._device.state.viewstate and self._device.state.viewstate.get("state") == "PLAYING":
            return MediaPlayerState.PLAYING

        if stbystate and stbystate == "OFF":
            return MediaPlayerState.ON
        # TOD O: There are other states to consider
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
        if not self._device:
            return None
        inputs = self._device.inputs
        # _LOGGER.debug("Source_list inputs: %s", inputs)
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
        """ Browse available media, only radio presets for the moment and NAIM supplies channels"""
        # browse_media code is messy, keep it a separate file
        return await media_browser.async_browse_media(self._device, media_content_type, media_content_id)

    async def async_play_media(
        self,
        media_type: str,
        media_id: str,
        enqueue: MediaPlayerEnqueue | None = None,
        announce: bool | None = None, **kwargs: Any
    ) -> None:
        """Play a piece of media. Only working with iRadio presets for now"""
        return await media_browser.async_play_media(self._device, media_type, media_id, enqueue, announce, **kwargs)

    @property
    def media_content_type(self) -> MediaType | str | None:
        """Source of current playing media."""

        source = self._device.media_source
        if source == "iradio":
            return MediaType.CHANNEL
        if source in ("spotify", "tidal"):
            return MediaType.TRACK
        if source == "upnp":
            return MediaType.TRACK

        return None

    @property
    def media_duration(self) -> int | None:
        """Duration of current playing media in seconds."""
        return self._device.media_duration

    @property
    def media_position(self) -> int | None:
        """Position of current playing media in seconds."""
        return self._device.now_playing_time

    @property
    def media_position_updated_at(self) -> datetime.datetime | None:
        """When was the position of the current playing media valid."""
        return self._device.state.last_update.get("now_playing_time", None)

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
