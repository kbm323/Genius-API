import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import lyricsgenius

app = FastAPI()

# 환경변수에서 토큰 가져오기
GENIUS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")
if not GENIUS_TOKEN:
    print("⚠️ Warning: GENIUS_ACCESS_TOKEN is not set in Runtime Variables.")

# Genius 클라이언트 초기화
# timeout: 응답 대기 시간을 15초로 늘림
genius = lyricsgenius.Genius(GENIUS_TOKEN, timeout=15)

# 로그 줄이기
genius.verbose = False 
# [Verse], [Chorus] 태그 유지
genius.remove_section_headers = False 

# 🚨 [중요] 403 에러 방지용 User-Agent 설정 (크롬 브라우저로 위장)
genius.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

@app.get("/")
def read_root():
    return {"status": "Lyrics Service is running"}

@app.get("/search")
def search_lyrics(q: str):
    """
    쿼리(q)를 받아 가사를 검색하고 반환합니다.
    """
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")

    # 토큰이 없는 경우 방어 로직
    if not GENIUS_TOKEN:
        raise HTTPException(status_code=500, detail="Server Error: API Token is missing.")

    try:
        # 가사 검색
        song = genius.search_song(q)
        
        if song:
            return {
                "found": True,
                "title": song.title,
                "artist": song.artist,
                "lyrics": song.lyrics,
                "image_url": song.song_art_image_url
            }
        else:
            return {
                "found": False,
                "message": "Song not found"
            }
    except Exception as e:
        # 에러 로그 출력 (Northflank 로그에서 확인 가능)
        print(f"Error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
