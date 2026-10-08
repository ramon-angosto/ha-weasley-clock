"""Set up the clock, migrate legacy people, and register frontend assets."""
from __future__ import annotations

import logging
from pathlib import Path
from shutil import copy2
from types import MappingProxyType

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er

from .const import DOMAIN
from .graphics import async_setup_graphics

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.SENSOR]
CARD_URL = "/weasley_clock/weasley-card.js"
CARD_RESOURCE = f"{CARD_URL}?v=1.3.0"
IMAGE_URL = "/weasley_clock/images"
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


async def async_setup(hass: HomeAssistant, config) -> bool:
    """Migrate separate person entries before any entry starts loading."""
    async_setup_graphics(hass)
    entries = hass.config_entries.async_entries(DOMAIN)
    clock = next((entry for entry in entries if "slot_1_name" in entry.data), None)
    if clock is None:
        return True
    hass.config_entries.async_update_entry(clock, title="Weasley Clock")
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)
    clock_device = device_registry.async_get_or_create(
        config_entry_id=clock.entry_id, identifiers={(DOMAIN, clock.entry_id)},
        name="Weasley Clock", manufacturer="Weasley Clock", model="Clock face",
    )
    # Rename the integration-provided name; preserve a user-customised name.
    device_registry.async_update_device(clock_device.id, name="Weasley Clock")
    for legacy in entries:
        if "slot_1_name" in legacy.data or "template" not in legacy.data:
            continue
        subentry = next((sub for sub in clock.subentries.values()
                         if sub.data.get("legacy_entry_id") == legacy.entry_id), None)
        if subentry is None:
            data = {**legacy.data, **legacy.options, "legacy_entry_id": legacy.entry_id}
            subentry = ConfigSubentry(
                data=MappingProxyType(data), subentry_type="person",
                title=data["name"], unique_id=legacy.entry_id,
            )
            hass.config_entries.async_add_subentry(clock, subentry)
        # Move registries before deleting the old entry, retaining entity IDs,
        # unique IDs, areas and any user customisations.
        for entity in er.async_entries_for_config_entry(entity_registry, legacy.entry_id):
            entity_registry.async_update_entity(
                entity.entity_id, config_entry_id=clock.entry_id,
                config_subentry_id=subentry.subentry_id,
            )
        for device in dr.async_entries_for_config_entry(device_registry, legacy.entry_id):
            device_registry.async_update_device(
                device.id, new_config_entry_id=clock.entry_id,
                new_config_subentry_id=subentry.subentry_id, via_device_id=clock_device.id,
            )
        await hass.config_entries.async_remove(legacy.entry_id)
    return True


def prepare_images(media_root: str, legacy_root: str) -> str:
    """Create the media folder and copy old images without overwriting uploads."""
    target = Path(media_root) / DOMAIN
    target.mkdir(parents=True, exist_ok=True)
    legacy = Path(legacy_root)
    if legacy.is_dir() and legacy.resolve() != target.resolve():
        for source in legacy.iterdir():
            destination = target / source.name
            if source.is_file() and source.suffix.lower() in IMAGE_EXTENSIONS and not destination.exists():
                copy2(source, destination)
    return str(target)


async def async_register_frontend(hass):
    """Serve assets and register the dashboard resource explicitly."""
    data = hass.data.setdefault(DOMAIN, {})
    if not data.get("static_path_registered"):
        media_root = hass.config.media_dirs.get("local") or next(
            iter(hass.config.media_dirs.values()), hass.config.path("media"),
        )
        data["image_path"] = await hass.async_add_executor_job(
            prepare_images, media_root, hass.config.path("www", DOMAIN),
        )
        await hass.http.async_register_static_paths([
            StaticPathConfig(CARD_URL, str(Path(__file__).parent / "www" / "weasley-card.js"), False),
            StaticPathConfig(IMAGE_URL, data["image_path"], False),
        ])
        add_extra_js_url(hass, CARD_RESOURCE)
        data["static_path_registered"] = True
    resources = hass.data[LOVELACE_DATA].resources
    if isinstance(resources, ResourceStorageCollection):
        await resources.async_get_info()
        matching = [item for item in resources.async_items()
                    if item["url"].split("?")[0] == CARD_URL]
        if matching:
            for item in matching:
                if item["url"] != CARD_RESOURCE or item["type"] != "module":
                    await resources.async_update_item(item["id"], {"url": CARD_RESOURCE, "res_type": "module"})
        else:
            await resources.async_create_item({"url": CARD_RESOURCE, "res_type": "module"})
    else:
        _LOGGER.info("Lovelace YAML resources: add %s as type module if required", CARD_RESOURCE)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await async_register_frontend(hass)
    entry.async_on_unload(entry.add_update_listener(async_update_options))
    hass.config_entries.async_update_entry(entry, title="Weasley Clock")
    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, entry.entry_id)},
        name="Weasley Clock", manufacturer="Weasley Clock", model="Clock face",
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload all locations and people when the clock or a subentry changes."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
