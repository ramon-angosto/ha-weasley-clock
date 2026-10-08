"""Automatic card configuration and the server-side snapshot action."""
from __future__ import annotations

import asyncio
import math
import re
from urllib.parse import quote

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.util import slugify

from .const import DOMAIN
from .render import SNAPSHOT_FILENAME, discover_face, find_image, render_snapshot, resolve_image

HAND_SCHEMA = vol.Schema({
    vol.Required('entity'): cv.entity_id,
    vol.Required('image'): cv.string,
    vol.Optional('width', default='100%'): cv.string,
    vol.Optional('top', default='0%'): cv.string,
    vol.Optional('left', default='0%'): cv.string,
})
SNAPSHOT_SCHEMA = vol.Schema({
    vol.Optional('image'): cv.string,
    vol.Optional('hands'): [HAND_SCHEMA],
    vol.Optional('filename', default=SNAPSHOT_FILENAME): vol.Match(r'^[a-zA-Z0-9_-]+\.png$'),
    vol.Optional('width'): vol.All(vol.Coerce(int), vol.Range(min=128, max=4096)),
})


def image_url(image):
    if not image:
        return None
    if image.startswith(('/', 'media-source://')):
        return image
    return f'/{DOMAIN}/images/{quote(image)}'


async def async_layout(hass):
    """Resolve configured images and conventional filenames in Multimedia."""
    root = hass.data.get(DOMAIN, {}).get('image_path')
    if not root:
        raise HomeAssistantError('Weasley Clock is not loaded')
    clock = next((e for e in hass.config_entries.async_entries(DOMAIN) if 'slot_1_name' in e.data), None)
    if not clock:
        raise HomeAssistantError('Configure Weasley Clock first')
    config = {**clock.data, **clock.options}
    image = config.get('image') or await hass.async_add_executor_job(discover_face, root)
    hands = []
    registry = er.async_get(hass)
    for person in clock.subentries.values():
        if person.subentry_type != 'person':
            continue
        data = person.data
        identifier = data.get('legacy_entry_id', person.subentry_id)
        entity = registry.async_get_entity_id('sensor', DOMAIN, f'{identifier}_clockhand')
        if not entity:
            continue
        name = slugify(data['name'])
        graphic = data.get('image') or await hass.async_add_executor_job(
            find_image, root, (f'manecilla_{name}', f'hand_{name}', name),
        )
        hands.append({
            'entity': entity, 'image': image_url(graphic), 'name': data['name'],
            'width': data.get('width', '100%'), 'top': data.get('top', '0%'),
            'left': data.get('left', '0%'),
        })
    return {'image': image_url(image), 'hands': hands}


@websocket_api.websocket_command({vol.Required('type'): f'{DOMAIN}/config'})
@websocket_api.async_response
async def websocket_config(hass, connection, message):
    try:
        layout = await async_layout(hass)
    except HomeAssistantError as error:
        connection.send_error(message['id'], 'not_ready', str(error))
    else:
        connection.send_result(message['id'], layout)


async def async_snapshot(hass, call):
    """Freeze current angles, then render outside the event loop."""
    async with hass.data[DOMAIN]['snapshot_lock']:
        layout = await async_layout(hass)
        image = call.data.get('image') or layout['image']
        if not image:
            raise HomeAssistantError('No clock face found. Configure its image or upload reloj_weasley.png in Multimedia')
        root = hass.data[DOMAIN]['image_path']
        hands = []
        skipped = []
        for hand in call.data.get('hands', layout['hands']):
            state = hass.states.get(hand['entity'])
            angle = state.attributes.get('angle') if state else None
            if not hand.get('image') or not state or state.state in ('unknown', 'unavailable') or not isinstance(angle, (int, float)) or not math.isfinite(angle):
                skipped.append(hand['entity'])
                continue
            hands.append({**hand, 'angle': angle})
        try:
            result = await hass.async_add_executor_job(
                create_snapshot, root, hass.config.path('www'), image, hands,
                call.data['filename'], call.data.get('width'),
            )
        except (ValueError, OSError) as error:
            raise HomeAssistantError(str(error)) from error
        result['skipped_entities'] = skipped
        if call.return_response:
            return result
        return None


def create_snapshot(root, www_root, image, hands, filename, width):
    from pathlib import Path
    from time import time_ns
    face = resolve_image(image, root, www_root)
    prepared = [{**hand, 'path': resolve_image(hand['image'], root, www_root)} for hand in hands]
    destination = Path(root) / filename
    if destination.resolve() in {face, *(hand['path'] for hand in prepared)}:
        raise ValueError('Snapshot filename must not overwrite a source graphic')
    size = render_snapshot(face, prepared, destination, width)
    return {
        'filename': str(destination),
        'url': f'/{DOMAIN}/images/{quote(filename)}?v={time_ns()}',
        'media_content_id': f'media-source://{DOMAIN}/{filename}',
        'width': size[0], 'height': size[1],
    }


def async_setup_graphics(hass):
    hass.data.setdefault(DOMAIN, {})['snapshot_lock'] = asyncio.Lock()
    websocket_api.async_register_command(hass, websocket_config)

    async def handle_snapshot(call):
        return await async_snapshot(hass, call)

    hass.services.async_register(
        DOMAIN, 'snapshot', handle_snapshot, schema=SNAPSHOT_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
