CREATE TABLE IF NOT EXISTS audit.invoice_audit (
    id SERIAL PRIMARY KEY,
    invoice_id UUID UNIQUE NOT NULL DEFAULT gen_random_uuid(),
    file_name VARCHAR(255),
    file_type VARCHAR(8),
    file_path TEXT NOT NULL,
    file_checksum VARCHAR(128) UNIQUE NOT NULL,
    processing_status VARCHAR(16) NOT NULL DEFAULT 'detected',
    validation_status VARCHAR(16) DEFAULT NULL,
    vendor_name VARCHAR(255),
    invoice_number VARCHAR(128),
    invoice_date DATE,
    currency VARCHAR(8),
    subtotal NUMERIC(14,2),
    tax_amount NUMERIC(14,2),
    total_amount NUMERIC(14,2),
    report_json JSONB,
    report_html TEXT,
    error_message TEXT,
    validation_run INT DEFAULT 0,
    indexed_at TIMESTAMPTZ,
    detected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS audit.invoice_line_items (
    id SERIAL PRIMARY KEY,
    invoice_id UUID NOT NULL,
    line_number INT NOT NULL,
    item_code VARCHAR(128),
    description TEXT,
    quantity NUMERIC(12,4),
    unit_price NUMERIC(14,2),
    line_total NUMERIC(14,2),
    UNIQUE (invoice_id, line_number),
    CONSTRAINT fk_invoice_line_items_invoice
        FOREIGN KEY (invoice_id) REFERENCES audit.invoice_audit (invoice_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit.discrepancies (
    id SERIAL PRIMARY KEY,
    invoice_id UUID NOT NULL,
    source VARCHAR(16) NOT NULL,
    line_number INT,
    field_name VARCHAR(128) NOT NULL,
    invoice_value TEXT,
    expected_value TEXT,
    deviation_pct NUMERIC(10,4),
    severity VARCHAR(16),
    message TEXT,
    validation_run INT DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_discrepancies_invoice
        FOREIGN KEY (invoice_id) REFERENCES audit.invoice_audit (invoice_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit.file_events (
    id SERIAL PRIMARY KEY,
    invoice_id UUID,
    file_path TEXT NOT NULL,
    file_checksum VARCHAR(128),
    event VARCHAR(32) NOT NULL,
    detail TEXT,
    at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT fk_file_events_invoice
        FOREIGN KEY (invoice_id) REFERENCES audit.invoice_audit (invoice_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_invoice_audit_vendor_name ON audit.invoice_audit (vendor_name);
CREATE INDEX IF NOT EXISTS idx_invoice_audit_invoice_number ON audit.invoice_audit (invoice_number);
CREATE INDEX IF NOT EXISTS idx_invoice_audit_invoice_date ON audit.invoice_audit (invoice_date);
CREATE INDEX IF NOT EXISTS idx_invoice_audit_validation_status ON audit.invoice_audit (validation_status);
CREATE INDEX IF NOT EXISTS idx_invoice_audit_processed_at ON audit.invoice_audit (processed_at);
CREATE INDEX IF NOT EXISTS idx_discrepancies_invoice_id ON audit.discrepancies (invoice_id);
