import re
import itertools
import pickle
import xbmc

from functools import partial
from bs4 import BeautifulSoup
from resources.lib.ui.BrowserBase import BrowserBase
from resources.lib.ui import database, source_utils, client
from resources.lib import debrid
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
    'Accept-Encoding': 'none',
    'Accept-Language': 'en-US,en;q=0.8',
    'Connection': 'keep-alive'
}

class sources(BrowserBase):
    _BASE_URL = 'https://anidex.info'
    
    def get_sources(self, query, anilist_id, episode, status, media_type, rescrape):
        query = self._clean_title(query)
        query = self._sphinx_clean(query)
        # Add debugging logs to track the title formatting issue
        print(f"Before formatting: {query}")
        # Remove extra parentheses from the title
        query = query.strip('()')
        print(f"After formatting: {query}")
        
        if rescrape:
            # todo add rescrape stuff here
            pass
            # return self._get_episode_sources_pack(query, anilist_id, episode)
        if media_type != "movie":
            query = '%s - %s' % (query, episode.zfill(2))  # noQA
            season = database.get_season_list(anilist_id)['season']
            season = str(season).zfill(2)
            query += '| S%sE%s ' % (season, episode.zfill(2))
        else:
            season = None
        rex = r'(magnet:)+[^"]*'

        # Generate the 'id' parameter based on the desired content type
        # In this case, we're searching for anime torrents
        content_type_ids = '1,2,3'
        show_meta = database.get_show_meta(anilist_id)
        params = {
            'q': query,
            'id': content_type_ids
        }

        html = client.request(self._BASE_URL, params=params, headers=headers)
        soup = BeautifulSoup(html, "html.parser")
        soup_all = soup.find('div', id='content').find_all('div', class_='table-responsive')
        list_ = [
            {'name': soup.find('div', class_='span-1440').a.text,
             'magnet': soup.find('a', {'href': re.compile(rex)}).get('href'),
             'size': soup.find('div', class_='text-center td-992').text,
             'downloads': 0,
             'torrent': soup.find('a', class_='fas fa-download fa-lg').get('href')
             }
            for soup in soup_all
        ]

        regex = r'\ss(\d+)|season\s(\d+)|(\d+)+(?:st|[nr]d|th)\sseason'
        regex_ep = r'\de(\d+)\b|\se(\d+)\b|\s-\s(\d{1,4})\b'
        rex = re.compile(regex)
        rex_ep = re.compile(regex_ep)

        filtered_list = []
        for torrent in list_:
            try:
                torrent['hash'] = re.match(r'https://anidex.info/dl/([^&]+)', torrent['torrent']).group(1)
            except AttributeError:
                continue
            if season:
                title = torrent['name'].lower()

                ep_match = rex_ep.findall(title)
                ep_match = list(map(int, list(filter(None, itertools.chain(*ep_match)))))

                if ep_match and ep_match[0] != int(episode):
                    regex_ep_range = r'\s\d+-\d+|\s\d+~\d+|\s\d+\s-\s\d+|\s\d+\s~\s\d+'
                    rex_ep_range = re.compile(regex_ep_range)

                    if not rex_ep_range.search(title):
                        continue

                match = rex.findall(title)
                match = list(map(int, list(filter(None, itertools.chain(*match)))))

                if not match or match[0] == int(season):
                    filtered_list.append(torrent)

            else:
                filtered_list.append(torrent)
        cache_list = debrid.TorrentCacheCheck().torrentCacheCheck(filtered_list)
        mapfunc = partial(parse_anidex_view, episode=episode)
        all_results = list(map(mapfunc, cache_list))
        return all_results


def parse_anidex_view(res, episode):
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
