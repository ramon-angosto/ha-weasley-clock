"""Config flow for Weasley Clock integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
import homeassistant.helpers.config_validation as cv

from .const import DOMAIN

# Default names for the 13 slots if user doesn't change them
DEFAULT_SLOTS = [
    "Home", "Work", "Gym", "Lost", "Traveling",
    "Mortal Peril", "Family", "Friends", "Cinema",
    "Diagon Alley", "Teleporting", "In Bed", "Platform 9 3/4"
]


class WeasleyClockConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Weasley Clock."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the start of the config flow."""
        # 1. Check if the Main Clock Face is already configured
        entries = self._async_current_entries()
        clock_face_exists = any("slot_1_name" in e.data for e in entries)

        # 2. If not, force the user to set up the locations first
        if not clock_face_exists:
            return await self.async_step_clock_face()

        # 3. If yes, go straight to adding a Person/Hand
        return await self.async_step_add_hand()

    async def async_step_clock_face(self, user_input=None):
        """Step 1: Configure the 13 Clock Locations."""
        if user_input is not None:
            return self.async_create_entry(title="Weasley Clock Hub", data=user_input)

        # Build schema for 13 slots
        schema = {}
        for i in range(1, 14):
            default_name = DEFAULT_SLOTS[i - 1] if i - 1 < len(DEFAULT_SLOTS) else f"Location {i}"
            schema[vol.Required(f"slot_{i}_name", default=default_name)] = str

        return self.async_show_form(
            step_id="clock_face",
            data_schema=vol.Schema(schema),
            description_placeholders={"info": "Define the names for your 13 clock positions."}
        )

    async def async_step_add_hand(self, user_input=None):
        """Step 2: Add a new Person (Hand)."""
        errors = {}

        if user_input is not None:
            # Validate the Jinja template
            try:
                self.hass.helpers.template.Template(user_input["template"], self.hass).ensure_valid()
                return self.async_create_entry(title=user_input["name"], data=user_input)
            except Exception:
                errors["template"] = "invalid_template"

        return self.async_show_form(
            step_id="add_hand",
            errors=errors,
            data_schema=vol.Schema({
                vol.Required("name"): str,
                vol.Optional("offset", default=0): int,
                vol.Required("template"): selector.TemplateSelector(),
            }),
            description_placeholders={
                "info": "Paste your logic below. It must return EXACTLY one of the names you defined in the Clock Face."
            }
        )