import json
import requests

def get_sources(self, query, anilist_id, episode, status, media_type, rescrape):
    query = self._clean_title(query)

    if media_type == 'movie':
        return self._get_movie_sources(query, anilist_id, episode)

    sources = self._get_episode_sources(query, anilist_id, episode, status, rescrape)

    if not sources and ':' in query:
        q1, q2 = (q[1:-1].split(':')[0] for q in query.split('|'))
        query2 = f"({q1})|({q2})"
        sources = self._get_episode_sources(query2, anilist_id, episode, status, rescrape)

    if not sources:
        sources = self._get_episode_sources_backup(query, anilist_id, episode)

    # Use the Kodi JSON-RPC API to search the AniList API
    url = 'https://graphql.anilist.co'
    headers = {'Content-Type': 'application/json'}
    query = '''
    query ($query: String) {
      Media (search: $query, type: ANIME) {
        id
        title {
          romaji
        }
      }
    }
    '''
    data = {'query': query, 'variables': {'query': query}}
    response = requests.post(url, headers=headers, json=data)
    results = response.json()['data']['Media']

    # Extract the relevant information from the search results
    for result in results:
        source = {
            'release_title': result['title']['romaji'],
            'hash': None,
            'type': 'torrent',
            'quality': source_utils.getQuality(result['title']['romaji']),
            'debrid_provider': None,
            'provider': 'anilist',
            'episode_re': None,
            'size': None,
            'info': source_utils.getInfo(result['title']['romaji']),
            'lang': source_utils.getAudio_lang(result['title']['romaji'])
        }

        sources.append(source)

    # Remove duplicate sources
    sources = list(set(sources))

    return sources
