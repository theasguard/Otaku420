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

    def get_sources(self, query, anilist_id, episode, status, media_type, rescrape):
        show = database.get_show(anilist_id)
        logging.debug("Retrieved show from database: %s", show)
        kodi_meta = pickle.loads(show.get('kodi_meta'))
        logging.debug("Kodi meta: %s", kodi_meta)

        query = self._build_query(kodi_meta, anilist_id, episode, media_type)
        logging.debug("Final query string: %s", query)

        anidb = self._get_anidb_id(anilist_id, show_meta)
        content_type_ids = '1,2,3'
        url = self._build_url(query, content_type_ids)
        logging.debug("URL string: %s", url)

        html = client.request(url, timeout=60)
        soup = BeautifulSoup(html, "html.parser")
        row = SoupStrainer('div', {'class': 'table-responsive'})

        list_ = self._parse_torrents(soup)
        logging.debug("List structure: %s", list_)

        filtered_list = self._filter_torrents(list_, season, episode)
        cache_list = debrid.TorrentCacheCheck().torrentCacheCheck(filtered_list)
        cache_list = sorted(cache_list, key=lambda k: k['downloads'], reverse=True)
        mapfunc = partial(self._parse_anidex_view, episode=episode)
        all_results = list(map(mapfunc, cache_list))
        return all_results

    def _build_query(self, kodi_meta, anilist_id, episode, media_type):
        query = kodi_meta.get('ename')
        logging.debug("Title: %s", query)
        query = kodi_meta.get('name')
        query = self._clean_title(query)
        logging.debug("Cleaned query string: %s", query)

        if media_type != "movie":
            season = database.get_season_list(anilist_id)['season']
            season = str(season).zfill(2)
            query_template = "{title} S{season}E{episode}"
            query = query_template.format(title=query, season=season, episode=episode.zfill(2))
            logging.debug("Query string for series: %s", query)
        else:
            query_template = "{title} - {episode}"
            query = query_template.format(title=query, episode=episode.zfill(2))
            logging.debug("Query string for movie: %s", query)

        return query

    def _get_anidb_id(self, anilist_id, show_meta):
        anidb = database.get_anidb_id(anilist_id)
        if anidb is None and show_meta:
            meta_ids = pickle.loads(show_meta['meta_ids'])
            anidb = meta_ids.get('anidb')
        return anidb

    def _build_url(self, query, content_type_ids):
        return '%s/?q=%s&id=%s' % (self._BASE_URL, urllib_parse.quote_plus(query), content_type_ids)

    def _parse_torrents(self, soup):
        list_ = []
        for row in soup.find_all('tr'):
            torrent_link = row.find('a', class_='torrent')
            magnet_link = row.find('a', title='Magnet')
            torrent_data = {
                'name': torrent_link.get_text(strip=True) if torrent_link else 'No name available',
                'magnet': magnet_link.get('href') if magnet_link else 'No magnet link available',
                'size': row.find_all('td')[6].get_text(strip=True) if len(row.find_all('td')) > 6 else 'No size available',
                'torrent_link': torrent_link.get('href') if torrent_link else 'No torrent link available'
            }
            list_.append(torrent_data)
        return list_

    def _filter_torrents(self, list_, season, episode):
        regex = r'Season\s*(\d+)\s*Episode\s*(\d+)|S(\d+)E(\d+)|(\d+)x(\d+)'
        regex_ep = r'\de(\d+)\b|\se(\d+)\b|\s-\s(\d{1,4})\b'
        rex = re.compile(regex)
        rex_ep = re.compile(regex_ep)

        filtered_list = []
        for torrent in list_:
            if 'magnet' in torrent and torrent['magnet']:
                try:
                    torrent['hash'] = re.findall(r'btih:(.*?)(?:&|$)', torrent['magnet'])[0]
                except IndexError:
                    continue  # Handle the case where no match is found
            if season:
                title = torrent['name'].lower()
                ep_match = rex_ep.findall(title)
                ep_match = list(map(int, list(filter(None, itertools.chain(*ep_match)))))

                if ep_match and ep_match[0] != int(episode):
                    regex_ep_range = r'\s(?:\d+(?:[-~]\d+)?)(?:-(?:\d+(?:[-~]\d+)?))?'
                    rex_ep_range = re.compile(regex_ep_range)

                    if not rex_ep_range.search(title):
                        continue

                match = rex.findall(title)
                match = list(map(int, list(filter(None, itertools.chain(*match)))))
                if not match or match[0] == int(season):
                    filtered_list.append(torrent)
            else:
                filtered_list.append(torrent)
        return filtered_list

    def _parse_anidex_view(self, res, episode):
        source = {
            'release_title': res.get('name'),
            'hash': res.get('hash'),
            'type': 'torrent',
            'quality': source_utils.getQuality(res.get('name')),
            'debrid_provider': res.get('debrid_provider'),
            'provider': 'anidex',
            'episode_re': episode,
            'size': res.get('size'),
            'info': source_utils.getInfo(res.get('name')),
            'lang': source_utils.getAudio_lang(res.get('name'))
        }
        return source
