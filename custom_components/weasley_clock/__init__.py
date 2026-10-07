"""The Weasley Clock integration."""
from __future__ import annotations

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.helpers import device_registry as dr
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from custom_components.weasley_clock.const import DOMAIN

PLATFORMS: list[Platform] = [Platform.SENSOR]

CARD_URL = "/weasley_clock/weasley-card.js"
STATIC_PATH_REGISTERED = "static_path_registered"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Weasley Clock from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    # 1. Register the frontend card resource automatically
    # This makes the file available at /weasley_clock/weasley-card.js
    # Only once: the path is global, not per config entry.
    if not hass.data[DOMAIN].get(STATIC_PATH_REGISTERED):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    CARD_URL,
                    hass.config.path(
                        "custom_components/weasley_clock/www/weasley-card.js"
                    ),
                    True,
                )
            ]
        )
        add_extra_js_url(hass, f"{CARD_URL}?v=1.1.0")
        hass.data[DOMAIN][STATIC_PATH_REGISTERED] = True

    entry.async_on_unload(entry.add_update_listener(async_update_options))

    # 2. Check if this entry is the "Clock Face" (Hub) or a "Hand" (Sensor)
    # The Clock Face entry has "slot_1_name" in its data
    if "slot_1_name" in entry.data:
        hass.data[DOMAIN]["clock_face"] = {**entry.data, **entry.options}
        dr.async_get(hass).async_get_or_create(
            config_entry_id=entry.entry_id, identifiers={(DOMAIN, entry.entry_id)},
            name="Weasley Clock Hub", manufacturer="Weasley Clock", model="Clock face",
        )
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        return True

    # 3. If it's a Hand, set up the sensor platform
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload sensors after editing the face or a hand."""
    await hass.config_entries.async_reload(entry.entry_id)
    if "slot_1_name" in entry.data:
        for hand in hass.config_entries.async_entries(DOMAIN):
            if "slot_1_name" not in hand.data:
                await hass.config_entries.async_reload(hand.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the hub or a hand."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
