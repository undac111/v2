from youtube_search import YoutubeSearch
import json

def search_youtube(query):
    results = YoutubeSearch(query, max_results=1).to_json()
    data = json.loads(results)

    if data["videos"]:
        video_id = data["videos"][0]["id"]
        return f"https://www.youtube.com/watch?v={video_id}"
    return None  # Retorna None si no hay resultados







