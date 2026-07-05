import yt_dlp

class YouTubeSearchService:
    def __init__(self):
        self.ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'skip_download': True,
            'no_warnings': True,
        }

    def search_songs(self, query: str, limit: int = 5) -> list[dict]:
        search_query = f"ytsearch{limit}:{query}"
        
        with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=False)
            
        results = []
        if 'entries' in info:
            for entry in info['entries']:
                thumbnails = entry.get('thumbnails')
                thumbnail_url = thumbnails[-1].get('url') if thumbnails else None
                
                results.append({
                    'youtube_id': entry.get('id'),
                    'title': entry.get('title'),
                    'duration': entry.get('duration'),
                    'url': entry.get('url'),
                    'thumbnail_url': thumbnail_url
                })
        return results