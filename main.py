import os
import requests
from fastapi import FastAPI, HTTPException

app = FastAPI()

GENIUS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")

def get_lyrics_from_lrclib(title: str, artist: str, duration: int = None):
    """
    Genius가 막혔으므로, 차단 없는 오픈소스 API (LRCLIB)에서 가사를 가져옵니다.
    """
    try:
        # LRCLIB API 엔드포인트
        url = "https://lrclib.net/api/get"
        params = {
            "artist_name": artist,
            "track_name": title
        }
        if duration:
            params["duration"] = duration

        resp = requests.get(url, params=params, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            # plainLyrics(일반 가사)가 있으면 반환, 없으면 syncedLyrics(싱크 가사) 반환
            return data.get("plainLyrics") or data.get("syncedLyrics")
        else:
            print(f"LRCLIB failed: {resp.status_code}")
            return None
            
    except Exception as e:
        print(f"LRCLIB Error: {e}")
        return None

@app.get("/")
def health_check():
    return {"status": "online", "mode": "Hybrid (Genius Meta + LRCLIB Text)"}

@app.get("/search")
def search_song(q: str):
    if not q:
        raise HTTPException(status_code=400, detail="Query is required")
    if not GENIUS_TOKEN:
        raise HTTPException(status_code=500, detail="GENIUS_ACCESS_TOKEN is missing")

    # 1. [Genius] 공식 API로 메타데이터 검색 (제목, 가수, 이미지)
    try:
        search_url = "https://api.genius.com/search"
        headers = {"Authorization": f"Bearer {GENIUS_TOKEN}"}
        resp = requests.get(search_url, params={"q": q}, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Genius API Error: {e}")

    hits = data.get("response", {}).get("hits", [])
    if not hits:
        return {"found": False, "message": "Song not found on Genius"}

    # 가장 정확한 결과 가져오기
    top_hit = hits[0]["result"]
    
    # 📌 [수정됨] 여기서 ID를 추출합니다!
    genius_id = top_hit["id"] 
    genius_title = top_hit["title"]
    genius_artist = top_hit["primary_artist"]["name"]
    genius_url = top_hit["url"]
    image_url = top_hit["song_art_image_url"]

    # 2. [LRCLIB] 가사 텍스트 가져오기
    print(f"Fetching lyrics for: {genius_title} by {genius_artist}")
    lyrics_text = get_lyrics_from_lrclib(genius_title, genius_artist)

    # 3. 결과 반환
    if lyrics_text:
        return {
            "found": True,
            "id": genius_id,  # 📌 ID 추가됨
            "source": "LRCLIB",
            "title": genius_title,
            "artist": genius_artist,
            "lyrics": lyrics_text,
            "image_url": image_url,
            "genius_link": genius_url
        }
    else:
        # LRCLIB에 없는 경우
        return {
            "found": True,
            "id": genius_id,  # 📌 ID 추가됨 (이걸로 n8n에서 Scrapfly 돌리면 됨)
            "source": "Genius Link Only",
            "title": genius_title,
            "artist": genius_artist,
            "lyrics": "Lyrics text not available in database. Please check the link.",
            "lyrics_url": genius_url,
            "image_url": image_url
        }
