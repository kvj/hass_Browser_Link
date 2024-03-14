from homeassistant.components import media_player, media_source
from homeassistant.helpers.entity import EntityCategory

from .coordinator import BaseEntity
from .constants import DOMAIN

import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_setup_entities):
    coordinator = hass.data[DOMAIN]["devices"][entry.entry_id]
    async_setup_entities([_EntityAction(coordinator)])

class _EntityAction(BaseEntity, media_player.MediaPlayerEntity):

    def __init__(self, coordinator):
        super().__init__(coordinator)
        self.with_name(f"player", "Player")
        self._attr_device_class = media_player.MediaPlayerDeviceClass.SPEAKER
        self._attr_supported_features = media_player.MediaPlayerEntityFeature.STOP | media_player.MediaPlayerEntityFeature.PLAY_MEDIA | media_player.MediaPlayerEntityFeature.MEDIA_ANNOUNCE | media_player.MediaPlayerEntityFeature.VOLUME_SET

    @property
    def _state(self):
        return self.coordinator.data.get("media_player", {})

    @property
    def state(self):
        state = self._state.get("state")
        return {
            "play": media_player.MediaPlayerState.PLAYING, 
        }.get(state, media_player.MediaPlayerState.IDLE)

    @property
    def volume_level(self):
        return self._state.get("volume", 100) / 100

    async def async_play_media(self, media_type: str, media_id: str, **kwargs):
        _LOGGER.debug(f"async_play_media: {media_type} / {media_id}, {kwargs}")
        if media_source.is_media_source_id(media_id):
            play_item = await media_source.async_resolve_media(self.hass, media_id, self.entity_id)
            _LOGGER.debug(f"async_play_media: resolved to: {play_item}")
            # media_id = media_player.browse_media.async_process_play_media_url(self.hass, play_item.url)
            media_id = play_item.url
            _LOGGER.debug(f"async_play_media: URL: {media_id}")
        await self.coordinator.async_trigger_event("play_media", {"url": media_id})        

    async def async_media_stop(self) -> None:
        _LOGGER.debug(f"async_media_stop:")
        await self.coordinator.async_trigger_event("stop_media", {})

    async def async_set_volume_level(self, volume: float) -> None:
        _LOGGER.debug(f"async_set_volume_level: {volume}")
        await self.coordinator.async_trigger_event("set_volume", {"volume": round(volume * 100)})
