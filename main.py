import os
import requests
from fastapi import FastAPI, HTTPException
from bs4 import BeautifulSoup

app = FastAPI()

# 환경변수 가져오기
GENIUS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")

def get_lyrics_scraping(url):
    """
    공식 API는 가사 텍스트를 안 주므로, URL로 접속해서 텍스트만 긁어오는 함수
    """
    # 봇 차단 방지용 헤더
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Connection': 'keep-alive',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"Scraping Error: {e}")
        return None

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Genius의 최신 가사 구조
    lyrics_containers = soup.find_all("div", attrs={"data-lyrics-container": "true"})
    
    if not lyrics_containers:
        return None

    lyrics = ""
    for container in lyrics_containers:
        for br in container.find_all("br"):
            br.replace_with("\n")
        lyrics += container.get_text() + "\n\n"
        
    return lyrics.strip()

@app.get("/")
def health_check():
    return {
        "status": "online", 
        "token_configured": bool(GENIUS_TOKEN)
    }

@app.get("/search")
def search_song(q: str):
    if not q:
        raise HTTPException(status_code=400, detail="Query is required")
    
    if not GENIUS_TOKEN:
        raise HTTPException(status_code=500, detail="Server Error: GENIUS_ACCESS_TOKEN is missing")

    # 1. 공식 API로 곡 검색
    search_url = "https://api.genius.com/search"
    headers = {"Authorization": f"Bearer {GENIUS_TOKEN}"}
    params = {"q": q}

    try:
        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid Access Token")
            
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Genius API Error: {str(e)}")

    hits = data.get("response", {}).get("hits", [])
    if not hits:
        return {"found": False, "message": "Song not found"}

    top_hit = hits[0]["result"]
    song_url = top_hit["url"]
    
    # 2. 가사 긁어오기
    lyrics_text = get_lyrics_scraping(song_url)

    if not lyrics_text:
        return {
            "found": True,
            "title": top_hit["title"],
            "artist": top_hit["primary_artist"]["name"],
            "lyrics": "Lyrics text could not be extracted (Bot protection active).",
            "lyrics_url": song_url,
            "image_url": top_hit["song_art_image_url"]
        }

    return {
        "found": True,
        "title": top_hit["title"],
        "artist": top_hit["primary_artist"]["name"],
        "lyrics": lyrics_text,
        "image_url": top_hit["song_art_image_url"]
    }
