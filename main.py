import os
import requests
import cloudscraper
from fastapi import FastAPI, HTTPException
from bs4 import BeautifulSoup

app = FastAPI()

GENIUS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")

# Cloudflare 우회용 스크래퍼 생성
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

def get_lyrics_from_lrclib(title: str, artist: str):
    """1순위: LRCLIB에서 안전하게 가져오기"""
    try:
        url = "https://lrclib.net/api/get"
        params = {"artist_name": artist, "track_name": title}
        resp = requests.get(url, params=params, timeout=5) # 5초 안에 안오면 포기
        if resp.status_code == 200:
            data = resp.json()
            return data.get("plainLyrics") or data.get("syncedLyrics")
    except:
        return None
    return None

def get_lyrics_from_genius_web(url: str):
    """2순위: Cloudscraper로 Genius 웹페이지 강제 돌파"""
    try:
        # requests.get 대신 scraper.get을 사용 (Cloudflare 우회)
        response = scraper.get(url, timeout=15)
        
        if response.status_code != 200:
            print(f"Genius Scraping Failed: {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 가사 컨테이너 찾기
        lyrics_containers = soup.find_all("div", attrs={"data-lyrics-container": "true"})
        
        if not lyrics_containers:
            return None

        lyrics = ""
        for container in lyrics_containers:
            # <br> 태그를 줄바꿈으로 변경
            for br in container.find_all("br"):
                br.replace_with("\n")
            lyrics += container.get_text() + "\n\n"
            
        return lyrics.strip()

    except Exception as e:
        print(f"Scraping Error: {e}")
        return None

@app.get("/")
def health_check():
    return {"status": "Hybrid Mode (LRCLIB + Cloudscraper)"}

@app.get("/search")
def search_song(q: str):
    if not q:
        raise HTTPException(status_code=400, detail="Query required")
    if not GENIUS_TOKEN:
        raise HTTPException(status_code=500, detail="Token missing")

    # [1단계] Genius API로 곡 정보 검색 (제목, 가수, URL 확보)
    try:
        headers = {"Authorization": f"Bearer {GENIUS_TOKEN}"}
        resp = requests.get("https://api.genius.com/search", params={"q": q}, headers=headers, timeout=10)
        data = resp.json()
    except:
        return {"lyrics": "Error: Genius API failed"}

    hits = data.get("response", {}).get("hits", [])
    if not hits:
        return {"lyrics": "Song not found"}

    top_hit = hits[0]["result"]
    title = top_hit["title"]
    artist = top_hit["primary_artist"]["name"]
    genius_url = top_hit["url"]

    # [2단계] LRCLIB 시도 (가장 안전)
    print(f"Trying LRCLIB for: {title}")
    lyrics = get_lyrics_from_lrclib(title, artist)

    if lyrics:
        return {"lyrics": lyrics, "source": "LRCLIB"}

    # [3단계] LRCLIB에 없으면 Genius 웹페이지 긁기 (Cloudscraper 사용)
    print(f"LRCLIB failed. Scraping Genius directly: {genius_url}")
    lyrics = get_lyrics_from_genius_web(genius_url)

    if lyrics:
        return {"lyrics": lyrics, "source": "Genius Web"}
    else:
        return {
            "lyrics": "Lyrics text could not be extracted even with Cloudscraper.",
            "url": genius_url # 실패하면 링크라도 줌
        }
