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
    
    # Genius의 최신 가사 구조 (div[data-lyrics-container="true"])
    lyrics_containers = soup.find_all("div", attrs={"data-lyrics-container": "true"})
    
    if not lyrics_containers:
        return None

    lyrics = ""
    for container in lyrics_containers:
        # <br> 태그를 줄바꿈으로 변경하여 가독성 확보
        for br in container.find_all("br"):
            br.replace_with("\n")
        lyrics += container.get_text() + "\n\n"
        
    return lyrics.strip()

@app.get("/")
def health_check():
    # 토큰이 잘 들어왔는지 확인
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

    # 1. 공식 API로 메타데이터 검색 (여기는 절대 403이 안 뜹니다)
    search_url = "https://api.genius.com/search"
    headers = {"Authorization": f"Bearer {GENIUS_TOKEN}"}
    params = {"q": q}

    try:
        response = requests.get(search_url, params=params, headers=headers, timeout=10)
        
        # 토큰이 틀렸을 경우 401 에러 처리
        if response.status_code == 401:
            raise HTTPException(status_code=401, detail="Invalid Access Token")
            
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Genius API Error: {str(e)}")

    # 검색 결과가 없으면
    hits = data.get("response", {}).get("hits", [])
    if not hits:
        return {"found": False, "message": "Song not found"}

    # 2. 첫 번째 결과 추출
    top_hit = hits[0]["result"]
    song_url = top_hit["url"]
    
    # 3. 가사 긁어오기 (Scraping)
    lyrics_text = get_lyrics_scraping(song_url)

    if not lyrics_text:
        # 곡은 찾았는데 텍스트 추출에 실패한 경우 (Scraping 차단 등)
        return {
            "found": True,
            "title": top_hit["title"],
            "artist": top_hit["primary_artist"]["name"],
            "lyrics": "Lyrics text could not be extracted (Bot protection active). Please verify the URL.",
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
