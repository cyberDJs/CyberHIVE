package manifest_test

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/cyberDJs/CyberHIVE/internal/cas"
	"github.com/cyberDJs/CyberHIVE/internal/manifest"
)

func TestBuildFileProducesValidManifestAndCAS(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	artifactPath := filepath.Join(root, "artifact.bin")
	if err := os.WriteFile(artifactPath, []byte("abcdefghijk"), 0o600); err != nil {
		t.Fatal(err)
	}
	store, err := cas.New(filepath.Join(root, "cas"))
	if err != nil {
		t.Fatal(err)
	}
	m, err := manifest.BuildFile(artifactPath, store, 4)
	if err != nil {
		t.Fatal(err)
	}
	if err := m.Validate(); err != nil {
		t.Fatal(err)
	}
	if len(m.Chunks) != 3 {
		t.Fatalf("expected 3 chunks, got %d", len(m.Chunks))
	}
	for _, chunk := range m.Chunks {
		if !store.Has(chunk.SHA256) {
			t.Fatalf("missing chunk %s", chunk.SHA256)
		}
	}
}
