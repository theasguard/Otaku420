    def get_syns(self, query, anilist_id):
        query = ""

        try:
            response = client.request("https://find-my-anime.dtimur.de/api?id={}&provider=Anilist".format(anilist_id))
            data = json.loads(response)
            synonyms = data[0].get('synonyms', [])
            
            english_synonyms = [synonym for synonym in synonyms if re.match(r"^[A-Za-z\s]+$", synonym)]
            romaji_synonyms = [synonym for synonym in synonyms if re.match(r"^[A-Za-z\s]+$", synonym) and not re.match(r"[^-a-zA-Z\s]+", synonym)]

            for synonym in english_synonyms + romaji_synonyms:
                encoded_synonym = urllib.parse.quote(synonym)
                query += " | ({})".format(encoded_synonym)

        except Exception as e:
            print(f"Error: {e}")
            fallback_data = self.fallback_anime_data(anilist_id)
            if fallback_data:
                for synonym in fallback_data.get("synonyms", []):
                    encoded_synonym = urllib.parse.quote(synonym)
                    query += " | ({})".format(encoded_synonym)
            else:
                print("Fallback data not found. Returning empty query.")
                query = ""

        control.setSetting("torrent.query.data", str(query))


    def fallback_anime_data(self, anilist_id):
        # Load the fallback JSON data
        fallback_data_url = "https://github.com/manami-project/anime-offline-database/raw/master/anime-offline-database.json"
        response = client.request(fallback_data_url)
        data = json.loads(response)

        # Find the relevant anime data based on the Anilist ID
        for anime in data["data"]:
            for source in anime["sources"]:
                if "anilist.co/anime/" + str(anilist_id) in source:
                    return anime["title"]

        # If no matching anime is found, return an empty string
        return ""
