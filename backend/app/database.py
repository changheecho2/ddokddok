import os
import httpx
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

supabase: Client = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SECRET_KEY"],
)

# supabase-py 내부 auth 클라이언트는 h2가 필요하지만,
# 실제 DB 쿼리를 담당하는 postgrest 세션은 HTTP/1.1로 교체해
# idle 연결 끊김(RemoteProtocolError) 문제를 방지한다.
_old_session = supabase.postgrest.session
supabase.postgrest.session = httpx.Client(
    headers=dict(_old_session.headers),
    http2=False,
    timeout=30.0,
)
_old_session.close()
