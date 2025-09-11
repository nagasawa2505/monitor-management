# Supabase関連処理
from supabase import create_client, Client
from .logger import get_logger

logger = get_logger(__name__)

# Supabase接続を返す
def get_client(url: str, key: str):
    try:
        client = create_client(url, key)
        return client
    except Exception as e:
        logger.error(f"{e} url:{url} key:{key}")
        return None

#def get_products(_supabase: Client):
#    if _supabase is None:
#        logger.error("Supabase接続がありません")
#        return None
#    res = _supabase.table("product").select("*").execute()
#    return res.data
