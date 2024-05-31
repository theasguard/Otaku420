
import os
import sys
import json
import threading
import importlib
import time
from importlib import import_module, reload
from contextlib import suppress
from resources.lib.common import tools
from resources.lib.database import providerCache
from resources.lib.modules.exceptions import RanOnceAlready
from resources.lib.modules.global_lock import GlobalLock
from resources.lib.modules.globals import g
from resources.lib.windows.get_sources_window import GetSources as DisplayWindow


class CancelProcess(Exception):
    pass


def getSourcesHelper(actionArgs):
    sources = Sources(actionArgs=actionArgs).doModal()
    del sources_window
    return sources


class CustomProviderManager:
    """Manages custom provider discovery, loading, and status."""

    def __init__(self):
        self.providers_path = os.path.join(g.ADDON_USERDATA_PATH, "providers")
        self.cache = providerCache.ProviderCache()  # Use Otaku's provider DB
        self._known_packages = {}
        self._known_providers = {}
        self.language = g.get_language_code()
        self._init_providers()

    def _init_providers(self):
        """Initializes providers by discovering packages and loading them."""
        g.log("Initializing custom providers...")
        with GlobalLock(self.__class__.__name__, True):
            self._discover_packages()
            self._load_providers()

    def _discover_packages(self):
        """Discovers provider packages from metadata.json files."""
        for package_name in os.listdir(self.providers_path):
            meta_path = os.path.join(self.providers_path, package_name, "metadata.json")
            if os.path.isfile(meta_path):
                try:
                    with open(meta_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    self._known_packages[metadata['id']] = metadata
                    self.cache.add_provider_package(
                        pack_name=metadata['id'],
                        author=metadata.get('author', 'Unknown'),
                        remote_meta=metadata.get('remote_meta', ''),
                        version=metadata.get('version', 'Unknown'),
                        services=','.join(metadata.get('services', []))
                    )  # Add to DB
                except Exception as e:
                    g.log(f"Error loading metadata for {package_name}: {e}", 'error')

    def _load_providers(self):
        """Loads provider modules dynamically for enabled packages."""
        enabled_packages = self.cache.get_providers()
        for package in enabled_packages:
            package_name = package["package"]
            if package["status"] == 'disabled':
                continue
            try:
                # Import based on package name from database
                provider_module = import_module(f"providers.{package_name}")

                for provider_type in ["torrent", "hosters", "adaptive", "direct"]:
                    provider_function = getattr(provider_module, f"get_{provider_type}_providers", None)
                    if provider_function:
                        providers = provider_function(self.language)
                        for provider_name, provider_class in providers:
                            if self.is_provider_enabled(provider_name, package_name):
                                provider_instance = provider_class()
                                # ... Store the provider_instance (Otaku needs it for scraping)
                                self._known_providers[(package_name, provider_name)] = provider_instance
                reload(provider_module)
            except Exception as e:
                g.log(f"Error loading providers from {package_name}: {e}", 'error')

    def is_provider_enabled(self, provider_name, package_name):
        """Checks if a provider is enabled in the database."""
        return self.cache.get_single_provider(provider_name, package_name)['status'] == 'enabled'

    def flip_provider_status(self, provider_name, package_name):
        """Toggles the enabled/disabled status of a provider."""
        return self.cache.flip_provider_status(provider_name, package_name)

    def get_provider_icon(self, provider_name, package_name):
        """Gets the provider icon from its package."""
        icon_path = os.path.join(self.providers_path, package_name, 'icon.png')
        if xbmcvfs.exists(icon_path):
            return icon_path
        return None

    def get_provider_instance(self, package_name, provider_name):
        return self._known_providers.get((package_name, provider_name))


class Sources(DisplayWindow):
    def __init__(self, xml_file, location, actionArgs=None):
        # Initialize CustomProviderManager within the Sources class
        self.provider_manager = CustomProviderManager()

        try:
            super(Sources, self).__init__(xml_file, location, actionArgs)
        except:
            self.args = actionArgs
            self.canceled = False

        self.torrent_threads = []
        self.hoster_threads = []
        self.torrentProviders = []
        self.hosterProviders = []
        self.language = g.get_language_code()  # Use language from globals.py
        self.torrentCacheSources = []
        self.embedSources = []
        self.hosterSources = []
        self.cloud_files = []
        self.local_files = []

        # Update remainingProviders to include all provider names from provider_manager
        self.remainingProviders = []
        for provider_type in ['torrent', 'hosters', 'adaptive', 'direct']:
            self.remainingProviders.extend(
                provider[1]
                for provider in self.provider_manager.cache.get_providers(provider_type=provider_type)
            )
        # Append the hard-coded providers
        self.remainingProviders.extend(['Local Inspection', 'Cloud Inspection'])
        self.allTorrents = {}
        self.allTorrents_len = 0
        self.hosterDomains = {}
        self.torrents_qual_len = [0, 0, 0, 0]
        self.hosters_qual_len = [0, 0, 0, 0]
        self.trakt_id = ''
        self.silent = False
        self.return_data = (None, None, None)
        self.basic_windows = True
        self.progress = 1
        self.duplicates_amount = 0
        self.domain_list = []
        self.display_style = 0
        self.background_dialog = None
        self.running_providers = []

        self.line1 = ''
        self.line2 = ''
        self.line3 = ''

        self.host_domains = []
        self.host_names = []

        self.remainingSources = ['1', '2', '3']
        self.threads = []
        self.usercloudSources = []
        self.userlocalSources = []
        self.terminate_on_cloud = control.getSetting('general.terminate.oncloud') == 'true'
        self.terminate_on_local = control.getSetting('general.terminate.onlocal') == 'true'

    # The getSources function stays almost the same but we will make changes 
    # to accommodate the new custom provider system

    def getSources(self, args):
        query = args['query']
        anilist_id = args['anilist_id']
        episode = args['episode']
        status = args['status']
        filter_lang = args['filter_lang']
        media_type = args['media_type']
        rescrape = args['rescrape']
        get_backup = args['get_backup']
        self.setProperty('process_started', 'true')
        duration = args['duration']

        self._start_scraping_threads(query, anilist_id, episode, status, filter_lang,
                                     media_type, rescrape, get_backup, duration)
        self._monitor_scraping_progress(timeout=60 if rescrape else int(control.getSetting('general.timeout')))
        sourcesList = self.sortSources(self.torrentCacheSources, self.embedSources, filter_lang, media_type,
                                     duration)
        self.return_data = sourcesList
        self.close()
        return

    # Function to start all the Scraping threads in getSources
    def _start_scraping_threads(self, query, anilist_id, episode, status, filter_lang, media_type, rescrape, get_backup,
                               duration):
        for provider in self.provider_manager.cache.get_providers():
            provider_name = provider['provider_name']
            package_name = provider['package']

            # Assuming each scraper function takes similar arguments
            scraper_function = getattr(self, f"{provider_name}_worker", None)
            if scraper_function is not None and self.provider_manager.is_provider_enabled(provider_name,
                                                                                          package_name):
                if provider['provider_type'] == 'torrent':
                    # If the provider is a torrent provider
                    self.threads.append(
                        threading.Thread(target=scraper_function,
                                         args=(query, anilist_id, episode, status, media_type, rescrape)))
                else:
                    # Assume the provider is an embed provider for now
                    self.threads.append(
                        threading.Thread(target=scraper_function, args=(anilist_id, episode, get_backup, rescrape)))

        if control.getSetting('scraping.localInspection') == 'true':
            self.threads.append(
                threading.Thread(target=self.user_local_inspection, args=(query, anilist_id, episode, rescrape)))
        else:
            self.remainingProviders.remove('Local Inspection')

        self.threads.append(
            threading.Thread(target=self.user_cloud_inspection, args=(query, anilist_id, episode, media_type, rescrape)))

        for i in self.threads:
            i.start()

    def _monitor_scraping_progress(self, timeout):
        start_time = time.time()
        runtime = 0
        while runtime < timeout:
            if (self.canceled
                or len(self.remainingProviders) < 1 and runtime > 5
                or self.terminate_on_cloud and len(self.cloud_files) > 0
                or self.terminate_on_local and len(self.local_files) > 0):
                self.updateProgress()
                self.setProgress()
                self.setText("4K: %s | 1080: %s | 720: %s | SD: %s" % (
                    control.colorString(self.torrents_qual_len[0] + self.hosters_qual_len[0]),
                    control.colorString(self.torrents_qual_len[1] + self.hosters_qual_len[1]),
                    control.colorString(self.torrents_qual_len[2] + self.hosters_qual_len[2]),
                    control.colorString(self.torrents_qual_len[3] + self.hosters_qual_len[3]),
                ))
                time.sleep(.5)
                break

            self.updateProgress()
            self.setProgress()
            self.setText("4K: %s | 1080: %s | 720: %s | SD: %s" % (
                control.colorString(self.torrents_qual_len[0] + self.hosters_qual_len[0]),
                control.colorString(self.torrents_qual_len[1] + self.hosters_qual_len[1]),
                control.colorString(self.torrents_qual_len[2] + self.hosters_qual_len[2]),
                control.colorString(self.torrents_qual_len[3] + self.hosters_qual_len[3]),
            ))

            # Update Progress
            time.sleep(.5)
            runtime = time.time() - start_time
            self.progress = runtime / timeout * 100

    # You need to modify or add worker functions for each custom provider
    # The examples below are just placeholders. You'll need to 
    # call the actual get_sources functions of each custom provider 

    def nyaa_worker(self, *args):
        with suppress(Exception):
            # Call the actual nyaa provider's get_sources here
            # Assuming it returns a list of sources
            self.nyaaSources = nyaa.sources().get_sources(*args)  
            self.torrentCacheSources += self.nyaaSources
        self.remainingProviders.remove('nyaa')

    # ... (Repeat for other custom providers, using the appropriate 
    #     scraper classes and their get_sources methods) ...

    def user_cloud_inspection(self, *args):
        # ... (Implement or adapt as needed) ...

    # ... (Other functions from Otaku's original Sources class) ...
