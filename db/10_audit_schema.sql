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

CREATE TABLE IF NOT EXISTS audit.human_feedback (
    id SERIAL PRIMARY KEY,
    invoice_id UUID NOT NULL,
    field_name VARCHAR(128) NOT NULL,
    original_value TEXT,
    corrected_value TEXT,
    corrected_by VARCHAR(255) NOT NULL,
    corrected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revalidated BOOLEAN NOT NULL DEFAULT false,
    CONSTRAINT fk_human_feedback_invoice
        FOREIGN KEY (invoice_id) REFERENCES audit.invoice_audit (invoice_id) ON DELETE CASCADE
);

CREATE OR REPLACE FUNCTION audit.block_human_feedback_mutation()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Deleting human feedback rows is forbidden; insert-only history is required.';
    ELSIF TG_OP = 'UPDATE' THEN
        IF NEW.invoice_id = OLD.invoice_id
           AND NEW.field_name = OLD.field_name
           AND NEW.original_value = OLD.original_value
           AND NEW.corrected_by = OLD.corrected_by
           AND NEW.corrected_value = OLD.corrected_value
           AND NEW.revalidated IS DISTINCT FROM OLD.revalidated THEN
            RETURN NEW;
        END IF;
        RAISE EXCEPTION 'Human feedback updates are forbidden except for revalidated flag changes.';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_block_human_feedback_mutation ON audit.human_feedback;
CREATE TRIGGER trg_block_human_feedback_mutation
BEFORE DELETE OR UPDATE ON audit.human_feedback
FOR EACH ROW EXECUTE FUNCTION audit.block_human_feedback_mutation();

CREATE INDEX IF NOT EXISTS idx_invoice_audit_vendor_name ON audit.invoice_audit (vendor_name);
CREATE INDEX IF NOT EXISTS idx_invoice_audit_invoice_number ON audit.invoice_audit (invoice_number);
CREATE INDEX IF NOT EXISTS idx_invoice_audit_invoice_date ON audit.invoice_audit (invoice_date);
CREATE INDEX IF NOT EXISTS idx_invoice_audit_validation_status ON audit.invoice_audit (validation_status);
CREATE INDEX IF NOT EXISTS idx_invoice_audit_processed_at ON audit.invoice_audit (processed_at);
CREATE INDEX IF NOT EXISTS idx_discrepancies_invoice_id ON audit.discrepancies (invoice_id);
CREATE INDEX IF NOT EXISTS idx_human_feedback_invoice_id ON audit.human_feedback (invoice_id);
