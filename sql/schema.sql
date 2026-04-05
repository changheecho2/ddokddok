-- 동아리원
CREATE TABLE members (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  deposit_balance INTEGER NOT NULL DEFAULT 50000,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 일지 마스터
CREATE TABLE journals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  hashtag TEXT NOT NULL,
  label TEXT NOT NULL,
  check_date DATE NOT NULL,
  comment_check_date DATE NOT NULL
);

-- 일지 작성 여부
CREATE TABLE journal_checks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  member_id UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
  journal_id UUID NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
  is_written BOOLEAN NOT NULL DEFAULT FALSE,
  checked_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (member_id, journal_id)
);

-- 댓글 수 체크
CREATE TABLE comment_checks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  member_id UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
  journal_id UUID NOT NULL REFERENCES journals(id) ON DELETE CASCADE,
  comment_count INTEGER NOT NULL DEFAULT 0,
  is_satisfied BOOLEAN GENERATED ALWAYS AS (comment_count >= 15) STORED,
  checked_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (member_id, journal_id)
);

-- 정기모임
CREATE TABLE meetings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  meeting_date DATE NOT NULL,
  sequence INTEGER NOT NULL
);

-- 정기모임 출석
CREATE TABLE meeting_attendance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  member_id UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
  meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
  is_attended BOOLEAN NOT NULL DEFAULT TRUE,
  UNIQUE (member_id, meeting_id)
);

-- 조모임 참석
CREATE TABLE small_group_attendance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  member_id UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
  attended_date DATE NOT NULL,
  note TEXT
);

-- 디파짓 차감 내역
CREATE TABLE deposit_history (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  member_id UUID NOT NULL REFERENCES members(id) ON DELETE CASCADE,
  reason TEXT NOT NULL,
  amount INTEGER NOT NULL,
  applied_at TIMESTAMPTZ DEFAULT NOW(),
  memo TEXT
);

-- 기초 데이터
INSERT INTO members (name) VALUES
  ('권민서'),('권민아'),('김민준'),('배은석'),
  ('방예지'),('성민정'),('송은서'),('안서진'),
  ('이나윤'),('이두희'),('이정민'),('이지원'),
  ('이한동'),('전유리'),('조창희'),('채연'),
  ('최다정'),('홍정민'),('홍정우'),('황규성');

INSERT INTO meetings (meeting_date, sequence) VALUES
  ('2025-03-14', 1), ('2025-04-25', 2),
  ('2025-06-13', 3), ('2025-07-18', 4);

INSERT INTO journals (hashtag, label, check_date, comment_check_date) VALUES
  ('#3월목표설정', '3월 목표설정',            '2025-03-14', '2025-03-21'),
  ('#3월목표달성', '3월 달성 + 4월 목표설정', '2025-04-05', '2025-04-12'),
  ('#4월목표달성', '4월 달성 + 5월 목표설정', '2025-05-03', '2025-05-10'),
  ('#5월목표달성', '5월 달성 + 6월 목표설정', '2025-06-07', '2025-06-14'),
  ('#6월목표달성', '6월 달성 + 7월 목표설정', '2025-07-05', '2025-07-12');
