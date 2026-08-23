package swarm_test

import (
	"bytes"
	"context"
	"net/http/httptest"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/cyberDJs/CyberHIVE/internal/cas"
	"github.com/cyberDJs/CyberHIVE/internal/manifest"
	"github.com/cyberDJs/CyberHIVE/internal/peer"
	"github.com/cyberDJs/CyberHIVE/internal/swarm"
	httptransport "github.com/cyberDJs/CyberHIVE/internal/transport/http"
)

func TestFetchArtifactFromMultiplePeers(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	sourceStore, err := cas.New(filepath.Join(root, "source"))
	if err != nil {
		t.Fatal(err)
	}
	artifact := bytes.Repeat([]byte("cyberhive-model-swarm-"), 256)
	artifactPath := filepath.Join(root, "model.gguf")
	if err := os.WriteFile(artifactPath, artifact, 0o600); err != nil {
		t.Fatal(err)
	}
	m, err := manifest.BuildFile(artifactPath, sourceStore, 1024)
	if err != nil {
		t.Fatal(err)
	}

	storeA, _ := cas.New(filepath.Join(root, "peer-a"))
	storeB, _ := cas.New(filepath.Join(root, "peer-b"))
	chunksA := map[string]struct{}{}
	chunksB := map[string]struct{}{}
	for _, chunk := range m.Chunks {
		data, err := sourceStore.Read(chunk.SHA256)
		if err != nil {
			t.Fatal(err)
		}
		if chunk.Index%2 == 0 {
			if err := storeA.Put(chunk.SHA256, data); err != nil {
				t.Fatal(err)
			}
			chunksA[chunk.SHA256] = struct{}{}
		} else {
			if err := storeB.Put(chunk.SHA256, data); err != nil {
				t.Fatal(err)
			}
			chunksB[chunk.SHA256] = struct{}{}
		}
	}

	serverA := httptest.NewServer(httptransport.NewServer(storeA).Handler())
	defer serverA.Close()
	serverB := httptest.NewServer(httptransport.NewServer(storeB).Handler())
	defer serverB.Close()

	inventory := peer.NewInventory([]peer.Peer{
		{ID: "peer-a", BaseURL: serverA.URL, Chunks: chunksA},
		{ID: "peer-b", BaseURL: serverB.URL, Chunks: chunksB},
	})
	destination, err := cas.New(filepath.Join(root, "destination"))
	if err != nil {
		t.Fatal(err)
	}
	fetcher, err := swarm.NewFetcher(destination, inventory, httptransport.NewClient(2*time.Second), 4)
	if err != nil {
		t.Fatal(err)
	}
	output := filepath.Join(root, "assembled", "model.gguf")
	if err := fetcher.FetchArtifact(context.Background(), m, output); err != nil {
		t.Fatal(err)
	}
	got, err := os.ReadFile(output)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, artifact) {
		t.Fatal("assembled artifact differs from source")
	}
	for _, chunk := range m.Chunks {
		if !destination.Has(chunk.SHA256) {
			t.Fatalf("destination CAS is missing chunk %s", chunk.SHA256)
		}
	}
}
