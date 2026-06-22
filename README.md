# 📸 Instagram Analyzer

인스타그램 공식 데이터 내보내기 파일을 분석하는 **로컬 전용 웹 애플리케이션**입니다.  
모든 데이터는 내 PC에서만 처리되며 외부로 전송되지 않습니다.

---

## ✨ 주요 기능

| 기능 | 설명 |
|------|------|
| **팔로워 목록** | 나를 팔로우하는 계정과 팔로우 날짜 조회, 검색·정렬·CSV 내보내기 |
| **팔로잉 목록** | 내가 팔로우하는 계정 목록 조회 |
| **언팔 분석** | 맞팔 안 됨 / 나만 팔로우 / 맞팔 / 언팔로워 감지 / 내가 최근 언팔 |
| **활동 검색** | 계정별 좋아요·댓글 내역 + DM 공유·반응·메시지 기록 검색 |
| **업로드 히스토리** | 업로드마다 팔로워·팔로잉 수를 기록하고 변화 추이 비교 |
| **관리자 페이지** | 사용자 생성·수정·삭제, 시스템 통계 |
| **Windows 런처** | 트레이 아이콘 + 실시간 로그 뷰어 GUI |

---

## 🗂 분석 가능한 데이터

인스타그램 앱 → **설정 → 계정 센터 → 내 정보 및 권한 → 정보 다운로드** → JSON 형식으로 요청

| 파일 | 위치 | 내용 |
|------|------|------|
| `followers_1.json` | `connections/followers_and_following/` | 팔로워 목록 + 날짜 |
| `following.json` | `connections/followers_and_following/` | 팔로잉 목록 + 날짜 |
| `liked_posts.json` | `likes/` | 내가 좋아요 누른 게시물 |
| `liked_comments.json` | `likes/` | 내가 좋아요 누른 댓글 |
| `post_comments_1.json` | `comments/` | 내가 단 댓글 |
| `recently_unfollowed_profiles.json` | `connections/followers_and_following/` | 내가 최근 언팔한 계정 |
| `messages/inbox/**` (ZIP 전체) | DM 폴더 | DM 공유·반응·메시지 기록 |

> ZIP 파일 전체를 업로드하면 자동으로 필요한 파일을 추출합니다.

---

## 🚀 설치 및 실행

### 요구사항
- Python 3.11 이상

### 1. 의존성 설치

```bash
pip install -r instagram_analyzer/requirements.txt
```

### 2. 실행 방법

#### 방법 A — Windows 바탕화면 바로가기 (권장)

```bash
python make_shortcut.py
```

최초 1회 실행하면 바탕화면에 **Instagram Analyzer** 아이콘이 생성됩니다.  
이후 더블클릭으로 실행하면 트레이 아이콘 + 로그 뷰어 GUI가 열리고 서버가 자동 시작됩니다.

#### 방법 B — 터미널에서 직접 실행

```bash
cd instagram_analyzer
python app.py
```

브라우저에서 [http://localhost:5000](http://localhost:5000) 접속

---

## 📁 프로젝트 구조

```
Instagram-insight/
├── make_shortcut.py              # 바탕화면 바로가기 생성기
├── reset_password.py             # 비밀번호 긴급 초기화 도구
│
└── instagram_analyzer/
    ├── app.py                    # Flask 앱 진입점
    ├── config.py                 # 설정값
    ├── models.py                 # DB 모델 (SQLite)
    ├── logging_config.py         # 로깅 설정
    ├── launcher.py               # Windows GUI 런처
    ├── requirements.txt
    │
    ├── routes/                   # Flask 라우트
    │   ├── auth.py               # 로그인·회원가입·계정 찾기·설정
    │   ├── followers.py          # 팔로워·팔로잉·언팔 분석
    │   ├── activity.py           # 활동 검색 (좋아요·댓글·DM)
    │   ├── history.py            # 업로드 히스토리
    │   └── admin.py              # 관리자 페이지
    │
    ├── services/                 # 비즈니스 로직
    │   ├── parser.py             # JSON·ZIP 파싱
    │   ├── follower_service.py   # 팔로워 분석
    │   └── activity_service.py  # 활동 검색
    │
    ├── templates/                # Jinja2 HTML 템플릿
    └── static/                   # CSS·JS
```

---

## 🔐 보안

- 모든 처리는 **로컬(내 PC)에서만** 수행됩니다.
- 계정별 데이터 격리 — 사용자마다 독립된 데이터 폴더
- 비밀번호는 해시(Werkzeug)로 저장, 평문 저장 없음
- Flask 세션 키는 재시작 후에도 유지되는 로컬 파일로 관리
- 인스타그램 로그인 정보를 수집하거나 저장하지 않음

---

## 🛠 비밀번호를 잊었을 때

#### 방법 1 — 비밀번호 찾기 (보안 질문 설정 시)
로그인 화면 하단의 **비밀번호 찾기** 링크 클릭

#### 방법 2 — 긴급 초기화 (터미널)
```bash
python reset_password.py
```

---

## 📝 라이선스

개인 사용 목적으로 제작된 로컬 전용 도구입니다.  
인스타그램 공식 데이터 내보내기만 사용하며 이용약관을 위반하지 않습니다.
