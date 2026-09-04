package report.authz

import future.keywords.if
import future.keywords.in

default allow := false

# REPORT_ADMIN can do ANY action on ANY resource
allow if {
    "REPORT_ADMIN" in input.user.roles
}

# PLATFORM_ADMIN can do ANY action on ANY resource
allow if {
    "PLATFORM_ADMIN" in input.user.roles
}

# REPORT_USER can only read within own tenant and region
allow if {
    "REPORT_USER" in input.user.roles
    input.action == "read"
    input.user.tenant_id == input.resource.tenant_id
    input.user.region == input.resource.region
}