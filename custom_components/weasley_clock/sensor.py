"""Platform for sensor integration."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.template import Template
from homeassistant.helpers.event import (
    TrackTemplate, async_track_template_result, async_track_state_change_event,
)
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, CLOCK_ANGLES


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Weasley Hand sensor."""

    registry = er.async_get(hass)
    old_entity = registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_locations")
    if old_entity:
        registry.async_remove(old_entity)
    data = {**entry.data, **entry.options}
    mapping = {data[f"slot_{i}_name"]: CLOCK_ANGLES[i - 1] for i in range(1, 14)}
    async_add_entities([WeasleyLocationSensor(entry, slot) for slot in range(1, 14)])
    for person in entry.subentries.values():
        if person.subentry_type == "person":
            async_add_entities(
                [WeasleyHandSensor(hass, person, mapping, entry)],
                config_subentry_id=person.subentry_id,
            )


class WeasleyHandSensor(SensorEntity):
    """Representation of a Weasley Clock Hand."""

    _attr_should_poll = False

    def __init__(self, hass, person, mapping, clock):
        """Initialize the sensor."""
        data = person.data
        identifier = data.get("legacy_entry_id", person.subentry_id)
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, identifier)}, name=data["name"],
            manufacturer="Weasley Clock", model="Clock hand",
            via_device=(DOMAIN, clock.entry_id),
        )
        # Naming Convention: "Ramon" -> "Ramon Clockhand" -> sensor.ramon_clockhand
        self._attr_name = f"{data['name']} Clockhand"
        self._attr_unique_id = f"{identifier}_clockhand"

        self._template = Template(data["template"], hass)
        self._diagnostic_unsubscribe = None
        self._mapping = mapping
        self._offset = data.get("offset", 0)

        # Initial state
        self._attr_native_value = "Unknown"
        self._attr_extra_state_attributes = {
            "angle": 0,
            "offset_applied": self._offset
        }

    async def async_added_to_hass(self):
        """Register callbacks."""
        tracker = async_track_template_result(
            self.hass, [TrackTemplate(self._template, None)],
            self._async_on_template_update,
        )
        self.async_on_remove(tracker.async_remove)
        tracker.async_refresh()
        self.async_on_remove(self._remove_diagnostic_listener)

    @callback
    def _async_on_template_update(self, event, updates):
        """Publish errors and unrecognised locations instead of a false angle."""
        result = updates[0].result
        if isinstance(result, TemplateError):
            self._attr_available = False
            self._attr_extra_state_attributes.update(angle=None, configuration_error=str(result))
        else:
            rendered = str(result).strip()
            self._attr_native_value = rendered or None
            self._attr_available = rendered in self._mapping
            self._attr_extra_state_attributes.update(
                angle=(self._mapping[rendered] + self._offset) % 360 if self._attr_available else None,
                configuration_error=None if self._attr_available else "Template must return a configured location",
                template_result=rendered,
            )
        self._update_diagnostics()
        self.async_write_ha_state()

    @callback
    def _remove_diagnostic_listener(self):
        if self._diagnostic_unsubscribe:
            self._diagnostic_unsubscribe()
            self._diagnostic_unsubscribe = None

    @callback
    def _update_diagnostics(self, event=None):
        """Report missing entities from the branch actually evaluated by Jinja."""
        info = self._template.async_render_to_info()
        entities = sorted(info.entities or [])
        missing = [entity for entity in entities if self.hass.states.get(entity) is None]
        unavailable = [entity for entity in entities
                       if (state := self.hass.states.get(entity)) is not None
                       and state.state in ("unknown", "unavailable")]
        warnings = []
        if missing:
            warnings.append("Entities do not exist: " + ", ".join(missing))
        if unavailable:
            warnings.append("Entities have no available state: " + ", ".join(unavailable))
        self._attr_extra_state_attributes.update(
            missing_entities=missing, unavailable_entities=unavailable,
            configuration_warning="; ".join(warnings) or None,
        )
        self._remove_diagnostic_listener()
        if entities:
            self._diagnostic_unsubscribe = async_track_state_change_event(
                self.hass, entities, self._update_diagnostics,
            )
        if event is not None:
            self.async_write_ha_state()


class WeasleyLocationSensor(SensorEntity):
    """Expose each configured location as a text sensor on the clock."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_icon = "mdi:clock-outline"

    def __init__(self, entry, slot):
        data = {**entry.data, **entry.options}
        self._attr_unique_id = f"{entry.entry_id}_location_{slot}"
        self._attr_name = f"Location {slot}"
        self._attr_native_value = data[f"slot_{slot}_name"]
        self._attr_extra_state_attributes = {
            "position": slot,
            "angle": CLOCK_ANGLES[slot - 1],
        }
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name="Weasley Clock",
            manufacturer="Weasley Clock", model="Clock face",
        )
