# Genius-API

이 프로젝트는 Genius API를 활용하여 노래 가사를 검색하고 텍스트로 반환해주는 경량 마이크로서비스입니다.
Python FastAPI와 lyricsgenius 라이브러리를 기반으로 제작되었으며, Northflank와 같은 클라우드 플랫폼에 배포하여 n8n 등의 자동화 도구와 연동하기 위해 설계되었습니다.

## 주요 기능
* 가수와 노래 제목으로 가사 검색
* 가사 텍스트, 앨범 아트 URL 등 메타데이터 반환
* Scraping 과정을 서버 내부에서 처리하여 클라이언트(n8n)의 차단 방지
* Docker 기반의 간편한 배포

## 사전 준비 (Prerequisites)
이 서비스를 실행하려면 Genius API Access Token이 필요합니다.
1. Genius API Clients Page (https://genius.com/api-clients)에 접속합니다.
2. 새로운 API Client를 생성합니다.
3. 'Client Access Token'을 복사해 둡니다. (이 토큰이 배포 시 환경 변수로 사용됩니다.)

## 배포 가이드 (Northflank)

이 프로젝트는 Dockerfile을 포함하고 있어 Northflank에 즉시 배포 가능합니다.

1. 서비스 생성: Northflank에서 'Combined Service' 또는 'API Service'를 생성하고 이 Git 리포지토리를 연결합니다.
2. Build 설정:
    * Build Type: Dockerfile
    * Context: / (Root)
3. 환경 변수 (Environment Variables) 설정:
    * Runtime Environment Variables에 다음 변수를 추가합니다.
    * Key: GENIUS_ACCESS_TOKEN
    * Value: (위에서 발급받은 Genius Access Token)
4. 네트워킹 (Networking) 설정:
    * Port: 8000
    * Protocol: HTTP
    * Publicly accessible: 활성화 (Check)
5. 배포 (Deploy): 서비스를 시작합니다.

## API 사용법

### 1. 헬스 체크 (Health Check)
서버가 정상적으로 작동 중인지 확인합니다.
* Endpoint: GET /
* Response: {"status": "Lyrics Service is running"}

### 2. 가사 검색 (Search Lyrics)
* Endpoint: GET /search
* Query Parameter: q (검색어: 아티스트명 + 노래제목)
* 예시: https://your-service.northflank.app/search?q=Hoang Hold On Tight

[성공 응답 예시 (200 OK)]
{
  "found": true,
  "title": "Hold On Tight (Culture Code Remix)",
  "artist": "Hoang",
  "lyrics": "[Verse 1]\nBeen thinking lately...\n(가사 내용 전체)",
  "image_url": "https://images.genius.com/..."
}

[실패 응답 예시 (곡 없음)]
{
  "found": false,
  "message": "Song not found"
}

## n8n 연동 방법 (HTTP Request Node)

n8n 워크플로우에서 다음과 같이 설정하여 사용하세요.

* Node: HTTP Request
* Method: GET
* URL: https://[본인의-Northflank-주소]/search
* Query Parameters:
    * Name: q
    * Value: {{ $json.artist_name }} {{ $json.song_title }}
* Authentication: None (공개 포트인 경우)

---

### 로컬 실행 (Local Development)

로컬 컴퓨터에서 테스트하려면 다음 단계를 따르세요.

# 1. 리포지토리 클론
git clone [REPOSITORY_URL]

# 2. 패키지 설치
pip install -r requirements.txt

# 3. 환경 변수 설정 (Mac/Linux 예시)
export GENIUS_ACCESS_TOKEN="your_token_here"

# 4. 서버 실행
uvicorn main:app --reload

서버 실행 후 http://127.0.0.1:8000/docs 로 접속하면 Swagger UI를 통해 API를 직접 테스트해볼 수 있습니다.
