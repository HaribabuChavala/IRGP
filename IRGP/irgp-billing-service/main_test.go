package main

import (
    "database/sql"
    "os"
    "testing"

    _ "github.com/lib/pq"
)

func TestInitBillingSchemaRepairsStaleOrganizationTable(t *testing.T) {
    dsn := os.Getenv("DATABASE_URL")
    if dsn == "" {
        dsn = "postgres://admin:postgres-dev-password@host.docker.internal:5432/report_platform?sslmode=disable"
    }

    db, err := sql.Open("postgres", dsn)
    if err != nil {
        t.Fatalf("open db: %v", err)
    }
    defer db.Close()

    if _, err := db.Exec(`DROP TABLE IF EXISTS payment_invoices CASCADE`); err != nil {
        t.Fatalf("drop payment_invoices: %v", err)
    }
    if _, err := db.Exec(`DROP TABLE IF EXISTS organizations CASCADE`); err != nil {
        t.Fatalf("drop organizations: %v", err)
    }
    if _, err := db.Exec(`CREATE TABLE organizations (organization_name TEXT NOT NULL)`); err != nil {
        t.Fatalf("create stale organizations table: %v", err)
    }

    if err := initBillingSchema(db); err != nil {
        t.Fatalf("expected initBillingSchema to repair stale schema but got: %v", err)
    }

    var hasOrgID bool
    if err := db.QueryRow(`SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'organizations'
          AND column_name = 'organization_id'
    )`).Scan(&hasOrgID); err != nil {
        t.Fatalf("check organization_id column: %v", err)
    }
    if !hasOrgID {
        t.Fatal("expected organization_id column after schema repair")
    }
}
