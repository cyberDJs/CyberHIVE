package httptransport

import (
	"net/http"
	"strings"
	"time"

	"github.com/cyberDJs/CyberHIVE/internal/cas"
	"github.com/cyberDJs/CyberHIVE/internal/security/authz"
	"github.com/cyberDJs/CyberHIVE/internal/security/identity"
	"github.com/cyberDJs/CyberHIVE/internal/security/ratelimit"
)

type Server struct {
	store *cas.Store
}

func NewServer(store *cas.Store) *Server {
	return &Server{store: store}
}

func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /v1/chunks/{hash}", s.getChunk)
	mux.HandleFunc("GET /healthz", health)
	return mux
}

func (s *Server) getChunk(w http.ResponseWriter, r *http.Request) {
	hash := strings.ToLower(r.PathValue("hash"))
	serveChunk(s.store, hash, w, r)
}

type SecureServer struct {
	store   *cas.Store
	policy  *authz.Policy
	limiter *ratelimit.Limiter
}

func NewSecureServer(store *cas.Store, policy *authz.Policy, limiter *ratelimit.Limiter) *SecureServer {
	return &SecureServer{store: store, policy: policy, limiter: limiter}
}

func (s *SecureServer) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /v1/artifacts/{artifact}/chunks/{hash}", s.getChunk)
	mux.HandleFunc("GET /healthz", health)
	return mux
}

func (s *SecureServer) getChunk(w http.ResponseWriter, r *http.Request) {
	peerID, ok := authenticatedPeerID(r)
	if !ok {
		http.Error(w, "authenticated peer identity required", http.StatusUnauthorized)
		return
	}
	artifactHash := strings.ToLower(r.PathValue("artifact"))
	chunkHash := strings.ToLower(r.PathValue("hash"))
	if !s.policy.Authorize(peerID, artifactHash, chunkHash) {
		http.Error(w, "artifact access denied", http.StatusForbidden)
		return
	}
	if s.limiter != nil {
		release, allowed := s.limiter.Acquire(peerID, time.Now())
		if !allowed {
			w.Header().Set("Retry-After", "1")
			http.Error(w, "peer rate limit exceeded", http.StatusTooManyRequests)
			return
		}
		defer release()
	}
	serveChunk(s.store, chunkHash, w, r)
}

func authenticatedPeerID(r *http.Request) (string, bool) {
	if r.TLS == nil || len(r.TLS.PeerCertificates) == 0 {
		return "", false
	}
	peerID, err := identity.NodeIDFromCertificate(r.TLS.PeerCertificates[0])
	if err != nil {
		return "", false
	}
	return peerID, true
}

func serveChunk(store *cas.Store, hash string, w http.ResponseWriter, r *http.Request) {
	data, err := store.Read(hash)
	if err != nil {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Content-Type", "application/octet-stream")
	w.Header().Set("ETag", `"sha256:`+hash+`"`)
	w.Header().Set("Cache-Control", "private, immutable")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write(data)
}

func health(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	w.WriteHeader(http.StatusOK)
	_, _ = w.Write([]byte("ok\n"))
}
