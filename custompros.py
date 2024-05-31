
import os
import json
import xbmcvfs
from importlib import import_module, reload 

from resources.lib.database import provider_db
from resources.lib.modules import globals  # Renamed from globals.py to avoid conflicts
from resources.lib.common import logger, tools  


class CustomProviders:
    """Manages custom provider discovery, loading, and status in Otaku."""

    def __init__(self):
        self.providers_path = os.path.join(globals.g.ADDON_USERDATA_PATH, "providers")
        self.db = provider_db.ProviderDatabase()
        self._known_packages = {}
        self._known_providers = {}
        self.language = globals.g.get_language_code()  
        self._init_providers()

    def _init_providers(self):
        """Initializes providers."""
        logger.info("Initializing custom providers...")
        self._discover_packages()
        self._load_providers()

    def _discover_packages(self):
        """Finds provider packages and loads metadata."""
        for package_name in os.listdir(self.providers_path):
            meta_path = os.path.join(self.providers_path, package_name, "metadata.json")
            if os.path.isfile(meta_path):
                try:
                    with open(meta_path, 'r') as f:
                        metadata = json.load(f)
                    metadata['id'] = metadata.get('id', package_name)  # Default ID to directory name
                    self._known_packages[metadata['id']] = metadata
                    self.db.add_package(metadata)  
                except Exception as e:
                    logger.error(f"Error loading metadata for {package_name}: {e}")

    def _load_providers(self):
        """Loads enabled providers."""
        enabled_packages = self.db.get_enabled_packages()
        for package in enabled_packages:
            package_id = package['pack_name']  # Assuming package ID is stored as 'pack_name'
            metadata = self._known_packages.get(package_id)
            if metadata:
                try:
                    # Dynamic module import 
                    provider_module = import_module(f"providers.{metadata['id']}") 
                    
                    for provider_type in ("torrent", "hosters", "adaptive", "direct"):
                        get_providers_func = getattr(provider_module, f"get_{provider_type}_providers", None)
                        if get_providers_func:
                            providers = get_providers_func(self.language) 
                            for provider_name, provider_class in providers:
                                if self.is_provider_enabled(provider_name, package_id):
                                    provider_instance = provider_class()
                                    # Store the instance (you'll need it in Otaku's scraper logic)
                                    self._known_providers[(package_id, provider_name)] = provider_instance
                                    
                    reload(provider_module)  
                except Exception as e:
                    logger.error(f"Error loading providers from {metadata.get('name', package_id)}: {e}")

    def is_provider_enabled(self, provider_name, package_id):
        """Checks if a provider is enabled."""
        return self.db.is_provider_enabled(provider_name, package_id)

    def flip_provider_status(self, provider_name, package_id):
        """Toggles provider status (enabled/disabled)."""
        new_status = self.db.flip_provider_status(provider_name, package_id)
        self._load_providers() # reload after enabling/disabling a provider
        return new_status

    def get_provider_icon(self, provider_name, package_id):
        """Gets the provider icon."""
        package_data = self._known_packages.get(package_id)
        if package_data:
            icon_path = os.path.join(self.providers_path, package_data['id'], 'icon.png')
            if xbmcvfs.exists(icon_path):
                return icon_path
        return None 

    def get_provider_instance(self, package_id, provider_name):
        """Retrieves an instance of a provider class."""
        return self._known_providers.get((package_id, provider_name))
