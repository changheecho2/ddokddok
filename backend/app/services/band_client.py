"""네이버 밴드 API 클라이언트 (async httpx)"""
import asyncio
from datetime import date, datetime, time, timezone
from typing import Any, Dict, List, Optional

import httpx

BAND_BASE_URL = "https://openapi.band.us/v2"


async def _fetch_all_posts(
    client: httpx.AsyncClient,
    access_token: str,
    band_key: str,
) -> List[Dict[str, Any]]:
    """밴드 전체 포스트를 페이징으로 수집"""
    posts: List[Dict[str, Any]] = []
    params: Dict[str, str] = {
        "access_token": access_token,
        "band_key": band_key,
    }

    while True:
        r = await client.get(f"{BAND_BASE_URL}/band/posts", params=params)
        r.raise_for_status()
        result_data = r.json()["result_data"]

        posts.extend(result_data.get("items", []))

        next_params = result_data.get("paging", {}).get("next_params")
        if not next_params:
            break
        # next_params는 dict {"after": "..."} 또는 문자열
        params["after"] = next_params["after"] if isinstance(next_params, dict) else next_params

    return posts


async def _fetch_all_comments(
    client: httpx.AsyncClient,
    access_token: str,
    band_key: str,
    post_key: str,
) -> List[Dict[str, Any]]:
    """특정 포스트의 전체 댓글을 페이징으로 수집"""
    comments: List[Dict[str, Any]] = []
    params: Dict[str, str] = {
        "access_token": access_token,
        "band_key": band_key,
        "post_key": post_key,
    }

    while True:
        r = await client.get(f"{BAND_BASE_URL}/band/post/comments", params=params)
        r.raise_for_status()
        result_data = r.json()["result_data"]

        comments.extend(result_data.get("items", []))

        next_params = result_data.get("paging", {}).get("next_params")
        if not next_params:
            break
        params["after"] = next_params["after"] if isinstance(next_params, dict) else next_params

    return comments


async def collect_journal_data(
    access_token: str,
    band_key: str,
    hashtag: str,
    member_name_map: Dict[str, str],  # {name: member_id}
    check_date: date | None = None,
) -> Dict[str, Any]:
    """
    밴드에서 hashtag에 해당하는 포스트를 수집하고 journal/comment 데이터를 반환.

    check_date가 주어지면 해당일 23:59:59 이하에 작성된 포스트만 유효하게 처리한다.

    Returns:
        {
            "journal_writes": {member_id: True},           # 일지 작성자
            "comment_counts": {member_id: int},            # 댓글 수
            "synced_posts": int,                           # 매칭된 포스트 수
            "total_comments": int,                         # 처리된 댓글 수
            "unmatched": [author_name, ...],               # 매칭 실패 작성자 이름
        }
    """
    # check_date → UTC Unix timestamp(ms) 상한값 계산 (해당일 23:59:59 KST = UTC+9)
    deadline_ms: int | None = None
    if check_date is not None:
        deadline_dt = datetime.combine(check_date, time(23, 59, 59))
        # KST(UTC+9) 기준으로 해석 → UTC로 변환
        from datetime import timezone as tz
        import zoneinfo
        try:
            kst = zoneinfo.ZoneInfo("Asia/Seoul")
        except Exception:
            from datetime import timedelta
            kst = tz(timedelta(hours=9))
        deadline_ms = int(deadline_dt.replace(tzinfo=kst).timestamp() * 1000)

    async with httpx.AsyncClient(timeout=30.0) as client:
        all_posts = await _fetch_all_posts(client, access_token, band_key)

    # hashtag 포함 + '#기타' 미포함 + check_date 이하 포스트만 필터링
    matched_posts = [
        p for p in all_posts
        if hashtag in p.get("content", "")
        and "#기타" not in p.get("content", "")
        and (deadline_ms is None or p.get("created_at", 0) <= deadline_ms)
    ]

    journal_writes: Dict[str, bool] = {}
    comment_counts: Dict[str, int] = {}
    unmatched: List[str] = []
    total_comments = 0

    async with httpx.AsyncClient(timeout=30.0) as client:
        for post in matched_posts:
            author_name: str = post.get("author", {}).get("name", "")
            post_key: str = post.get("post_key", "")

            # 일지 작성자 매칭
            if author_name in member_name_map:
                member_id = member_name_map[author_name]
                journal_writes[member_id] = True
            else:
                if author_name and author_name not in unmatched:
                    unmatched.append(author_name)

            # 댓글 수집 (rate limit 대비 0.1초 딜레이)
            if post_key:
                await asyncio.sleep(0.1)
                comments = await _fetch_all_comments(client, access_token, band_key, post_key)
                total_comments += len(comments)

                for comment in comments:
                    commenter_name: str = comment.get("author", {}).get("name", "")
                    if commenter_name in member_name_map:
                        cid = member_name_map[commenter_name]
                        comment_counts[cid] = comment_counts.get(cid, 0) + 1

    return {
        "journal_writes": journal_writes,
        "comment_counts": comment_counts,
        "synced_posts": len(matched_posts),
        "total_comments": total_comments,
        "unmatched": unmatched,
    }
