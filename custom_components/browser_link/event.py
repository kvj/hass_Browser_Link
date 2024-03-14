from homeassistant.components import event
from homeassistant.helpers.entity import EntityCategory

from .coordinator import BaseEntity
from .constants import DOMAIN

import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_setup_entities):
    coordinator = hass.data[DOMAIN]["devices"][entry.entry_id]
    async_setup_entities([_EntityAction(coordinator)])

class _EntityAction(BaseEntity, event.EventEntity):

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.with_name(f"action", "Entity Action")
        self._attr_event_types = ["more_info", "play_media", "stop_media", "set_volume"]

    async def _on_event(self, name, config):
        self._trigger_event(name, config)
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        self.coordinator._event_listeners.append(self._on_event)
