# 똑똑 (ddokddok) — 동아리 디파짓 관리 서비스

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
│   │   ├── routers/       # API 라우터 (members, journals, meetings 등)
│   │   ├── models/        # Pydantic 모델
│   │   └── main.py        # FastAPI 진입점
│   ├── .env.example       # 환경변수 예시 (실제 값 없이)
│   └── requirements.txt
├── frontend/              # Vite React 프로젝트 (추후 생성)
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
npm run dev
```

### 프론트엔드 GitHub Pages 배포

```bash
cd frontend
npm run build
# gh-pages 브랜치로 dist/ 배포
```

---

## 디파짓 차감 규칙

초기 디파짓: **50,000원**

| 항목 | 기준 | 차감액 |
|------|------|--------|
| 정기모임 결석 | 정기모임 1회 불참 | 10,000원 |
| 일지 미작성 | 해시태그 일지 미제출 (check_date 기준) | 5,000원 |
| 댓글 미달 | 타인 일지 댓글 15개 미만 (comment_check_date 기준) | 5,000원 |
| 조모임 미참석 | 해당 기간 조모임 불참 | 5,000원 |

- 차감은 `deposit_history` 테이블에 이력으로 기록
- 운영진이 수기로 차감 적용 가능
- `members.deposit_balance`는 차감 후 잔액을 반영

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

## 환경변수 목록

`backend/.env` 에 아래 키를 설정한다 (값은 절대 커밋하지 말 것):

```
SUPABASE_URL=           # Supabase 프로젝트 URL
SUPABASE_SERVICE_ROLE_KEY=  # Supabase service_role 키 (백엔드 전용)
BAND_ACCESS_TOKEN=      # 네이버 밴드 OAuth 액세스 토큰
```
