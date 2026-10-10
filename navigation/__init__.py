"""
navigation — Fully Offline Pedestrian Navigation for SURDAS.

All routing, geocoding, and map management work with zero internet
connectivity after the one-time setup has been run.

Routing engines (automatic priority):
  1. Valhalla (local Docker)  — rich pedestrian routing
  2. OfflineRouter (osmnx)    — pure-Python fallback

Public API:
    from navigation import Navigator, OfflineMapManager, OfflineRouter
    from navigation import ValhallaRouter, LocationProvider, OfflineGeocoder
"""

from navigation.map_manager import OfflineMapManager
from navigation.geocoder import OfflineGeocoder
from navigation.router import OfflineRouter
from navigation.navigator import Navigator
from navigation.location import LocationProvider, ManualLocation, LocationUnavailableError

# Valhalla router is optional — only exported if the module is present
try:
    from navigation.valhalla_router import ValhallaRouter, valhalla_available
    _has_valhalla = True
except ImportError:
    _has_valhalla = False

__all__ = [
    "OfflineMapManager",
    "OfflineGeocoder",
    "OfflineRouter",
    "Navigator",
    "LocationProvider",
    "ManualLocation",
    "LocationUnavailableError",
    "ValhallaRouter",
    "valhalla_available",
]

