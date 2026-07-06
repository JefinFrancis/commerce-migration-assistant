-- Synthetic ATG GSA schema dump matching productCatalog.xml, used to develop and
-- test the database analyzer's reconciliation. Note:
--   * brand is NOT NULL here but not required in the XML  -> required is corrected.
--   * internal_sku_code exists here but not in the XML     -> surfaced as DB-only.

CREATE TABLE dcs_product (
  product_id        VARCHAR(40)  NOT NULL,
  display_name      VARCHAR(254) NOT NULL,
  long_desc         CLOB,
  brand             VARCHAR(80)  NOT NULL,
  launch_date       TIMESTAMP,
  featured          NUMERIC(1),
  internal_sku_code VARCHAR(40),
  PRIMARY KEY (product_id)
);

CREATE TABLE dcs_product_kw (
  product_id VARCHAR(40) NOT NULL,
  keyword    VARCHAR(80),
  PRIMARY KEY (product_id, keyword),
  FOREIGN KEY (product_id) REFERENCES dcs_product (product_id)
);

CREATE TABLE dcs_product_rel (
  product_id VARCHAR(40) NOT NULL,
  related_id VARCHAR(40) NOT NULL,
  FOREIGN KEY (product_id) REFERENCES dcs_product (product_id)
);

CREATE TABLE dcs_product_skus (
  product_id VARCHAR(40) NOT NULL,
  sku_id     VARCHAR(40) NOT NULL,
  FOREIGN KEY (product_id) REFERENCES dcs_product (product_id),
  FOREIGN KEY (sku_id)     REFERENCES dcs_sku (sku_id)
);

CREATE TABLE dcs_sku (
  sku_id     VARCHAR(40)   NOT NULL,
  color      VARCHAR(20),
  storage_gb NUMERIC(6),
  list_price NUMERIC(12,2),
  in_stock   NUMERIC(1),
  PRIMARY KEY (sku_id)
);
