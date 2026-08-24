package httptransport_test

import (
	"context"
	"crypto/tls"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/cyberDJs/CyberHIVE/internal/cas"
	"github.com/cyberDJs/CyberHIVE/internal/manifest"
	"github.com/cyberDJs/CyberHIVE/internal/peer"
	"github.com/cyberDJs/CyberHIVE/internal/security/authz"
	"github.com/cyberDJs/CyberHIVE/internal/security/identity"
	"github.com/cyberDJs/CyberHIVE/internal/security/ratelimit"
	"github.com/cyberDJs/CyberHIVE/internal/swarm"
	httptransport "github.com/cyberDJs/CyberHIVE/internal/transport/http"
)

func TestSecureSwarmIntegratesWithCurrentFetcher(t *testing.T) {
	root := t.TempDir()
	caDir := filepath.Join(root, "ca")
	caPaths, err := identity.InitCA(caDir, "CyberHIVE test CA")
	if err != nil {
		t.Fatal(err)
	}
	serverPaths, err := identity.IssueNode(caDir, filepath.Join(root, "server-id"), "server-a", []string{"127.0.0.1"})
	if err != nil {
		t.Fatal(err)
	}
	authorizedPaths, err := identity.IssueNode(caDir, filepath.Join(root, "peer-a-id"), "peer-a", nil)
	if err != nil {
		t.Fatal(err)
	}
	unauthorizedPaths, err := identity.IssueNode(caDir, filepath.Join(root, "peer-b-id"), "peer-b", nil)
	if err != nil {
		t.Fatal(err)
	}

	store, err := cas.New(filepath.Join(root, "source-cas"))
	if err != nil {
		t.Fatal(err)
	}
	artifactPath := filepath.Join(root, "model.gguf")
	if err := os.WriteFile(artifactPath, []byte(strings.Repeat("secure-cyberhive-model-", 1024)), 0o600); err != nil {
		t.Fatal(err)
	}
	m, err := manifest.BuildFile(artifactPath, store, 1024)
	if err != nil {
		t.Fatal(err)
	}
	policyConfig, err := authz.ConfigForManifest(m, []string{"peer-a"})
	if err != nil {
		t.Fatal(err)
	}
	policy, err := authz.New(policyConfig)
	if err != nil {
		t.Fatal(err)
	}
	limiter, err := ratelimit.New(ratelimit.Config{MaxConcurrent: 8, RatePerSecond: 1000, Burst: 1000})
	if err != nil {
		t.Fatal(err)
	}

	serverTLS, err := httptransport.LoadServerTLSConfig(caPaths.Certificate)
	if err != nil {
		t.Fatal(err)
	}
	serverCert, err := identity.LoadCertificate(serverPaths.Certificate, serverPaths.PrivateKey)
	if err != nil {
		t.Fatal(err)
	}
	serverTLS.Certificates = []tls.Certificate{serverCert}
	server := httptest.NewUnstartedServer(httptransport.NewSecureServer(store, policy, limiter).Handler())
	server.TLS = serverTLS
	server.StartTLS()
	defer server.Close()

	authorizedTLS, err := httptransport.LoadClientTLSConfig(authorizedPaths.Certificate, authorizedPaths.PrivateKey, caPaths.Certificate)
	if err != nil {
		t.Fatal(err)
	}
	authorizedClient, err := httptransport.NewMTLSClient(3*time.Second, authorizedTLS)
	if err != nil {
		t.Fatal(err)
	}
	inventory := peer.NewInventory([]peer.Peer{{ID: "server-a", BaseURL: server.URL, Chunks: manifestChunks(m)}})
	destination, err := cas.New(filepath.Join(root, "destination"))
	if err != nil {
		t.Fatal(err)
	}
	fetcher, err := swarm.NewFetcher(destination, inventory, authorizedClient, 4)
	if err != nil {
		t.Fatal(err)
	}
	output := filepath.Join(root, "downloaded.gguf")
	if err := fetcher.FetchArtifact(context.Background(), m, output); err != nil {
		t.Fatalf("authorized fetch failed: %v", err)
	}
	got, err := os.ReadFile(output)
	if err != nil {
		t.Fatal(err)
	}
	want, err := os.ReadFile(artifactPath)
	if err != nil {
		t.Fatal(err)
	}
	if string(got) != string(want) {
		t.Fatal("authorized secure fetch did not preserve artifact bytes")
	}

	unauthorizedTLS, err := httptransport.LoadClientTLSConfig(unauthorizedPaths.Certificate, unauthorizedPaths.PrivateKey, caPaths.Certificate)
	if err != nil {
		t.Fatal(err)
	}
	unauthorizedClient, err := httptransport.NewMTLSClient(3*time.Second, unauthorizedTLS)
	if err != nil {
		t.Fatal(err)
	}
	if _, err := unauthorizedClient.FetchArtifactChunk(context.Background(), server.URL, m.SHA256, m.Chunks[0].SHA256); err == nil || !strings.Contains(err.Error(), "403") {
		t.Fatalf("unauthorized peer was not rejected with 403: %v", err)
	}

	roots, err := identity.LoadCertPool(caPaths.Certificate)
	if err != nil {
		t.Fatal(err)
	}
	noCertHTTP := &http.Client{Timeout: 3 * time.Second, Transport: &http.Transport{TLSClientConfig: &tls.Config{RootCAs: roots, MinVersion: tls.VersionTLS13}}}
	if _, err := noCertHTTP.Get(server.URL + "/healthz"); err == nil {
		t.Fatal("unenrolled client completed mTLS handshake")
	}
}

func manifestChunks(m manifest.Manifest) map[string]struct{} {
	out := make(map[string]struct{}, len(m.Chunks))
	for _, chunk := range m.Chunks {
		out[chunk.SHA256] = struct{}{}
	}
	return out
}
