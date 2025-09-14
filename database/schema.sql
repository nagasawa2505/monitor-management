BEGIN;

-- ================================
-- 型定義
-- ================================

-- 製品ステータス
CREATE TYPE product_status AS ENUM ('active', 'discontinued');

-- ================================
-- テーブル定義
-- ================================

-- ブランド
CREATE TABLE brands (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

COMMENT ON TABLE brands IS 'ブランド';
COMMENT ON COLUMN brands.id IS 'ID';
COMMENT ON COLUMN brands.name IS '名称';
COMMENT ON COLUMN brands.created_at IS '作成日時';
COMMENT ON COLUMN brands.updated_at IS '更新日時';

-- パネル方式
CREATE TABLE panel_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL
);

COMMENT ON TABLE panel_types IS 'パネル方式';
COMMENT ON COLUMN panel_types.id IS 'ID';
COMMENT ON COLUMN panel_types.name IS '名称';
COMMENT ON COLUMN panel_types.created_at IS '作成日時';
COMMENT ON COLUMN panel_types.updated_at IS '更新日時';

-- 製品
CREATE TABLE products (
    product_id VARCHAR(100) PRIMARY KEY,
    model_name VARCHAR(100) NOT NULL UNIQUE,
    brand_id INT NOT NULL,
    size_inch NUMERIC(4,1) NOT NULL,
    resolution_w INT NOT NULL,
    resolution_h INT NOT NULL,
    panel_type_id INT NOT NULL,
    refresh_rate INT NOT NULL,
    price_jpy INT NOT NULL,
    stock_quantity INT NOT NULL,
    release_date DATE NOT NULL,
    status product_status NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,

    -- 外部キー制約(ブランド)
    CONSTRAINT fk_brands FOREIGN KEY (brand_id) REFERENCES brands (id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT,

    -- 外部キー制約(パネル方式)
    CONSTRAINT fk_panel_types FOREIGN KEY (panel_type_id) REFERENCES panel_types (id)
        ON DELETE RESTRICT
        ON UPDATE RESTRICT
);

COMMENT ON TABLE products IS '製品';
COMMENT ON COLUMN products.product_id IS '製品ID';
COMMENT ON COLUMN products.model_name IS '製品名';
COMMENT ON COLUMN products.brand_id IS 'ブランドID';
COMMENT ON COLUMN products.size_inch IS '画面サイズ';
COMMENT ON COLUMN products.resolution_w IS '解像度(横)';
COMMENT ON COLUMN products.resolution_h IS '解像度(縦)';
COMMENT ON COLUMN products.panel_type_id IS 'パネル方式ID';
COMMENT ON COLUMN products.refresh_rate IS 'リフレッシュレート(Hz)';
COMMENT ON COLUMN products.price_jpy IS '価格(円)';
COMMENT ON COLUMN products.stock_quantity IS '在庫数';
COMMENT ON COLUMN products.release_date IS '発売日';
COMMENT ON COLUMN products.status IS '製品ステータス';
COMMENT ON COLUMN products.created_at IS '作成日時';
COMMENT ON COLUMN products.updated_at IS '更新日時';

-- ================================
-- インデックス定義
-- ================================
CREATE INDEX idx_products_brand_id ON products (brand_id);
CREATE INDEX idx_products_panel_type_id ON products (panel_type_id);
CREATE INDEX idx_products_status ON products (status);

-- ================================
-- 関数定義
-- ================================

-- 更新日時更新
CREATE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = now();
   RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ================================
-- トリガー定義
-- ================================

-- ブランド.更新日時
CREATE TRIGGER trg_update_brands_updated_at
BEFORE UPDATE ON brands
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();

-- パネル方式.更新日時
CREATE TRIGGER trg_update_panel_types_updated_at
BEFORE UPDATE ON panel_types
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();

-- 製品.更新日時
CREATE TRIGGER trg_update_products_updated_at
BEFORE UPDATE ON products
FOR EACH ROW
EXECUTE FUNCTION update_updated_at();

-- ================================
-- サンプルマスター登録
-- ================================

-- ブランド
INSERT INTO brands (name) VALUES
  ('Apple'),
  ('Samsung'),
  ('ASUS'),
  ('AOC'),
  ('Dell'),
  ('LG');

-- パネル方式
INSERT INTO panel_types (name) VALUES
  ('IPS'),
  ('VA'),
  ('TN');

COMMIT;
