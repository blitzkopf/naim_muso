from typing import Any

from homeassistant.components.media_player import (
    BrowseMedia,
    MediaClass,
    MediaType,
    MediaPlayerEnqueue
)
from naimco import NaimCo
import asyncio

from .const import LOGGER as _LOGGER


async def async_browse_media(
    device: NaimCo, media_content_type: str | None = None, media_content_id: str | None = None
) -> BrowseMedia:
    """ Browse available media, only radio presets for the moment"""
    _LOGGER.debug("async_browse_media %s %s",
                  media_content_type, media_content_id)
    if media_content_id is None:
        category = "root"
    else:
        (category, _, selection) = media_content_id.partition("/")

    if category == "root" or media_content_id is None:
        seq = []
        for key, value in device.presets.items():
            seq.append(BrowseMedia(media_class=MediaClass.CHANNEL, media_content_id=f"radio/{key}",
                                   media_content_type=MediaType.CHANNEL, title=value,
                                   can_play=True, can_expand=False))
        seq.append(BrowseMedia(media_class=MediaClass.DIRECTORY, media_content_id="browse",
                               media_content_type=MediaType.CHANNELS, title="Browse",
                               can_play=False, can_expand=True))

        return BrowseMedia(media_class=MediaClass.DIRECTORY, media_content_id="presets",
                           media_content_type=MediaType.CHANNELS, title="Favourites",
                           can_play=False, can_expand=True,
                           children=seq, children_media_class=MediaClass.CHANNEL)
    if category == "browse":
        if selection == "up":
            await device.controller.nvm.send_command("BROWSEPARENT", wait_for_reply_timeout=10)
        elif selection:
            await device.select_row(selection, wait_for_reply_timeout=10)
        await asyncio.wait_for(initiate_browsing(device), timeout=120)
        # await initiate_browsing(device)
        kids = []
        if device.state.active_list["depth"] > 0:
            kids.append(BrowseMedia(media_class=MediaClass.DIRECTORY, media_content_id="browse/up",
                                    media_content_type=MediaType.CHANNELS, title="Back",
                                    can_play=False, can_expand=True))
        for row in device.state.rows["rows"]:
            _LOGGER.debug("row: %s", row)
            m = row_to_media(row)
            if m:
                kids.append(m)
        return BrowseMedia(media_class=MediaClass.DIRECTORY, media_content_id="root",
                           media_content_type=MediaType.CHANNELS, title=device.state.active_list[
                               "title"],
                           can_play=False, can_expand=True,
                           children=kids
                           )
    return None

# @catch_comm_error


async def async_play_media(
    device: NaimCo,
    media_type: str,
    media_id: str,
    enqueue: MediaPlayerEnqueue | None = None,
    announce: bool | None = None, **kwargs: Any
) -> None:
    """Play a piece of media. Only working with iRadio presets for now"""
    _LOGGER.debug("async_play_media %s %s", media_type, media_id)
    (category, selection) = media_id.split("/")
    if category == "radio":
        await device.select_preset(selection)
        return
    if category == "browse":
        await device.play_row(selection)
        return


async def initiate_browsing(device: NaimCo):
    """Initiate browsing."""

    await device.controller.nvm.send_command(
        "SETVIEWSTATE BROWSE", wait_for_reply_timeout=10
    )
    await device.controller.nvm.send_command("GETVIEWSTATE", wait_for_reply_timeout=10)
    waittime = 0.05
    while device.state.viewstate["state"] != "BROWSE":
        # ACHTUNG: This might never end
        # Sometime we get  #NVM GETVIEWSTATE BROWSECANRESTART  ...
        # what does that mean?
        await asyncio.sleep(waittime)
        waittime = min(waittime*2, 1)
        await device.controller.nvm.send_command(
            "GETVIEWSTATE", wait_for_reply_timeout=10
        )

    await asyncio.sleep(0.5)

    await device.controller.send_command("GetViewState", wait_for_reply_timeout=10)
    await device.controller.send_command("GetActiveList", wait_for_reply_timeout=10)
    list_handle = device.state.active_list["list_handle"]

    list_handle = device.state.active_list["list_handle"]
    count = device.state.active_list["count"]

    await device.controller.send_command(
        "GetRows",
        [
            {"item": {"name": "list_handle", "int": f"{list_handle}"}},
            {"item": {"name": "from", "int": "1"}},
            {"item": {"name": "to", "int": f"{count}"}},
        ],
        wait_for_reply_timeout=10,
    )


def row_to_media(row: dict) -> BrowseMedia:
    """Convert row to media."""
    if row.get("play", 0) == 1:
        return BrowseMedia(
            media_class=MediaClass.CHANNEL,
            media_content_id=f"browse/{row['index']}",
            media_content_type=MediaType.CHANNEL,
            title=row["text"],
            can_play=True,
            can_expand=False,
            thumbnail=row["metadata"]["albumart_url"],
        )
    if row.get("browse", 0) == 1:
        return BrowseMedia(
            media_class=MediaClass.DIRECTORY,
            media_content_id=f"browse/{row['index']}",
            media_content_type=MediaType.CHANNEL,
            title=row["text"],
            can_play=False,
            can_expand=True,
            thumbnail=row["metadata"]["albumart_url"],
        )
    _LOGGER.info("Unknown row: %s", row)
    return None
