# Supabase関連処理

import streamlit as st
from supabase import create_client
from .logger import get_logger

# ログ準備
logger = get_logger(__name__)

supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]

# Supabase接続を返す
@st.cache_resource(ttl=3600)
def get_supabase_client():
    try:
        client = create_client(supabase_url, supabase_key)
        return client
    except Exception as e:
        logger.error(f"{e} url:{supabase_url} key:{supabase_key}")
        return None
