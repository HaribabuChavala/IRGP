import { PrismaClient, RoleName, PlanType, OrganizationStatus, UserStatus, DataSourceType, DataSourceStatus, NotificationType, ReminderType, AuditDecision, QueryStatus, ReportJobStatus } from '@prisma/client';

const prisma = new PrismaClient();

async function main() {
  const orgAcme = await prisma.organization.upsert({
    where: { id: '11111111-1111-1111-1111-111111111111' },
    update: {},
    create: {
      id: '11111111-1111-1111-1111-111111111111',
      externalId: 'org-acme',
      name: 'Acme Financial',
      plan: 'year',
      status: OrganizationStatus.active,
      region: 'us-east',
      contactEmail: 'ops@acme.example',
    },
  });

  const orgHsbc = await prisma.organization.upsert({
    where: { id: '22222222-2222-2222-2222-222222222222' },
    update: {},
    create: {
      id: '22222222-2222-2222-2222-222222222222',
      externalId: 'org-hsbc',
      name: 'HSBC Analytics',
      plan: 'half_year',
      status: OrganizationStatus.active,
      region: 'uk',
      contactEmail: 'analytics@hsbc.example',
    },
  });

  const orgStartup = await prisma.organization.upsert({
    where: { id: '33333333-3333-3333-3333-333333333333' },
    update: {},
    create: {
      id: '33333333-3333-3333-3333-333333333333',
      externalId: 'org-startup',
      name: 'DataStart Inc',
      plan: PlanType.free,
      status: OrganizationStatus.trial,
      region: 'us-west',
      contactEmail: 'hello@datastart.example',
    },
  });

  const platformAdmin = await prisma.user.upsert({
    where: { email: 'platform-admin@demo.local' },
    update: {},
    create: {
      id: 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
      keycloakUserId: 'platform-admin-id',
      email: 'platform-admin@demo.local',
      username: 'platform-admin',
      fullName: 'Platform Admin',
      tenantId: 'platform',
      region: 'global',
      organizationName: 'Platform',
      status: UserStatus.active,
    },
  });

  const orgAdmin = await prisma.user.upsert({
    where: { email: 'org-admin@demo.local' },
    update: {},
    create: {
      id: 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
      keycloakUserId: 'org-admin-id',
      email: 'org-admin@demo.local',
      username: 'org-admin',
      fullName: 'Organization Admin',
      organizationId: orgAcme.id,
      tenantId: 'org-acme',
      region: 'us-east',
      organizationName: 'Acme Financial',
      status: UserStatus.active,
    },
  });

  const reportUser = await prisma.user.upsert({
    where: { email: 'report-user@demo.local' },
    update: {},
    create: {
      id: 'cccccccc-cccc-cccc-cccc-cccccccccccc',
      keycloakUserId: 'report-user-id',
      email: 'report-user@demo.local',
      username: 'report-user',
      fullName: 'Report User',
      organizationId: orgHsbc.id,
      tenantId: 'org-hsbc',
      region: 'uk',
      organizationName: 'HSBC Analytics',
      status: UserStatus.active,
    },
  });

  const roleNames: RoleName[] = ['PLATFORM_ADMIN', 'REPORT_ADMIN', 'REPORT_USER', 'VIEWER'];
  const roleMap = new Map<RoleName, number>();

  for (const roleName of roleNames) {
    const role = await prisma.role.upsert({
      where: { name: roleName },
      update: {},
      create: { name: roleName, description: roleName },
    });
    roleMap.set(roleName, role.id);
  }

  await prisma.userRole.upsert({
    where: { userId_roleId: { userId: platformAdmin.id, roleId: roleMap.get('PLATFORM_ADMIN')! } },
    update: {},
    create: { userId: platformAdmin.id, roleId: roleMap.get('PLATFORM_ADMIN')! },
  });

  await prisma.userRole.upsert({
    where: { userId_roleId: { userId: orgAdmin.id, roleId: roleMap.get('REPORT_ADMIN')! } },
    update: {},
    create: { userId: orgAdmin.id, roleId: roleMap.get('REPORT_ADMIN')! },
  });

  await prisma.userRole.upsert({
    where: { userId_roleId: { userId: reportUser.id, roleId: roleMap.get('REPORT_USER')! } },
    update: {},
    create: { userId: reportUser.id, roleId: roleMap.get('REPORT_USER')! },
  });

  await prisma.dataSource.upsert({
    where: { id: '10000000-0000-0000-0000-000000000001' },
    update: {},
    create: {
      id: '10000000-0000-0000-0000-000000000001',
      organizationId: orgAcme.id,
      name: 'Production Oracle',
      type: DataSourceType.oracle,
      host: 'oracle-prod.internal',
      port: 1521,
      databaseName: 'FINWARE',
      status: DataSourceStatus.connected,
      lastUsedAt: new Date(),
      queryCount: 8420,
    },
  });

  await prisma.notification.upsert({
    where: { id: '20000000-0000-0000-0000-000000000001' },
    update: {},
    create: {
      id: '20000000-0000-0000-0000-000000000001',
      organizationId: orgAcme.id,
      userId: orgAdmin.id,
      title: 'Report ready: Q2 Revenue',
      message: 'Your instant report has been generated and is ready to export.',
      type: NotificationType.report,
      isRead: false,
    },
  });

  await prisma.reminder.upsert({
    where: { id: '30000000-0000-0000-0000-000000000001' },
    update: {},
    create: {
      id: '30000000-0000-0000-0000-000000000001',
      organizationId: orgAcme.id,
      title: 'Renewal reminder',
      message: 'Your annual subscription renews soon.',
      reminderType: ReminderType.renewal,
      dueAt: new Date(Date.now() + 14 * 24 * 60 * 60 * 1000),
      isSent: false,
    },
  });

  console.log('Seed data inserted successfully.');
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
