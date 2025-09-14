# 単一ユーザー認証処理

import streamlit as st
from .logger import get_logger

# ログ準備
logger = get_logger(__name__)

# 認証済みかを返す
def has_session():
    return st.session_state.get("user") is not None

# ログイン
def login(supabase, email: str, password: str):
    if supabase is None:
        logger.error("Supabase接続がありません")
        return False

    try:
        res = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
    except Exception as e:
        logger.error(f"{e} email:{email} password:{password}")
        return False

    if "error" in res:
        logger.error(res.error)
        return False

    # ログイン成功
    st.session_state["user"] = res.user.email
    return True

# ログアウト
def logout():
    st.session_state.clear()
