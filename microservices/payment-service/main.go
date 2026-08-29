package main

import (
    "crypto/hmac"
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "fmt"
    "io"
    "log"
    "math"
    "net/http"
    "os"
    "strings"

    stripe "github.com/stripe/stripe-go/v82"
    stripePaymentIntent "github.com/stripe/stripe-go/v82/paymentintent"
)

type SupportedRegion struct {
    Code     string `json:"code"`
    Name     string `json:"name"`
    Currency string `json:"currency"`
}

var supportedRegions = map[string]SupportedRegion{
    "US": {Code: "US", Name: "United States", Currency: "USD"},
    "UK": {Code: "UK", Name: "United Kingdom", Currency: "GBP"},
    "AE": {Code: "AE", Name: "United Arab Emirates", Currency: "AED"},
    "IN": {Code: "IN", Name: "India", Currency: "INR"},
}

type CheckoutRequest struct {
    OrganizationID string  `json:"organization_id"`
    CustomerEmail  string  `json:"customer_email"`
    Country        string  `json:"country"`
    Currency       string  `json:"currency"`
    Amount         float64 `json:"amount"`
    Plan           string  `json:"plan,omitempty"`
    Description    string  `json:"description,omitempty"`
}

type PaymentResponse struct {
    Provider       string `json:"provider"`
    Mode           string `json:"mode"`
    PaymentIntent  string `json:"payment_intent,omitempty"`
    ClientSecret   string `json:"client_secret,omitempty"`
    CheckoutURL    string `json:"checkout_url,omitempty"`
    Status         string `json:"status,omitempty"`
    Currency       string `json:"currency,omitempty"`
    Amount         float64 `json:"amount,omitempty"`
    OrganizationID string `json:"organization_id,omitempty"`
    Message        string `json:"message,omitempty"`
}

func writeJSON(w http.ResponseWriter, statusCode int, payload any) {
    w.Header().Set("Content-Type", "application/json")
    w.WriteHeader(statusCode)
    if err := json.NewEncoder(w).Encode(payload); err != nil {
        log.Printf("encode response: %v", err)
    }
}

func readJSON(r *http.Request, target any) error {
    defer r.Body.Close()
    return json.NewDecoder(r.Body).Decode(target)
}

func validRegion(code string) (SupportedRegion, bool) {
    region, ok := supportedRegions[strings.ToUpper(strings.TrimSpace(code))]
    return region, ok
}

func normalizeCurrency(countryCode string, currency string) string {
    code := strings.TrimSpace(strings.ToUpper(currency))
    if code != "" {
        return code
    }
    region, ok := validRegion(countryCode)
    if ok {
        return region.Currency
    }
    return "USD"
}

func notifyBillingService(method, endpoint string, payload any) error {
    billingURL := os.Getenv("BILLING_SERVICE_URL")
    if billingURL == "" {
        billingURL = "http://billing-service:8000"
    }

    body, err := json.Marshal(payload)
    if err != nil {
        return err
    }

    req, err := http.NewRequest(method, billingURL+endpoint, strings.NewReader(string(body)))
    if err != nil {
        return err
    }
    req.Header.Set("Content-Type", "application/json")
    req.Header.Set("X-IRGP-Role", "IRGP_ADMIN")

    resp, err := http.DefaultClient.Do(req)
    if err != nil {
        return err
    }
    defer resp.Body.Close()
    if resp.StatusCode >= 400 {
        out, _ := io.ReadAll(resp.Body)
        return fmt.Errorf("billing service error: %s: %s", resp.Status, string(out))
    }
    return nil
}

func createStripePaymentIntent(req CheckoutRequest) (PaymentResponse, error) {
    apiKey := strings.TrimSpace(os.Getenv("STRIPE_API_KEY"))
    if apiKey == "" || apiKey == "dummy" {
        return PaymentResponse{
            Provider:      "stripe",
            Mode:          "demo",
            CheckoutURL:   "https://checkout.stripe.com/mock-demo",
            Status:        "demo",
            Currency:      normalizeCurrency(req.Country, req.Currency),
            Amount:        req.Amount,
            OrganizationID: req.OrganizationID,
            Message:       "Stripe API key missing; using secure demo mode for local development",
        }, nil
    }

    stripe.Key = apiKey
    amountInCents := int64(math.Round(req.Amount * 100))
    currency := strings.ToLower(normalizeCurrency(req.Country, req.Currency))
    description := strings.TrimSpace(req.Description)
    if description == "" {
        description = fmt.Sprintf("IRGP subscription for %s", req.OrganizationID)
    }

    params := &stripe.PaymentIntentParams{
        Amount:      stripe.Int64(amountInCents),
        Currency:    stripe.String(currency),
        Description: stripe.String(description),
        Metadata: map[string]string{
            "organization_id": req.OrganizationID,
            "country": req.Country,
            "currency": currency,
            "plan": req.Plan,
            "customer_email": req.CustomerEmail,
        },
        AutomaticPaymentMethods: &stripe.PaymentIntentAutomaticPaymentMethodsParams{Enabled: stripe.Bool(true)},
    }

    intent, err := stripePaymentIntent.New(params)
    if err != nil {
        return PaymentResponse{}, err
    }

    return PaymentResponse{
        Provider:       "stripe",
        Mode:           "live",
        PaymentIntent:  intent.ID,
        ClientSecret:   intent.ClientSecret,
        Status:         string(intent.Status),
        Currency:       strings.ToUpper(currency),
        Amount:         req.Amount,
        OrganizationID: req.OrganizationID,
    }, nil
}

func handleCheckout(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodPost {
        http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
        return
    }

    var req CheckoutRequest
    if err := readJSON(r, &req); err != nil {
        http.Error(w, fmt.Sprintf("invalid payload: %v", err), http.StatusBadRequest)
        return
    }

    if strings.TrimSpace(req.OrganizationID) == "" {
        http.Error(w, "organization_id is required", http.StatusBadRequest)
        return
    }
    if _, ok := validRegion(req.Country); !ok {
        http.Error(w, "unsupported country. Supported regions: US, UK, AE, IN", http.StatusBadRequest)
        return
    }
    if req.Amount <= 0 {
        http.Error(w, "amount must be greater than zero", http.StatusBadRequest)
        return
    }
    if req.CustomerEmail == "" {
        req.CustomerEmail = "billing@irgp.local"
    }
    if req.Currency == "" {
        req.Currency = normalizeCurrency(req.Country, "")
    }

    response, err := createStripePaymentIntent(req)
    if err != nil {
        http.Error(w, fmt.Sprintf("stripe payment intent failed: %v", err), http.StatusBadGateway)
        return
    }

    writeJSON(w, http.StatusOK, response)
}

func handleCountries(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodGet {
        http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
        return
    }

    regions := make([]SupportedRegion, 0, len(supportedRegions))
    for _, value := range supportedRegions {
        regions = append(regions, value)
    }
    writeJSON(w, http.StatusOK, map[string][]SupportedRegion{"supported_regions": regions})
}

func verifyStripeSignature(payload []byte, signatureHeader, secret string) bool {
    items := strings.Split(signatureHeader, ",")
    values := make(map[string]string, len(items))
    for _, item := range items {
        part := strings.SplitN(item, "=", 2)
        if len(part) != 2 {
            continue
        }
        values[part[0]] = part[1]
    }

    timestamp := values["t"]
    signedHash := values["v1"]
    if timestamp == "" || signedHash == "" {
        return false
    }

    mac := hmac.New(sha256.New, []byte(secret))
    if _, err := mac.Write([]byte(timestamp + "." + string(payload))); err != nil {
        return false
    }
    expected := hex.EncodeToString(mac.Sum(nil))
    return hmac.Equal([]byte(expected), []byte(signedHash))
}

func handleWebhook(w http.ResponseWriter, r *http.Request) {
    if r.Method != http.MethodPost {
        http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
        return
    }

    raw, err := io.ReadAll(r.Body)
    if err != nil {
        http.Error(w, fmt.Sprintf("read webhook body failed: %v", err), http.StatusBadRequest)
        return
    }

    secret := strings.TrimSpace(os.Getenv("STRIPE_WEBHOOK_SECRET"))
    if secret == "" {
        writeJSON(w, http.StatusAccepted, map[string]string{"status": "demo-webhook-accepted", "message": "Stripe webhook secret not configured; demo mode accepted"})
        return
    }

    signature := r.Header.Get("Stripe-Signature")
    if signature == "" {
        http.Error(w, "missing Stripe-Signature header", http.StatusBadRequest)
        return
    }

    if !verifyStripeSignature(raw, signature, secret) {
        http.Error(w, "invalid stripe signature", http.StatusBadRequest)
        return
    }

    var payload map[string]any
    if err := json.Unmarshal(raw, &payload); err != nil {
        http.Error(w, fmt.Sprintf("invalid webhook payload: %v", err), http.StatusBadRequest)
        return
    }

    eventType, _ := payload["type"].(string)
    if eventType == "payment_intent.succeeded" {
        dataMap, ok := payload["data"].(map[string]any)
        if ok {
            object, ok2 := dataMap["object"].(map[string]any)
            if ok2 {
                metadata, _ := object["metadata"].(map[string]any)
                orgID, _ := metadata["organization_id"].(string)
                if orgID != "" {
                    _ = notifyBillingService(http.MethodPut, "/api/v1/billing/organizations/"+orgID, map[string]string{"status": "active", "updated_by": "payment-service", "reason": "subscription payment received"})
                    _ = notifyBillingService(http.MethodPost, "/api/v1/billing/invoices", map[string]any{
                        "organization_id": orgID,
                        "country": metadata["country"],
                        "currency": strings.ToUpper(fmt.Sprint(metadata["currency"])),
                        "amount": 0,
                        "status": "paid",
                        "plan": metadata["plan"],
                        "payment_provider": "stripe",
                    })
                }
            }
        }
    }

    writeJSON(w, http.StatusOK, map[string]string{"status": "success", "event_type": eventType})
}

func main() {
    mux := http.NewServeMux()
    mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
        writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "service": "payment-service"})
    })
    mux.HandleFunc("/api/v1/payment/countries", handleCountries)
    mux.HandleFunc("/api/v1/payment/checkout", handleCheckout)
    mux.HandleFunc("/api/v1/payment/webhook", handleWebhook)

    port := os.Getenv("PORT")
    if port == "" {
        port = "8000"
    }

    log.Printf("payment service listening on :%s", port)
    if err := http.ListenAndServe(":"+port, mux); err != nil {
        log.Fatalf("payment service failed: %v", err)
    }
}
