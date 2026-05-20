"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.template import Template

from .const import DOMAIN, CLOCK_ANGLES


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Weasley Hand sensor."""

    # 1. Retrieve the Global Clock Face configuration
    clock_config = None
    for e in hass.config_entries.async_entries(DOMAIN):
        if "slot_1_name" in e.data:
            clock_config = e.data
            break

    if not clock_config:
        return

    # 2. Build the name-to-angle mapping
    mapping = {}
    for i in range(1, 14):
        name = clock_config.get(f"slot_{i}_name")
        if name:
            mapping[name] = CLOCK_ANGLES[i - 1]

    # 3. Create the Entity
    async_add_entities([WeasleyHandSensor(hass, entry, mapping)])


class WeasleyHandSensor(SensorEntity):
    """Representation of a Weasley Clock Hand."""

    def __init__(self, hass, entry, mapping):
        """Initialize the sensor."""
        # Naming Convention: "Ramon" -> "Ramon Clockhand" -> sensor.ramon_clockhand
        self._attr_name = f"{entry.data['name']} Clockhand"
        self._attr_unique_id = f"{entry.entry_id}_clockhand"

        self._template = Template(entry.data["template"], hass)
        self._mapping = mapping
        self._offset = entry.data.get("offset", 0)

        # Initial state
        self._attr_native_value = "Unknown"
        self._attr_extra_state_attributes = {
            "angle": 0,
            "offset_applied": self._offset
        }

    async def async_added_to_hass(self):
        """Register callbacks."""
        self.async_on_remove(
            self._template.async_track_changes(
                self.hass, self._async_on_template_update
            )
        )
        self._async_on_template_update(None, None)

    @callback
    def _async_on_template_update(self, event, updates):
        """Update the state when template changes."""
        try:
            rendered = self._template.async_render(parse_result=False).strip()
            self._attr_native_value = rendered

            # Lookup angle
            base_angle = self._mapping.get(rendered, 0)
            final_angle = (base_angle + self._offset) % 360

            self._attr_extra_state_attributes["angle"] = final_angle
            self.async_write_ha_state()
        except Exception:
            self._attr_native_value = "Error"