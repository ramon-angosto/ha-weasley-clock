"""Browse clock graphics in Home Assistant Multimedia."""
from __future__ import annotations

import mimetypes
from pathlib import Path
from urllib.parse import quote

from homeassistant.components.media_player import BrowseError, MediaClass
from homeassistant.components.media_source import (
    BrowseMediaSource, MediaSource, MediaSourceItem, PlayMedia, Unresolvable,
)

from . import IMAGE_EXTENSIONS, IMAGE_URL
from .const import DOMAIN


async def async_get_media_source(hass):
    return WeasleyMediaSource(hass)


class WeasleyMediaSource(MediaSource):
    name = "Weasley Clock"

    def __init__(self, hass):
        super().__init__(DOMAIN)
        self.hass = hass

    def _root(self):
        path = self.hass.data.get(DOMAIN, {}).get("image_path")
        if not path:
            raise Unresolvable("Configure Weasley Clock first")
        return Path(path).resolve()

    def _image(self, identifier):
        root = self._root()
        path = (root / identifier).resolve()
        if not path.is_relative_to(root) or path.suffix.lower() not in IMAGE_EXTENSIONS or not path.is_file():
            raise Unresolvable("Image not found in the Weasley Clock folder")
        return path

    async def async_resolve_media(self, item: MediaSourceItem):
        path = await self.hass.async_add_executor_job(self._image, item.identifier or "")
        return PlayMedia(f"{IMAGE_URL}/{quote(path.name)}", mimetypes.guess_type(path.name)[0] or "image/png")

    async def async_browse_media(self, item: MediaSourceItem):
        if item.identifier:
            raise BrowseError("Select the Weasley Clock root to browse images")
        try:
            return await self.hass.async_add_executor_job(self._browse)
        except Unresolvable as err:
            raise BrowseError(str(err)) from err

    def _browse(self):
        children = []
        for path in sorted(self._root().iterdir()):
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                try:
                    self._image(path.name)
                except Unresolvable:
                    continue
                children.append(BrowseMediaSource(
                    domain=DOMAIN, identifier=path.name, title=path.name,
                    media_class=MediaClass.IMAGE,
                    media_content_type=mimetypes.guess_type(path.name)[0] or "image/png",
                    can_play=True, can_expand=False,
                    thumbnail=f"{IMAGE_URL}/{quote(path.name)}",
                ))
        return BrowseMediaSource(
            domain=DOMAIN, identifier=None, title="Weasley Clock",
            media_class=MediaClass.DIRECTORY, media_content_type="",
            can_play=False, can_expand=True, children_media_class=MediaClass.IMAGE,
            children=children,
        )
