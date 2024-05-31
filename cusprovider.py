import os
import sys
import json
from importlib import import_module, reload

from resources.lib.database import provider_db  # Assuming this is Otaku's provider DB
from resources.lib.common import tools, logger  # Import appropriate logging 
from resources.lib.modules.globals import g


class CustomProviders:
    """Manages custom provider discovery, loading, and status."""

    def __init__(self):
        self.providers_path = os.path.join(g.ADDON_USERDATA_PATH, "providers")
        self.providers_db = provider_db.ProviderDatabase()
        self._known_packages = {}
        self._known_providers = {}
        self.language = g.get_language_code()  # Get language from Otaku settings
        self._init_providers()

    def _init_providers(self):
        """Initializes providers by discovering packages and loading them."""
        logger.info("Initializing custom providers...")
        self._discover_packages()
        self._load_providers()

    def _discover_packages(self):
        """Discovers provider packages from metadata.json files."""
        for package_name in os.listdir(self.providers_path):
            meta_path = os.path.join(self.providers_path, package_name, "metadata.json")
            if os.path.isfile(meta_path):
                try:
                    with open(meta_path, 'r') as f:
                        metadata = json.load(f)
                    self._known_packages[metadata['id']] = metadata
                    self.providers_db.update_package(metadata)  # Add to DB
                except Exception as e:
                    logger.error(f"Error loading metadata for {package_name}: {e}")

    def _load_providers(self):
        """Loads provider modules dynamically for enabled packages."""
        enabled_packages = self.providers_db.get_enabled_packages()
        for package_id in enabled_packages:
            metadata = self._known_packages.get(package_id)  
            if metadata:
                try:
                    # Import based on ID in metadata.json
                    provider_module = import_module(f"providers.{metadata['id']}")

                    for provider_type in ["torrent", "hosters", "adaptive", "direct"]:
                        provider_function = getattr(provider_module, f"get_{provider_type}_providers", None)
                        if provider_function:
                            providers = provider_function(self.language)
                            for provider_name, provider_class in providers:
                                if self.is_provider_enabled(provider_name, package_id):
                                    provider_instance = provider_class()
                                    # ... Store the provider_instance (Otaku needs it for scraping)
                                    self._known_providers[(package_id, provider_name)] = provider_instance
                    reload(provider_module)  
                except Exception as e:
                    logger.error(f"Error loading providers from {metadata.get('name', 'Unknown Package')}: {e}")

    def is_provider_enabled(self, provider_name, package_id):
        """Checks if a provider is enabled in the database."""
        return self.providers_db.is_provider_enabled(provider_name, package_id)

    def flip_provider_status(self, provider_name, package_id):
        """Toggles the enabled/disabled status of a provider."""
        return self.providers_db.flip_provider_status(provider_name, package_id)

    def get_provider_icon(self, provider_name, package_id):
        """Gets the provider icon from its package."""
        icon_path = os.path.join(self.providers_path,
                                 self._known_packages.get(package_id, {}).get('id', ''), 
                                 'icon.png')  
        if xbmcvfs.exists(icon_path):
            return icon_path
        return None 

    def get_provider_instance(self, package_id, provider_name):
        return self._known_providers.get((package_id, provider_name))
