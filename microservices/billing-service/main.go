package main

import (
    "database/sql"
    "encoding/json"
    "fmt"
    "log"
    "net/http"
    "os"
    "strings"
    "time"

    _ "github.com/lib/pq"
)

type OrganizationBillingState struct {
    OrganizationID string    `json:"organization_id"`
    Status         string    `json:"status"`
    ManualStatus   string    `json:"manual_status"`
    Region         string    `json:"region"`
    Plan           string    `json:"plan"`
    PaymentStatus  string    `json:"payment_status"`
    UpdatedBy      string    `json:"updated_by"`
    UpdatedAt      time.Time `json:"updated_at"`
    Reason         string    `json:"reason,omitempty"`
    AccessEnabled  bool      `json:"access_enabled"`
    InvoiceCount   int       `json:"invoice_count"`
}

type InvoiceRecord struct {
    ID              string     `json:"id"`
    OrganizationID  string     `json:"organization_id"`
    Country         string     `json:"country"`
    Currency        string     `json:"currency"`
    Amount          float64    `json:"amount"`
    Status          string     `json:"status"`
    Plan            string     `json:"plan,omitempty"`
    PaymentProvider string     `json:"payment_provider,omitempty"`
    CreatedAt       time.Time  `json:"created_at"`
    DueAt           time.Time  `json:"due_at,omitempty"`
    PaidAt          *time.Time `json:"paid_at,omitempty"`
}

type ReminderRecord struct {
    ID             string    `json:"id"`
    OrganizationID string    `json:"organization_id"`
    InvoiceID      string    `json:"invoice_id"`
    Status         string    `json:"status"`
    DueAt          time.Time `json:"due_at"`
    DaysRemaining  int       `json:"days_remaining"`
    Message        string    `json:"message"`
}

type BillingService struct {
    db *sql.DB
}

func newBillingService(dsn string) (*BillingService, error) {
    db, err := sql.Open("postgres", dsn)
    if err != nil {
        return nil, err
    }
    db.SetMaxOpenConns(10)
    db.SetMaxIdleConns(5)

    if err := initBillingSchema(db); err != nil {
        db.Close()
        return nil, err
    }
    return &BillingService{db: db}, nil
}

func initBillingSchema(db *sql.DB) error {
    var tableExists bool
    if err := db.QueryRow(`
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = 'organizations'
        )
    `).Scan(&tableExists); err != nil {
        return err
    }

    if tableExists {
        requiredColumns := map[string]struct{}{
            "organization_id": {},
            "status":         {},
            "manual_status":  {},
            "region":         {},
            "plan":           {},
            "payment_status": {},
            "updated_by":     {},
            "updated_at":     {},
            "reason":         {},
            "access_enabled": {},
            "invoice_count":  {},
        }

        rows, err := db.Query(`
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'organizations'
        `)
        if err != nil {
            return err
        }
        defer rows.Close()

        present := make(map[string]struct{}, len(requiredColumns))
        for rows.Next() {
            var name string
            if err := rows.Scan(&name); err != nil {
                return err
            }
            present[name] = struct{}{}
        }
        if err := rows.Err(); err != nil {
            return err
        }

        stale := false
        for col := range requiredColumns {
            if _, ok := present[col]; !ok {
                stale = true
                break
            }
        }

        if stale {
            log.Printf("repairing stale billing schema for organizations table")
            if _, err := db.Exec(`DROP TABLE IF EXISTS payment_invoices CASCADE`); err != nil {
                return err
            }
            if _, err := db.Exec(`DROP TABLE IF EXISTS organizations CASCADE`); err != nil {
                return err
            }
        }
    }

    statements := []string{
        `CREATE TABLE IF NOT EXISTS organizations (
            organization_id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'inactive',
            manual_status TEXT NOT NULL DEFAULT 'inactive',
            region TEXT,
            plan TEXT,
            payment_status TEXT NOT NULL DEFAULT 'unpaid',
            updated_by TEXT,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            reason TEXT,
            access_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            invoice_count INTEGER NOT NULL DEFAULT 0
        )`,
        `CREATE TABLE IF NOT EXISTS payment_invoices (
            id TEXT PRIMARY KEY,
            organization_id TEXT NOT NULL,
            country TEXT,
            currency TEXT NOT NULL DEFAULT 'USD',
            amount NUMERIC(12,2) NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            plan TEXT,
            payment_provider TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            due_at TIMESTAMPTZ NOT NULL,
            paid_at TIMESTAMPTZ,
            CONSTRAINT fk_org FOREIGN KEY (organization_id) REFERENCES organizations(organization_id)
        )`,
        `CREATE INDEX IF NOT EXISTS idx_payment_invoices_org ON payment_invoices(organization_id)`,
        `CREATE INDEX IF NOT EXISTS idx_payment_invoices_due ON payment_invoices(due_at)`,
    }

    for _, stmt := range statements {
        if _, err := db.Exec(stmt); err != nil {
            return err
        }
    }
    return nil
}

func (s *BillingService) setState(orgID, manualStatus, reason, updatedBy, region, plan string) (*OrganizationBillingState, error) {
    now := time.Now().UTC()
    accessEnabled := strings.EqualFold(manualStatus, "active")
    status := "inactive"
    paymentStatus := "suspended"
    if accessEnabled {
        status = "active"
        paymentStatus = "active"
    }

    if _, err := s.db.Exec(`
        INSERT INTO organizations (organization_id, status, manual_status, region, plan, payment_status, updated_by, updated_at, reason, access_enabled, invoice_count)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 0)
        ON CONFLICT (organization_id)
        DO UPDATE SET
            status = EXCLUDED.status,
            manual_status = EXCLUDED.manual_status,
            region = EXCLUDED.region,
            plan = EXCLUDED.plan,
            payment_status = EXCLUDED.payment_status,
            updated_by = EXCLUDED.updated_by,
            updated_at = EXCLUDED.updated_at,
            reason = EXCLUDED.reason,
            access_enabled = EXCLUDED.access_enabled,
            invoice_count = (
                SELECT COUNT(*) FROM payment_invoices WHERE organization_id = EXCLUDED.organization_id
            )
    `, orgID, status, manualStatus, region, plan, paymentStatus, updatedBy, now, reason, accessEnabled); err != nil {
        return nil, err
    }

    return s.accessState(orgID)
}

func (s *BillingService) accessState(orgID string) (*OrganizationBillingState, error) {
    row := s.db.QueryRow(`
        SELECT organization_id, status, manual_status, region, plan, payment_status, updated_by, updated_at, reason, access_enabled,
               COALESCE((SELECT COUNT(*) FROM payment_invoices WHERE organization_id = organizations.organization_id), 0)
        FROM organizations WHERE organization_id = $1`, orgID)

    state := &OrganizationBillingState{}
    if err := row.Scan(&state.OrganizationID, &state.Status, &state.ManualStatus, &state.Region, &state.Plan, &state.PaymentStatus,
        &state.UpdatedBy, &state.UpdatedAt, &state.Reason, &state.AccessEnabled, &state.InvoiceCount); err != nil {
        if err == sql.ErrNoRows {
            return &OrganizationBillingState{OrganizationID: orgID, Status: "inactive", PaymentStatus: "unpaid", AccessEnabled: false}, nil
        }
        return nil, err
    }
    return state, nil
}

func (s *BillingService) addInvoice(inv InvoiceRecord) (InvoiceRecord, error) {
    now := time.Now().UTC()
    if inv.DueAt.IsZero() {
        inv.DueAt = now.Add(30 * 24 * time.Hour)
    }
    if inv.CreatedAt.IsZero() {
        inv.CreatedAt = now
    }

    if _, err := s.db.Exec(`
        INSERT INTO organizations (organization_id, status, manual_status, region, plan, payment_status, updated_by, updated_at, reason, access_enabled, invoice_count)
        VALUES ($1, 'inactive', 'inactive', NULL, $2, 'unpaid', 'system', $3, 'initial organization state', false, 0)
        ON CONFLICT (organization_id) DO NOTHING
    `, inv.OrganizationID, inv.Plan, now); err != nil {
        return InvoiceRecord{}, err
    }

    if _, err := s.db.Exec(`
        INSERT INTO payment_invoices (id, organization_id, country, currency, amount, status, plan, payment_provider, created_at, due_at, paid_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
        ON CONFLICT (id) DO UPDATE SET
            organization_id = EXCLUDED.organization_id,
            country = EXCLUDED.country,
            currency = EXCLUDED.currency,
            amount = EXCLUDED.amount,
            status = EXCLUDED.status,
            plan = EXCLUDED.plan,
            payment_provider = EXCLUDED.payment_provider,
            created_at = EXCLUDED.created_at,
            due_at = EXCLUDED.due_at,
            paid_at = EXCLUDED.paid_at
    `, inv.ID, inv.OrganizationID, inv.Country, inv.Currency, inv.Amount, inv.Status, inv.Plan, inv.PaymentProvider, inv.CreatedAt, inv.DueAt, inv.PaidAt); err != nil {
        return InvoiceRecord{}, err
    }

    if strings.EqualFold(inv.Status, "paid") {
        paidAt := inv.PaidAt
        if paidAt == nil {
            tm := now
            paidAt = &tm
        }
        if _, err := s.db.Exec(`
            UPDATE organizations
            SET status = 'active', manual_status = 'active', payment_status = 'paid', updated_by = 'payment-service', updated_at = $1, reason = 'subscription payment received', access_enabled = true, invoice_count = (SELECT COUNT(*) FROM payment_invoices WHERE organization_id = $2)
            WHERE organization_id = $2
        `, now, inv.OrganizationID); err != nil {
            return InvoiceRecord{}, err
        }
    }

    return inv, nil
}

func (s *BillingService) listInvoices(orgID string) ([]InvoiceRecord, error) {
    rows, err := s.db.Query(`
        SELECT id, organization_id, country, currency, amount, status, plan, payment_provider, created_at, due_at, paid_at
        FROM payment_invoices
        WHERE organization_id = $1
        ORDER BY created_at DESC`, orgID)
    if err != nil {
        return nil, err
    }
    defer rows.Close()

    items := make([]InvoiceRecord, 0)
    for rows.Next() {
        inv := InvoiceRecord{}
        var paidAt sql.NullTime
        if err := rows.Scan(&inv.ID, &inv.OrganizationID, &inv.Country, &inv.Currency, &inv.Amount, &inv.Status, &inv.Plan, &inv.PaymentProvider,
            &inv.CreatedAt, &inv.DueAt, &paidAt); err != nil {
            return nil, err
        }
        if paidAt.Valid {
            t := paidAt.Time
            inv.PaidAt = &t
        }
        items = append(items, inv)
    }
    return items, nil
}

func (s *BillingService) listReminders(days int) ([]ReminderRecord, error) {
    if days <= 0 {
        days = 15
    }

    rows, err := s.db.Query(`
        SELECT i.id, i.organization_id, i.id AS invoice_id, i.status,
               i.due_at,
               DATE_PART('day', i.due_at - NOW())::int AS days_remaining
        FROM payment_invoices i
        WHERE i.status <> 'paid'
          AND i.due_at >= NOW() - ($1 || ' days')::interval
          AND i.due_at <= NOW() + ($1 || ' days')::interval
        ORDER BY i.due_at ASC`, days)
    if err != nil {
        return nil, err
    }
    defer rows.Close()

    reminders := make([]ReminderRecord, 0)
    for rows.Next() {
        r := ReminderRecord{}
        var daysRemaining int
        if err := rows.Scan(&r.ID, &r.OrganizationID, &r.InvoiceID, &r.Status, &r.DueAt, &daysRemaining); err != nil {
            return nil, err
        }
        r.DaysRemaining = daysRemaining
        switch {
        case daysRemaining < 0:
            r.Message = "invoice overdue"
            r.Status = "overdue"
        case daysRemaining == 0:
            r.Message = "payment due today"
            r.Status = "due_today"
        default:
            r.Message = "payment due soon"
            r.Status = "due_soon"
        }
        reminders = append(reminders, r)
    }
    return reminders, nil
}

type statusRequest struct {
    Status    string `json:"status"`
    Reason    string `json:"reason,omitempty"`
    UpdatedBy string `json:"updated_by,omitempty"`
    Region    string `json:"region,omitempty"`
    Plan      string `json:"plan,omitempty"`
}

type invoiceRequest struct {
    OrganizationID  string     `json:"organization_id"`
    Country         string     `json:"country"`
    Currency        string     `json:"currency"`
    Amount          float64    `json:"amount"`
    Status          string     `json:"status"`
    Plan            string     `json:"plan,omitempty"`
    PaymentProvider string     `json:"payment_provider,omitempty"`
    DueAt           *time.Time `json:"due_at,omitempty"`
}

func requireIRGPAdmin(next http.HandlerFunc) http.HandlerFunc {
    return func(w http.ResponseWriter, r *http.Request) {
        if r.Method == http.MethodOptions {
            next.ServeHTTP(w, r)
            return
        }

        role := strings.TrimSpace(r.Header.Get("X-IRGP-Role"))
        if role == "" {
            auth := strings.TrimSpace(r.Header.Get("Authorization"))
            if !strings.HasPrefix(auth, "Bearer ") || strings.TrimSpace(strings.TrimPrefix(auth, "Bearer ")) == "" {
                http.Error(w, "IRGP admin access required", http.StatusUnauthorized)
                return
            }
            role = "IRGP_ADMIN"
        }

        switch role {
        case "IRGP_ADMIN", "PLATFORM_ADMIN", "REPORT_ADMIN":
            next.ServeHTTP(w, r)
        default:
            http.Error(w, "forbidden: admin role required", http.StatusForbidden)
        }
    }
}

func writeJSON(w http.ResponseWriter, statusCode int, payload interface{}) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(statusCode)
    if err := json.NewEncoder(w).Encode(payload); err != nil {
        log.Printf("encode response: %v", err)
    }
}

func readJSON(r *http.Request, target interface{}) error {
    defer r.Body.Close()
    return json.NewDecoder(r.Body).Decode(target)
}

func main() {
    dsn := strings.TrimSpace(os.Getenv("DATABASE_URL"))
    if dsn == "" {
        dsn = "postgres://admin:postgres-dev-password@postgres:5432/report_platform?sslmode=disable"
    }

    svc, err := newBillingService(dsn)
    if err != nil {
        log.Fatalf("billing service database init failed: %v", err)
    }
    if os.Getenv("BILLING_SERVICE_ENV") == "local" {
        if _, err := svc.setState("org-acme", "active", "seed", "system", "us-east", "starter"); err != nil {
            log.Printf("seed org state failed: %v", err)
        }
    }

    mux := http.NewServeMux()

    mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
        writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "service": "billing-service"})
    })

    mux.HandleFunc("/api/v1/billing/organizations/", func(w http.ResponseWriter, r *http.Request) {
        orgID := strings.TrimPrefix(r.URL.Path, "/api/v1/billing/organizations/")
        orgID = strings.Trim(orgID, "/")
        if orgID == "" {
            http.Error(w, "organization_id is required", http.StatusBadRequest)
            return
        }

        switch r.Method {
        case http.MethodGet:
            state, err := svc.accessState(orgID)
            if err != nil {
                http.Error(w, fmt.Sprintf("load organization state failed: %v", err), http.StatusInternalServerError)
                return
            }
            writeJSON(w, http.StatusOK, state)
        case http.MethodPut:
            requireIRGPAdmin(func(w http.ResponseWriter, r *http.Request) {
                var body statusRequest
                if err := readJSON(r, &body); err != nil {
                    http.Error(w, fmt.Sprintf("invalid payload: %v", err), http.StatusBadRequest)
                    return
                }
                statusValue := strings.ToLower(strings.TrimSpace(body.Status))
                if statusValue == "" {
                    statusValue = "inactive"
                }
                if statusValue != "active" && statusValue != "inactive" {
                    http.Error(w, "status must be active or inactive", http.StatusBadRequest)
                    return
                }
                state, err := svc.setState(orgID, statusValue, body.Reason, body.UpdatedBy, body.Region, body.Plan)
                if err != nil {
                    http.Error(w, fmt.Sprintf("update state failed: %v", err), http.StatusInternalServerError)
                    return
                }
                writeJSON(w, http.StatusOK, state)
            })(w, r)
        default:
            http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
        }
    })

    mux.HandleFunc("/api/v1/billing/invoices", requireIRGPAdmin(func(w http.ResponseWriter, r *http.Request) {
        switch r.Method {
        case http.MethodGet:
            orgID := strings.TrimSpace(r.URL.Query().Get("organization_id"))
            if orgID == "" {
                http.Error(w, "organization_id is required", http.StatusBadRequest)
                return
            }
            invoices, err := svc.listInvoices(orgID)
            if err != nil {
                http.Error(w, fmt.Sprintf("load invoices failed: %v", err), http.StatusInternalServerError)
                return
            }
            writeJSON(w, http.StatusOK, map[string][]InvoiceRecord{"invoices": invoices})
        case http.MethodPost:
            var body invoiceRequest
            if err := readJSON(r, &body); err != nil {
                http.Error(w, fmt.Sprintf("invalid payload: %v", err), http.StatusBadRequest)
                return
            }
            if body.OrganizationID == "" {
                http.Error(w, "organization_id is required", http.StatusBadRequest)
                return
            }
            if body.Amount < 0 {
                http.Error(w, "amount cannot be negative", http.StatusBadRequest)
                return
            }
            if body.Status == "" {
                body.Status = "pending"
            }
            now := time.Now().UTC()
            inv := InvoiceRecord{
                ID:              fmt.Sprintf("inv-%d", now.UnixNano()),
                OrganizationID:  body.OrganizationID,
                Country:         body.Country,
                Currency:        body.Currency,
                Amount:          body.Amount,
                Status:          body.Status,
                Plan:            body.Plan,
                PaymentProvider: body.PaymentProvider,
                CreatedAt:       now,
            }
            if inv.Currency == "" {
                inv.Currency = "USD"
            }
            if inv.PaymentProvider == "" {
                inv.PaymentProvider = "stripe"
            }
            if body.DueAt != nil {
                inv.DueAt = body.DueAt.UTC()
            } else {
                inv.DueAt = now.Add(30 * 24 * time.Hour)
            }
            if strings.EqualFold(inv.Status, "paid") {
                paidAt := now
                inv.PaidAt = &paidAt
            }
            saved, err := svc.addInvoice(inv)
            if err != nil {
                http.Error(w, fmt.Sprintf("persist invoice failed: %v", err), http.StatusInternalServerError)
                return
            }
            writeJSON(w, http.StatusCreated, saved)
        default:
            http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
        }
    }))

    mux.HandleFunc("/api/v1/billing/reminders", func(w http.ResponseWriter, r *http.Request) {
        if r.Method != http.MethodGet {
            http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
            return
        }
        days := 15
        if q := strings.TrimSpace(r.URL.Query().Get("days")); q != "" {
            if value, err := fmt.Sscanf(q, "%d", &days); err != nil || value != 1 {
                http.Error(w, "days must be an integer", http.StatusBadRequest)
                return
            }
        }
        reminders, err := svc.listReminders(days)
        if err != nil {
            http.Error(w, fmt.Sprintf("load reminders failed: %v", err), http.StatusInternalServerError)
            return
        }
        writeJSON(w, http.StatusOK, map[string][]ReminderRecord{"reminders": reminders})
    })

    port := os.Getenv("PORT")
    if port == "" {
        port = "8000"
    }

    log.Printf("billing service listening on :%s", port)
    if err := http.ListenAndServe(":"+port, mux); err != nil {
        log.Fatalf("billing service failed: %v", err)
    }
}
