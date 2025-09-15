# エントリーポイント
import streamlit as st
import pandas as pd
from io import BytesIO
from streamlit.components.v1 import html
from utils import constant
from utils import database
from utils import data_processor
from utils import auth
from utils.logger import get_logger

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
            constant.PAGE_NAME_PRODUCTS_EDITOR,
            constant.PAGE_NAME_IMPORT,
            constant.PAGE_NAME_BRAND_MANAGEMENT,
            constant.PAGE_NAME_PANEL_TYPE_MANAGEMENT
        ])

# ログ準備
logger = get_logger(__name__)

# Supabase接続取得
supabase = database.get_supabase_client()

# ヘッダー表示
put_header()

# ログイン済み
if auth.has_session():
    # 画面幅変更
    st.set_page_config(layout="wide")

    # サイドバー表示
    put_sidebar()

    # 表示ページ取得
    page = st.session_state.get("page", "")

    # データ表示・編集
    if page == constant.PAGE_NAME_PRODUCTS_EDITOR:
        st.subheader(constant.PAGE_NAME_PRODUCTS_EDITOR)
        try:
            # DBからデータ取得
            res = supabase.table("products").select("*").order("product_id").execute()
        except Exception as e:
            logger.error(e)
            st.error("製品データを取得できませんでした")

        if not res.data:
            st.write("データがありません")
        else:
            # 取得したデータを表示用に変換
            df = pd.DataFrame(res.data)
            data_processor.convert_products_to_edit(df)

            # 検索入力
            query = st.text_input("検索：", "")
            if query:
                df = df[df.apply(lambda row: row.astype(str).str.contains(query, case=False).any(), axis=1)]

            # ブランドフィルター
            selected_brands = st.sidebar.multiselect("ブランド", df["brand"].unique())

            # ステータスフィルター
            selected_status = st.sidebar.multiselect("ステータス", df["status"].unique())

            # 価格帯フィルター
            min_price = int(df["price_jpy"].min())
            max_price = int(df["price_jpy"].max())
            if min_price == max_price:
                min_price = 0
            selected_price = st.sidebar.slider(
                "価格",
                min_value=min_price,
                max_value=max_price,
                value=(min_price, max_price)
            )

            # サイズフィルター
            min_size = int(df["size_inch"].min())
            max_size = int(df["size_inch"].max())
            if min_size == max_size:
                min_size = 0
            selected_size = st.sidebar.slider(
                "画面サイズ",
                min_value=min_size,
                max_value=max_size,
                value=(min_size, max_size)
            )

            # フィルタリング
            filtered_df = df.copy()
            if selected_brands:
                filtered_df = filtered_df[filtered_df["brand"].isin(selected_brands)]
            if selected_status:
                filtered_df = filtered_df[filtered_df["status"].isin(selected_status)]
            filtered_df = filtered_df[
                (filtered_df["price_jpy"] >= selected_price[0]) & (filtered_df["price_jpy"] <= selected_price[1])
            ]
            filtered_df = filtered_df[
                (filtered_df["size_inch"] >= selected_size[0]) & (filtered_df["size_inch"] <= selected_size[1])
            ]

            # データ表示
            edited_df = st.data_editor(
                filtered_df,
                use_container_width=True,
                num_rows="dynamic",
                key="products_editor"
            )

            # チェックしてエラーを表示
            errors = []
            validated_df = edited_df.copy()
            if data_processor.validate_products(validated_df, errors) is False:
                for e in errors:
                    st.error(e)

            # 更新日時は自動更新
            validated_df.drop(columns=["updated_at"], inplace=True)

            # 更新用に変換
            records = validated_df.to_dict(orient="records")

            # floatになっちゃうのでintに戻す
            records = data_processor.cast_products_to_int(records)

            if len(errors) == 0:
                # Excelダウンロード
                excel_bytes = data_processor.to_excel_bytes(edited_df)
                st.download_button(
                    label="Excelダウンロード",
                    data=excel_bytes,
                    file_name="products.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            if records:
                # 登録/更新の保存
                if st.button("登録・更新を保存"):
                    if len(errors) != 0:
                        st.error("編集内容を保存できませんでした  \nエラーを確認してください")
                    else:
                        try:
                            # 登録/更新
                            supabase.table("products").upsert(records).execute()
                            st.success("保存しました")
                        except Exception as e:
                            logger.error(e)
                            st.error(f"保存できませんでした  \n{e}")

            # 削除対象を取得
            db_ids = supabase.table("products").select("product_id").execute()
            db_ids = [row["product_id"] for row in db_ids.data]
            df_ids = [row["product_id"] for row in records]
            ids_to_delete = list(set(db_ids) - set(df_ids))
            delete_len = len(ids_to_delete)

            # 削除の保存
            if ids_to_delete:
                if st.button("削除を保存", type="primary"):
                    try:
                        # 削除
                        supabase.table("products").delete().in_("product_id", ids_to_delete).execute()
                        st.success("保存しました")
                    except Exception as e:
                        logger.error(e)
                        st.error(f"保存できませんでした  \n{e}")
                st.write(f"**※ {delete_len} 件が削除されます**")

    # CSVインポート
    elif page == constant.PAGE_NAME_IMPORT:
        st.subheader(constant.PAGE_NAME_IMPORT)
        uploaded_file = st.file_uploader("CSVファイルをドラッグ＆ドロップしてください", type=["csv"])

        # CSVファイルがアップロードされたらセッションに保存
        if uploaded_file is not None:
            try:
                # ファイル読み込み
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
                if data_processor.validate_products(validated_df, errors) is False:
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
                        records = data_processor.cast_products_to_int(records)
                        try:
                            # DB登録/更新
                            supabase.table("products").upsert(records).execute()
                            st.success("保存しました")
                        except Exception as e:
                            logger.error(e)
                            st.error(f"保存できませんでした  \n{e}")

    # ブランド管理
    elif page == constant.PAGE_NAME_BRAND_MANAGEMENT:
        st.subheader(constant.PAGE_NAME_BRAND_MANAGEMENT)
        try:
            # DBからデータ取得
            res = supabase.table("brands").select("*").order("id").execute()
        except Exception as e:
            logger.error(e)
            st.error("ブランドデータを取得できませんでした")
    
        df = pd.DataFrame(res.data)
        data_processor.convert_timestamp(df)
        edited_df = st.data_editor(df, num_rows="dynamic", key=f"editor_brands")

        # チェックしてエラーを表示
        validated_df = edited_df.copy()
        errors = []
        if data_processor.validate_brands(validated_df, errors) is False:
            for e in errors:
                st.error(e)

        # 保存ボタン
        if st.button("保存"):
            if len(errors) != 0:
                st.error("編集内容を保存できませんでした  \nファイルの内容を確認してください")
            else:
                # 登録用に変換
                records = validated_df.to_dict(orient="records")
                try:
                    # DB登録/更新
                    supabase.table("brands").upsert(records).execute()
                    st.success("保存しました")
                except Exception as e:
                    logger.error(e)
                    st.error(f"保存できませんでした  \n{e}")

    # パネル方式管理
    elif page == constant.PAGE_NAME_PANEL_TYPE_MANAGEMENT:
        st.subheader(constant.PAGE_NAME_PANEL_TYPE_MANAGEMENT)
        try:
            # DBからデータ取得
            res = supabase.table("panel_types").select("*").order("id").execute()
        except Exception as e:
            logger.error(e)
            st.error("パネル方式データを取得できませんでした")
    
        df = pd.DataFrame(res.data)
        data_processor.convert_timestamp(df)
        edited_df = st.data_editor(df, num_rows="dynamic", key=f"editor_panel_types")

        # チェックしてエラーを表示
        validated_df = edited_df.copy()
        errors = []
        if data_processor.validate_panel_types(validated_df, errors) is False:
            for e in errors:
                st.error(e)

        # 保存ボタン
        if st.button("保存"):
            if len(errors) != 0:
                st.error("編集内容を保存できませんでした  \nファイルの内容を確認してください")
            else:
                # 登録用に変換
                records = validated_df.to_dict(orient="records")
                try:
                    # DB登録/更新
                    supabase.table("panel_types").upsert(records).execute()
                    st.success("保存しました")
                except Exception as e:
                    logger.error(e)
                    st.error(f"保存できませんでした  \n{e}")
    # ダッシュボード
    else:
        # DBからデータ取得
        res = supabase.table("products").select("*").order("product_id").execute()
        df = pd.DataFrame(res.data)

        total_products = len(df)
        average_price = df["price_jpy"].mean()
        total_stock = df["stock_quantity"].sum()
        active_products = len(df[df["status"] == "active"])

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("総商品数", total_products)
        col2.metric("平均価格", f"{average_price:,.0f}")
        col3.metric("在庫総数", total_stock)
        col4.metric("アクティブ商品数", active_products)

        res = supabase.table("products").select("*").order("created_at", desc=True).limit(10).execute()
        df_recent = pd.DataFrame(res.data)
        data_processor.convert_timestamp(df_recent)

        st.write("最近登録された商品")
        if not df_recent.empty:
            st.data_editor(
                df_recent,
                disabled=True
            )
        else:
            st.info("データがありません")

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
                is_success = auth.login(input_email, input_password)
                if is_success:
                    st.rerun()
                else:
                    logger.error(f"email: {input_email}, password: {input_password}")
                    st.error("ログインできません  \nメールアドレス、パスワードを確認してください")

# フッター表示
put_footer()
