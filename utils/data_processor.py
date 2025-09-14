# データチェック、加工処理

import streamlit as st
import pandas as pd
import re
from supabase import create_client
from utils import constant
from utils import database
from .logger import get_logger

# ログ準備
logger = get_logger(__name__)

# Supabase接続取得
supabase = database.get_supabase_client()

# ブランド名 -> ID変換用
id_by_brands = {}
res = supabase.table("brands").select("id, name").execute()
for row in res.data:
    id_by_brands[row["name"]] = row["id"]

# パネル方式名 -> ID変換用
id_by_panel_types = {}
res = supabase.table("panel_types").select("id, name").execute()
for row in res.data:
    id_by_panel_types[row["name"]] = row["id"]

# 製品テーブル列チェック用
column_defs_products = {
    "product_id":     {"required": True,  "type": str, "max_length": 100},
    "model_name":     {"required": True,  "type": str, "max_length": 100},
    "brand_id":       {},
    "size_inch":      {"required": True,  "type": float},
    "resolution_w":   {},
    "resolution_h":   {},
    "panel_type_id":  {},
    "refresh_rate":   {"required": True,  "type": int},
    "price_jpy":      {"required": True,  "type": float},
    "stock_quantity": {"required": True,  "type": int},
    "release_date":   {"required": True,  "type": "date"},
    "status":         {"required": True,  "type": str, "allowed": ["active", "discontinued"]}
}

# 製品CSVインポートチェック
def validate_csv_products(df: pd.DataFrame, errors: list) -> bool:
    # ブランドチェック
    if "brand" not in df.columns:
        errors.append(f"行 {idx + 1}: brand は必須項目です")
    else:
        for idx, value in df["brand"].items():
            id = id_by_brands.get(value, None)
            if not id:
                errors.append(f"行 {idx + 1}: brand \"{value}\" は未登録です  \nマスター登録後にインポートしてください")
            else:
                # 登録用にIDに変換
                df.loc[idx, "brand_id"] = int(id)
        df.drop(columns=["brand"], inplace=True)

    # パネル方式チェック
    if "panel_type" not in df.columns:
        errors.append(f"行 {idx + 1}: panel_type は必須項目です")
    else:
        for idx, value in df["panel_type"].items():
            id = id_by_panel_types.get(value, None)
            if not id:
                errors.append(f"行 {idx + 1}: panel_type \"{value}\" は未登録です  \nマスター登録後にインポートしてください")
            else:
                # 登録用にIDに変換
                df.loc[idx, "panel_type_id"] = int(id)
        df.drop(columns=["panel_type"], inplace=True)

    # 解像度チェック
    if "resolution" not in df.columns:
        errors.append(f"行 {idx + 1}: resolution は必須項目です")
    else:
        for idx, value in df["resolution"].items():
            if not re.match(r'^\d+x\d+$', str(value)):
                errors.append(f"行 {idx + 1}: resolution は 数値x数値 の形式にしてください")
            else:
                # 登録用に解像度を分割
                x, y = value.split("x")
                df.loc[idx, "resolution_w"] = int(x)
                df.loc[idx, "resolution_h"] = int(y)
        df.drop(columns=["resolution"], inplace=True)

    # 重複チェック
    if "product_id" in df.columns:
        duplicates = df[df.duplicated(subset=["product_id"], keep=False)]
        if not duplicates.empty:
            for idx in duplicates.index:
                errors.append(f"行 {idx + 1}: 重複する product_id が存在します")

    # 共通チェック
    return validate_csv(column_defs_products, df, errors)

# CSVインポート共通チェック
def validate_csv(column_defs: dict, df: pd.DataFrame, errors: list) -> bool:
    # 行ループ
    for idx, row in df.iterrows():
        row_prefix = f"行 {idx + 1}: "

        # 列ループ
        for col, defs in column_defs.items():
            # 必須列存在チェック
            if col not in row:
                if defs.get("required", False):
                    errors.append(f"{row_prefix}{col} 列を追加してください")
                continue

            # 値取得
            value = row[col]

            # 必須列値チェック
            if defs.get("required", False):
                if pd.isna(value) or str(value).strip() == "":
                    errors.append(f"{row_prefix}{col} は必須項目です")
                    continue

            # 型チェック
            expected_type = defs.get("type")
            if expected_type == int:
                if not (isinstance(value, int) or (isinstance(value, float) and value.is_integer())):
                    errors.append(f"{row_prefix}{col} は整数にしてください: {value}")
            elif expected_type == float:
                if not isinstance(value, (int, float)):
                    errors.append(f"{row_prefix}{col} は数値にしてください: {value}")
            elif expected_type == str:
                if not isinstance(value, str):
                    errors.append(f"{row_prefix}{col} は文字列にしてください: {value}")
            elif expected_type == "date":
                try:
                    pd.to_datetime(value)
                except Exception:
                    errors.append(f"{row_prefix}{col} は日付形式(YYYY-MM-DD)にしてください: {value}")

            # 最大文字長チェック
            max_len = defs.get("max_length")
            if max_len and isinstance(value, str):
                if len(value) > max_len:
                    errors.append(f"{row_prefix}{col} は {max_len} 文字以内にしてください: {value}")

            # 許可値チェック
            allowed = defs.get("allowed")
            if allowed and value not in allowed:
                allowed_str = ", ".join(map(str, allowed))
                errors.append(
                    f"{row_prefix}{col} は {allowed_str} のいずれかにしてください: {value}"
                )

    return len(errors) == 0

# 指定列の値をintに型変換
def cast_records_to_int(records: list[dict], columns: list[str]) -> list[dict]:
    new_records = []
    for row in records:
        new_row = row.copy()
        for col in columns:
            if col in new_row and new_row[col] is not None:
                new_row[col] = int(new_row[col])
        new_records.append(new_row)
    return new_records
