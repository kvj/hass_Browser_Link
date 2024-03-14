from __future__ import annotations
from .constants import (
    DOMAIN, 
    PLATFORMS, 
    FE_SCRIPT_URI,
    CONF_BROWSER_ID,
)
from .coordinator import Coordinator, Platform
from .frontend import locate_dir

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers import service
from homeassistant.loader import async_get_integration

from aiohttp.web import json_response
from homeassistant.components import webhook, frontend, websocket_api

from homeassistant.helpers import issue_registry as ir



import voluptuous as vol
import homeassistant.helpers.config_validation as cv

import logging
_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
    }, extra=vol.ALLOW_EXTRA),
}, extra=vol.ALLOW_EXTRA)

async def _async_update_entry(hass, entry):
    _LOGGER.debug(f"_async_update_entry: {entry}")
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)

async def async_setup_entry(hass: HomeAssistant, entry):
    data = entry.as_dict()["options"]

    platform = hass.data[DOMAIN]["platform"]
    coordinator = Coordinator(platform, entry)
    hass.data[DOMAIN]["devices"][entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_entry))
    await coordinator.async_config_entry_first_refresh()
    await coordinator.async_load()

    for p in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, p)
        )
    return True

async def async_unload_entry(hass: HomeAssistant, entry):
    data = entry.as_dict()["options"]

    coordinator = hass.data[DOMAIN]["devices"][entry.entry_id]
    for p in PLATFORMS:
        await hass.config_entries.async_forward_entry_unload(entry, p)
    await coordinator.async_unload()
    hass.data[DOMAIN]["devices"].pop(entry.entry_id)
    return True

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    cmp = await async_get_integration(hass, DOMAIN)
    ver = cmp.manifest["version"]
    _LOGGER.debug(f"async_setup: {ver}")
    platform = Platform(hass)
    await platform.async_load()
    hass.data[DOMAIN] = {"devices": {}, "platform": platform}
    hass.http.register_static_path(
        FE_SCRIPT_URI,
        "{}/dist/browser_link.js".format(locate_dir()),
        cache_headers=False,
    )
    frontend.add_extra_js_url(hass, "{}?ver={}".format(FE_SCRIPT_URI, ver))
    for fn in (_ws_update_uri, _ws_get_entities, _ws_media_player_state, _ws_update_visibility):
        hass.components.websocket_api.async_register_command(fn)

    async def async_more_info(call):
        for entry_id in await service.async_extract_config_entry_ids(hass, call):
            if coordinator := hass.data[DOMAIN]["devices"].get(entry_id):
                await coordinator.async_trigger_event("more_info", {"entity_id": call.data.get("entity", "")})
    hass.services.async_register(DOMAIN, "more_info", async_more_info)

    return True

def _remove_repair(hass, browser_id):
    ir.async_delete_issue(hass, DOMAIN, "new_browser_id_{}".format(browser_id))

def _create_repair(hass, browser_id, user):
    ir.async_create_issue(
        hass,
        DOMAIN,
        "new_browser_id_{}".format(browser_id),
        is_fixable=False,
        is_persistent=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key="new_browser_id",
        translation_placeholders={
            "browser_id": browser_id,
            "user": user.name,
        },
    )

def _coordinator_by_msg(hass, msg: dict, connection):
    for (id, coordinator) in hass.data[DOMAIN]["devices"].items():
        if coordinator._config[CONF_BROWSER_ID] == msg["browser_id"]:
            _remove_repair(hass, msg["browser_id"])
            return coordinator
    _create_repair(hass, msg["browser_id"], connection.user)
    return None

@websocket_api.websocket_command({
    vol.Required("type"): "browser_link/update_uri",
    vol.Required("browser_id"): str,
    vol.Required("uri"): str,
})
@websocket_api.async_response
async def _ws_update_uri(hass, connection, msg: dict):
    _LOGGER.debug("ws_update_uri: %s", msg)
    if c := _coordinator_by_msg(hass, msg, connection):
        await c.async_update_uri(msg.get("uri"))
    connection.send_result(msg["id"], {})

@websocket_api.websocket_command({
    vol.Required("type"): "browser_link/get_entities",
    vol.Required("browser_id"): str,
})
@websocket_api.async_response
async def _ws_get_entities(hass, connection, msg: dict):
    _LOGGER.debug("_ws_get_entities: %s, %s, %s", msg, connection.user, connection.supported_features)
    if c := _coordinator_by_msg(hass, msg, connection):
        return connection.send_result(msg["id"], await c.async_get_entities())
    connection.send_result(msg["id"], {})

@websocket_api.websocket_command({
    vol.Required("type"): "browser_link/media_player_state",
    vol.Required("browser_id"): str,
    vol.Required("state"): str,
    vol.Optional("volume"): int,
})
@websocket_api.async_response
async def _ws_media_player_state(hass, connection, msg: dict):
    _LOGGER.debug("_ws_media_player_state: %s", msg)
    if c := _coordinator_by_msg(hass, msg, connection):
        await c.async_update_media_player_state(msg.get("state"), msg.get("volume"))
    connection.send_result(msg["id"], {})

@websocket_api.websocket_command({
    vol.Required("type"): "browser_link/update_visibility",
    vol.Required("browser_id"): str,
    vol.Required("hidden"): bool,
})
@websocket_api.async_response
async def _ws_update_visibility(hass, connection, msg: dict):
    _LOGGER.debug("_ws_update_visibility: %s", msg)
    if c := _coordinator_by_msg(hass, msg, connection):
        await c.async_update_visibility(msg["hidden"])
    connection.send_result(msg["id"], {})
