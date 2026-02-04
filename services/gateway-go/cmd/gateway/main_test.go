package main

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

func TestHealth(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	rec := httptest.NewRecorder()

	healthHandler(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected status 200, got %d", rec.Code)
	}

	body := rec.Body.String()
	if body == "" || !containsAll(body, []string{"\"status\"", "\"ok\"", "\"gateway\""}) {
		t.Fatalf("unexpected body: %s", body)
	}
}

func TestValidateJWTMissing(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/v1/chat", nil)
	if err := validateJWT(req, "secret"); err == nil {
		t.Fatalf("expected error for missing token")
	}
}

func containsAll(body string, terms []string) bool {
	for _, term := range terms {
		if !strings.Contains(body, term) {
			return false
		}
	}
	return true
}
