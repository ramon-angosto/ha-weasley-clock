"""Configure one clock with person subentries."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import selector
from homeassistant.helpers.template import Template

from .const import DOMAIN

DEFAULT_SLOTS = [
    "Home", "Work", "Gym", "Lost", "Traveling", "Mortal Peril", "Family",
    "Friends", "Cinema", "Diagon Alley", "Teleporting", "In Bed", "Platform 9 3/4",
]


def validate_slots(data):
    """Require a distinct nonempty name for every position."""
    names = [data.get(f"slot_{i}_name", "").strip() for i in range(1, 14)]
    if not all(names) or len(set(names)) != 13:
        return {"base": "invalid_slots"}
    for i, name in enumerate(names, 1):
        data[f"slot_{i}_name"] = name
    return {}


def face_schema(values):
    return vol.Schema({
        vol.Required(f"slot_{i}_name", default=values.get(f"slot_{i}_name", DEFAULT_SLOTS[i - 1])): str
        for i in range(1, 14)
    })


def hand_schema(values):
    return vol.Schema({
        vol.Required("name", default=values.get("name", "")): str,
        vol.Optional("offset", default=values.get("offset", 0)): int,
        vol.Required("template", default=values.get("template", "")): selector.TemplateSelector(),
    })


def validate_hand(hass, data):
    errors = {}
    if not data["name"].strip():
        errors["name"] = "invalid_name"
    try:
        Template(data["template"], hass).ensure_valid()
    except TemplateError:
        errors["template"] = "invalid_template"
    return errors


class WeasleyClockConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return WeasleyClockOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry):
        return {"person": WeasleyPersonFlow}

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        return await self.async_step_clock_face(user_input)

    async def async_step_clock_face(self, user_input=None):
        errors = validate_slots(user_input) if user_input is not None else {}
        if user_input is not None and not errors:
            return self.async_create_entry(title="Weasley Clock", data=user_input)
        return self.async_show_form(
            step_id="clock_face", data_schema=face_schema(user_input or {}), errors=errors,
        )


class WeasleyClockOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        current = {**self.config_entry.data, **self.config_entry.options}
        errors = validate_slots(user_input) if user_input is not None else {}
        if user_input is not None and not errors:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init", data_schema=face_schema(user_input or current), errors=errors,
        )


class WeasleyPersonFlow(config_entries.ConfigSubentryFlow):
    """People belong to the clock entry and can be reconfigured individually."""

    async def async_step_user(self, user_input=None):
        return await self._async_person_form("user", user_input)

    async def async_step_reconfigure(self, user_input=None):
        return await self._async_person_form("reconfigure", user_input)

    async def _async_person_form(self, step, user_input):
        existing = self._get_reconfigure_subentry() if step == "reconfigure" else None
        errors = validate_hand(self.hass, user_input) if user_input is not None else {}
        if user_input is not None and not errors:
            if existing:
                return self.async_update_and_abort(
                    self._get_entry(), existing, title=user_input["name"],
                    data={**existing.data, **user_input},
                )
            return self.async_create_entry(title=user_input["name"], data=user_input)
        entry = self._get_entry()
        face = {**entry.data, **entry.options}
        return self.async_show_form(
            step_id=step, data_schema=hand_schema(user_input or (existing.data if existing else {})),
            errors=errors, description_placeholders={
                "locations": ", ".join(face[f"slot_{i}_name"] for i in range(1, 14)),
            },
        )
