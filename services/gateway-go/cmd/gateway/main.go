package main

import (
	"bytes"
	"crypto/rand"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/golang-jwt/jwt/v5"
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

const appVersion = "0.1.0"

var (
	requestCount = prometheus.NewCounterVec(
		prometheus.CounterOpts{
			Name: "gateway_requests_total",
			Help: "Total gateway requests",
		},
		[]string{"method", "path", "status"},
	)
	requestLatency = prometheus.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "gateway_request_latency_seconds",
			Help:    "Gateway request latency in seconds",
			Buckets: prometheus.DefBuckets,
		},
		[]string{"path"},
	)
)

type config struct {
	InferenceBaseURL string
	JWTSecret        string
	RateLimitRPS     int
	Port             string
}

type rateLimiter struct {
	mu    sync.Mutex
	limit int
	state map[string]*rateState
}

type rateState struct {
	second int64
	count  int
}

func newRateLimiter(limit int) *rateLimiter {
	return &rateLimiter{
		limit: limit,
		state: make(map[string]*rateState),
	}
}

func (rl *rateLimiter) Allow(ip string) bool {
	if rl.limit <= 0 {
		return true
	}
	if ip == "" {
		ip = "unknown"
	}
	now := time.Now().Unix()

	rl.mu.Lock()
	defer rl.mu.Unlock()

	entry, ok := rl.state[ip]
	if !ok || entry.second != now {
		rl.state[ip] = &rateState{second: now, count: 1}
		return true
	}

	if entry.count >= rl.limit {
		return false
	}
	entry.count++
	return true
}

func main() {
	log.SetFlags(0)

	prometheus.MustRegister(requestCount, requestLatency)

	cfg := loadConfig()
	if cfg.JWTSecret == "" {
		logJSON("warn", "JWT_SECRET not set; all requests are allowed", nil)
	}

	ml := newRateLimiter(cfg.RateLimitRPS)
	client := &http.Client{Timeout: 30 * time.Second}

	mux := http.NewServeMux()
	mux.HandleFunc("/health", healthHandler)
	mux.Handle("/metrics", promhttp.Handler())
	mux.HandleFunc("/v1/chat", chatHandler(cfg, ml, client))

	handler := withLogging(withCORS(mux))

	server := &http.Server{
		Addr:         ":" + cfg.Port,
		Handler:      handler,
		ReadTimeout:  15 * time.Second,
		WriteTimeout: 60 * time.Second,
	}

	logJSON("info", "gateway started", map[string]any{"port": cfg.Port})
	if err := server.ListenAndServe(); err != nil {
		logJSON("error", "gateway stopped", map[string]any{"error": err.Error()})
		os.Exit(1)
	}
}

func loadConfig() config {
	return config{
		InferenceBaseURL: envOrDefault("INFERENCE_BASE_URL", "http://inference:8000"),
		JWTSecret:        os.Getenv("JWT_SECRET"),
		RateLimitRPS:     envIntOrDefault("RATE_LIMIT_RPS", 5),
		Port:             envOrDefault("PORT", "8080"),
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		w.WriteHeader(http.StatusMethodNotAllowed)
		return
	}
	writeJSON(w, http.StatusOK, map[string]string{
		"status":  "ok",
		"service": "gateway",
		"version": appVersion,
	})
}

func chatHandler(cfg config, rl *rateLimiter, client *http.Client) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			w.WriteHeader(http.StatusMethodNotAllowed)
			return
		}

		ip := clientIP(r)
		if !rl.Allow(ip) {
			writeJSON(w, http.StatusTooManyRequests, map[string]string{
				"error": "rate limit exceeded",
			})
			return
		}

		if cfg.JWTSecret != "" {
			if err := validateJWT(r, cfg.JWTSecret); err != nil {
				writeJSON(w, http.StatusUnauthorized, map[string]string{
					"error": "unauthorized",
				})
				return
			}
		}

		requestID := r.Header.Get("X-Request-Id")
		if requestID == "" {
			requestID = newUUID()
			if requestID != "" {
				r.Header.Set("X-Request-Id", requestID)
			}
		}

		body, err := io.ReadAll(r.Body)
		if err != nil {
			writeJSON(w, http.StatusBadRequest, map[string]string{
				"error": "invalid request body",
			})
			return
		}

		proxyReq, err := http.NewRequest(http.MethodPost, cfg.InferenceBaseURL+"/v1/chat", bytes.NewReader(body))
		if err != nil {
			writeJSON(w, http.StatusInternalServerError, map[string]string{
				"error": "failed to build request",
			})
			return
		}
		proxyReq.Header.Set("Content-Type", "application/json")
		if auth := r.Header.Get("Authorization"); auth != "" {
			proxyReq.Header.Set("Authorization", auth)
		}
		if requestID != "" {
			proxyReq.Header.Set("X-Request-Id", requestID)
		}

		resp, err := client.Do(proxyReq)
		if err != nil {
			writeJSON(w, http.StatusBadGateway, map[string]string{
				"error": "inference service unreachable",
			})
			return
		}
		defer resp.Body.Close()

		for key, values := range resp.Header {
			for _, value := range values {
				w.Header().Add(key, value)
			}
		}
		if requestID != "" {
			w.Header().Set("X-Request-Id", requestID)
		}
		w.WriteHeader(resp.StatusCode)
		_, _ = io.Copy(w, resp.Body)
	}
}

func validateJWT(r *http.Request, secret string) error {
	authHeader := r.Header.Get("Authorization")
	if authHeader == "" {
		return fmt.Errorf("missing authorization header")
	}
	parts := strings.Fields(authHeader)
	if len(parts) != 2 || strings.ToLower(parts[0]) != "bearer" {
		return fmt.Errorf("invalid authorization header")
	}

	tokenString := parts[1]
	token, err := jwt.Parse(tokenString, func(token *jwt.Token) (any, error) {
		if token.Method != jwt.SigningMethodHS256 {
			return nil, fmt.Errorf("unexpected signing method")
		}
		return []byte(secret), nil
	})
	if err != nil {
		return err
	}
	if !token.Valid {
		return fmt.Errorf("invalid token")
	}
	return nil
}

func withLogging(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		recorder := &statusRecorder{ResponseWriter: w, status: http.StatusOK}

		next.ServeHTTP(recorder, r)

		duration := time.Since(start)
		requestLatency.WithLabelValues(r.URL.Path).Observe(duration.Seconds())
		requestCount.WithLabelValues(r.Method, r.URL.Path, strconv.Itoa(recorder.status)).Inc()

		logJSON("info", "request", map[string]any{
			"method":     r.Method,
			"path":       r.URL.Path,
			"status":     recorder.status,
			"durationMs": duration.Milliseconds(),
			"requestId":  recorder.Header().Get("X-Request-Id"),
			"ip":         clientIP(r),
		})
	})
}

func withCORS(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Request-Id")

		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}

		next.ServeHTTP(w, r)
	})
}

type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (s *statusRecorder) WriteHeader(status int) {
	s.status = status
	s.ResponseWriter.WriteHeader(status)
}

func clientIP(r *http.Request) string {
	if forwarded := r.Header.Get("X-Forwarded-For"); forwarded != "" {
		parts := strings.Split(forwarded, ",")
		return strings.TrimSpace(parts[0])
	}

	host, _, err := net.SplitHostPort(r.RemoteAddr)
	if err != nil {
		return r.RemoteAddr
	}
	return host
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func logJSON(level string, message string, fields map[string]any) {
	entry := map[string]any{
		"level": level,
		"msg":   message,
		"time":  time.Now().UTC().Format(time.RFC3339),
	}
	for key, value := range fields {
		entry[key] = value
	}

	data, err := json.Marshal(entry)
	if err != nil {
		log.Printf("{\"level\":\"error\",\"msg\":\"log marshal failed\",\"time\":\"%s\"}", time.Now().UTC().Format(time.RFC3339))
		return
	}
	log.Print(string(data))
}

func envOrDefault(key, fallback string) string {
	value := strings.TrimSpace(os.Getenv(key))
	if value == "" {
		return fallback
	}
	return value
}

func envIntOrDefault(key string, fallback int) int {
	value := strings.TrimSpace(os.Getenv(key))
	if value == "" {
		return fallback
	}
	parsed, err := strconv.Atoi(value)
	if err != nil {
		return fallback
	}
	return parsed
}

func newUUID() string {
	buf := make([]byte, 16)
	if _, err := rand.Read(buf); err != nil {
		return fmt.Sprintf("%d", time.Now().UnixNano())
	}
	buf[6] = (buf[6] & 0x0f) | 0x40
	buf[8] = (buf[8] & 0x3f) | 0x80
	return fmt.Sprintf("%x-%x-%x-%x-%x", buf[0:4], buf[4:6], buf[6:8], buf[8:10], buf[10:])
}
