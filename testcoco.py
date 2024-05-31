import threading
import time
import pickle
import xbmcaddon

from resources.lib.pages import nyaa, animetosho, anidex, animeland, animixplay, debrid_cloudfiles, \
    aniwave, gogoanime, gogohd, animepahe, hianime, animess, animelatino, animecat, aniplay, \
    local_localfiles
from resources.lib.ui import control
from resources.lib.windows.get_sources_window import GetSources as DisplayWindow
from resources.lib.common import logger, tools
from resources.lib.modules.globals import g

# CocoScrapers Imports
from cocoscrapers import sources_cocoscrapers

COCO_PROVIDER = 'CocoScrapers'

class CancelProcess(Exception):
    pass


def getSourcesHelper(actionArgs):
    # ... (Your getSourcesHelper function - remains unchanged) ...


class Sources(DisplayWindow):
    def __init__(self, xml_file, location, actionArgs=None):
        try:
            super(Sources, self).__init__(xml_file, location, actionArgs)
        except:
            self.args = actionArgs
            self.canceled = False

        # ... (Rest of your existing __init__ logic) ... 

        self.cocoscrapers_sources = [] 
        self.remainingProviders.append(COCO_PROVIDER) 
        self.terminate_on_source = control.getSetting('general.terminate.onsource') == 'true' 

    def getSources(self, args):
        # ... [Your code for argument fetching remains unchanged.] ...
        
        # --- THREAD CREATION SECTION --- #
        self._create_worker_threads(query, anilist_id, episode, status, filter_lang, media_type,
                                   rescrape, get_backup, duration)
        self._start_threads()

        #  --- SOURCE PROCESSING SECTION --- #
        self._monitor_scraping_progress(timeout=60 if rescrape else int(control.getSetting('general.timeout')))
        self._combine_sources() #Combine sources
        sourcesList = self.sortSources(self.torrentCacheSources, self.embedSources, filter_lang, media_type, duration)
        self.return_data = sourcesList
        self.close()
        return

    def _monitor_scraping_progress(self, timeout):
        # ... [Progress monitoring logic - No changes needed here]... 

    def _cocoscrapers_worker(self, query, anilist_id, episode, media_type, rescrape, get_backup):
        """Fetches sources using CocoScrapers, optimized for anime."""
        try:
            coco_scraper = sources_cocoscrapers.SourcesCocoScrapers()

            show_info = self._get_show_info(anilist_id)
            title = show_info.get('ename') or show_info.get('name')
            year = show_info.get('year')
            imdb_id = show_info.get('imdbnumber')
            tmdb_id = show_info.get('tmdb_id')
            aliases = show_info.get('aliases', [])

            if media_type == 'movie':
                season = episode = tvshowtitle = None
            else:
                season = episode = int(episode)
                tvshowtitle = title

            sources = coco_scraper.get_sources(
                title=title,
                year=year,
                imdb=imdb_id,
                tmdb=tmdb_id,
                season=season,
                episode=episode,
                tvshowtitle=tvshowtitle,
                aliases=aliases,
                language=self.language,
                manual_select=False,
                prescrape=False, # Set prescrape to false 
                progress_callback=self._cocoscrapers_progress_callback,
            )

            self.cocoscrapers_sources.extend(sources)

        except Exception as e:
            logger.error(f"Error in CocoScrapers worker: {e}")
        finally:
            self.remainingProviders.remove(COCO_PROVIDER)
            if self.terminate_on_source and len(self.cocoscrapers_sources) > 0:
                self.remainingProviders.clear()

    # Moved Thread Starting Logic
    def _start_threads(self):
        """Start all scraping threads."""
        for thread in self.threads:
            thread.start()

        cloud_thread = threading.Thread(target=self.user_cloud_inspection,
                                      args=(query, anilist_id, episode, media_type, rescrape))
        cloud_thread.start()
        cloud_thread.join()

    # Added CocoScrapers Worker logic in a combined method 
    # for thread creating logic to improve organization.
    def _create_worker_threads(self, query, anilist_id, episode, status, filter_lang, media_type,
                                 rescrape, get_backup, duration):
        """Creates worker threads for scraping."""
        if control.getSetting('provider.cocoscrapers') == 'true':
            self.threads.append(
                threading.Thread(target=self._cocoscrapers_worker,
                                 args=(query, anilist_id, episode, media_type, rescrape, get_backup))
            )
        else:
            self.remainingProviders.remove(COCO_PROVIDER)

        if control.real_debrid_enabled() or control.all_debrid_enabled() or control.debrid_link_enabled() or control.premiumize_enabled():
            if control.getSetting('provider.nyaa') == 'true':
                self.threads.append(
                    threading.Thread(target=self.nyaa_worker,
                                     args=(query, anilist_id, episode, status, media_type, rescrape)))
            else:
                self.remainingProviders.remove('nyaa')

            if control.getSetting('provider.animetosho') == 'true':
                self.threads.append(
                    threading.Thread(target=self.animetosho_worker,
                                     args=(query, anilist_id, episode, status, media_type, rescrape)))
            else:
                self.remainingProviders.remove('animetosho')

            if control.getSetting('provider.anidex') == 'true':
                self.threads.append(
                    threading.Thread(target=self.anidex_worker,
                                     args=(query, anilist_id, episode, status, media_type, rescrape)))
            else:
                self.remainingProviders.remove('anidex')
        else:
            self.remainingProviders.remove('nyaa')
            self.remainingProviders.remove('animetosho')
            self.remainingProviders.remove('anidex')

        #Add the rest of the worker threads in here using the pattern above


    def _combine_sources(self):
        """Combine the sources found by CocoScrapers."""
        self.torrentCacheSources.extend(source for source in self.cocoscrapers_sources if source['type'] == 'torrent')
        self.embedSources.extend(source for source in self.cocoscrapers_sources if source['type'] != 'torrent')
    def _get_show_info(self, anilist_id):
    #... [Unchanged helper method remains the same] ... 

    def _cocoscrapers_progress_callback(self, progress, total):
    #... [Callback remains the same] ... 

    #... [Rest of your worker functions and the Sources class code -  no changes needed] ...
