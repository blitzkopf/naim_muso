"""Naim Mu-so Media Player."""
import asyncio
from typing import Any

from naimco import NaimCo

from homeassistant import config_entries
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    BrowseMedia,
    MediaClass,
    MediaType,
    MediaPlayerEnqueue
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from collections.abc import Sequence

from .const import LOGGER as _LOGGER


async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the DlnaDmrEntity from a config entry."""
    # _LOGGER.debug("media_player.async_setup_entry %s (%s)", entry.entry_id, entry.title)

    # Create our own device-wrapping entity
    print(f"entry {entry}")
    device = NaimCo(entry.data["host"])
    await device.startup()
    _ = asyncio.create_task(device.run_connection(10))
    await device.controller.send_command("GetViewState")
    await device.controller.nvm.send_command("GETVIEWSTATE")
    await device.controller.nvm.send_command("GETPREAMP")
    await device.controller.nvm.send_command("GETSTANDBYSTATUS")
    await device.controller.nvm.send_command("GETINPUTBLK")
    await device.controller.nvm.send_command("PRODUCT")
    await device.controller.nvm.send_command("GETROOMNAME")
    await device.controller.nvm.send_command("GETSERIALNUM")

    entity = NaimMediaPlayer(
        device=device,
    )

    async_add_entities([entity])


class NaimMediaPlayer(MediaPlayerEntity):
    """NaimMediaPlayer to interfac ewith naim Mu-so."""

    _device: NaimCo

    def __init__(self, device: NaimCo) -> None:
        """Store the naimco device used to control naim device."""
        self._device = device

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
