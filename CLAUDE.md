# 승수머신 (ddokddok) — 동아리 디파짓 관리 서비스

## 프로젝트 개요

동아리원 20명의 활동 현황(일지 작성, 댓글, 모임 출석)을 관리하고, 활동 미달 시 5만원 디파짓에서 자동 차감하는 웹 서비스.

- **운영진**: 전체 현황 조회 + 수기 입력
- **동아리원**: 본인 현황 조회

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 백엔드 | Python FastAPI |
| DB | Supabase (PostgreSQL) |
| 프론트엔드 | React (Vite) |
| 배포 — 백엔드 | Render 무료티어 |
| 배포 — 프론트 | GitHub Pages |

---

## 폴더 구조

```
ddokddok/
├── backend/
│   ├── app/
│   │   ├── routers/       # API 라우터 (members, journals, meetings, band, deposit, refresh, notify)
│   │   ├── models/        # Pydantic 모델
│   │   ├── services/      # 비즈니스 로직 (band_client, deposit_calculator, discord_notify)
│   │   └── main.py        # FastAPI 진입점
│   ├── .env.example       # 환경변수 예시 (실제 값 없이)
│   └── requirements.txt
├── frontend/              # Vite React 프로젝트
│   ├── src/
│   │   ├── api/           # Axios API 클라이언트 (client.js)
│   │   ├── components/    # 공통 컴포넌트 (PasswordGate, MemberCard)
│   │   ├── pages/         # 페이지 컴포넌트 (Dashboard, Admin)
│   │   ├── App.jsx        # 라우팅 정의
│   │   └── main.jsx       # 진입점 (HashRouter — GitHub Pages 호환)
│   └── .env               # VITE_API_BASE_URL, VITE_ADMIN_PASSWORD
├── sql/
│   └── schema.sql         # Supabase에 실행할 DB 스키마
├── .gitignore
└── CLAUDE.md
```

---

## 자주 쓰는 명령어

### 백엔드 실행

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # .env에 실제 값 입력
uvicorn app.main:app --reload
```

### 프론트엔드 실행

```bash
cd frontend
npm install
# frontend/.env 파일에 VITE_API_BASE_URL, VITE_ADMIN_PASSWORD 설정
npm run dev
# → http://localhost:5173  (일반 멤버 뷰)
# → http://localhost:5173/admin  (관리자 — 비밀번호 필요)
```

### 프론트엔드 GitHub Pages 배포

```bash
cd frontend
npm run deploy    # build + gh-pages 브랜치로 dist/ 자동 배포
```

### 프론트엔드 환경변수 (frontend/.env)

```
VITE_API_BASE_URL=http://localhost:8000   # 백엔드 URL
VITE_ADMIN_PASSWORD=admin                 # 관리자 비밀번호
```

---

## 디파짓 차감 규칙

초기 디파짓: **50,000원**

| 항목 | 기준 | 차감액 |
|------|------|--------|
| 정기모임 결석 | 누적 결석 횟수 기반 (0~1회: 0원, 2회: 10,000원, 3회: 30,000원, 4회+: 50,000원) | 단계별 |
| 일지 미작성 | 해시태그 일지 미제출 (check_date 다음날 기준, KST) | 10,000원/건 |
| 댓글 미달 | 타인 일지 댓글 15개 미만 (comment_check_date 다음날 기준, KST) | 10,000원/건 |
| 조모임 미참석 | `small_group_satisfied = FALSE` (NULL=미입력=차감없음) | 50,000원 |

- 차감은 `deposit_history` 테이블에 이력으로 기록
- 운영진이 수기로 차감 적용 가능
- `members.deposit_balance`는 차감 후 잔액을 반영
- 새로고침(POST /refresh) 쿨다운: **1분**

---

## 네이버 밴드 API 연동

### 개요
네이버 밴드 API를 사용해 동아리 밴드의 포스트를 조회하고, 해시태그로 일지 작성 여부를 확인한다.

### 인증
- `BAND_ACCESS_TOKEN` 환경변수 사용 (OAuth 2.0 액세스 토큰)
- 밴드 개발자 센터에서 발급: https://developers.band.us

### 포스트 조회 흐름

```
GET https://openapi.band.us/v2/band/posts
  ?access_token={BAND_ACCESS_TOKEN}
  &band_key={BAND_KEY}
  &locale=ko_KR
```

1. 응답의 `result_data.items` 배열에서 포스트 순회
2. 각 포스트의 `content` 필드에서 해시태그 매칭 (예: `#3월목표설정`)
3. 작성자 이름(`author.name`)으로 동아리원 식별 → `members` 테이블과 매칭
4. 페이징: 응답의 `result_data.paging.next_params`가 존재하면 `after` 파라미터로 다음 페이지 요청
5. `next_params`가 없으면 마지막 페이지 → 순회 종료

### 댓글 조회 흐름

```
GET https://openapi.band.us/v2/band/post/comments
  ?access_token={BAND_ACCESS_TOKEN}
  &band_key={BAND_KEY}
  &post_key={POST_KEY}
```

1. 특정 포스트의 댓글 목록 조회
2. 댓글 작성자별로 카운트
3. 동아리원 1인당 댓글 수 → `comment_checks.comment_count` 업데이트
4. 15개 이상이면 `is_satisfied`가 자동으로 `TRUE` (Generated Column)

---

## 디스코드 알림

디스코드 웹훅을 통해 일지/댓글 마감 알림을 자동 전송한다.

### 알림 종류

| 시간 (KST) | 내용 |
|------------|------|
| 매주 일요일 21:00 | 마감 3시간 전 경고 (미작성자 + 작성자 명단) |
| 매주 월요일 00:10 | 마감 후 결과 (미작성자 + 예상 차감액) |

- 일지(`check_date`)와 댓글(`comment_check_date`) 알림이 별도로 동작
- 해당 주에 마감일이 없으면 자동 스킵
- 엔드포인트: `POST /notify/check` (cron-job.org에서 호출)
- cron 스케줄: `0 12 * * 0` (경고), `10 15 * * 1` (결과)

---

## 주의사항

- DB 데이터 삽입/수정은 반드시 Python supabase 클라이언트로만 할 것
  (PowerShell 등 터미널에서 직접 SQL 실행 시 한글이 ?로 깨지는 문제 있음)
- Render 서버는 UTC 기준 → 날짜 비교 시 반드시 `today_kst()` 사용 (`backend/app/services/deposit_calculator.py`)
- supabase-py postgrest 세션은 `http2=False`로 교체해야 함 (`backend/app/database.py`) — HTTP/2 idle 연결 끊김 방지
- Render 무료티어 콜드스타트 방지를 위해 UptimeRobot으로 5분마다 ping 설정됨

---

## 환경변수 목록

`backend/.env` 에 아래 키를 설정한다 (값은 절대 커밋하지 말 것):

```
SUPABASE_URL=           # Supabase 프로젝트 URL
SUPABASE_SECRET_KEY=        # Supabase secret 키 (sb_secret_... 형식, 백엔드 전용)
BAND_ACCESS_TOKEN=      # 네이버 밴드 OAuth 액세스 토큰
DISCORD_WEBHOOK_URL=    # 디스코드 웹훅 URL
```
