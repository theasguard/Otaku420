import os
import sys
import json
from importlib import import_module, reload 

from resources.lib.database import provider_db  # Assuming Otaku uses this for providers
from resources.lib.common import tools 
from resources.lib.modules.globals import g # Global Variables in the addon


class CustomProviders:
    def __init__(self):
        self.providers_path = os.path.join(g.ADDON_USERDATA_PATH, "providers")  
        self.providers_db = provider_db.ProviderDatabase()  # Assuming a ProviderDatabase class
        self._init_providers()

    def _init_providers(self):
        # 1. Discover provider packages and load metadata (from JSON files)
        self._discover_packages()

        # 2. Load provider modules dynamically 
        self._load_providers()

    def _discover_packages(self):
        for package_name in os.listdir(self.providers_path):
            metadata_path = os.path.join(self.providers_path, package_name, 'metadata.json')
            if os.path.isfile(metadata_path):
                try:
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    self.providers_db.update_package(metadata)
                except Exception as e:
                    g.log(f'Error loading metadata for {package_name}: {e}', 'error') 

    def _load_providers(self):
        enabled_packages = self.providers_db.get_enabled_packages()
        for package in enabled_packages:
            try:
                package_module = import_module(f"providers.{package['pack_name']}") 
                for provider_type in ["torrent", "hosters", "adaptive", "direct"]:
                    providers = getattr(package_module, f"get_{provider_type}_providers")() 
                    for provider_name, provider_class in providers:
                        if self.providers_db.is_provider_enabled(provider_name, package['pack_name']):
                            provider_instance = provider_class()  # Create provider instance
                            # Store provider instance, you'll need it later in Otaku's scraper logic 
                    reload(package_module)
            except Exception as e:
                g.log(f'Error loading providers from {package["pack_name"]}: {e}', 'error')

    def get_provider_icon(self, provider_name, package_name):
        # Adapt Seren's get_icon logic for Otaku's file paths 
