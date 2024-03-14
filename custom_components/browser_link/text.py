from homeassistant.components import text
from homeassistant.helpers.entity import EntityCategory

from .coordinator import BaseEntity
from .constants import DOMAIN

import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_setup_entities):
    coordinator = hass.data[DOMAIN]["devices"][entry.entry_id]
    async_setup_entities([_Path(coordinator)])

class _Path(BaseEntity, text.TextEntity):

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.with_name(f"path", "Path")
        self._attr_native_max = 255

    @property
    def native_value(self) -> bool | None:
        return self.coordinator.data.get("uri")

    async def async_set_value(self, value: str) -> None:
        await self.coordinator.async_update_uri(value)
