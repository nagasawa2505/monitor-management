# ユーザー認証処理
from .logger import get_logger

logger = get_logger(__name__)

# 認証
def login(supabase, email: str, password: str):
    if supabase is None:
        logger.error("Supabase接続がありません")
        return None
    try:
        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
    except Exception as e:
        logger.error(f"{e} email:{email} password:{password}")
        return None
    if "error" in res:
        logger.error(res.error)
        return None
    return res
