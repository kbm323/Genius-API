import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import lyricsgenius

app = FastAPI()

# 환경변수에서 토큰 가져오기
GENIUS_TOKEN = os.getenv("GENIUS_ACCESS_TOKEN")
if not GENIUS_TOKEN:
    print("Warning: GENIUS_ACCESS_TOKEN is not set.")

# Genius 클라이언트 초기화
genius = lyricsgenius.Genius(GENIUS_TOKEN)
genius.verbose = False # 로그 지저분하지 않게
genius.remove_section_headers = False # [Verse], [Chorus] 태그 유지 여부 (필요에 따라 True로 변경)

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
        # 에러 발생 시 (타임아웃 등)
        raise HTTPException(status_code=500, detail=str(e))
