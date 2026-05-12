CREATE TABLE IF NOT EXISTS stg_sap_zsd017_sales (
    id INTEGER PRIMARY KEY,
    source_file_name TEXT NOT NULL,
    source_sheet_name TEXT,
    source_row_number INTEGER NOT NULL,
    import_batch_id TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    raw_record_json TEXT NOT NULL,

    sales_org_code TEXT,
    sales_org_text TEXT,
    center_code TEXT,
    center_text TEXT,
    model_doc_number TEXT,
    sales_doc_position TEXT,
    sales_doc_type_code TEXT,
    sales_doc_type_text TEXT,
    seller_group_code TEXT,
    seller_group_text TEXT,
    requester_code TEXT,
    requester_name TEXT,
    ship_to_code TEXT,
    ship_to_name TEXT,

    material_number TEXT,
    material_text TEXT,
    material_type_code TEXT,
    material_type_text TEXT,
    customer_material_number TEXT,

    delivery_number TEXT,
    delivery_type_code TEXT,
    delivery_type_text TEXT,
    movement_date TEXT,
    availability_date TEXT,

    ordered_qty REAL,
    sales_uom TEXT,
    delivered_qty REAL,
    net_weight REAL,
    gross_weight REAL,
    weight_uom TEXT,

    net_value REAL,
    currency TEXT,
    unit_sales_value REAL,

    lot_number TEXT,
    family_code TEXT,
    family_text TEXT,
    internal_quality_code TEXT,
    quality_description TEXT,

    thickness_mm REAL,
    width_mm REAL,
    length_mm REAL,

    customer_number TEXT,
    customer_name TEXT,
    units_count REAL,
    meters REAL,
    requested_delivery_date TEXT,
    period TEXT,
    sales_unit_price REAL,
    customer_order_number TEXT,
    supplier_lot_number TEXT,
    coil_number TEXT,

    is_valid_row INTEGER NOT NULL CHECK (is_valid_row IN (0, 1)),
    validation_error TEXT,
    processed_to_core INTEGER NOT NULL CHECK (processed_to_core IN (0, 1))
);

CREATE TABLE IF NOT EXISTS stg_boss_matrix (
    id INTEGER PRIMARY KEY,
    source_file_name TEXT NOT NULL,
    source_sheet_name TEXT,
    source_row_number INTEGER NOT NULL,
    import_batch_id TEXT NOT NULL,
    imported_at TEXT NOT NULL,
    raw_record_json TEXT NOT NULL,

    our_ref TEXT,
    product TEXT,
    grade TEXT,
    thickness_mm REAL,
    width_mm REAL,
    length_mm REAL,
    thickness_tolerance_text TEXT,
    width_tolerance_text TEXT,
    cw_min REAL,
    cw_max REAL,
    tn REAL,

    notes TEXT,
    is_valid_row INTEGER NOT NULL CHECK (is_valid_row IN (0, 1)),
    validation_error TEXT,
    processed_to_core INTEGER NOT NULL CHECK (processed_to_core IN (0, 1))
);

CREATE TABLE IF NOT EXISTS materials (
    id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL,
    quality TEXT NOT NULL,
    thickness_mm REAL NOT NULL,
    width_mm REAL NOT NULL,
    length_mm REAL,
    coating TEXT NOT NULL,
    finish TEXT,
    product_form_code TEXT,
    product_form_text TEXT,
    technical_notes TEXT,
    material_key TEXT NOT NULL UNIQUE,
    is_active INTEGER NOT NULL CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL,
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

CREATE INDEX IF NOT EXISTS idx_stg_sap_batch
ON stg_sap_zsd017_sales(import_batch_id);

CREATE INDEX IF NOT EXISTS idx_stg_sap_material_number
ON stg_sap_zsd017_sales(material_number);

CREATE INDEX IF NOT EXISTS idx_stg_sap_requester_code
ON stg_sap_zsd017_sales(requester_code);

CREATE INDEX IF NOT EXISTS idx_stg_sap_processed_to_core
ON stg_sap_zsd017_sales(processed_to_core);

CREATE INDEX IF NOT EXISTS idx_stg_boss_batch
ON stg_boss_matrix(import_batch_id);

CREATE INDEX IF NOT EXISTS idx_stg_boss_grade
ON stg_boss_matrix(grade);

CREATE INDEX IF NOT EXISTS idx_stg_boss_processed_to_core
ON stg_boss_matrix(processed_to_core);