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
    regex_ep = r'\b(?:e|ep|eps|episode)\s*(\d{1,4})\b'
    regex_ep_range = r'\s(?:\d+(?:[-~]\d+)?)(?:-(?:\d+(?:[-~]\d+)?))?'
    regex_season = r'\b(?:s|season|series)\s*(\d+)\b'
    regex_title = r'^r'(.+)'
    rex = re.compile(regex)
    rex_ep = re.compile(regex_ep)
    rex_ep_range = re.compile(regex_ep_range)
    rex_season = re.compile(regex_season)
    rex_title = re.compile(regex_title)

    url = '%s?f=0&c=1_2&q=%s&s=seeders&&o=desc' % (self._BASE_URL, urllib_parse.quote_plus(query))
    return self._process_nyaa_backup(url, anilist_id, 2, episode.zfill(2), True)
