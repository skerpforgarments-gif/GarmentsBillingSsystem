

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

DROP TABLE IF EXISTS cheque_entries CASCADE;
DROP TABLE IF EXISTS dyeing_program_items CASCADE;
DROP TABLE IF EXISTS dyeing_programs CASCADE;
DROP TABLE IF EXISTS knitting_program_items CASCADE;
DROP TABLE IF EXISTS knitting_programs CASCADE;
DROP TABLE IF EXISTS yarn_po_items CASCADE;
DROP TABLE IF EXISTS yarn_purchase_orders CASCADE;
DROP TABLE IF EXISTS ledger_entries CASCADE;
DROP TABLE IF EXISTS payment_vouchers CASCADE;
DROP TABLE IF EXISTS receipt_vouchers CASCADE;
DROP TABLE IF EXISTS final_invoice_items CASCADE;
DROP TABLE IF EXISTS final_invoices CASCADE;
DROP TABLE IF EXISTS transport_invoice_items CASCADE;
DROP TABLE IF EXISTS transport_invoices CASCADE;
DROP TABLE IF EXISTS packing_slip_items CASCADE;
DROP TABLE IF EXISTS packing_slips CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS price_list_items CASCADE;
DROP TABLE IF EXISTS price_lists CASCADE;
DROP TABLE IF EXISTS party_contacts CASCADE;
DROP TABLE IF EXISTS parties CASCADE;
DROP TABLE IF EXISTS items CASCADE;
DROP TABLE IF EXISTS general_items CASCADE;
DROP TABLE IF EXISTS expense_ledgers CASCADE;
DROP TABLE IF EXISTS staff CASCADE;
DROP TABLE IF EXISTS taxes CASCADE;
DROP TABLE IF EXISTS banks CASCADE;
DROP TABLE IF EXISTS agents CASCADE;
DROP TABLE IF EXISTS transporters CASCADE;
DROP TABLE IF EXISTS companies CASCADE;

DROP FUNCTION IF EXISTS public.get_user_company_id CASCADE;

-- =========================================================
-- 1. SAAS CORE
-- =========================================================
CREATE TABLE companies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    company_code    TEXT,
    branch_code     TEXT,
    name            TEXT NOT NULL,
    address         TEXT,
    city            TEXT,
    phone           TEXT,
    mobile          TEXT,
    email           TEXT,
    website         TEXT,
    gst_details     TEXT,
    pan_no          TEXT,
    state_code      TEXT DEFAULT '33',
    financial_period TEXT,
    logo_base64     TEXT,
    created_at      TIMESTAMP DEFAULT now()
);

CREATE OR REPLACE FUNCTION public.get_user_company_id()
RETURNS uuid LANGUAGE sql SECURITY DEFINER
SET search_path = public STABLE AS $$
  SELECT id FROM public.companies WHERE user_id = auth.uid() LIMIT 1;
$$;

-- =========================================================
-- 2. SIMPLE MASTERS
-- =========================================================
CREATE TABLE transporters (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id  UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    address     TEXT,
    gstin       TEXT,
    UNIQUE(company_id, name)
);

CREATE TABLE agents (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name                TEXT NOT NULL,
    address             TEXT,
    gstin               TEXT,
    bank_name           TEXT,
    bank_account        TEXT,
    bank_ifsc           TEXT,
    commission_percent  NUMERIC(5,2) DEFAULT 0,
    UNIQUE(company_id, name)
);

CREATE TABLE banks (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id       UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name             TEXT NOT NULL,
    account_holder   TEXT,
    account_no       TEXT,
    ifsc_code        TEXT,
    branch           TEXT,
    opening_balance  NUMERIC(15,2) DEFAULT 0
);

CREATE TABLE taxes (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id    UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name          TEXT NOT NULL,
    hsn_code      TEXT,                        -- HSN / SAC code for GST returns
    tax_type      TEXT DEFAULT 'GST',           -- GST / IGST / TCS / Exempt
    cgst_percent  NUMERIC(5,2) DEFAULT 0,       -- Central GST component
    sgst_percent  NUMERIC(5,2) DEFAULT 0,       -- State GST component
    igst_percent  NUMERIC(5,2) DEFAULT 0,       -- Integrated GST (inter-state)
    tcs_percent   NUMERIC(5,2) DEFAULT 0,       -- Tax Collected at Source
    cess_percent  NUMERIC(5,2) DEFAULT 0,       -- Compensation Cess
    rate_percent  NUMERIC(5,2) DEFAULT 0        -- Total effective tax rate
);

CREATE TABLE staff (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id  UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    designation TEXT,
    department  TEXT,
    phone       TEXT,
    address     TEXT,
    salary      NUMERIC(12,2) DEFAULT 0
);

CREATE TABLE expense_ledgers (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id       UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    name             TEXT NOT NULL,
    account_code     TEXT,
    group_name       TEXT DEFAULT 'Indirect Expenses',
    hsn_sac          TEXT,
    opening_balance  NUMERIC(15,2) DEFAULT 0,
    opn_bal_type     TEXT DEFAULT 'DEBIT',
    tax_id           UUID REFERENCES taxes(id),
    description      TEXT
);

CREATE TABLE general_items (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id  UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    item_code   TEXT,
    item_name   TEXT NOT NULL,
    uom         TEXT,                    -- Pcs / Box / Kg / Meter / Litre / Set / Pair
    hsn_code    TEXT,                    -- HSN / SAC code
    tax_name    TEXT,                    -- Display name of applicable tax
    tax_id      UUID REFERENCES taxes(id) -- FK to taxes master
);

-- =========================================================
-- 3. ITEM MASTER
-- =========================================================
CREATE TABLE items (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    item_code           TEXT NOT NULL,
    item_order          INTEGER DEFAULT 1,
    brand_name          TEXT,
    variety             TEXT,
    style               TEXT,
    item_name           TEXT NOT NULL,
    item_type           TEXT DEFAULT 'Sales',        -- Sales / Supplies / Both
    sizes               TEXT[] NOT NULL DEFAULT '{}',
    pcs_per_inner_box   INTEGER DEFAULT 1,
    boxes_per_outer_box INTEGER DEFAULT 1,
    box_type            TEXT DEFAULT 'Single Box Pack',
    hsn_code            TEXT,
    tax_id              UUID REFERENCES taxes(id),
    tax_name            TEXT,                        -- Display name for the tax slab
    is_approved         BOOLEAN DEFAULT TRUE,
    is_blocked          BOOLEAN DEFAULT FALSE,
    reason              TEXT,
    opening_stock       JSONB DEFAULT '{}',
    created_at          TIMESTAMP DEFAULT now(),
    UNIQUE(company_id, item_code)
);

-- =========================================================
-- 4. PRICE LIST MASTER
-- =========================================================
CREATE TABLE price_lists (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    list_name       TEXT NOT NULL,
    effective_date  DATE,
    price_type      TEXT DEFAULT 'Wholesale',
    created_at      TIMESTAMP DEFAULT now(),
    UNIQUE(company_id, list_name)
);

-- Size-wise rate pivot table
CREATE TABLE price_list_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    price_list_id   UUID NOT NULL REFERENCES price_lists(id) ON DELETE CASCADE,
    item_id         UUID NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    size_value      TEXT NOT NULL,
    wholesale_rate  NUMERIC(10,2) DEFAULT 0,
    retail_rate     NUMERIC(10,2) DEFAULT 0,
    mrp_rate        NUMERIC(10,2) DEFAULT 0,
    UNIQUE(price_list_id, item_id, size_value)
);

-- =========================================================
-- 5. PARTY MASTER (30+ fields from screenshot)
-- =========================================================
CREATE TABLE parties (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    -- Basic Info
    name                TEXT NOT NULL,
    party_type          TEXT DEFAULT 'Both',   -- Customer / Supplier / Both
    -- Billing Address
    billing_address_line1  TEXT,
    billing_address_line2  TEXT,
    billing_address_line3  TEXT,
    billing_city                TEXT,
    billing_district            TEXT,
    billing_state               TEXT,
    billing_pincode             TEXT,
    -- Delivery Address
    delivery_address_line1 TEXT,
    delivery_address_line2 TEXT,
    delivery_address_line3 TEXT,
    delivery_city          TEXT,
    delivery_district      TEXT,
    delivery_state         TEXT,
    delivery_pincode       TEXT,
    -- Communication
    code                TEXT,
    phone               TEXT,
    mobile              TEXT,
    fax                 TEXT,
    email               TEXT,
    -- Tax IDs
    gstin               TEXT,
    cst_no              TEXT,
    pan_no              TEXT,
    -- Bank Details (Requested in Requirement Doc)
    bank_name           TEXT,
    bank_account_no     TEXT,
    bank_ifsc           TEXT,
    -- Linked Masters
    agent_id            UUID REFERENCES agents(id),
    transporter_id      UUID REFERENCES transporters(id),
    price_list_id       UUID REFERENCES price_lists(id),
    -- Logistics
    destination         TEXT,
    courier_name        TEXT,
    reference           TEXT,
    documents_thro      TEXT DEFAULT 'Direct', -- Direct / Bank
    order_by            TEXT,
    order_thro          TEXT DEFAULT 'DIRECT',
    -- Financial Terms
    opening_balance     NUMERIC(12,2) DEFAULT 0,
    opn_bal_type        TEXT DEFAULT 'DEBIT',  -- DEBIT / CREDIT
    for_allowed         BOOLEAN DEFAULT TRUE,
    credit_days         INTEGER DEFAULT 0,
    credit_limit        NUMERIC(12,2) DEFAULT 0,
    price_type          TEXT DEFAULT 'Wholesale',  -- Wholesale / Retail / MRP
    -- Tax Settings
    tax_type            TEXT DEFAULT 'GST',   -- GST / TCS / IGST
    gst_percent         NUMERIC(5,2) DEFAULT 0,
    igst_percent        NUMERIC(5,2) DEFAULT 0,
    cgst_percent        NUMERIC(5,2) DEFAULT 0,
    sgst_percent        NUMERIC(5,2) DEFAULT 0,
    tcs_percent         NUMERIC(5,2) DEFAULT 0,
    cess_percent        NUMERIC(5,2) DEFAULT 0,
    rate_percent        NUMERIC(5,2) DEFAULT 0,
    tcs_applicable      BOOLEAN DEFAULT FALSE,
    -- Discount Structure (%)
    discount_percent    NUMERIC(5,2) DEFAULT 0,
    -- Remarks & Status
    remarks             TEXT,
    is_approved         BOOLEAN DEFAULT TRUE,
    is_blocked          BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMP DEFAULT now(),
    UNIQUE(company_id, code),
    UNIQUE(company_id, name)
);

-- Party Contacts Sub-Table (screenshot: grid at bottom of party master)
CREATE TABLE party_contacts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    party_id        UUID NOT NULL REFERENCES parties(id) ON DELETE CASCADE,
    contact_person  TEXT,
    designation     TEXT,
    phone_no        TEXT,
    cell            TEXT
);

-- =========================================================
-- 6. ORDER ENTRY
-- =========================================================
CREATE TABLE orders (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    -- Header
    order_no            TEXT NOT NULL,
    order_date          DATE NOT NULL DEFAULT CURRENT_DATE,
    is_completed        BOOLEAN DEFAULT FALSE,
    party_id            UUID NOT NULL REFERENCES parties(id),
    agent_id            UUID REFERENCES agents(id),
    transporter_id      UUID REFERENCES transporters(id),
    destination         TEXT,
    documents_by        TEXT DEFAULT 'Direct',
    price_list_id       UUID REFERENCES price_lists(id),
    price_type          TEXT DEFAULT 'Wholesale',
    order_by            TEXT,
    order_thro          TEXT DEFAULT 'DIRECT',
    party_order_no      TEXT,
    party_order_date    DATE,
    remarks             TEXT,
    qty_type            TEXT DEFAULT 'Pieces',  -- Pieces / Boxes
    no_of_cases         INTEGER DEFAULT 0,
    -- Footer Totals
    no_of_items         INTEGER DEFAULT 0,
    total_pcs           INTEGER DEFAULT 0,
    total_boxes         NUMERIC(10,2) DEFAULT 0,
    total_amount        NUMERIC(12,2) DEFAULT 0,
    -- Tax & Discount Footer (Sequential)
    tax_type            TEXT DEFAULT 'IGST',
    tax_per             NUMERIC(5,2) DEFAULT 5,
    gst_rate            NUMERIC(5,2) DEFAULT 0,
    cgst_rate           NUMERIC(5,2) DEFAULT 0,
    sgst_rate           NUMERIC(5,2) DEFAULT 0,
    igst_rate           NUMERIC(5,2) DEFAULT 0,
    tcs_rate            NUMERIC(5,2) DEFAULT 0,
    cess_rate           NUMERIC(5,2) DEFAULT 0,
    taxable_amount      NUMERIC(12,2) DEFAULT 0,
    cgst_amount         NUMERIC(12,2) DEFAULT 0,
    sgst_amount         NUMERIC(12,2) DEFAULT 0,
    igst_amount         NUMERIC(12,2) DEFAULT 0,
    tcs_amount          NUMERIC(12,2) DEFAULT 0,
    cess_amount         NUMERIC(12,2) DEFAULT 0,
    gst_amount          NUMERIC(12,2) DEFAULT 0,
    discount_percent    NUMERIC(5,2) DEFAULT 0,
    discount_amount     NUMERIC(12,2) DEFAULT 0,
    round_off           NUMERIC(10,2) DEFAULT 0,
    net_amount          NUMERIC(12,2) DEFAULT 0,
    -- Status
    status              TEXT DEFAULT 'Pending',  -- Pending, Packed, Invoiced
    created_at          TIMESTAMP DEFAULT now()
);

CREATE TABLE order_items (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    order_id        UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    item_id         UUID NOT NULL REFERENCES items(id),
    item_name       TEXT,
    size_value      TEXT NOT NULL,
    rate            NUMERIC(10,2) DEFAULT 0,
    qty_pieces      INTEGER DEFAULT 0,
    qty_boxes       NUMERIC(10,2) DEFAULT 0,
    amount          NUMERIC(12,2) DEFAULT 0,
    discount_amount NUMERIC(12,2) DEFAULT 0,
    gross_amount    NUMERIC(12,2) DEFAULT 0,
    tax_percent     NUMERIC(5,2) DEFAULT 0
);

-- =========================================================
-- 7. PACKING SLIP
-- =========================================================
CREATE TABLE packing_slips (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    -- Header
    slip_no             TEXT NOT NULL,
    slip_year           TEXT,
    slip_date           DATE NOT NULL DEFAULT CURRENT_DATE,
    party_id            UUID NOT NULL REFERENCES parties(id),
    agent_id            UUID REFERENCES agents(id),
    transporter_id      UUID REFERENCES transporters(id),
    destination         TEXT,
    documents_by        TEXT DEFAULT 'Direct',
    price_list_id       UUID REFERENCES price_lists(id),
    price_type          TEXT DEFAULT 'Wholesale',
    party_order_no      TEXT,
    party_order_date    DATE,
    order_by            TEXT,
    order_thro          TEXT DEFAULT 'DIRECT',
    qty_type            TEXT DEFAULT 'Pieces',
    compliments         TEXT,
    -- Case Tracking (from screenshot)
    total_order_cases   INTEGER DEFAULT 0,
    packed_cases        INTEGER DEFAULT 0,
    no_of_cases         INTEGER DEFAULT 0,
    -- Prep Details (from screenshot)
    prepared_by         TEXT,
    checked_by          TEXT,
    packed_by           TEXT,
    barcode_type        TEXT DEFAULT 'Laser',  -- Laser / Dot Matrix
    export_to_word      BOOLEAN DEFAULT FALSE,
    -- Tax
    tax_type            TEXT DEFAULT 'IGST',
    tax_per             NUMERIC(5,2) DEFAULT 5,
    gst_rate            NUMERIC(5,2) DEFAULT 0,
    cgst_rate           NUMERIC(5,2) DEFAULT 0,
    sgst_rate           NUMERIC(5,2) DEFAULT 0,
    igst_rate           NUMERIC(5,2) DEFAULT 0,
    tcs_rate            NUMERIC(5,2) DEFAULT 0,
    cess_rate           NUMERIC(5,2) DEFAULT 0,
    taxable_amount      NUMERIC(12,2) DEFAULT 0,
    cgst_amount         NUMERIC(12,2) DEFAULT 0,
    sgst_amount         NUMERIC(12,2) DEFAULT 0,
    igst_amount         NUMERIC(12,2) DEFAULT 0,
    tcs_amount          NUMERIC(12,2) DEFAULT 0,
    cess_amount         NUMERIC(12,2) DEFAULT 0,
    gst_amount          NUMERIC(12,2) DEFAULT 0,
    tax_amount          NUMERIC(12,2) DEFAULT 0,
    -- Footer Totals
    no_of_items         INTEGER DEFAULT 0,
    total_pcs           INTEGER DEFAULT 0,
    total_boxes         NUMERIC(10,2) DEFAULT 0,
    total_amount        NUMERIC(12,2) DEFAULT 0,
    aftdis_amount       NUMERIC(12,2) DEFAULT 0,
    discount_percent    NUMERIC(5,2) DEFAULT 0,
    discount_amount     NUMERIC(12,2) DEFAULT 0,
    tax_amount          NUMERIC(12,2) DEFAULT 0,
    round_off           NUMERIC(10,2) DEFAULT 0,
    net_amount          NUMERIC(12,2) DEFAULT 0,
    bar_cod_percent     NUMERIC(5,2) DEFAULT 0,
    -- Status
    status              TEXT DEFAULT 'Unbilled',  -- Unbilled / Billed
    created_at          TIMESTAMP DEFAULT now()
);

CREATE TABLE packing_slip_items (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    packing_slip_id     UUID NOT NULL REFERENCES packing_slips(id) ON DELETE CASCADE,
    order_id            UUID REFERENCES orders(id),
    item_id             UUID NOT NULL REFERENCES items(id),
    item_name           TEXT,
    size_value          TEXT NOT NULL,
    rate                NUMERIC(10,2) DEFAULT 0,
    qty_pieces          INTEGER DEFAULT 0,
    qty_boxes           NUMERIC(10,2) DEFAULT 0,
    amount              NUMERIC(12,2) DEFAULT 0
);

-- =========================================================
-- 8. TRANSPORT INVOICE (Original Invoice in screenshots)
-- =========================================================
CREATE TABLE transport_invoices (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    -- Header
    invoice_no          TEXT NOT NULL,
    invoice_year        TEXT,
    invoice_date        DATE NOT NULL DEFAULT CURRENT_DATE,
    party_ref_no        TEXT,
    party_id            UUID NOT NULL REFERENCES parties(id),
    agent_id            UUID REFERENCES agents(id),
    transporter_id      UUID REFERENCES transporters(id),
    destination         TEXT,
    documents_by        TEXT DEFAULT 'Direct',
    price_list_id       UUID REFERENCES price_lists(id),
    price_type          TEXT DEFAULT 'Wholesale',
    packing_slip_no     TEXT,
    order_by            TEXT,
    order_thro          TEXT DEFAULT 'DIRECT',
    qty_type            TEXT DEFAULT 'Pieces',
    party_order_date    DATE,
    -- Print Options
    barcode_laser           BOOLEAN DEFAULT TRUE,
    barcode_dot_matrix      BOOLEAN DEFAULT FALSE,
    barcode_transport       BOOLEAN DEFAULT FALSE,
    preparation_date        DATE,
    -- Footer Totals
    no_of_items         INTEGER DEFAULT 0,
    total_pcs           INTEGER DEFAULT 0,
    total_boxes         NUMERIC(10,2) DEFAULT 0,
    total_amount        NUMERIC(12,2) DEFAULT 0,
    gross_amount        NUMERIC(12,2) DEFAULT 0,
    -- Discount
    discount_percent    NUMERIC(5,2) DEFAULT 0,
    discount_amount     NUMERIC(12,2) DEFAULT 0,
    -- Tax
    tax_type            TEXT DEFAULT 'IGST',
    tax_per             NUMERIC(5,2) DEFAULT 5,
    gst_rate            NUMERIC(5,2) DEFAULT 0,
    cgst_rate           NUMERIC(5,2) DEFAULT 0,
    sgst_rate           NUMERIC(5,2) DEFAULT 0,
    igst_rate           NUMERIC(5,2) DEFAULT 0,
    tcs_rate            NUMERIC(5,2) DEFAULT 0,
    cess_rate           NUMERIC(5,2) DEFAULT 0,
    taxable_amount      NUMERIC(12,2) DEFAULT 0,
    cgst_amount         NUMERIC(12,2) DEFAULT 0,
    sgst_amount         NUMERIC(12,2) DEFAULT 0,
    igst_amount         NUMERIC(12,2) DEFAULT 0,
    tcs_amount          NUMERIC(12,2) DEFAULT 0,
    cess_amount         NUMERIC(12,2) DEFAULT 0,
    gst_amount          NUMERIC(12,2) DEFAULT 0,
    tax_amount          NUMERIC(12,2) DEFAULT 0,
    -- Bottom Summary
    round_off           NUMERIC(10,2) DEFAULT 0,
    net_amount          NUMERIC(12,2) DEFAULT 0,
    -- LR Details (at the bottom of screenshot)
    lr_no               TEXT,
    lr_date             DATE,
    case_no             TEXT,
    no_case             INTEGER DEFAULT 0,
    tot_weight          NUMERIC(10,2) DEFAULT 0,
    charges             NUMERIC(12,2) DEFAULT 0,
    -- Status
    status              TEXT DEFAULT 'Unbilled',  -- Unbilled / Invoiced
    created_at          TIMESTAMP DEFAULT now()
);

CREATE TABLE transport_invoice_items (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id              UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    transport_invoice_id    UUID NOT NULL REFERENCES transport_invoices(id) ON DELETE CASCADE,
    packing_slip_id         UUID REFERENCES packing_slips(id),
    item_id                 UUID NOT NULL REFERENCES items(id),
    item_name               TEXT,
    size_value              TEXT NOT NULL,
    rate                    NUMERIC(10,2) DEFAULT 0,
    qty_pieces              INTEGER DEFAULT 0,
    qty_boxes               NUMERIC(10,2) DEFAULT 0,
    amount                  NUMERIC(12,2) DEFAULT 0
);

-- =========================================================
-- 9. FINAL INVOICE
-- =========================================================
CREATE TABLE final_invoices (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id              UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    transport_invoice_id    UUID REFERENCES transport_invoices(id),
    -- Header
    invoice_no              TEXT NOT NULL,
    invoice_date            DATE NOT NULL DEFAULT CURRENT_DATE,
    party_id                UUID NOT NULL REFERENCES parties(id),
    agent_id                UUID REFERENCES agents(id),
    transporter_id          UUID REFERENCES transporters(id),
    destination             TEXT,
    documents_by            TEXT DEFAULT 'Direct',
    price_list_id           UUID REFERENCES price_lists(id),
    price_type              TEXT DEFAULT 'Wholesale',
    order_by                TEXT,
    order_thro              TEXT DEFAULT 'DIRECT',
    party_order_no          TEXT,
    party_order_date        DATE,
    qty_type                TEXT DEFAULT 'Pieces',
    -- Mandatory LR fields
    lr_no                   TEXT,
    lr_date                 DATE,
    no_of_boxes             INTEGER DEFAULT 0,
    freight_charges         NUMERIC(12,2) DEFAULT 0,
    -- Footer Totals (inherited + tax breakup)
    no_of_items             INTEGER DEFAULT 0,
    total_pcs               INTEGER DEFAULT 0,
    total_boxes             NUMERIC(10,2) DEFAULT 0,
    total_amount            NUMERIC(12,2) DEFAULT 0,
    gross_amount            NUMERIC(12,2) DEFAULT 0,
    -- Discount
    discount_percent    NUMERIC(5,2) DEFAULT 0,
    discount_amount     NUMERIC(12,2) DEFAULT 0,
    taxable_amount          NUMERIC(12,2) DEFAULT 0,
    tax_type                TEXT DEFAULT 'IGST',
    tax_per                 NUMERIC(5,2) DEFAULT 5,
    gst_rate                NUMERIC(5,2) DEFAULT 0,
    cgst_rate               NUMERIC(5,2) DEFAULT 0,
    sgst_rate               NUMERIC(5,2) DEFAULT 0,
    igst_rate               NUMERIC(5,2) DEFAULT 0,
    tcs_rate                NUMERIC(5,2) DEFAULT 0,
    cess_rate               NUMERIC(5,2) DEFAULT 0,
    cgst_amount             NUMERIC(12,2) DEFAULT 0,
    sgst_amount             NUMERIC(12,2) DEFAULT 0,
    igst_amount             NUMERIC(12,2) DEFAULT 0,
    tcs_amount              NUMERIC(12,2) DEFAULT 0,
    cess_amount             NUMERIC(12,2) DEFAULT 0,
    gst_amount              NUMERIC(12,2) DEFAULT 0,
    round_off               NUMERIC(10,2) DEFAULT 0,
    net_amount              NUMERIC(12,2) DEFAULT 0,
    created_at              TIMESTAMP DEFAULT now()
);

CREATE TABLE final_invoice_items (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    final_invoice_id    UUID NOT NULL REFERENCES final_invoices(id) ON DELETE CASCADE,
    item_id             UUID NOT NULL REFERENCES items(id),
    item_name           TEXT,
    size_value          TEXT NOT NULL,
    rate                NUMERIC(10,2) DEFAULT 0,
    qty_pieces          INTEGER DEFAULT 0,
    qty_boxes           NUMERIC(10,2) DEFAULT 0,
    amount              NUMERIC(12,2) DEFAULT 0
);

-- =========================================================
-- 9A. PROCUREMENT (PURCHASE ORDERS)
-- =========================================================
CREATE TABLE purchase_orders (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    po_no               TEXT NOT NULL,
    po_date             DATE NOT NULL DEFAULT CURRENT_DATE,
    supplier_id         UUID NOT NULL REFERENCES parties(id),
    agent_id            UUID REFERENCES agents(id),
    destination         TEXT,
    transporter_id      UUID REFERENCES transporters(id),
    remarks             TEXT,
    freight             NUMERIC(12,2) DEFAULT 0,
    other_charges       NUMERIC(12,2) DEFAULT 0,
    total_pcs           INTEGER DEFAULT 0,
    total_amount        NUMERIC(12,2) DEFAULT 0,
    tax_per             NUMERIC(5,2) DEFAULT 0,
    net_amount          NUMERIC(12,2) DEFAULT 0,
    status              TEXT DEFAULT 'Pending',
    created_at          TIMESTAMP DEFAULT now()
);

CREATE TABLE purchase_order_items (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    purchase_order_id   UUID NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    item_id             UUID NOT NULL REFERENCES items(id),
    item_name           TEXT,
    size_value          TEXT NOT NULL,
    rate                NUMERIC(10,2) DEFAULT 0,
    qty_pieces          INTEGER DEFAULT 0,
    amount              NUMERIC(12,2) DEFAULT 0
);

-- =========================================================
-- 9B. PROCUREMENT (PURCHASE INVOICES)
-- =========================================================
CREATE TABLE purchase_invoices (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    purchase_order_id   UUID REFERENCES purchase_orders(id),
    invoice_no          TEXT NOT NULL,
    invoice_date        DATE NOT NULL DEFAULT CURRENT_DATE,
    supplier_id         UUID NOT NULL REFERENCES parties(id),
    agent_id            UUID REFERENCES agents(id),
    destination         TEXT,
    transporter_id      UUID REFERENCES transporters(id),
    order_by            TEXT,
    order_thro          TEXT DEFAULT 'DIRECT',
    qty_type            TEXT DEFAULT 'Pieces',
    lr_no               TEXT,
    lr_date             DATE,
    freight_charges     NUMERIC(12,2) DEFAULT 0,
    remarks             TEXT,
    total_pcs           INTEGER DEFAULT 0,
    total_amount        NUMERIC(12,2) DEFAULT 0,
    taxable_amount      NUMERIC(12,2) DEFAULT 0,
    tax_type            TEXT DEFAULT 'GST',
    tax_per             NUMERIC(5,2) DEFAULT 0,
    cgst_amount         NUMERIC(12,2) DEFAULT 0,
    sgst_amount         NUMERIC(12,2) DEFAULT 0,
    igst_amount         NUMERIC(12,2) DEFAULT 0,
    round_off           NUMERIC(10,2) DEFAULT 0,
    net_amount          NUMERIC(12,2) DEFAULT 0,
    status              TEXT DEFAULT 'Billed',
    created_at          TIMESTAMP DEFAULT now()
);

CREATE TABLE purchase_invoice_items (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    purchase_invoice_id UUID NOT NULL REFERENCES purchase_invoices(id) ON DELETE CASCADE,
    item_id             UUID NOT NULL REFERENCES items(id),
    item_name           TEXT,
    size_value          TEXT NOT NULL,
    rate                NUMERIC(10,2) DEFAULT 0,
    qty_pieces          INTEGER DEFAULT 0,
    amount              NUMERIC(12,2) DEFAULT 0
);

-- =========================================================
-- 9C. INVENTORY (STOCK LEDGER)
-- =========================================================
CREATE TABLE stock_ledger (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    entry_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    item_id         UUID NOT NULL REFERENCES items(id),
    size_value      TEXT NOT NULL,
    transaction_type TEXT NOT NULL, -- 'IN' / 'OUT' / 'OPENING'
    ref_type        TEXT,           -- 'Purchase Invoice' / 'Sales Invoice' / 'Manual'
    ref_id          TEXT,
    qty             INTEGER DEFAULT 0,
    rate            NUMERIC(10,2) DEFAULT 0,
    created_at      TIMESTAMP DEFAULT now()
);

-- =========================================================
-- 10. FINANCIALS
-- =========================================================
CREATE TABLE receipt_vouchers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    voucher_no      TEXT,
    voucher_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    party_id        UUID REFERENCES parties(id),
    agent_id        UUID REFERENCES agents(id),
    amount          NUMERIC(12,2) DEFAULT 0,
    mode            TEXT,  -- Cash / Bank / Cheque
    bank_id         UUID REFERENCES banks(id),
    narration       TEXT,
    created_at      TIMESTAMP DEFAULT now()
);

CREATE TABLE payment_vouchers (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    voucher_no      TEXT,
    voucher_date    DATE NOT NULL DEFAULT CURRENT_DATE,
    party_id        UUID REFERENCES parties(id),
    agent_id        UUID REFERENCES agents(id),
    expense_id      UUID REFERENCES expense_ledgers(id),
    amount          NUMERIC(12,2) DEFAULT 0,
    mode            TEXT,
    bank_id         UUID REFERENCES banks(id),
    narration       TEXT,
    created_at      TIMESTAMP DEFAULT now()
);

CREATE TABLE ledger_entries (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    entry_date      DATE NOT NULL DEFAULT CURRENT_DATE,
    account_type    TEXT,   -- Party / Agent / Expense
    account_id      UUID NOT NULL,
    ref_type        TEXT,   -- Invoice / Receipt / Payment
    ref_id          TEXT,
    debit           NUMERIC(12,2) DEFAULT 0,
    credit          NUMERIC(12,2) DEFAULT 0,
    narration       TEXT
);

-- =========================================================
-- 10A. YARN PURCHASE ORDERS
-- =========================================================
CREATE TABLE yarn_purchase_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    po_no TEXT,
    year TEXT,
    po_date TEXT,
    supplier_id UUID REFERENCES parties(id),
    supplier_name TEXT,
    attn TEXT,
    ref TEXT,
    delivery TEXT,
    remarks TEXT,
    total_qty_kgs NUMERIC(10,2) DEFAULT 0,
    total_amount NUMERIC(12,2) DEFAULT 0,
    total_tax NUMERIC(12,2) DEFAULT 0,
    grand_total NUMERIC(12,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE yarn_po_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    po_id UUID NOT NULL REFERENCES yarn_purchase_orders(id) ON DELETE CASCADE,
    s_no INT DEFAULT 1,
    item_name TEXT,
    bags INT DEFAULT 0,
    qty_kgs NUMERIC(10,2) DEFAULT 0,
    rate NUMERIC(10,2) DEFAULT 0,
    tax_type TEXT DEFAULT 'Gst 5%',
    gst_percent NUMERIC(5,2) DEFAULT 5,
    amount NUMERIC(12,2) DEFAULT 0,
    tax_amount NUMERIC(12,2) DEFAULT 0,
    total_amount NUMERIC(12,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT now()
);

-- =========================================================
-- 10B. KNITTING PROGRAMS
-- =========================================================
CREATE TABLE knitting_programs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    prog_no TEXT,
    year TEXT,
    prog_date TEXT,
    party_id UUID REFERENCES parties(id),
    party_name TEXT,
    attn TEXT,
    ref TEXT,
    delivery TEXT,
    remarks TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE knitting_program_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    program_id UUID NOT NULL REFERENCES knitting_programs(id) ON DELETE CASCADE,
    s_no INT DEFAULT 1,
    item_name TEXT,
    yarn_description TEXT,
    gsm_ll TEXT,
    gg TEXT,
    dia TEXT,
    weight NUMERIC(10,2) DEFAULT 0,
    roll_pcs INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT now()
);

-- =========================================================
-- 10C. DYEING PROGRAMS
-- =========================================================
CREATE TABLE dyeing_programs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    prog_no TEXT,
    year TEXT,
    prog_date TEXT,
    party_id UUID REFERENCES parties(id),
    party_name TEXT,
    attn TEXT,
    ref TEXT,
    delivery TEXT,
    remarks TEXT,
    created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE dyeing_program_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    program_id UUID NOT NULL REFERENCES dyeing_programs(id) ON DELETE CASCADE,
    s_no INT DEFAULT 1,
    item_name TEXT,
    colour TEXT,
    process TEXT,
    weight_kgs NUMERIC(10,2) DEFAULT 0,
    batch TEXT,
    created_at TIMESTAMP DEFAULT now()
);

-- =========================================================
-- 10D. CHEQUE ENTRIES
-- =========================================================
CREATE TABLE cheque_entries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    entry_no TEXT,
    entry_date TEXT,
    bank_id UUID REFERENCES banks(id),
    bank_name TEXT,
    bank_branch TEXT,
    bank_ifsc TEXT,
    bank_account_no TEXT,
    payee_name TEXT,
    amount NUMERIC(12,2) DEFAULT 0,
    cheque_no TEXT,
    cheque_date TEXT,
    ac_payee BOOLEAN DEFAULT TRUE,
    print_with_date BOOLEAN DEFAULT TRUE,
    narration TEXT,
    created_at TIMESTAMP DEFAULT now()
);

-- =========================================================
-- 11. ROW LEVEL SECURITY (Automatic SaaS Isolation)
-- =========================================================
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
ALTER TABLE transporters ENABLE ROW LEVEL SECURITY;
CREATE TABLE settings (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id          UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
    flow_type           TEXT DEFAULT 'Full' CHECK (flow_type IN ('Full', 'Direct')), -- Full = Order->Slip->Invoice
    financial_year_start DATE,
    financial_year_end   DATE,
    invoice_prefix      TEXT,
    order_prefix        TEXT,
    UNIQUE(company_id)
);

ALTER TABLE agents ENABLE ROW LEVEL SECURITY;
ALTER TABLE banks ENABLE ROW LEVEL SECURITY;
ALTER TABLE taxes ENABLE ROW LEVEL SECURITY;
ALTER TABLE staff ENABLE ROW LEVEL SECURITY;
ALTER TABLE expense_ledgers ENABLE ROW LEVEL SECURITY;
ALTER TABLE general_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE items ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_lists ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_list_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE parties ENABLE ROW LEVEL SECURITY;
ALTER TABLE party_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE packing_slips ENABLE ROW LEVEL SECURITY;
ALTER TABLE packing_slip_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE transport_invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE transport_invoice_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE final_invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE final_invoice_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE receipt_vouchers ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_vouchers ENABLE ROW LEVEL SECURITY;
ALTER TABLE ledger_entries ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_order_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_invoices ENABLE ROW LEVEL SECURITY;
ALTER TABLE purchase_invoice_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE stock_ledger ENABLE ROW LEVEL SECURITY;
ALTER TABLE yarn_purchase_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE yarn_po_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE knitting_programs ENABLE ROW LEVEL SECURITY;
ALTER TABLE knitting_program_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE dyeing_programs ENABLE ROW LEVEL SECURITY;
ALTER TABLE dyeing_program_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE cheque_entries ENABLE ROW LEVEL SECURITY;


-- NOTE: All ALTER TABLE migrations have been merged into the CREATE TABLE
-- statements above. This section is kept for reference only.
-- Re-running this file on a fresh DB will produce the complete, up-to-date schema.


-- Companies: user owns their own row
CREATE POLICY "company_select" ON companies FOR SELECT TO authenticated USING (user_id = auth.uid());
CREATE POLICY "company_insert" ON companies FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());
CREATE POLICY "company_update" ON companies FOR UPDATE TO authenticated USING (user_id = auth.uid());

-- Macro: Apply SaaS policy to every other table
DO $$ DECLARE tbl TEXT;
BEGIN FOR tbl IN SELECT unnest(ARRAY[
    'transporters','agents','banks','taxes','staff','expense_ledgers','general_items',
    'items','price_lists','price_list_items',
    'parties','party_contacts',
    'orders','order_items',
    'packing_slips','packing_slip_items',
    'transport_invoices','transport_invoice_items',
    'final_invoices','final_invoice_items',
    'receipt_vouchers','payment_vouchers','ledger_entries',
    'settings','purchase_orders','purchase_order_items',
    'purchase_invoices','purchase_invoice_items','stock_ledger',
    'yarn_purchase_orders','yarn_po_items','knitting_programs','knitting_program_items',
    'dyeing_programs','dyeing_program_items','cheque_entries'
]) LOOP
    EXECUTE format('
        CREATE POLICY "saas_all_%s" ON %I
        FOR ALL TO authenticated
        USING (company_id = get_user_company_id())
        WITH CHECK (company_id = get_user_company_id());
    ', tbl, tbl);
END LOOP; END $$;
