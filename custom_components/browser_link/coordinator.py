from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import storage, entity_platform
from homeassistant.util import dt

from .constants import (
    DOMAIN,
    CONF_BROWSER_ID,
)

import logging
from datetime import datetime

_LOGGER = logging.getLogger(__name__)


class Platform():

    def __init__(self, hass):
        self.hass = hass
        self._storage = storage.Store(hass, 1, DOMAIN)

    async def async_load(self):
        data_ = await self._storage.async_load()
        _LOGGER.debug(f"async_load(): Loaded stored data: {data_}")
        self._storage_data = data_ if data_ else {}

    def get_data(self, key: str, def_={}):
        if key in self._storage_data:
            return self._storage_data[key]
        return def_

    async def async_put_data(self, key: str, data):
        if data:
            self._storage_data = {
                **self._storage_data,
                key: data,
            }
        else:
            if key in self._storage_data:
                del self._storage_data[key]
        await self._storage.async_save(self._storage_data)


class Coordinator(DataUpdateCoordinator):

    def __init__(self, platform, entry):
        super().__init__(
            platform.hass,
            _LOGGER,
            name=DOMAIN,
            update_method=self._async_update,
        )
        self._platform = platform
        self._entry = entry
        self._entry_id = entry.entry_id

        self._event_listeners = []

    async def _async_update(self):
        return self._platform.get_data(self._entry_id)

    async def _async_update_state(self, data: dict):
        self.async_set_updated_data({
            **self.data,
            **data,
        })
        await self._platform.async_put_data(self._entry_id, self.data)

    async def async_load(self):
        self._config = self._entry.as_dict()["options"]
        _LOGGER.debug(f"async_load: {self._config}")

    async def async_unload(self):
        _LOGGER.debug(f"async_unload:")

    async def async_update_uri(self, uri):
        _LOGGER.debug(f"async_update_uri: {uri}")
        await self._async_update_state({
            "uri": uri,
        })

    async def async_update_media_player_state(self, state, volume):
        _LOGGER.debug(f"async_update_media_player_state: {state} {volume}")
        await self._async_update_state({
            "media_player": {
                "state": state,
                "volume": volume,
            },
        })

    async def async_update_visibility(self, hidden: bool):
        _LOGGER.debug(f"async_update_visibility: {hidden}")
        await self._async_update_state({
            "hidden": hidden,
        })

    async def async_get_entities(self):
        result = {}
        from .text import _Path
        from .event import _EntityAction
        mapping = ((_Path, "uri"), (_EntityAction, "action"))
        platforms = entity_platform.async_get_platforms(self.hass, DOMAIN)
        for p in platforms:
            if p.config_entry == self._entry:
                for (entity_id, obj) in p.entities.items():
                    for (cls_, name) in mapping:
                        if isinstance(obj, cls_):
                            result[entity_id] = name
        return result

    async def async_trigger_event(self, name, config):
        _LOGGER.debug(f"async_trigger_event: {name}, {config}")
        for l in self._event_listeners:
            await l(name, config)


class BaseEntity(CoordinatorEntity):

    def __init__(self, coordinator: Coordinator):
        super().__init__(coordinator)

    def with_name(self, id: str, name: str):
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{DOMAIN}_{self.coordinator._entry_id}_{id}"
        self._attr_name = name
        return self

    @property
    def device_info(self):
        return {
            "identifiers": {
                ("entry_id", self.coordinator._entry_id), 
            },
            "name": self.coordinator._entry.title,
        }
