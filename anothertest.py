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
    def _parse_anidex_view(res, episode):
        source = {
            'release_title': res['name'].encode('utf-8') if six.PY2 else res['name'],
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


    def get_sources(self, query, anilist_id, episode, status, media_type, rescrape):
        show = database.get_show(anilist_id)
        kodi_meta = pickle.loads(show.get('kodi_meta'))

        query = kodi_meta.get('ename')
        query = kodi_meta.get('name')
        query = self._clean_title(query)
        show_meta = database.get_show_meta(anilist_id)

        if rescrape:
            # todo add rescrape stuff here
            pass
            # todo
        if media_type != "movie":
            season = database.get_season_list(anilist_id)['season']
            season = str(season).zfill(2)
            query_template = "{title} - S{season}E{episode}"
            query = query_template.format(title=query, season=season, episode=episode.zfill(2))
        else:
            query_template = "{title} - {episode}"
            query = query_template.format(title=query, episode=episode.zfill(2))

        anidb = database.get_anidb_id(anilist_id)
        if anidb is None and show_meta:
            meta_ids = pickle.loads(show_meta['meta_ids'])
            anidb = meta_ids.get('anidb')

        # Generate the URL with the content type IDs, this case Anime
        content_type_ids = '1,2,3'
        url = '%s/?q=%s&id=%s' % (self._BASE_URL, urllib_parse.quote_plus(query), content_type_ids)

        html = client.request(url, headers=headers, timeout=70)
        soup = BeautifulSoup(html, "html.parser")
        print("Soup structure:", soup.prettify())
        soup_all = soup.find('div', id='content').find_all('div', class_='table-responsive')
        rex = r'(magnet:)[^&]+'

        list_ = []
        for soup in soup_all:
            torrent_url_tag = soup.find('a', {'href': lambda x: x and x.startswith('/dl/')})
            if torrent_url_tag is not None:
                torrenturl = 'https://anidex.info' + torrent_url_tag.get('href')
            else:
                torrenturl = None

            list_.append({
                'name': soup.find('a', class_='torrent').find('span', attrs={'title': True}).get('title'),
                'magnet': soup.find('a', {'href': re.compile(rex)}).get('href').strip(),
                'size': soup.find('td', class_='text-center td-992').text,
                'downloads': 0,
                'torrent': torrenturl
            })

        regex = r'Season\s*(\d+)\s*Episode\s*(\d+)|S(\d+)E(\d+)|(\d+)x(\d+)|(\d+)\s*of\s*(\d+)'
        regex_ep = r'\de(\d+)\b|\se(\d+)\b|\s-\s(\d{1,4})\b'
        rex = re.compile(regex)
        rex_ep = re.compile(regex_ep)
        url = '%s/?q=%s&id=%s' % (self._BASE_URL, urllib_parse.quote_plus(query), content_type_ids)

        filtered_list = []
        for idx, torrent in enumerate(list_):
            torrent['hash'] = re.findall(r'btih:(.*?)(?:&|$)', torrent['magnet'])[0]
            if season:
                title = torrent['name'].lower()

                ep_match = rex_ep.findall(title)
                ep_match = list(map(int, list(filter(None, itertools.chain(*ep_match)))))

                if ep_match and ep_match[0] != int(episode):
                    regex_ep_range = r'\b(Ep?\s?\d+(?:[-~]\d+)?|S?\d+E?\d+)\b'
                    rex_ep_range = re.compile(regex_ep_range)

                    if not rex_ep_range.search(title):
                        continue

                match = rex.findall(title)
                match = list(map(int, list(filter(None, itertools.chain(*match)))))
                if not match or match[0] == int(season):
                    filtered_list.append(torrent)
            else:
                filtered_list.append(torrent)

        cache_list = debrid.TorrentCacheCheck().torrentCacheCheck(list_)
        mapfunc = partial(self._parse_anidex_view, episode=episode)
        all_results = list(map(mapfunc, cache_list))
        return all_results
