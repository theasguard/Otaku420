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

