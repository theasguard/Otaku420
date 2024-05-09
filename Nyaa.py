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

def _get_episode_sources_pack(self, show, anilist_id, episode):
    query = '%s "Batch"|"Complete Series"' % show

    episodes = pickle.loads(database.get_show(anilist_id)['kodi_meta'])['episodes']
    if episodes:
        query += '|"01-{0}"|"01~{0}"|"01 - {0}"|"01 ~ {0}"'.format(episodes)

    season = database.get_tvdb_season(anilist_id)
    if season:
        query += '|"S{0}"|"Season {0}"'.format(season)

    part = database.get_tvdb_part(anilist_id)
    if part:
        query += '|"Part {0}"|"Cour {0}"'.format(part)

    season_list = database.get_season_list(anilist_id)
    if season_list:
        season_list = season_list['season']
        query += '|"%s"' % season_list

    regex = r'\b(?:s|season|series)\s*(\d+)\b(?:episode|ep|eps)\s*(\d+)'
    regex_season = r'\b(?:s|season|series)\s*(\d+)\b'
    regex_title = r'^r'(.+)'
    rex = re.compile(regex)
    rex_season = re.compile(regex_season)
    rex_title = re.compile(regex_title)

    url = '%s?f=0&c=1_2&q=%s&s=seeders&&o=desc' % (self._BASE_URL, urllib_parse.quote_plus(query))
    return self._process_nyaa_backup(url, anilist_id, 2, episode.zfill(2), True)


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
        torrent['hash'] = re.findall(r'btih:(.*?)(?:&|$)', torrent['magnet'])[0]
        if season:
            title = torrent['name'].lower()

            ep_match = rex_ep.findall(title)
            ep_match = list(map(int, list(filter(None, itertools.chain(*ep_match)))))
            if ep_match and ep_match[0] != int(episode):
                if not rex_ep_range.search(title):
                    continue

            match = rex.findall(title)
            match = list(map(int, list(filter(None, itertools.chain(*match)))))
            if not match or match[0] == int(season):
                filtered_list.append(torrent)
        else:
            filtered_list.append(torrent)

    cache_list = debrid.TorrentCacheCheck().torrentCacheCheck(filtered_list)
    cache_list = sorted(cache_list, key=lambda k: k['downloads'], reverse=True)
    mapfunc = partial(self._parse_nyaa_episode_view, episode=episode)
    all_results = list(map(mapfunc, cache_list))
    return all_results

