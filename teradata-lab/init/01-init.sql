DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'td_owner') THEN
        CREATE ROLE td_owner LOGIN PASSWORD 'TdOwnerPass123';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'td_readonly') THEN
        CREATE ROLE td_readonly LOGIN PASSWORD 'TdReadOnly123';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'td_writer') THEN
        CREATE ROLE td_writer LOGIN PASSWORD 'TdWriter123';
    END IF;
END $$;

GRANT CONNECT ON DATABASE teradata_lab TO td_readonly;
GRANT CONNECT ON DATABASE teradata_lab TO td_writer;

CREATE TABLE public.customers (
    customer_id SERIAL PRIMARY KEY,
    customer_name VARCHAR(120) NOT NULL,
    region VARCHAR(50) NOT NULL
);

CREATE TABLE public.sales_orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT NOT NULL REFERENCES public.customers(customer_id),
    order_date DATE NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    status VARCHAR(30) NOT NULL
);

INSERT INTO public.customers (customer_name, region) VALUES
('Teradata Lab UK', 'UK'),
('Teradata Lab US', 'US'),
('Teradata Lab IN', 'IN');

INSERT INTO public.sales_orders (customer_id, order_date, amount, status) VALUES
(1, DATE '2026-01-08', 10300.00, 'completed'),
(1, DATE '2026-01-20', 7600.00, 'completed'),
(2, DATE '2026-02-09', 18450.00, 'completed'),
(3, DATE '2026-02-19', 5250.00, 'pending'),
(2, DATE '2026-03-07', 20120.00, 'completed');

ALTER TABLE public.customers OWNER TO td_owner;
ALTER TABLE public.sales_orders OWNER TO td_owner;

REVOKE ALL ON DATABASE teradata_lab FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM PUBLIC;

GRANT USAGE ON SCHEMA public TO td_readonly, td_writer;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO td_readonly;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO td_writer;

ALTER DEFAULT PRIVILEGES FOR USER td_owner IN SCHEMA public
GRANT SELECT ON TABLES TO td_readonly;

ALTER DEFAULT PRIVILEGES FOR USER td_owner IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO td_writer;
