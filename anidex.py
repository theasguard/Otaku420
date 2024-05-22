import xbmcgui
import itertools
import json
import pickle
import re
import six
import logging
import time

from functools import partial
from bs4 import BeautifulSoup, SoupStrainer
from resources.lib.ui.BrowserBase import BrowserBase
from resources.lib.ui import database, source_utils, client, control
from resources.lib import debrid

logging.basicConfig(level=logging.INFO)

class sources(BrowserBase):
    _BASE_URL = 'https://anidex.info/'

    def get_sources(self, query, anilist_id, episode, status, media_type, rescrape):
        query = self._clean_title(query)
        query = self._sphinx_clean(query)

        if rescrape:
            # todo add rescrape stuff here
            pass
            # return self._get_episode_sources_pack(quary, anilist_id, episode)
        if media_type != "movie":
            query = '%s "- %s"' % (query, episode.zfill(2))  # noQA
            season = database.get_season_list(anilist_id)['season']
            season = str(season).zfill(2)
            query += '|"S%sE%s "' % (season, episode.zfill(2))
        else:
            season = None
        rex = r'(magnet:)+[^"]*'

        # Generate the 'id' parameter based on the desired content type
        # In this case, we're searching for anime torrents
        content_type_ids = '1,2,3'
        params = {
            'q': query,
            'id': content_type_ids
        }

        MAX_RETRIES = 5
        RETRY_DELAY = 2  # seconds

        # Retry logic to handle timeout errors when fetching HTML response
        for i in range(MAX_RETRIES):
            try:
                html = client.request(self._BASE_URL, params=params)
                break
            except Exception as e:
                if i < MAX_RETRIES - 1:
                    logging.warning("Error fetching HTML response (retry %d/%d): %s", i+1, MAX_RETRIES, e)
                    time.sleep(RETRY_DELAY)
                else:
                    logging.error("Error fetching HTML response: %s", e)
                    html = None

        if html is None:
            logging.error("Error fetching HTML response after %d retries", MAX_RETRIES)
        else:
            logging.debug("HTML response fetched successfully!")

        # Extract torrent information from the soup
        soup = BeautifulSoup(html, "html.parser")
        torrents = []
        for tr in soup.find_all('tr'):
            # Extract title, size, seeds, leeches, and magnet link from each row
            title = tr.find('td', {'class': 'title'}).text.strip()
            size = tr.find('td', {'class': 'size'}).text.strip()
            seeds = tr.find('td', {'class': 'seeds'}).text.strip()
            leeches = tr.find('td', {'class': 'leeches'}).text.strip()
            magnet_link = tr.find('td', {'class': 'text-center'}).a['href']

            # Add extracted information to the torrents list
            torrents.append({
                'title': title,
                'size': size,
                'seeds': seeds,
                'leeches': leeches,
                'magnet_link': magnet_link
            })

        # Process torrent data to extract hash, filter by episode and season
        _list = []  
        for idx, torrent in enumerate(torrents):
            torrent['hash'] = re.findall(r'btih:(.*?)(?:&|$)', torrent['magnet'])[0]

            if season and (self._filter_by_episode(torrent['name'], episode) or not self._filter_by_season(torrent['name'], season)):
                _list.append(torrent)
            if season:
                title = torrent['name'].lower()
                _list.append(torrent)

        cache_list = debrid.TorrentCacheCheck().torrentCacheCheck(_list)
        mapfunc = partial(self._parse_anidex_view, episode=episode)
        all_results = list(map(mapfunc, cache_list))
        return all_results

    def _filter_by_season(self, title, season):
        season_regex = re.compile(r's(?:eason)?\s*(\d+)')
        match = season_regex.findall(title)
        match = list(map(int, list(filter(None, itertools.chain(*match)))))
        return not match or match[0] == int(season)

    def _filter_by_episode(self, title, episode):
        episode_regex = re.compile(r'(?:e|ep|eps|episode)\s*(\d{1,4})\b')
        ep_match = episode_regex.findall(title)
        ep_match = list(map(int, list(filter(None, itertools.chain(*ep_match)))))
        return ep_match and ep_match[0] != int(episode)

    def _parse_anidex_view(res, episode):
        source = {
            'release_title': res['name'],
            'hash': res['hash'],
            'type': 'torrent',
            'quality': source_utils.getQuality(res['name']),
            'debrid_provider': res['debrid_provider'],
            'provider': 'anidex',
            'episode_re': episode,
            'size': res['size'],
            'info': source_utils.getInfo(res['name']),
            'lang': source_utils.getAudio_lang(res['name'])
        }
        return source