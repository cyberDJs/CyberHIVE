package main

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"

	"github.com/cyberDJs/CyberHIVE/internal/cas"
	"github.com/cyberDJs/CyberHIVE/internal/manifest"
	"github.com/cyberDJs/CyberHIVE/internal/peer"
	httptransport "github.com/cyberDJs/CyberHIVE/internal/transport/http"
)

func TestPackInventoryFetchWorkflow(t *testing.T) {
	root := t.TempDir()
	artifact := bytes.Repeat([]byte("cyberhive-cli-workflow-"), 1024)
	artifactPath := filepath.Join(root, "model.gguf")
	if err := os.WriteFile(artifactPath, artifact, 0o600); err != nil {
		t.Fatal(err)
	}
	sourceCAS := filepath.Join(root, "source-cas")
	var packOut bytes.Buffer
	if err := run(context.Background(), []string{"pack", artifactPath, sourceCAS}, &packOut, &bytes.Buffer{}); err != nil {
		t.Fatal(err)
	}
	var m manifest.Manifest
	if err := json.Unmarshal(packOut.Bytes(), &m); err != nil {
		t.Fatal(err)
	}
	if err := m.Validate(); err != nil {
		t.Fatal(err)
	}
	manifestPath := filepath.Join(root, "model.manifest.json")
	if err := os.WriteFile(manifestPath, packOut.Bytes(), 0o600); err != nil {
		t.Fatal(err)
	}
	store, err := cas.New(sourceCAS)
	if err != nil {
		t.Fatal(err)
	}
	server := httptest.NewServer(httptransport.NewServer(store).Handler())
	defer server.Close()
	var inventoryOut bytes.Buffer
	if err := run(context.Background(), []string{"inventory", "peer-a", server.URL, manifestPath}, &inventoryOut, &bytes.Buffer{}); err != nil {
		t.Fatal(err)
	}
	peersPath := filepath.Join(root, "peers.json")
	if err := os.WriteFile(peersPath, inventoryOut.Bytes(), 0o600); err != nil {
		t.Fatal(err)
	}
	output := filepath.Join(root, "downloaded", "model.gguf")
	var fetchOut bytes.Buffer
	if err := run(context.Background(), []string{"fetch", manifestPath, peersPath, filepath.Join(root, "destination-cas"), output}, &fetchOut, &bytes.Buffer{}); err != nil {
		t.Fatal(err)
	}
	got, err := os.ReadFile(output)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, artifact) {
		t.Fatal("fetched artifact differs from source")
	}
	if !bytes.Contains(fetchOut.Bytes(), []byte(m.SHA256)) {
		t.Fatalf("fetch output does not confirm artifact hash: %s", fetchOut.String())
	}
}

func TestFetchUsesOptionalOriginFallback(t *testing.T) {
	root := t.TempDir()
	artifact := []byte("origin-fallback")
	sourcePath := filepath.Join(root, "source.bin")
	if err := os.WriteFile(sourcePath, artifact, 0o600); err != nil {
		t.Fatal(err)
	}
	originStore, _ := cas.New(filepath.Join(root, "origin-cas"))
	m, err := manifest.BuildFile(sourcePath, originStore, 4)
	if err != nil {
		t.Fatal(err)
	}
	manifestBytes, _ := json.Marshal(m)
	manifestPath := filepath.Join(root, "manifest.json")
	if err := os.WriteFile(manifestPath, manifestBytes, 0o600); err != nil {
		t.Fatal(err)
	}
	origin := httptest.NewServer(httptransport.NewServer(originStore).Handler())
	defer origin.Close()
	cfg, err := peer.ConfigForManifest("dead-peer", "http://127.0.0.1:1", m)
	if err != nil {
		t.Fatal(err)
	}
	peersBytes, _ := json.Marshal(cfg)
	peersPath := filepath.Join(root, "peers.json")
	if err := os.WriteFile(peersPath, peersBytes, 0o600); err != nil {
		t.Fatal(err)
	}
	output := filepath.Join(root, "out.bin")
	if err := run(context.Background(), []string{"fetch", manifestPath, peersPath, filepath.Join(root, "destination"), output, origin.URL}, &bytes.Buffer{}, &bytes.Buffer{}); err != nil {
		t.Fatal(err)
	}
	got, err := os.ReadFile(output)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, artifact) {
		t.Fatal("origin fallback output differs from source")
	}
}
