# エントリーポイント

import streamlit as st
from utils import database
from utils import auth
from utils.logger import get_logger

logger = get_logger(__name__)

# キャッシュ用wrapper
@st.cache_resource(ttl=3600)
def cached_get_client(url: str, key: str):
    return database.get_client(url, key)

# キャッシュ用wrapper
@st.cache_data
def cached_get_products():
    return database.get_products()

def logout():
    st.session_state["user"] = None

# Supabase接続
supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]
supabase = cached_get_client(supabase_url, supabase_key)

if "user" not in st.session_state:
    st.session_state["user"] = None

# 未ログイン
if st.session_state["user"] is None:
    st.title("ログインしてください")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("ログイン")

        if submitted:
            if not email:
                st.warning("メールアドレスを入力してください")
            elif not password:
                st.warning("パスワードを入力してください")
            else:
                user = auth.login(supabase, email, password)
                if user:
                    st.session_state["user"] = user.user
                    st.success("ログインしました")
                    st.rerun()
                else:
                    st.error("ログインできません  \nメールアドレス、パスワードを確認してください")
# ログイン済み
else:
    st.sidebar.write(st.session_state['user'].email)
    if st.sidebar.button("ログアウト"):
        logout()
        st.rerun()

    st.title("保護されたページ")
    st.write("ログインできました")
