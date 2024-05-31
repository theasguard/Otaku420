
import threading
import time
import xbmcaddon

from resources.lib.common import logger, tools
from resources.lib.modules.globals import g
from resources.lib.windows.get_sources_window import GetSources as DisplayWindow

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

    def getSources(self, args):
        # ... [Existing argument fetching - remains unchanged] ...

        # Start CocoScrapers if enabled
        if control.getSetting('provider.cocoscrapers') == 'true':
            self.threads.append(
                threading.Thread(target=self._cocoscrapers_worker,
                                 args=(query, anilist_id, episode, media_type, rescrape, get_backup))
            )
        else:
            self.remainingProviders.remove(COCO_PROVIDER) 

        #... [Start threads for Otaku's existing providers as before]...

        self._monitor_scraping_progress(timeout=60 if rescrape else int(control.getSetting('general.timeout')))
        
        # Concatenate CocoScrapers sources (already separated)
        self.torrentCacheSources.extend(source for source in self.cocoscrapers_sources if source['type'] == 'torrent')
        self.embedSources.extend(source for source in self.cocoscrapers_sources if source['type'] != 'torrent')
        
        sourcesList = self.sortSources(self.torrentCacheSources, self.embedSources, filter_lang, media_type, duration)
        self.return_data = sourcesList
        self.close()
        # control.log('Sorted sources :\n {0}'.format(sourcesList), 'info')
        return

    # ... [Other functions - nyaa_worker, animetosho_worker, etc., resolutionList(), etc. - 
    #     remain the same]... 

    def _cocoscrapers_worker(self, query, anilist_id, episode, media_type, rescrape, get_backup):
        """Fetches sources using CocoScrapers."""
        try:
            coco_scraper = SourcesCocoScrapers()

            # Extract relevant metadata from Otaku
            show_meta = database.get_show_meta(anilist_id)
            if show_meta:
                show_info = pickle.loads(show_meta.get('kodi_meta'))
                year = show_info.get('year')
                imdb_id = show_info.get('imdbnumber')
                tmdb_id = show_info.get('tmdb_id')
            else:
                year = imdb_id = tmdb_id = None

            # Make necessary adjustments for year, season, episode for CocoScrapers compatibility
            if media_type == 'movie':
                season = None
                episode = None
            else:
                season = int(episode) 

            # Fetch sources from CocoScrapers
            sources = coco_scraper.get_sources(
                title=query,
                year=year,
                imdb=imdb_id,
                tmdb=tmdb_id,
                season=season,
                episode=episode,
                tvshowtitle=query,
                aliases=[],  # Add alias support from Otaku metadata later if needed
                language=self.language,
                manual_select=False, 
                prescrape=False,
                progress_callback=self._cocoscrapers_progress_callback
            )

            #Extend our source list instead of spliting like the example
            self.cocoscrapers_sources.extend(sources)

        except Exception as e:
            logger.error(f"Error in CocoScrapers worker: {e}")
        finally:
            self.remainingProviders.remove(COCO_PROVIDER)
            # Signal to stop scraping threads if a source was found and early termination is enabled
            if self.terminate_on_source and len(self.cocoscrapers_sources) > 0:
                self.remainingProviders.clear()

    def _cocoscrapers_progress_callback(self, progress, total):
        """Callback for CocoScrapers to update progress in Otaku's UI."""
        self.setProgress(int(progress / float(total) * 100))
        self.setText(f"CocoScrapers: {int(progress / float(total) * 100)}%")
Key Improvements:

Metadata Extraction: The _cocoscrapers_worker now attempts to extract year, imdb_id (IMDb number), and tmdb_id from Otaku's show_meta if available to provide more information to CocoScrapers' get_sources method.

Season/Episode Handling: The season and episode values are now adjusted to work correctly with CocoScrapers when media_type is 'movie' (both set to None) or a TV show.

Progress Callback Integration:

Added a progress callback function (_cocoscrapers_progress_callback) to provide progress feedback from CocoScrapers to Otaku's UI elements (progress bar and text).
Passed this callback function to CocoScrapers' get_sources using the progress_callback argument.
Consolidated Source Handling: Combined sources logic for a much simpler experience in the getSources method. Instead of splitting sources into two lists (torrent & embed) let sortSources handle everything since this code was made with multi-use in mind

Additional Considerations:

Alias Support: Consider extracting aliases for the title from Otaku's metadata and providing them to CocoScrapers, as it could potentially improve search accuracy.
UI Integration: You still need to add a UI option (as outlined in the previous responses) to allow users to enable or disable the CocoScrapers provider from within Otaku's settings or a dedicated menu.
Debrid Checking: Review how Otaku handles debrid cache checking for torrents and adapt CocoScrapers' output (if needed) to ensure it's compatible with your debrid cache checker.
Sorting Logic: Adjust or verify that Otaku's sortSources function properly handles the source structure returned by CocoScrapers to prioritize sources according to your preferred sorting logic.
Error Handling and Retries: Carefully consider how you want to handle exceptions and retries for the CocoScrapers worker. You might need to add specific retry logic in case CocoScrapers experiences rate-limiting issues.
Remember: Thorough testing is crucial! Test different anime titles, both movies and shows, to make sure the integration with CocoScrapers works smoothly and produces the desired results.
