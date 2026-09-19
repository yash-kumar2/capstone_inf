CREATE TABLE IF NOT EXISTS erp.vendors (
    vendor_id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    currency VARCHAR(8) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS erp.purchase_orders (
    po_number VARCHAR(64) PRIMARY KEY,
    vendor_id VARCHAR(64) NOT NULL,
    currency VARCHAR(8) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'open',
    CONSTRAINT fk_purchase_orders_vendor
        FOREIGN KEY (vendor_id) REFERENCES erp.vendors(vendor_id)
);

CREATE TABLE IF NOT EXISTS erp.po_line_items (
    id SERIAL PRIMARY KEY,
    po_number VARCHAR(64) NOT NULL,
    line_number INT NOT NULL,
    sku VARCHAR(128) NOT NULL,
    description TEXT NOT NULL,
    quantity NUMERIC(12,4) NOT NULL,
    unit_price NUMERIC(14,2) NOT NULL,
    UNIQUE (po_number, line_number),
    CONSTRAINT fk_po_line_items_po
        FOREIGN KEY (po_number) REFERENCES erp.purchase_orders(po_number) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS erp.sku_master (
    sku VARCHAR(128) PRIMARY KEY,
    description TEXT NOT NULL,
    uom VARCHAR(32) NOT NULL,
    list_price NUMERIC(14,2) NOT NULL,
    currency VARCHAR(8) NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);

INSERT INTO erp.vendors (vendor_id, name, currency, status)
VALUES
    ('V001', 'Acme Supplies Ltd', 'USD', 'active'),
    ('V002', 'Northwind GmbH', 'EUR', 'active'),
    ('V003', 'BluePeak SA', 'INR', 'active')
ON CONFLICT (vendor_id) DO NOTHING;

INSERT INTO erp.purchase_orders (po_number, vendor_id, currency, status)
VALUES
    ('PO-1001', 'V001', 'USD', 'open'),
    ('PO-1002', 'V002', 'EUR', 'open'),
    ('PO-1003', 'V003', 'INR', 'open'),
    ('PO-1004', 'V001', 'USD', 'closed')
ON CONFLICT (po_number) DO NOTHING;

INSERT INTO erp.sku_master (sku, description, uom, list_price, currency, active)
VALUES
    ('SKU-001', 'Office Chair', 'EA', 120.00, 'USD', TRUE),
    ('SKU-002', 'Desk Lamp', 'EA', 45.00, 'USD', TRUE),
    ('SKU-003', 'USB-C Hub', 'EA', 75.00, 'EUR', TRUE),
    ('SKU-004', 'Notebook', 'EA', 12.50, 'EUR', TRUE),
    ('SKU-005', 'Monitor Arm', 'EA', 210.00, 'INR', TRUE),
    ('SKU-006', 'Keyboard', 'EA', 55.00, 'INR', TRUE)
ON CONFLICT (sku) DO NOTHING;

INSERT INTO erp.po_line_items (po_number, line_number, sku, description, quantity, unit_price)
VALUES
    ('PO-1001', 1, 'SKU-001', 'Office Chair', 2, 120.00),
    ('PO-1001', 2, 'SKU-002', 'Desk Lamp', 3, 45.00),
    ('PO-1002', 1, 'SKU-003', 'USB-C Hub', 4, 75.00),
    ('PO-1002', 2, 'SKU-004', 'Notebook', 10, 12.50),
    ('PO-1003', 1, 'SKU-005', 'Monitor Arm', 2, 210.00),
    ('PO-1003', 2, 'SKU-006', 'Keyboard', 4, 55.00),
    ('PO-1004', 1, 'SKU-001', 'Office Chair', 1, 110.00)
ON CONFLICT (po_number, line_number) DO NOTHING;
