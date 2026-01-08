import os
import requests
import json
import re
from fastapi import FastAPI, HTTPException
from bs4 import BeautifulSoup

app = FastAPI()

GENIUS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")

def get_lyrics_from_embed(song_id: int):
    """
    일반 페이지 스크래핑이 막힐 때 사용하는 강력한 우회 방법입니다.
    Genius의 '블로그 임베드(Embed)'용 자바스크립트 파일에서 가사를 추출합니다.
    """
    url = f"https://genius.com/songs/{song_id}/embed.js"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://genius.com/'
    }

    try:
        # 1. 임베드 JS 파일 요청
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # 2. 자바스크립트 코드 내에서 JSON 데이터 추출
        # document.write(JSON.parse('...')) 형태에서 ... 부분만 발라냄
        content = response.text
        
        # 정규표현식으로 JSON 문자열 찾기
        match = re.search(r"JSON\.parse\('(.*?)'\)", content)
        if not match:
            print("Embed pattern not found")
            return None
            
        # 이스케이프 문자 처리하여 JSON 로드
        json_str = match.group(1).encode().decode('unicode-escape')
        json_data = json.loads(json_str)
        
        # 3. HTML 추출
        html_content = json_data.get('song', {}).get('lyrics_html')
        if not html_content:
            return None
            
        # 4. HTML에서 텍스트만 깔끔하게 정제
        soup = BeautifulSoup(html_content, "html.parser")
        
        # 클릭해서 보는 주석(Annotation) 링크 제거
        for a in soup.find_all("a"):
            a.replace_with(a.get_text())
            
        lyrics_text = soup.get_text(separator="\n").strip()
        return lyrics_text

    except Exception as e:
        print(f"Embed Scraping Error: {e}")
        return None

@app.get("/")
def health_check():
    return {"status": "online", "method": "embed_bypass"}

@app.get("/search")
def search_song(q: str):
    if not q:
        raise HTTPException(status_code=400, detail="Query is required")
    if not GENIUS_TOKEN:
        raise HTTPException(status_code=500, detail="GENIUS_ACCESS_TOKEN is missing")

    # 1. 공식 API로 검색
    try:
        search_url = "https://api.genius.com/search"
        headers = {"Authorization": f"Bearer {GENIUS_TOKEN}"}
        resp = requests.get(search_url, params={"q": q}, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API Error: {e}")

    hits = data.get("response", {}).get("hits", [])
    if not hits:
        return {"found": False, "message": "Song not found"}

    # 2. 결과에서 ID와 URL 추출
    top_hit = hits[0]["result"]
    song_id = top_hit["id"]     # 여기서 ID를 가져옵니다 (예: 4734898)
    song_url = top_hit["url"]
    
    # 3. 임베드 방식으로 가사 추출
    print(f"Attempting embed fetch for ID: {song_id}")
    lyrics_text = get_lyrics_from_embed(song_id)

    if not lyrics_text:
        return {
            "found": True,
            "title": top_hit["title"],
            "artist": top_hit["primary_artist"]["name"],
            "lyrics": "Lyrics unavailable due to severe blocking.",
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
