BEGIN;

INSERT INTO organizations (id, name, contact_email, region, plan, status, created_at, updated_at)
VALUES
    ('11111111-1111-1111-1111-111111111111', 'Acme Financial', 'ops@acme.example', 'us-east', 'year', 'active', NOW(), NOW()),
    ('22222222-2222-2222-2222-222222222222', 'HSBC Analytics', 'analytics@hsbc.example', 'uk', 'half_year', 'active', NOW(), NOW()),
    ('33333333-3333-3333-3333-333333333333', 'DataStart Inc', 'hello@datastart.example', 'us-west', 'free', 'trial', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

INSERT INTO users (id, email, username, full_name, organization_id, role, status, created_at, updated_at)
VALUES
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'platform-admin@demo.local', 'platform-admin', 'Platform Admin', '11111111-1111-1111-1111-111111111111', 'PLATFORM_ADMIN', 'active', NOW(), NOW()),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'org-admin@demo.local', 'org-admin', 'Organization Admin', '11111111-1111-1111-1111-111111111111', 'ORG_ADMIN', 'active', NOW(), NOW()),
    ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'report-user@demo.local', 'report-user', 'Report User', '22222222-2222-2222-2222-222222222222', 'REPORT_USER', 'active', NOW(), NOW())
ON CONFLICT (email) DO NOTHING;

INSERT INTO data_sources (id, organization_id, name, type, status, created_at, updated_at)
VALUES
    ('10000000-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'Production Oracle', 'oracle', 'active', NOW(), NOW()),
    ('10000000-0000-0000-0000-000000000002', '11111111-1111-1111-1111-111111111111', 'Analytics Hive', 'hive', 'active', NOW(), NOW()),
    ('10000000-0000-0000-0000-000000000003', '22222222-2222-2222-2222-222222222222', 'HSBC Warehouse', 'warehouse', 'active', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

INSERT INTO subscription_plans (id, organization_id, plan, status, billing_cycle, created_at, updated_at)
VALUES
    ('50000000-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'starter', 'active', 'monthly', NOW(), NOW()),
    ('50000000-0000-0000-0000-000000000002', '22222222-2222-2222-2222-222222222222', 'growth', 'active', 'monthly', NOW(), NOW()),
    ('50000000-0000-0000-0000-000000000003', '33333333-3333-3333-3333-333333333333', 'free', 'trial', 'monthly', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

INSERT INTO notifications (id, organization_id, message, type, read, created_at, updated_at)
VALUES
    ('20000000-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'Q2 revenue report is ready for review.', 'report', FALSE, NOW(), NOW()),
    ('20000000-0000-0000-0000-000000000002', '22222222-2222-2222-2222-222222222222', 'Subscription renewal reminder is scheduled for this week.', 'subscription', FALSE, NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

INSERT INTO reminders (id, organization_id, title, schedule, message, status, created_at, updated_at)
VALUES
    ('30000000-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'Renewal reminder', '0 9 * * MON', 'Annual plan review is due.', 'active', NOW(), NOW()),
    ('30000000-0000-0000-0000-000000000002', '22222222-2222-2222-2222-222222222222', 'Month-end check-in', '0 8 1 * *', 'Check report quota before month end.', 'active', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

INSERT INTO report_jobs (id, organization_id, title, data_source_id, template, status, created_at, updated_at)
VALUES
    ('40000000-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'Q2 Revenue Summary', '10000000-0000-0000-0000-000000000001', 'default', 'completed', NOW(), NOW()),
    ('40000000-0000-0000-0000-000000000002', '22222222-2222-2222-2222-222222222222', 'Month End Dashboard', '10000000-0000-0000-0000-000000000003', 'default', 'running', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

INSERT INTO reports (id, organization_id, title, data_source_id, job_id, status, content, created_at, updated_at)
VALUES
    ('60000000-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'Q2 Revenue Summary', '10000000-0000-0000-0000-000000000001', '40000000-0000-0000-0000-000000000001', 'completed', '{"summary":"Revenue up 18%","region":"us-east"}', NOW(), NOW()),
    ('60000000-0000-0000-0000-000000000002', '22222222-2222-2222-2222-222222222222', 'Month End Dashboard', '10000000-0000-0000-0000-000000000003', '40000000-0000-0000-0000-000000000002', 'running', '{"summary":"Generating dashboard","region":"uk"}', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

COMMIT;
