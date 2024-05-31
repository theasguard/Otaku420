import os
import sys
import json
import threading
import time
from importlib import import_module, reload

from contextlib import suppress
from resources.lib.common import tools, logger  
from resources.lib.database import providerCache
from resources.lib.modules.exceptions import RanOnceAlready
from resources.lib.modules.global_lock import GlobalLock
from resources.lib.modules.globals import g
from resources.lib.windows.get_sources_window import GetSources as DisplayWindow


class CancelProcess(Exception):
    pass


def getSourcesHelper(actionArgs):
    sources = Sources(actionArgs=actionArgs).doModal()
    del sources
    return sources


class CustomProviderManager:
    """Manages custom provider discovery, loading, and status."""
    # ... (Previous implementation of CustomProviderManager - remains unchanged) ...


class Sources(DisplayWindow):
    def __init__(self, xml_file, location, actionArgs=None):
        # Initialize both provider systems
        self.provider_manager = CustomProviderManager()
        self._init_local_providers()  # Initialize Otaku's original local providers

        try:
            super(Sources, self).__init__(xml_file, location, actionArgs)
        except:
            self.args = actionArgs
            self.canceled = False

        # ... (The rest of the Sources class variables initialization) ...

    def _init_local_providers(self):
        """Initialize Otaku's original local providers."""
        # Import the required provider modules
        from resources.lib.pages import nyaa, animetosho, anidex, animeland, animixplay, debrid_cloudfiles, \
            aniwave, gogoanime, gogohd, animepahe, hianime, animess, animelatino, animecat, aniplay, \
            local_localfiles
        # You can either add them manually to self.remainingProviders 
        # or create a logic to automate this based on your structure.

        self.local_providers = {
            'nyaa': nyaa.sources(),
            'animetosho': animetosho.sources(),
            'anidex': anidex.sources(),
            # ... (add other providers here) ...
            'animeland': animeland.sources() # Include animeland
        }

    def getSources(self, args):
        # ... (Get arguments - remains the same) ...
        self._start_scraping_threads(query, anilist_id, episode, status, filter_lang,
                                    media_type, rescrape, get_backup, duration)

        self._monitor_scraping_progress(timeout=60 if rescrape else int(control.getSetting('general.timeout')))

        # Call both local and custom providers:
        sourcesList = self.sortSources(
            self.torrentCacheSources + self._get_local_torrent_sources(query, anilist_id, episode, status,
                                                                       media_type, rescrape),  # Add local
            self.embedSources + self._get_local_embed_sources(anilist_id, episode, get_backup,
                                                                rescrape),  # Add local
            filter_lang,
            media_type,
            duration
        )
        self.return_data = sourcesList
        self.close()
        return

    # ... (_start_scraping_threads and _monitor_scraping_progress -  remain mostly the same) ...

    def _get_local_torrent_sources(self, query, anilist_id, episode, status, media_type, rescrape):
        """Retrieve sources from Otaku's original torrent providers."""
        local_torrent_sources = []
        for provider_name, provider_instance in self.local_providers.items():
            if provider_name in ['nyaa', 'animetosho', 'anidex']: # Example local torrent providers
                with suppress(Exception):
                    local_torrent_sources.extend(
                        provider_instance.get_sources(query, anilist_id, episode, status, media_type, rescrape))
        return local_torrent_sources

    def _get_local_embed_sources(self, anilist_id, episode, get_backup, rescrape):
        """Retrieve sources from Otaku's original embed providers."""
        local_embed_sources = []
        for provider_name, provider_instance in self.local_providers.items():
            if provider_name not in ['nyaa', 'animetosho', 'anidex', 'Local Inspection', 'Cloud Inspection']:
                # Assume any provider not listed is an embed provider
                with suppress(Exception):
                    local_embed_sources.extend(
                        provider_instance.get_sources(anilist_id, episode, get_backup, rescrape))
        return local_embed_sources

    # ... (The rest of the Sources class functions: resolutionList, 
    #     debrid_priority, sortSources, etc. - remain unchanged) ...
