-- ============================================================
-- HIERROS Steel MVP — Schema canónico
-- Generado desde: C:\Users\carca\OneDrive\CARLOS\AA PRACTICAS\steel\db\steel_mvp.db
-- Última generación: 2026-05-22 12:39:59
--
-- Este fichero debe reflejar la estructura REAL de steel_mvp.db.
-- Capas: staging SAP, staging BOSS, staging proveedor, core operativo y legacy.
-- ============================================================

PRAGMA foreign_keys = ON;


-- ============================================================
-- CAPA 1 — STAGING SAP
-- ============================================================

-- table: stg_sap_zsd017_sales
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


-- ============================================================
-- CAPA 2 — STAGING BOSS
-- ============================================================

-- table: stg_boss_matrix
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
, am_flag TEXT, luso_flag TEXT, import_flag TEXT, missing_tons REAL, client_name TEXT, sheet_date TEXT, grouping_text TEXT, agreement_am TEXT, sales_price_or_cost REAL, am_spot_cost REAL, am_spot_cost_net REAL, am_auto_cost REAL, am_auto_cost_net REAL, ssab_cost REAL, ssab_cost_net REAL, adi_cost REAL, adi_cost_net REAL, luso_cost REAL, luso_cost_net REAL, galmed_cost REAL, leon_cost REAL, tata_cost REAL, tata_cost_net REAL, bao_cfrfo REAL, bao_ddp_hl REAL, base_equivalent REAL, offer_14 REAL, offer_15 REAL, offer_16 REAL, offer_17 REAL, am_tons REAL, luso_tons REAL, import_tons REAL, offer_14_total REAL, offer_15_total REAL, offer_16_total REAL, offer_17_total REAL);

-- table: stg_boss_request_candidates
CREATE TABLE IF NOT EXISTS stg_boss_request_candidates (
        id INTEGER PRIMARY KEY,
        boss_row_id INTEGER NOT NULL,
        our_ref TEXT,
        client_name TEXT,
        client_id INTEGER,
        product TEXT,
        grade TEXT,
        thickness_mm REAL,
        width_mm REAL,
        tn REAL,
        missing_tons REAL,
        sheet_date TEXT,
        matched_material_count INTEGER NOT NULL,
        matched_material_id INTEGER,
        match_status TEXT NOT NULL,
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (boss_row_id) REFERENCES stg_boss_matrix(id),
        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (matched_material_id) REFERENCES materials(id)
    );


-- ============================================================
-- CAPA 3 — STAGING DOCUMENTOS DE PROVEEDOR
-- ============================================================

-- table: stg_supplier_documents
CREATE TABLE IF NOT EXISTS stg_supplier_documents (
        id INTEGER PRIMARY KEY,
        file_name TEXT NOT NULL,
        file_type TEXT NOT NULL,                -- pdf | excel | email | docx
        supplier_code TEXT,
        file_path TEXT NOT NULL,
        imported_at TEXT NOT NULL,
        n_quotes_extracted INTEGER NOT NULL DEFAULT 0,
        raw_text TEXT,
        notes TEXT
    );

-- table: stg_supplier_quotes
CREATE TABLE IF NOT EXISTS stg_supplier_quotes (
        id INTEGER PRIMARY KEY,
        supplier_document_id INTEGER NOT NULL,
        source_type TEXT NOT NULL,                  -- pdf | excel | email
        supplier_code TEXT,
        supplier_name TEXT,

        extracted_grade TEXT,
        extracted_thickness_mm REAL,
        extracted_width_mm REAL,
        extracted_price_per_ton REAL,
        currency TEXT,
        incoterm TEXT,
        lead_time_days INTEGER,
        valid_until TEXT,

        raw_row_json TEXT,
        raw_text_snippet TEXT,

        matched_sourcing_request_id INTEGER,
        review_status TEXT NOT NULL DEFAULT 'pending',   -- pending | approved | rejected
        notes TEXT,
        created_at TEXT NOT NULL, needs_manual_review INTEGER DEFAULT 1, coating_raw TEXT,

        FOREIGN KEY (supplier_document_id) REFERENCES stg_supplier_documents(id),
        FOREIGN KEY (matched_sourcing_request_id) REFERENCES sourcing_requests(id)
    );


-- ============================================================
-- CAPA 4 — CORE OPERATIVO
-- ============================================================

-- table: clients
CREATE TABLE IF NOT EXISTS clients (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    sap_code TEXT,
    notes TEXT,
    created_at TEXT NOT NULL
);

-- table: client_aliases
CREATE TABLE IF NOT EXISTS client_aliases (
        id INTEGER PRIMARY KEY,
        alias_name TEXT NOT NULL UNIQUE,
        client_id INTEGER NOT NULL,
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (client_id) REFERENCES clients(id)
    );

-- table: materials
CREATE TABLE IF NOT EXISTS materials (
    id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL,
    quality TEXT NOT NULL,
    thickness_mm REAL NOT NULL,
    width_mm REAL NOT NULL,
    length_mm REAL,
    coating TEXT NOT NULL,
    finish TEXT,
    technical_notes TEXT,
    material_key TEXT NOT NULL UNIQUE,
    is_active INTEGER NOT NULL CHECK (is_active IN (0, 1)),
    created_at TEXT NOT NULL, product_form_code TEXT, product_form_text TEXT,
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

-- table: request_specs
CREATE TABLE IF NOT EXISTS request_specs (
        id INTEGER PRIMARY KEY,
        product TEXT NOT NULL,
        grade TEXT NOT NULL,
        thickness_mm REAL NOT NULL,
        width_mm REAL NOT NULL,
        thickness_tolerance_text TEXT,
        width_tolerance_text TEXT,
        cw_min REAL,
        cw_max REAL,
        spec_key TEXT NOT NULL UNIQUE,
        notes TEXT,
        created_at TEXT NOT NULL
    );

-- table: sourcing_requests
CREATE TABLE IF NOT EXISTS sourcing_requests (
        id INTEGER PRIMARY KEY,
        source_row_id INTEGER NOT NULL,
        client_id INTEGER NOT NULL,
        request_spec_id INTEGER NOT NULL,
        our_ref TEXT NOT NULL,
        requested_tons REAL NOT NULL,
        missing_tons REAL,
        sheet_date TEXT,
        notes TEXT,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (source_row_id) REFERENCES stg_boss_matrix(id),
        FOREIGN KEY (client_id) REFERENCES clients(id),
        FOREIGN KEY (request_spec_id) REFERENCES request_specs(id)
    );

-- table: request_intakes
CREATE TABLE IF NOT EXISTS request_intakes (
        id INTEGER PRIMARY KEY,
        input_mode TEXT NOT NULL,
        raw_input_text TEXT,
        parsed_input_json TEXT,
        input_quality_status TEXT,
        match_quality TEXT,
        warnings_json TEXT,
        chosen_spec_id INTEGER,
        sourcing_request_id INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY (chosen_spec_id) REFERENCES request_specs(id),
        FOREIGN KEY (sourcing_request_id) REFERENCES sourcing_requests(id)
    );

-- table: provider_capabilities
CREATE TABLE IF NOT EXISTS provider_capabilities (
        id INTEGER PRIMARY KEY,
        provider_code TEXT NOT NULL,
        provider_name TEXT NOT NULL,
        product TEXT,
        grade_pattern TEXT,
        min_thickness_mm REAL,
        max_thickness_mm REAL,
        min_width_mm REAL,
        max_width_mm REAL,
        is_active INTEGER NOT NULL DEFAULT 1,
        notes TEXT,
        created_at TEXT NOT NULL
    );

-- table: supplier_options
CREATE TABLE IF NOT EXISTS supplier_options (
        id INTEGER PRIMARY KEY,
        sourcing_request_id INTEGER NOT NULL,
        option_code TEXT NOT NULL,
        supplier_name TEXT,
        cost_type TEXT NOT NULL,
        unit_cost REAL,
        total_cost REAL,
        currency TEXT NOT NULL,
        notes TEXT,
        created_at TEXT NOT NULL, is_available INTEGER, is_zero_placeholder INTEGER, is_suspicious INTEGER, is_rankable INTEGER, validation_note TEXT, is_comparable INTEGER, comparability_note TEXT, capability_allowed INTEGER, capability_rule_id INTEGER, capability_note TEXT,
        FOREIGN KEY (sourcing_request_id) REFERENCES sourcing_requests(id)
    );

-- table: sourcing_request_shortlist
CREATE TABLE IF NOT EXISTS sourcing_request_shortlist (
        id INTEGER PRIMARY KEY,
        sourcing_request_id INTEGER NOT NULL UNIQUE,
        best_option_code TEXT,
        best_supplier_name TEXT,
        best_unit_cost REAL,
        best_total_cost REAL,

        second_option_code TEXT,
        second_supplier_name TEXT,
        second_unit_cost REAL,
        second_total_cost REAL,

        third_option_code TEXT,
        third_supplier_name TEXT,
        third_unit_cost REAL,
        third_total_cost REAL,

        am_spot_unit_cost REAL,
        am_spot_total_cost REAL,
        delta_best_vs_am_spot REAL,
        savings_total_vs_am_spot REAL,

        created_at TEXT NOT NULL,
        FOREIGN KEY (sourcing_request_id) REFERENCES sourcing_requests(id)
    );

-- table: sourcing_quotes
CREATE TABLE IF NOT EXISTS sourcing_quotes (
        id INTEGER PRIMARY KEY,
        sourcing_request_id INTEGER NOT NULL,
        supplier_code TEXT NOT NULL,
        supplier_name TEXT NOT NULL,
        quoted_price_per_ton REAL NOT NULL,
        transport_cost_per_ton REAL NOT NULL DEFAULT 0,
        surcharges_per_ton REAL NOT NULL DEFAULT 0,
        total_price_per_ton REAL NOT NULL,
        total_estimated_cost REAL NOT NULL,
        currency TEXT NOT NULL DEFAULT 'EUR',
        quoted_tons REAL,
        lead_time_days INTEGER,
        transport_type TEXT,
        quality_confirmed TEXT,
        source_type TEXT NOT NULL DEFAULT 'manual',
        needs_manual_review INTEGER NOT NULL DEFAULT 0,
        notes TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (sourcing_request_id) REFERENCES sourcing_requests(id)
    );

-- table: sourcing_decisions
CREATE TABLE IF NOT EXISTS sourcing_decisions (
        id INTEGER PRIMARY KEY,
        sourcing_request_id INTEGER NOT NULL,
        selected_quote_id INTEGER NOT NULL,
        decision_reason TEXT,
        decided_by TEXT,
        decided_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (sourcing_request_id) REFERENCES sourcing_requests(id),
        FOREIGN KEY (selected_quote_id) REFERENCES sourcing_quotes(id)
    );


-- ============================================================
-- ÍNDICES
-- ============================================================

-- index: idx_materials_material_key ON materials
CREATE INDEX IF NOT EXISTS idx_materials_material_key
ON materials(material_key);

-- index: idx_provider_capabilities_product ON provider_capabilities
CREATE INDEX IF NOT EXISTS idx_provider_capabilities_product
    ON provider_capabilities(product);

-- index: idx_provider_capabilities_provider ON provider_capabilities
CREATE INDEX IF NOT EXISTS idx_provider_capabilities_provider
    ON provider_capabilities(provider_code);

-- index: idx_request_intakes_mode ON request_intakes
CREATE INDEX IF NOT EXISTS idx_request_intakes_mode
    ON request_intakes(input_mode);

-- index: idx_request_intakes_request ON request_intakes
CREATE INDEX IF NOT EXISTS idx_request_intakes_request
    ON request_intakes(sourcing_request_id);

-- index: idx_request_intakes_spec ON request_intakes
CREATE INDEX IF NOT EXISTS idx_request_intakes_spec
    ON request_intakes(chosen_spec_id);

-- index: idx_request_specs_dimensions ON request_specs
CREATE INDEX IF NOT EXISTS idx_request_specs_dimensions
    ON request_specs(thickness_mm, width_mm);

-- index: idx_request_specs_product_grade ON request_specs
CREATE INDEX IF NOT EXISTS idx_request_specs_product_grade
    ON request_specs(product, grade);

-- index: idx_request_specs_spec_key ON request_specs
CREATE INDEX IF NOT EXISTS idx_request_specs_spec_key
    ON request_specs(spec_key);

-- index: idx_sourcing_decisions_quote ON sourcing_decisions
CREATE INDEX IF NOT EXISTS idx_sourcing_decisions_quote
    ON sourcing_decisions(selected_quote_id);

-- index: idx_sourcing_decisions_request_unique ON sourcing_decisions
CREATE UNIQUE INDEX IF NOT EXISTS idx_sourcing_decisions_request_unique
    ON sourcing_decisions(sourcing_request_id);

-- index: idx_sourcing_quotes_request ON sourcing_quotes
CREATE INDEX IF NOT EXISTS idx_sourcing_quotes_request
    ON sourcing_quotes(sourcing_request_id);

-- index: idx_sourcing_quotes_supplier ON sourcing_quotes
CREATE INDEX IF NOT EXISTS idx_sourcing_quotes_supplier
    ON sourcing_quotes(supplier_code);

-- index: idx_sourcing_requests_client ON sourcing_requests
CREATE INDEX IF NOT EXISTS idx_sourcing_requests_client
    ON sourcing_requests(client_id);

-- index: idx_sourcing_requests_our_ref ON sourcing_requests
CREATE INDEX IF NOT EXISTS idx_sourcing_requests_our_ref
    ON sourcing_requests(our_ref);

-- index: idx_sourcing_requests_spec ON sourcing_requests
CREATE INDEX IF NOT EXISTS idx_sourcing_requests_spec
    ON sourcing_requests(request_spec_id);

-- index: idx_stg_boss_batch ON stg_boss_matrix
CREATE INDEX IF NOT EXISTS idx_stg_boss_batch
ON stg_boss_matrix(import_batch_id);

-- index: idx_stg_boss_grade ON stg_boss_matrix
CREATE INDEX IF NOT EXISTS idx_stg_boss_grade
ON stg_boss_matrix(grade);

-- index: idx_stg_boss_processed_to_core ON stg_boss_matrix
CREATE INDEX IF NOT EXISTS idx_stg_boss_processed_to_core
ON stg_boss_matrix(processed_to_core);

-- index: idx_stg_sap_batch ON stg_sap_zsd017_sales
CREATE INDEX IF NOT EXISTS idx_stg_sap_batch
ON stg_sap_zsd017_sales(import_batch_id);

-- index: idx_stg_sap_material_number ON stg_sap_zsd017_sales
CREATE INDEX IF NOT EXISTS idx_stg_sap_material_number
ON stg_sap_zsd017_sales(material_number);

-- index: idx_stg_sap_processed_to_core ON stg_sap_zsd017_sales
CREATE INDEX IF NOT EXISTS idx_stg_sap_processed_to_core
ON stg_sap_zsd017_sales(processed_to_core);

-- index: idx_stg_sap_requester_code ON stg_sap_zsd017_sales
CREATE INDEX IF NOT EXISTS idx_stg_sap_requester_code
ON stg_sap_zsd017_sales(requester_code);

-- index: idx_stg_supplier_documents_file_type ON stg_supplier_documents
CREATE INDEX IF NOT EXISTS idx_stg_supplier_documents_file_type
    ON stg_supplier_documents(file_type);

-- index: idx_stg_supplier_documents_supplier_code ON stg_supplier_documents
CREATE INDEX IF NOT EXISTS idx_stg_supplier_documents_supplier_code
    ON stg_supplier_documents(supplier_code);

-- index: idx_stg_supplier_quotes_document ON stg_supplier_quotes
CREATE INDEX IF NOT EXISTS idx_stg_supplier_quotes_document
    ON stg_supplier_quotes(supplier_document_id);

-- index: idx_stg_supplier_quotes_matched_request ON stg_supplier_quotes
CREATE INDEX IF NOT EXISTS idx_stg_supplier_quotes_matched_request
    ON stg_supplier_quotes(matched_sourcing_request_id);

-- index: idx_stg_supplier_quotes_review_status ON stg_supplier_quotes
CREATE INDEX IF NOT EXISTS idx_stg_supplier_quotes_review_status
    ON stg_supplier_quotes(review_status);

-- index: idx_stg_supplier_quotes_supplier_code ON stg_supplier_quotes
CREATE INDEX IF NOT EXISTS idx_stg_supplier_quotes_supplier_code
    ON stg_supplier_quotes(supplier_code);

-- index: idx_supplier_options_code ON supplier_options
CREATE INDEX IF NOT EXISTS idx_supplier_options_code
    ON supplier_options(option_code);

-- index: idx_supplier_options_request ON supplier_options
CREATE INDEX IF NOT EXISTS idx_supplier_options_request
    ON supplier_options(sourcing_request_id);
