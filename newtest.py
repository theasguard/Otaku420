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

# ... (Your existing headers code)

class sources(BrowserBase):
    _BASE_URL = 'https://anidex.info'

    @staticmethod
    def _parse_anidex_view(res, episode):
        source = {
            'release_title': res['name'].encode('utf-8') if six.PY2 else res['name'],
            'hash': res['hash'],
            'type': 'torrent',
            'quality': source_utils.getQuality(res['name']),
            'debrid_provider': res['debrid_provider'], # Assuming this is set correctly in your debrid library
            'provider': 'anidex',
            'episode_re': episode,
            'size': res['size'],
            'info': source_utils.getInfo(res['name']),
            'lang': source_utils.getAudio_lang(res['name'])
        }
        return source

    def get_sources(self, query, anilist_id, episode, status, media_type, rescrape):
        # ... (Your existing code for show, query, anidb) 

        url = '%s/?q=%s&id=%s' % (self._BASE_URL, urllib_parse.quote_plus(query), content_type_ids)

        html = client.request(url, headers=headers, timeout=70)
        soup = BeautifulSoup(html, "html.parser")
        logging.info("Soup structure:", soup.prettify())
        
        torrent_tables = soup.find('div', id='content').find_all('div', class_='table-responsive')

        list_ = []
        for torrent_table in torrent_tables:
            torrent_rows = torrent_table.find_all('tr')
            for torrent_row in torrent_rows:
                torrent_url_tag = torrent_row.find('a', {'href': lambda x: x and x.startswith('/dl/')})
                torrent_url = 'https://anidex.moe' + torrent_url_tag.get('href') if torrent_url_tag is not None else None

                name = torrent_row.find('a', class_='torrent').find('span', attrs={'title': True}).get('title')
                magnet = torrent_row.find('a', {'href': re.compile(r'(magnet:)[^&]+')}).get('href').strip() # Might need refinement if URL contains other parameters
                size = torrent_row.find('td', class_='text-center td-992').text

                list_.append({
                    'name': name,
                    'magnet': magnet,
                    'size': size,
                    'downloads': 0, # Assuming no way to extract this easily
                    'torrent': torrent_url
                })

        # Filtering logic 
        regex = r'Season\s*(\d+)\s*Episode\s*(\d+)|S(\d+)E(\d+)|(\d+)x(\d+)'
        regex_ep = r'\de(\d+)\b|\se(\d+)\b|\s-\s(\d{1,4})\b'
        rex = re.compile(regex)
        rex_ep = re.compile(regex_ep)

        filtered_list = []
        for idx, torrent in enumerate(list_):
            torrent['hash'] = re.findall(r'btih:(.*?)(?:&|$)', torrent['magnet'])[0] 

            if season:
                title = torrent['name'].lower()

                ep_match = rex_ep.findall(title)
                ep_match = list(map(int, list(filter(None, itertools.chain(*ep_match)))))

                # Episode filtering 
                if ep_match:
                    if ep_match[0] != int(episode):
                        regex_ep_range = r'\b(Ep?\s?\d+(?:[-~]\d+)?|S?\d+E?\d+)\b'
                        rex_ep_range = re.compile(regex_ep_range)

                        if not rex_ep_range.search(title):
                            continue # Skip torrent that doesn't match the episode

                    # Season Filtering 
                    match = rex.findall(title)
                    match = list(map(int, list(filter(None, itertools.chain(*match)))))

                    if not match or match[0] == int(season):
                        filtered_list.append(torrent) 
                else:
                    # Assuming if there's no ep match, you still want to consider the torrent
                    filtered_list.append(torrent)
            else:
                filtered_list.append(torrent)

        cache_list = debrid.TorrentCacheCheck().torrentCacheCheck(filtered_list)
        mapfunc = partial(self._parse_anidex_view, episode=episode)
        all_results = list(map(mapfunc, cache_list))
        return all_results
