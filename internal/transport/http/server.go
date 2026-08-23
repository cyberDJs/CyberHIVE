package httptransport

import (
	"net/http"
	"strings"

	"github.com/cyberDJs/CyberHIVE/internal/cas"
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
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "text/plain; charset=utf-8")
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok\n"))
	})
	return mux
}

func (s *Server) getChunk(w http.ResponseWriter, r *http.Request) {
	hash := strings.ToLower(r.PathValue("hash"))
	data, err := s.store.Read(hash)
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
