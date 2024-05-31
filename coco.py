import threading
import time
import xbmcaddon

from resources.lib.common import logger, tools
from resources.lib.modules.globals import g
from resources.lib.windows.get_sources_window import GetSources as DisplayWindow

#CocoScrapers Imports
from cocoscrapers.sources_cocoscrapers import SourcesCocoScrapers


class CancelProcess(Exception):
    pass


def getSourcesHelper(actionArgs):
    sources = Sources(actionArgs=actionArgs).doModal()
    del sources
    return sources

# coco_provider 
COCO_PROVIDER = 'CocoScrapers'

class Sources(DisplayWindow):
    def __init__(self, xml_file, location, actionArgs=None):
        super(Sources, self).__init__(xml_file, location, actionArgs)

        self.threads = []
        self.language = g.get_language_code()
        self.torrent_results = []  # Collect CocoScrapers torrent results
        self.hoster_results = []  # Collect CocoScrapers hoster results
        self.remainingProviders = ['CocoScrapers']  # For progress monitoring
        self.terminate_on_source = g.get_bool_setting('general.terminate.onsource')

        # ... other init code  ...

    def getSources(self, args):
        # ... (Argument fetching code remains the same) ...

        if control.getSetting('provider.cocoscrapers') == 'true':
            self.threads.append(
                threading.Thread(target=self._cocoscrapers_worker, 
                                 args=(query, anilist_id, episode, media_type, rescrape, get_backup))
            )
        else:
            self.remainingProviders.remove(COCO_PROVIDER)

        # ... start other providers (local providers from Otaku) ... 

        self._monitor_scraping_progress(timeout=60 if rescrape else int(control.getSetting('general.timeout')))

        sourcesList = self.sortSources(
            self.torrentCacheSources + self.torrent_results,  # Combine Otaku and CocoScrapers torrents
            self.embedSources + self.hoster_results,      # Combine Otaku and CocoScrapers hosters
            filter_lang, 
            media_type, 
            duration
        )
        self.return_data = sourcesList
        self.close()
        return

    def _cocoscrapers_worker(self, query, anilist_id, episode, media_type, rescrape, get_backup):
        """Calls CocoScrapers and retrieves sources."""
        try:
            coco_sources = SourcesCocoScrapers().get_sources(
                title=query,
                year=None,  # Extract year from metadata if needed
                imdb=None,  # Extract IMDb ID from metadata if needed
                tmdb=None,  # Extract TMDb ID from metadata if needed
                season=None if media_type == 'movie' else episode,  # Adapt season argument
                episode=None if media_type == 'movie' else episode,
                tvshowtitle=query,
                aliases=[],  # Extract aliases from metadata if available
                language=self.language,  
                manual_select=False, 
                prescrape=False,
                progress_callback=None  # Use Otaku's UI elements for progress feedback
            )
            self.torrent_results.extend(source for source in coco_sources if source['type'] == 'torrent')
            self.hoster_results.extend(source for source in coco_sources if source['type'] != 'torrent')
            if self.terminate_on_source and (len(self.torrent_results) > 0 or len(self.hoster_results) > 0):
                self.remainingProviders.clear()
        except Exception as e:
            logger.error(f"Error in _cocoscrapers_worker: {e}")
        finally:
            self.remainingProviders.remove(COCO_PROVIDER)  # Update progress
    #... other workers
    def _monitor_scraping_progress(self, timeout):
        """
        Monitors the progress of scraping from various providers, updates the progress bar,
        and provides visual feedback to the user. Allows early termination if sources are
        found and the corresponding setting is enabled.

        Args:
            timeout (int): The maximum time (in seconds) to wait for sources.
        """
        start_time = time.time()
        runtime = 0
        while runtime < timeout:
            if (self.canceled
                or len(self.remainingProviders) < 1 and runtime > 5
                or self.terminate_on_source and (
                    len(self.torrent_results) > 0
                    or len(self.hoster_results) > 0
                    or len(self.cloud_files) > 0
                    or len(self.local_files) > 0
                )
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

            # ... Rest of the  _monitor_scraping_progress function (progress updating) ...
Explanation and Adaptations:

CocoScrapers Integration:

Imports: Import SourcesCocoScrapers from cocoscrapers.sources_cocoscrapers.
Worker Function: Create _cocoscrapers_worker in the Sources class:
Instantiates SourcesCocoScrapers and calls its get_sources method with arguments adapted for Otaku's context.
Extends self.torrent_results and self.hoster_results lists with the results from CocoScrapers.
Progress Tracking: Add CocoScrapers to self.remainingProviders and remove it when the worker is done.
Thread Creation: Start a thread for _cocoscrapers_worker in getSources.
Combining Sources:

In getSources, concatenate the results from Otaku's local providers and CocoScrapers:
Torrents: self.torrentCacheSources + self.torrent_results
Hosters/Embeds: self.embedSources + self.hoster_results
This combined source list is then passed to Otaku's sortSources function for filtering, sorting, and ranking.
Provider Configuration in Settings: Add a new option (e.g., provider.cocoscrapers) to Otaku's addon settings, which is used in the getSources function to determine whether to start the CocoScrapers worker thread or not.

Dependency Management: CocoScrapers is a separate addon with its dependencies. Users of Otaku will need to install CocoScrapers separately for this integration to work. Consider:

Providing instructions to users on how to install CocoScrapers.
Adding a mechanism in Otaku to check if CocoScrapers is installed, and notify the user if it's missing.
Key Considerations:

Argument Mapping: The example assumes you've examined both CocoScrapers and Otaku's get_sources function to ensure that the arguments passed to SourcesCocoScrapers.get_sources are correctly mapped. You might need to extract the year, IMDb ID, TMDb ID, or aliases from Otaku's metadata and provide them to CocoScrapers.
Progress Feedback: The current _cocoscrapers_worker does not use CocoScrapers' progress callback. Integrate Otaku's progress display logic into the callback mechanism of CocoScrapers (if needed) or handle progress within the _monitor_scraping_progress function based on the state of the worker threads.
Error Handling: Add error handling and retry logic to _cocoscrapers_worker based on Otaku's error handling conventions.
Threading Issues: Carefully consider potential thread-safety issues. Ensure that lists like self.torrent_results are accessed in a thread-safe way to prevent conflicts between different scraper threads.
By following these guidelines, you can enhance Otaku to utilize providers from CocoScrapers, expanding the available sources for anime content!
