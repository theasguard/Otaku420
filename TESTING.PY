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

        regex_season_episode = re.compile(r'\b(?:s|season|series)\s*(\d+)\b.*?\b(?:e|ep|eps|episode)\s*(\d+)\b', re.IGNORECASE)
        regex_episode = re.compile(r'\b(?:e|ep|eps|episode)\s*(\d{1,4})\b', re.IGNORECASE)
        regex_dub = re.compile(r'\b(?:dub|dual|multi)\b', re.IGNORECASE)
        filtered_list = []

        for torrent in list_:
            torrent['hash'] = re.findall(r'btih:(.*?)(?:&|$)', torrent['magnet'])[0]
            title = torrent['name'].lower()

            # Check for season and episode match
            if season:
                season_episode_match = regex_season_episode.search(title)
                if season_episode_match:
                    season_num, episode_num = map(int, season_episode_match.groups())
                    if season_num == int(season) and episode_num == int(episode):
                        filtered_list.append(torrent)
                        continue

            # Check for episode match if season is not specified
            episode_match = regex_episode.search(title)
            if episode_match:
                episode_num = int(episode_match.group(1))
                if episode_num == int(episode):
                    filtered_list.append(torrent)
                    continue

            # Check for English dub or dual audio
            if regex_dub.search(title):
                filtered_list.append(torrent)

            # Include season packs
            if 'batch' in title or 'complete' in title:
                filtered_list.append(torrent)

        # Additional filtering to ensure correct season and episode matching
        final_filtered_list = []
        for torrent in filtered_list:
            title = torrent['name'].lower()
            if season:
                season = int(season)
                episode = int(episode)
                if f's{season:02d}e{episode:02d}' in title or f's{season}e{episode}' in title:
                    final_filtered_list.append(torrent)
                elif f'season {season}' in title and f'episode {episode}' in title:
                    final_filtered_list.append(torrent)
            else:
                episode = int(episode)
                if f'episode {episode}' in title or f'e{episode:02d}' in title or f'e{episode}' in title:
                    final_filtered_list.append(torrent)

        cache_list = debrid.TorrentCacheCheck().torrentCacheCheck(final_filtered_list)
        cache_list = sorted(cache_list, key=lambda k: k['downloads'], reverse=True)
        mapfunc = partial(self._parse_nyaa_episode_view, episode=episode)
        all_results = list(map(mapfunc, cache_list))
        return all_results
