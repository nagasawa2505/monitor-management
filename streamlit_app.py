# エントリーポイント
import streamlit as st
import pandas as pd
from utils import constant
from utils import database
from utils import data_processor
from utils import auth
from utils import view
from utils.logger import get_logger

# ログ準備
logger = get_logger(__name__)

# Supabase接続取得
supabase = database.get_supabase_client()

# ヘッダー表示
view.put_header()

# ログイン済み
if auth.has_session():
    # 画面幅変更
    st.set_page_config(layout="wide")

    # サイドバー表示
    view.put_sidebar()

    # 表示ページ取得
    page = st.session_state.get("page", "")

    # CSVインポート
    if page == constant.PAGE_NAME_CSV_IMPORT:
        st.subheader(constant.PAGE_NAME_CSV_IMPORT)
        uploaded_file = st.file_uploader("CSVファイルをドラッグ＆ドロップしてください", type=["csv"])

        # CSVファイルがアップロードされたらセッションに保存
        if uploaded_file is not None:
            try:
                df = pd.read_csv(uploaded_file)
                st.session_state["uploaded_filename"] = uploaded_file.name
                st.session_state["uploaded_df"] = df
            except Exception as e:
                logger.error(f"{e} file:{uploaded_file.name}")
                st.error(f"{uploaded_file.name}を読み込めませんでした  \nファイルの内容を確認してください")

            # 確認/編集画面表示
            if st.session_state.get("uploaded_df") is not None:
                fname = st.session_state["uploaded_filename"]
                df = st.session_state["uploaded_df"]

                st.subheader(f"確認・編集：{fname}")
                edited_df = st.data_editor(df, num_rows="dynamic", key=f"editor_{fname}")
                st.session_state["uploaded_df"] = edited_df

                # チェックしてエラーを表示
                validated_df = edited_df.copy()
                errors = []
                if data_processor.validate_csv_products(validated_df, errors) is False:
                    for e in errors:
                        st.error(e)

                # 保存ボタン
                if st.button("保存"):
                    if len(errors) != 0:
                        st.error("編集内容を保存できませんでした  \nファイルの内容を確認してください")
                    else:
                        # 登録用に変換
                        records = validated_df.to_dict(orient="records")
                        # floatになっちゃうのでintに戻す
                        records = data_processor.cast_records_to_int(records, [
                            "brand_id",
                            "panel_type_id",
                            "resolution_w",
                            "resolution_h"
                        ])
                        try:
                            # UPSERT
                            res = supabase.table("products").upsert(records).execute()
                            if "error" in res:
                                logger.error(res.error)
                                st.error(f"保存できませんでした  \n{res.error}")
                            else:
                                st.success("保存しました")
                        except Exception as e:
                            logger.error(e)
                            st.error(f"保存できませんでした  \n{e}")
    # ブランド管理
    elif page == constant.PAGE_NAME_BRAND_MANAGEMENT:
        st.write("未実装")

    # パネル方式管理
    elif page == constant.PAGE_NAME_PANEL_TYPE_MANAGEMENT:
        st.write("未実装")

# 未ログイン
else:
    # 画面幅変更
    st.set_page_config(layout="centered")

    # 認証フォーム表示
    with st.form("login_form"):
        input_email = st.text_input("メールアドレス")
        input_password = st.text_input("パスワード", type="password")
        submitted = st.form_submit_button("ログイン")

        if submitted:
            if not input_email:
                st.warning("メールアドレスを入力してください")
            elif not input_password:
                st.warning("パスワードを入力してください")
            else:
                is_success = auth.login(supabase, input_email, input_password)
                if is_success:
                    st.success("ログインしました")
                    st.rerun()
                else:
                    st.error("ログインできません  \nメールアドレス、パスワードを確認してください")

# フッター表示
view.put_footer()
