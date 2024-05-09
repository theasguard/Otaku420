def _get_episode_sources_backup(self, db_query, anilist_id, episode):
    # Use the Kodi JSON-RPC API to search the AniList API
    url = 'https://graphql.anilist.co'
    headers = {'Content-Type': 'application/json'}
    query = '''
    query ($id: Int) {
      Media (id: $id) {
        id
        title {
          romaji
        }
      }
    }
    '''
    data = {'query': query, 'variables': {'id': anilist_id}}
    response = requests.post(url, headers=headers, json=data)
    results = response.json()['data']['Media']

    if not results:
        return []

    # Extract the relevant information from the search results
    show = results[0]
    query = show['title']['romaji'].encode('utf-8') if six.PY2 else show['title']['romaji']
    _zfill = 2
    episode = episode.zfill(_zfill)
    query = urllib_parse.quote_plus(query)
    url = '%s?f=0&c=1_0&q=%s&s=downloads&o=desc' % (self._BASE_URL, query)
    return self._process_nyaa_backup(url, anilist_id, _zfill, episode)
