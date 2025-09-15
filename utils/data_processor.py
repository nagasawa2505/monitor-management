# データチェック、加工処理

import streamlit as st
import pandas as pd
import io
import math
import re
from io import BytesIO
from supabase import create_client
from utils import constant
from utils import database
from .logger import get_logger

# 製品テーブル列チェック用
COLUMN_DEFS_PRODUCTS = {
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

# ブランドテーブル列チェック用
COLUMN_DEFS_BRANDS = {
    "name": {"required": True,  "type": str, "max_length": 100},
}

# パネル方式テーブル列チェック用
COLUMN_DEFS_PANEL_TYPES = {
    "name": {"required": True,  "type": str, "max_length": 100},
}

# 製品バリデーション
def validate_products(df: pd.DataFrame, errors: list) -> bool:
    # ブランドチェック
    if "brand" not in df.columns:
        errors.append(f"行 {idx + 1}: brand は必須項目です")
    else:
        # IDに変換
        convert_brand_to_id(df, errors)

    # パネル方式チェック
    if "panel_type" not in df.columns:
        errors.append(f"行 {idx + 1}: panel_type は必須項目です")
    else:
        # IDに変換
        convert_panel_type_to_id(df, errors)

    # 解像度チェック
    if "resolution" not in df.columns:
        errors.append(f"行 {idx + 1}: resolution は必須項目です")
    else:
        for idx, value in df["resolution"].items():
            if not re.match(r'^\d+x\d+$', str(value)):
                errors.append(f"行 {idx + 1}: resolution は \"数値x数値\" の形式にしてください")
            else:
                # 登録用に解像度を分割
                x, y = split_resolution(value)
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
    return validate_data(COLUMN_DEFS_PRODUCTS, df, errors)

# ブランドバリデーション
def validate_brands(df: pd.DataFrame, errors: list) -> bool:
    # 共通チェック
    return validate_data(COLUMN_DEFS_BRANDS, df, errors)

# パネル方式バリデーション
def validate_panel_types(df: pd.DataFrame, errors: list) -> bool:
    # 共通チェック
    return validate_data(COLUMN_DEFS_PANEL_TYPES, df, errors)

# 共通バリデーション
def validate_data(column_defs: dict, df: pd.DataFrame, errors: list) -> bool:
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

# ブランド名 -> ID変換データ作成
def get_id_by_brand() -> dict:
    id_by_brand = {}
    supabase = database.get_supabase_client()
    res = supabase.table("brands").select("id, name").execute()
    for row in res.data:
        id_by_brand[row["name"]] = row["id"]
    
    return id_by_brand

# パネル方式名 -> ID変換データ作成
def get_id_by_panel_type() -> dict:
    id_by_panel_type = {}
    supabase = database.get_supabase_client()
    res = supabase.table("panel_types").select("id, name").execute()
    for row in res.data:
        id_by_panel_type[row["name"]] = row["id"]
    
    return id_by_panel_type

# ブランドをIDに変換
def convert_brand_to_id(df: pd.DataFrame, errors: list):
    id_by_brand = get_id_by_brand()
    for idx, value in df["brand"].items():
        id = id_by_brand.get(value, None)
        if not id:
            if value:
                errors.append(f"行 {idx + 1}: brand \"{value}\" は未登録です  \n先にマスターに登録してください")
            else:
                errors.append(f"行 {idx + 1}: brand は必須項目です")
        else:
            # IDに変換
            df.loc[idx, "brand_id"] = int(id)
    df.drop(columns=["brand"], inplace=True)

# IDをブランドに変換
def convert_id_to_brand(df: pd.DataFrame):
    id_by_brand = get_id_by_brand()
    brand_by_id = {v: k for k, v in id_by_brand.items()}
    for idx, value in df["brand_id"].items():
        name = brand_by_id.get(value, None)
        df.loc[idx, "brand"] = name
    df.drop(columns=["brand_id"], inplace=True)

# パネル方式をIDに変換
def convert_panel_type_to_id(df: pd.DataFrame, errors: list):
    id_by_panel_type = get_id_by_panel_type()
    for idx, value in df["panel_type"].items():
        id = id_by_panel_type.get(value, None)
        if not id:
            if value:
                errors.append(f"行 {idx + 1}: panel_type \"{value}\" は未登録です  \n先にマスターに登録してください")
            else:
                errors.append(f"行 {idx + 1}: panel_type は必須項目です")
        else:
            # IDに変換
            df.loc[idx, "panel_type_id"] = int(id)
    df.drop(columns=["panel_type"], inplace=True)

# IDをパネル方式に変換
def convert_id_to_panel_type(df: pd.DataFrame):
    id_by_panel_type = get_id_by_panel_type()
    panel_type_by_id = {v: k for k, v in id_by_panel_type.items()}
    for idx, value in df["panel_type_id"].items():
        name = panel_type_by_id.get(value, None)
        df.loc[idx, "panel_type"] = name
    df.drop(columns=["panel_type_id"], inplace=True)

# 解像度を分割
def split_resolution(resolution: str):
    return resolution.split("x")

# 解像度を連結
def concat_resolution(resolution_w: str, resolution_h: str):
    return f"{resolution_w}x{resolution_h}"

# 解像度をまとめて連結
def concat_resolution_all(df: pd.DataFrame):
    df["resolution"] = df.apply(
        lambda row: concat_resolution(str(row["resolution_w"]), str(row["resolution_h"])),
        axis=1
    )
    df.drop(columns=["resolution_w"], inplace=True)
    df.drop(columns=["resolution_h"], inplace=True)

# タイムスタンプを表示用に変換
def convert_timestamp(df: pd.DataFrame):
    for col in ["created_at", "updated_at"]:
        df[col] = pd.to_datetime(df[col], utc=True)

    # 日本時間に変換
    df["created_at"] = df["created_at"].dt.tz_convert("Asia/Tokyo")
    df["updated_at"] = df["updated_at"].dt.tz_convert("Asia/Tokyo")

    # フォーマット変換
    df["created_at"] = df["created_at"].dt.strftime("%Y-%m-%d %H:%M")
    df["updated_at"] = df["updated_at"].dt.strftime("%Y-%m-%d %H:%M")

# 製品データを編集用に変換
def convert_products_to_edit(df: pd.DataFrame):
    convert_timestamp(df)
    convert_id_to_brand(df)
    convert_id_to_panel_type(df)
    concat_resolution_all(df)

# 製品データの値をintに型変換
def cast_products_to_int(records: list[dict]) -> list[dict]:
    return cast_records_to_int(records, [
        "brand_id",
        "panel_type_id",
        "resolution_w",
        "resolution_h"
    ])

# 指定列の値をintに型変換
def cast_records_to_int(records: list[dict], columns: list[str]) -> list[dict]:
    new_records = []
    for row in records:
        new_row = row.copy()
        for col in columns:
            if col in new_row:
                val = new_row[col]
                if val is None or (isinstance(val, float) and math.isnan(val)):
                    new_row[col] = 0
                else:
                    new_row[col] = int(val)
        new_records.append(new_row)
    return new_records

# DataFrameをExcel形式のバイト列に変換
def to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    if df.empty:
        df = pd.DataFrame(columns=df.columns)
    
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    return output.getvalue()
