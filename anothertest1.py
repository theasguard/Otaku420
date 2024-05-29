import re
import itertools
import pickle
import xbmc
import six
import json

from functools import partial
from bs4 import BeautifulSoup, SoupStrainer
from resources.lib.ui.BrowserBase import BrowserBase
from resources.lib.ui import database, source_utils, client
from resources.lib import debrid
from resources.lib.debrid import TorrentCacheCheck
from six.moves import urllib_parse

import logging

logging.basicConfig(level=logging.DEBUG)


headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 10; Android SDK built for x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Mobile Safari/537.36',  # mobile User-Agent string
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
    'Accept-Encoding': 'gzip, deflate, br',  # added gzip and deflate
    'Accept-Language': 'en-US,en;q=0.8',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',  # added this header
    'DNT': '1',  # added this header
    'Proxy-Connection': 'keep-alive',  # added proxy connection header
}

class sources(BrowserBase):
    _BASE_URL = 'https://anidex.info'
    

    @staticmethod
    def _parse_anidex_episode_view(res, episode):
        # Encode the release title if necessary for Python 2 compatibility
        release_title = res['name'].encode('utf-8') if six.PY2 else res['name']
        source = {
            'release_title': release_title,
            'hash': res['hash'],
            'type': 'torrent',
            'quality': source_utils.getQuality(release_title),
            'debrid_provider': res['debrid_provider'],
            'provider': 'anidex',
            'episode_re': episode,
            'size': res['size'],
            'info': source_utils.getInfo(release_title),
            'lang': source_utils.getAudio_lang(release_title)
        }
        return source

    @staticmethod
    def _parse_anidex_cached_episode_view(res, episode):
        release_title = res['name'].encode('utf-8') if six.PY2 else res['name']
        source = {
            'release_title': release_title,
            'hash': res['hash'],
            'type': 'torrent',
            'quality': source_utils.getQuality(release_title),
            'debrid_provider': res['debrid_provider'],
            'provider': 'anidex (Local Cache)',
            'episode_re': episode,
            'size': res['size'],
            'info': source_utils.getInfo(release_title),
            'lang': source_utils.getAudio_lang(release_title)
        }
        return source

    def get_sources(self, query, anilist_id, episode, status, media_type, rescrape):
        query = self._clean_title(query)

        # Get the episode sources first, and then try alternate searches if needed
        sources = self._get_episode_sources(query, anilist_id, episode, status, rescrape)
        if not sources and ':' in query:
            q1, q2 = (q[1:-1].split(':')[0] for q in query.split('|'))
            query2 = f"({q1})|({q2})"
            sources = self._get_episode_sources(query2, anilist_id, episode, status, rescrape)

        return sources
        
    def _get_episode_sources(self, show, anilist_id, episode, status, rescrape):
        # Try to retrieve sources from the local cache first
        try:
            cached_sources, zfill_int = database.getTorrentList(anilist_id)
            if cached_sources:
                return self._process_cached_sources(cached_sources, episode.zfill(zfill_int))
        except ValueError:
            pass

        # If rescrape is True, or there are no cached sources, scrape from AniDex
        if rescrape:
            return self._get_episode_sources_pack(show, anilist_id, episode)
        
        # Construct search queries and URL for AniDex
        query = '%s "- %s"' % (show, episode.zfill(2))
        season = database.get_season_list(anilist_id)
        if season:
            season = str(season['season']).zfill(2)
            query += '|"S%sE%s "' % (season, episode.zfill(2))

        url = self._BASE_URL + '/?q=' + urllib_parse.quote_plus(query)
        
        if status == 'FINISHED':
            query = '%s "%s"' % (show, episode.zfill(2))
            url = self._BASE_URL + '/?q=' + urllib_parse.quote_plus(query)

        return self._process_anidex_episodes(url, episode.zfill(2), season)

    def _get_episode_sources_pack(self, show, anilist_id, episode):
        query = '%s "- %s"' % (show, episode.zfill(2))
        season = database.get_season_list(anilist_id)
        if season:
            season = str(season['season']).zfill(2)
            query += '|"S%sE%s "' % (season, episode.zfill(2))

        # Scrape the results from AniDex directly, handling different HTML structure
        try:
            url = self._BASE_URL + '/?q=' + urllib_parse.quote_plus(query)
            soup = self.get_soup(url, headers=headers)
            # Use a soup strainer to get only table body for performance improvement
            torrents = soup.find_all('tbody')
            if torrents:
                return self._process_anidex_episodes(url, episode.zfill(2), season)
            else:
                return []
        except Exception as e:
            xbmc.log("Error getting episode sources: " + str(e), level=xbmc.LOGERROR)
            return []

    def _process_cached_sources(self, cached_sources, episode):
        sources = []
        for item in cached_sources:
            if episode == item['episode']:
                source = self._parse_anidex_cached_episode_view(item, episode)
                if source:
                    sources.append(source)

        return sources
        
    def _process_anidex_episodes(self, url, episode, season=None):
        html = client.request(url, headers=headers, timeout=70)
        mlink = SoupStrainer('div', {'class': 'table-responsive'})
        soup = BeautifulSoup(html, "html.parser", parse_only=mlink)
        logging.debug(f"Requesting {url}")

        filtered_list = []

        list_ = []
        for i in soup.select("tr.danger,tr.default,tr.success"):
            magnet_link = i.find('a', {'href': re.compile('magnet:')})
            if magnet_link:
                magnet = magnet_link.get('href')
                name = i.find_all('a', {'class': None})[1].get('title')
                size = i.find_all('td', {'class': 'text-center'})[1].text.replace('i', '')
                downloads = int(i.find_all('td', {'class': 'text-center'})[-1].text)
                list_.append(
                    {'magnet': magnet, 'name': name, 'size': size, 'downloads': downloads}
                )
                
        print("List structure:", list_)
        for idx, torrent in enumerate(list_):
            torrent['hash'] = re.findall(r'btih:(.*?)(?:&|$)', torrent['magnet'])[0]

            # Extract episode number from title
            ep_match = re.findall(r'S\d{1,2}E\d{1,2}|E\d{1,2}', torrent['name'])
            if ep_match:
                # Convert string to int
                ep_match = list(map(int, list(filter(None, itertools.chain(*ep_match)))))
                # Ensure episode is within the searched range
                if ep_match and ep_match[0] != int(episode):
                    continue
            else:
                continue

            # Further filtering for same season:
            if season:
                # Ensure all remaining torrents are in the same season
                if not re.search(f'S{season}E', torrent['name'].lower()):
                    continue
            else:
                # Not searching by season, append all
                filtered_list.append(torrent)

        # Debrid cache check
        cache_list = debrid.TorrentCacheCheck().torrentCacheCheck(filtered_list)
        # Sort by downloads
        cache_list = sorted(cache_list, key=lambda k: k['downloads'], reverse=True)
        mapfunc = partial(self._parse_anidex_episode_view, episode=episode)
        all_results = list(map(mapfunc, cache_list))
        return all_results
