import itertools
import json
import pickle
import re
import six

from functools import partial
from bs4 import BeautifulSoup, SoupStrainer
from resources.lib import debrid
from resources.lib.ui import control, database, source_utils
from resources.lib.ui.BrowserBase import BrowserBase
from six.moves import urllib_parse


class sources(BrowserBase):
    _BASE_URL = 'https://nyaa-si.translate.goog/?_x_tr_sl=es&_x_tr_tl=en&_x_tr_hl=en/' if control.getSetting('provider.nyaaalt') == 'true' else 'https://nyaa.si/'

    @staticmethod
    def _parse_nyaa_episode_view(res, episode):
        source = {
            'release_title': res['name'].encode('utf-8') if six.PY2 else res['name'],
            'hash': res['hash'],
            'type': 'torrent',
            'quality': source_utils.getQuality(res['name']),
            'debrid_provider': res['debrid_provider'],
            'provider': 'nyaa',
            'episode_re': episode,
            'size': res['size'],
            'info': source_utils.getInfo(res['name']),
            'lang': source_utils.getAudio_lang(res['name'])
        }

        return source

    @staticmethod
    def _parse_nyaa_cached_episode_view(res, episode):
        source = {
            'release_title': res['name'].encode('utf-8') if six.PY2 else res['name'],
            'hash': res['hash'],
            'type': 'torrent',
            'quality': source_utils.getQuality(res['name']),
            'debrid_provider': res['debrid_provider'],
            'provider': 'nyaa (Local Cache)',
            'episode_re': episode,
            'size': res['size'],
            'info': source_utils.getInfo(res['name']),
            'lang': source_utils.getAudio_lang(res['name'])
        }

        return source

    def _process_nyaa_episodes(self, url, episode, season=None):
        html = self._get_request(url)
        mlink = SoupStrainer('div', {'class': 'table-responsive'})
        soup = BeautifulSoup(html, "html.parser", parse_only=mlink)
        rex = r'(magnet:)+[^"]*'

        list_ = [
            {'magnet': i.find('a', {'href': re.compile(rex)}).get('href'),
             'name': i.find_all('a', {'class': None})[1].get('title'),
             'size': i.find_all('td', {'class': 'text-center'})[1].text.replace('i', ''),
             'downloads': int(i.find_all('td', {'class': 'text-center'})[-1].text)}
            for i in soup.select("tr.danger,tr.default,tr.success")
        ]

        regex = r'\b(?:s|season|series)\s*(\d+)\b(?:episode|ep|eps)\s*(\d+)'
        regex_ep = r'\b(?:e|ep|eps|episode)\s*(\d{1,4})\b'
        regex_ep_range = r'\s(?:\d+(?:[-~]\d+)?)(?:-(?:\d+(?:[-~]\d+)?))?'
        regex_season = r'\b(?:s|season|series)\s*(\d+)\b'
        regex_title = r'^r'(.+)'
        rex = re.compile(regex)
        rex_ep = re.compile(regex_ep)
        rex_ep_range = re.compile(regex_ep_range)
        rex_season = re.compile(regex_season)
        rex_title = re.compile(regex_title)
        filtered_list = []

        for idx, torrent in enumerate(list_):
            torrent['hash'] = re.findall(r'btih:(.*?)(?:


                                         
