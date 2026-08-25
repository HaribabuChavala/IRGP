-- Seed data for demo organizations and their users.

INSERT INTO organizations (id, external_id, name, plan, status, region, contact_email)
VALUES
    ('11111111-1111-1111-1111-111111111111', 'org-acme', 'Acme Financial', 'year', 'active', 'us-east', 'ops@acme.example'),
    ('22222222-2222-2222-2222-222222222222', 'org-hsbc', 'HSBC Analytics', 'half_year', 'active', 'uk', 'analytics@hsbc.example'),
    ('33333333-3333-3333-3333-333333333333', 'org-startup', 'DataStart Inc', 'free', 'trial', 'us-west', 'hello@datastart.example')
ON CONFLICT (id) DO NOTHING;

INSERT INTO users (id, keycloak_user_id, email, username, full_name, organization_id, tenant_id, region, organization_name, status)
VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'platform-admin-id', 'platform-admin@demo.local', 'platform-admin', 'Platform Admin', NULL, 'platform', 'global', 'Platform', 'active'),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'org-admin-id', 'org-admin@demo.local', 'org-admin', 'Organization Admin', '11111111-1111-1111-1111-111111111111', 'org-acme', 'us-east', 'Acme Financial', 'active'),
    ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'report-user-id', 'report-user@demo.local', 'report-user', 'Report User', '22222222-2222-2222-2222-222222222222', 'org-hsbc', 'uk', 'HSBC Analytics', 'active')
ON CONFLICT (email) DO NOTHING;

INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u
JOIN roles r ON r.name = 'PLATFORM_ADMIN'
WHERE u.username = 'platform-admin'
ON CONFLICT DO NOTHING;

INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u
JOIN roles r ON r.name = 'REPORT_ADMIN'
WHERE u.username = 'org-admin'
ON CONFLICT DO NOTHING;

INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u
JOIN roles r ON r.name = 'REPORT_USER'
WHERE u.username = 'report-user'
ON CONFLICT DO NOTHING;

INSERT INTO data_sources (id, organization_id, name, type, host, port, database_name, status, last_used_at, query_count)
VALUES
    ('10000000-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'Production Oracle', 'oracle', 'oracle-prod.internal', 1521, 'FINWARE', 'connected', NOW(), 8420),
    ('10000000-0000-0000-0000-000000000002', '11111111-1111-1111-1111-111111111111', 'Analytics Hive', 'hive', 'hive-cluster.internal', 10000, 'analytics', 'connected', NOW(), 3210),
    ('10000000-0000-0000-0000-000000000003', '22222222-2222-2222-2222-222222222222', 'HSBC Warehouse', 'warehouse', 'warehouse.internal', 5432, 'dashboards', 'connected', NOW(), 5100)
ON CONFLICT (id) DO NOTHING;

INSERT INTO subscription_plans (code, name, price, quota_monthly, features)
VALUES
    ('free', 'Free', 0.00, 1000, '{"reports": "5/month", "support": "community"}'),
    ('starter', 'Starter', 49.00, 5000, '{"reports": "unlimited", "support": "email"}'),
    ('growth', 'Growth', 149.00, 25000, '{"reports": "unlimited", "support": "priority"}'),
    ('enterprise', 'Enterprise', 499.00, 100000, '{"reports": "unlimited", "support": "24x7"}')
ON CONFLICT (code) DO NOTHING;

INSERT INTO notifications (id, organization_id, user_id, title, message, type, is_read)
VALUES
    ('20000000-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'Report ready: Q2 Revenue', 'Your instant report has been generated and is ready to export.', 'report', FALSE),
    ('20000000-0000-0000-0000-000000000002', '22222222-2222-2222-2222-222222222222', 'cccccccc-cccc-cccc-cccc-cccccccccccc', 'Subscription renewal', 'Your plan renews in 14 days.', 'subscription', FALSE)
ON CONFLICT (id) DO NOTHING;

INSERT INTO reminders (id, organization_id, title, message, reminder_type, due_at, is_sent)
VALUES
    ('30000000-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'Renewal reminder', 'Your annual subscription renews soon.', 'renewal', NOW() + INTERVAL '14 days', FALSE),
    ('30000000-0000-0000-0000-000000000002', '22222222-2222-2222-2222-222222222222', 'Plan check-in', 'Review available quota before month end.', 'subscription', NOW() + INTERVAL '7 days', FALSE)
ON CONFLICT (id) DO NOTHING;
