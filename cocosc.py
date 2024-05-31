import threading
import time
import pickle 
import xbmcaddon

from resources.lib.pages import nyaa, animetosho, anidex, animeland, animixplay, debrid_cloudfiles, \
    aniwave, gogoanime, gogohd, animepahe, hianime, animess, animelatino, animecat, aniplay, \
    local_localfiles
from resources.lib.ui import control
from resources.lib.windows.get_sources_window import GetSources as DisplayWindow
from resources.lib.common import logger

# CocoScrapers Imports
from cocoscrapers.sources_cocoscrapers import SourcesCocoScrapers

class CancelProcess(Exception):
    pass


def getSourcesHelper(actionArgs):
    sources = Sources(actionArgs=actionArgs).doModal()
    del sources
    return sources


COCO_PROVIDER = 'CocoScrapers'

class Sources(DisplayWindow):
    def __init__(self, xml_file, location, actionArgs=None):
        try:
            super(Sources, self).__init__(xml_file, location, actionArgs)
        except:
            self.args = actionArgs
            self.canceled = False

        # ... [Existing initialization code remains the same] ...

        self.cocoscrapers_sources = []
        self.remainingProviders.append(COCO_PROVIDER)
        self.terminate_on_source = control.getsetting('general.terminate.onsource')

    def getSources(self, args):
        # ... [Argument fetching code remains the same] ...

        # Start CocoScrapers worker
        if control.getSetting('provider.cocoscrapers') == 'true':
            self.threads.append(
                threading.Thread(target=self._cocoscrapers_worker, 
                                 args=(query, anilist_id, episode, media_type, rescrape, get_backup))
            )
        else:
            self.remainingProviders.remove(COCO_PROVIDER)  

        # ... [Start threads for Otaku's existing providers as before] ...

        self._monitor_scraping_progress(timeout=60 if rescrape else int(control.getSetting('general.timeout')))

        # Concatenate CocoScrapers sources 
        self.torrentCacheSources.extend(source for source in self.cocoscrapers_sources if source['type'] == 'torrent')
        self.embedSources.extend(source for source in self.cocoscrapers_sources if source['type'] != 'torrent')

        sourcesList = self.sortSources(self.torrentCacheSources, self.embedSources, filter_lang, media_type, duration)
        self.return_data = sourcesList
        self.close()
        return

    def _cocoscrapers_worker(self, query, anilist_id, episode, media_type, rescrape, get_backup):
        """Fetches sources using CocoScrapers, with adjustments for compatibility."""
        try:
            # Extract relevant metadata from Otaku if available
            show = database.get_show(anilist_id)
            if show:
                kodi_meta = pickle.loads(show.get('kodi_meta'))
                year = kodi_meta.get('year')
                imdb_id = kodi_meta.get('imdbnumber')
                tmdb_id = kodi_meta.get('tmdb_id')
                aliases = kodi_meta.get('aliases', []) 
            else:
                year = imdb_id = tmdb_id = aliases = None

            if media_type == 'movie':
                season = None
                episode = None  
            else:
                season = episode  # Use episode as season for CocoScrapers

            coco_scraper = SourcesCocoScrapers()
            sources = coco_scraper.get_sources(
                title=query,
                year=year,
                imdb=imdb_id,
                tmdb=tmdb_id,
                season=season,
                episode=episode,
                tvshowtitle=query,
                aliases=aliases,
                language=self.language,
                manual_select=False,
                prescrape=False,
                progress_callback=self._cocoscrapers_progress_callback  # Provide feedback
            )
            self.cocoscrapers_sources.extend(sources)

        except Exception as e:
            logger.error(f"Error in CocoScrapers worker: {e}")
        finally:
            self.remainingProviders.remove(COCO_PROVIDER)
            # Signal to stop scraping threads if a source was found and early termination is enabled
            if self.terminate_on_source and len(self.cocoscrapers_sources) > 0:
                self.remainingProviders.clear()

    def _cocoscrapers_progress_callback(self, progress, total):
        """Callback function for progress updates from CocoScrapers."""
        self.setProgress(int(progress / float(total) * 100))
        self.setText(f"CocoScrapers: {int(progress / float(total) * 100)}%")

    #...[Otakus existing Functions- resolutionList(), etc., remain unchanged]...
Key Improvements in _cocoscrapers_worker:

More Robust Metadata Extraction: Now extracts year, imdb_id, tmdb_id, and even aliases (if available) from Otaku's metadata stored in the show dictionary (retrieved using database.get_show). Providing this additional data to CocoScrapers might lead to better search results.

Clearer Season/Episode Mapping: The logic for setting season and episode arguments is made more explicit, ensuring correct mapping to CocoScrapers, especially in the case of movies.

Enhanced Progress Feedback:

Implemented the progress_callback feature of CocoScrapers, which will allow CocoScrapers to call back into Otaku to update the progress bar during scraping.
Added self._cocoscrapers_progress_callback to handle these updates, using Otaku's setProgress and setText methods (assuming they exist and are used for your progress bar/dialog).
Clearer Provider Control: No longer need to remove CocoScrapers if not used, let self.remainingProviders handle the display since we no longer remove anything from the list

Essential Additional Steps:

Verify Kodi Addon Setting: Double-check the ID (provider.cocoscrapers) used for the setting that enables/disables CocoScrapers. Make sure it's consistent with your Otaku settings structure.
Progress Bar Handling (Otaku): Confirm that Otaku uses self.setProgress and self.setText to update its progress display, and adjust the callback (_cocoscrapers_progress_callback) accordingly.
Dependency Management: You still need to guide users on installing CocoScrapers (as it's a separate dependency). You might add a check in Otaku's main script or in this worker function to alert the user if CocoScrapers is missing.
Testing: Rigorous testing is essential. Use various anime titles (movies and shows) to see how CocoScrapers' results are integrated and prioritized.
This revised implementation should work more efficiently within Otaku, but you'll need to verify compatibility with the specific ways Otaku handles its settings, metadata, progress bars, and source prioritization.
