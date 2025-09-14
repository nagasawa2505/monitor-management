# 画面描画関連処理

import streamlit as st
from streamlit.components.v1 import html
from utils import constant
from utils import auth

# サイドバー表示
def put_sidebar():
    with st.sidebar:
        # ログイン状態
        st.write(f"{st.session_state["user"]}でログイン中")

        # ログアウトボタン
        if st.button("ログアウト"):
            auth.logout()
            st.rerun()

        # 画面切り替えメニュー
        st.session_state["page"] = st.sidebar.radio("ページを選択", [
            constant.PAGE_NAME_HOME,
            constant.PAGE_NAME_CSV_IMPORT,
            constant.PAGE_NAME_BRAND_MANAGEMENT,
            constant.PAGE_NAME_PANEL_TYPE_MANAGEMENT
        ])

# ヘッダー表示
def put_header():
    st.header(f"PCモニター商品管理・分析システム", divider="blue")

# フッター表示
def put_footer():
    html(f"""
        <div style="
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        text-align: center;">
            <p>Developed by nagasawa2505</p>
        </div>
    """)
