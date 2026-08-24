package swarm_test

import (
	"bytes"
	"context"
	"errors"
	"net/http/httptest"
	"os"
	"path/filepath"
	"reflect"
	"sync"
	"testing"
	"time"

	"github.com/cyberDJs/CyberHIVE/internal/cas"
	"github.com/cyberDJs/CyberHIVE/internal/manifest"
	"github.com/cyberDJs/CyberHIVE/internal/peer"
	"github.com/cyberDJs/CyberHIVE/internal/swarm"
	httptransport "github.com/cyberDJs/CyberHIVE/internal/transport/http"
)

type chunkClientFunc func(context.Context, string, string) ([]byte, error)

func (f chunkClientFunc) Fetch(ctx context.Context, baseURL, hash string) ([]byte, error) {
	return f(ctx, baseURL, hash)
}

func buildArtifact(t *testing.T, root string, data []byte, chunkSize int64) (manifest.Manifest, *cas.Store) {
	t.Helper()
	store, err := cas.New(filepath.Join(root, "source"))
	if err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(root, "model.gguf")
	if err := os.WriteFile(path, data, 0o600); err != nil {
		t.Fatal(err)
	}
	m, err := manifest.BuildFile(path, store, chunkSize)
	if err != nil {
		t.Fatal(err)
	}
	return m, store
}

func allChunksPeer(id, baseURL string, m manifest.Manifest) peer.Peer {
	chunks := make(map[string]struct{}, len(m.Chunks))
	for _, chunk := range m.Chunks {
		chunks[chunk.SHA256] = struct{}{}
	}
	return peer.Peer{ID: id, BaseURL: baseURL, Chunks: chunks}
}

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
	inventory := peer.NewInventory([]peer.Peer{{ID: "peer-a", BaseURL: serverA.URL, Chunks: chunksA}, {ID: "peer-b", BaseURL: serverB.URL, Chunks: chunksB}})
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
		if !destination.HasVerified(chunk.SHA256) {
			t.Fatalf("destination CAS is missing verified chunk %s", chunk.SHA256)
		}
	}
}

func TestResumeSkipsVerifiedLocalChunks(t *testing.T) {
	root := t.TempDir()
	artifact := []byte("abcdefghijkl")
	m, source := buildArtifact(t, root, artifact, 4)
	destination, _ := cas.New(filepath.Join(root, "destination"))
	first, err := source.Read(m.Chunks[0].SHA256)
	if err != nil {
		t.Fatal(err)
	}
	if err := destination.Put(m.Chunks[0].SHA256, first); err != nil {
		t.Fatal(err)
	}
	calls := map[string]int{}
	var mu sync.Mutex
	client := chunkClientFunc(func(_ context.Context, _ string, hash string) ([]byte, error) {
		mu.Lock()
		calls[hash]++
		mu.Unlock()
		return source.Read(hash)
	})
	inventory := peer.NewInventory([]peer.Peer{allChunksPeer("peer-a", "peer-a", m)})
	fetcher, err := swarm.NewFetcher(destination, inventory, client, 1)
	if err != nil {
		t.Fatal(err)
	}
	output := filepath.Join(root, "out.bin")
	if err := fetcher.FetchArtifact(context.Background(), m, output); err != nil {
		t.Fatal(err)
	}
	if calls[m.Chunks[0].SHA256] != 0 {
		t.Fatalf("verified local chunk was fetched %d times", calls[m.Chunks[0].SHA256])
	}
	for _, chunk := range m.Chunks[1:] {
		if calls[chunk.SHA256] != 1 {
			t.Fatalf("missing chunk %s fetched %d times", chunk.SHA256, calls[chunk.SHA256])
		}
	}
}

func TestCorruptLocalChunkIsRefetchedAndRepaired(t *testing.T) {
	root := t.TempDir()
	m, source := buildArtifact(t, root, []byte("abcdefgh"), 4)
	destination, _ := cas.New(filepath.Join(root, "destination"))
	good, _ := source.Read(m.Chunks[0].SHA256)
	if err := destination.Put(m.Chunks[0].SHA256, good); err != nil {
		t.Fatal(err)
	}
	path, _ := destination.Path(m.Chunks[0].SHA256)
	if err := os.WriteFile(path, []byte("xxxx"), 0o640); err != nil {
		t.Fatal(err)
	}
	if destination.HasVerified(m.Chunks[0].SHA256) {
		t.Fatal("corrupt local chunk was considered verified")
	}
	client := chunkClientFunc(func(_ context.Context, _ string, hash string) ([]byte, error) { return source.Read(hash) })
	inventory := peer.NewInventory([]peer.Peer{allChunksPeer("peer-a", "peer-a", m)})
	fetcher, _ := swarm.NewFetcher(destination, inventory, client, 1)
	if err := fetcher.FetchArtifact(context.Background(), m, filepath.Join(root, "out.bin")); err != nil {
		t.Fatal(err)
	}
	if !destination.HasVerified(m.Chunks[0].SHA256) {
		t.Fatal("corrupt local chunk was not repaired")
	}
}

func TestFailedPeerRotatesToNextCandidate(t *testing.T) {
	root := t.TempDir()
	m, source := buildArtifact(t, root, []byte("abcd"), 4)
	destination, _ := cas.New(filepath.Join(root, "destination"))
	inventory := peer.NewInventory([]peer.Peer{allChunksPeer("a", "a", m), allChunksPeer("b", "b", m)})
	client := chunkClientFunc(func(_ context.Context, baseURL, hash string) ([]byte, error) {
		if baseURL == "a" {
			return nil, errors.New("peer disappeared")
		}
		return source.Read(hash)
	})
	fetcher, _ := swarm.NewFetcher(destination, inventory, client, 1)
	if err := fetcher.FetchArtifact(context.Background(), m, filepath.Join(root, "out.bin")); err != nil {
		t.Fatal(err)
	}
}

func TestRetryRoundsRotateStartingPeer(t *testing.T) {
	root := t.TempDir()
	m, source := buildArtifact(t, root, []byte("abcd"), 4)
	destination, _ := cas.New(filepath.Join(root, "destination"))
	inventory := peer.NewInventory([]peer.Peer{allChunksPeer("a", "a", m), allChunksPeer("b", "b", m)})
	var calls []string
	var mu sync.Mutex
	bCalls := 0
	client := chunkClientFunc(func(_ context.Context, baseURL, hash string) ([]byte, error) {
		mu.Lock()
		calls = append(calls, baseURL)
		if baseURL == "b" {
			bCalls++
		}
		currentB := bCalls
		mu.Unlock()
		if baseURL == "a" || currentB == 1 {
			return nil, errors.New("transient")
		}
		return source.Read(hash)
	})
	fetcher, _ := swarm.NewFetcher(destination, inventory, client, 1, swarm.WithPeerRounds(2))
	if err := fetcher.FetchArtifact(context.Background(), m, filepath.Join(root, "out.bin")); err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(calls, []string{"a", "b", "b"}) {
		t.Fatalf("unexpected retry order: %#v", calls)
	}
}

func TestCorruptPeerCannotPoisonCAS(t *testing.T) {
	root := t.TempDir()
	m, _ := buildArtifact(t, root, []byte("abcd"), 4)
	destination, _ := cas.New(filepath.Join(root, "destination"))
	inventory := peer.NewInventory([]peer.Peer{allChunksPeer("evil", "evil", m)})
	client := chunkClientFunc(func(_ context.Context, _ string, _ string) ([]byte, error) { return []byte("wxyz"), nil })
	fetcher, _ := swarm.NewFetcher(destination, inventory, client, 1, swarm.WithPeerRounds(1))
	err := fetcher.FetchArtifact(context.Background(), m, filepath.Join(root, "out.bin"))
	if err == nil {
		t.Fatal("expected corrupt peer failure")
	}
	if destination.Has(m.Chunks[0].SHA256) {
		t.Fatal("corrupt bytes poisoned CAS")
	}
}

func TestOriginFallbackIsLastSource(t *testing.T) {
	root := t.TempDir()
	m, source := buildArtifact(t, root, []byte("abcd"), 4)
	destination, _ := cas.New(filepath.Join(root, "destination"))
	inventory := peer.NewInventory([]peer.Peer{allChunksPeer("peer", "peer", m)})
	var calls []string
	var mu sync.Mutex
	client := chunkClientFunc(func(_ context.Context, baseURL, hash string) ([]byte, error) {
		mu.Lock()
		calls = append(calls, baseURL)
		mu.Unlock()
		if baseURL == "origin" {
			return source.Read(hash)
		}
		return nil, errors.New("offline")
	})
	fetcher, err := swarm.NewFetcher(destination, inventory, client, 1, swarm.WithPeerRounds(2), swarm.WithOrigin("origin"))
	if err != nil {
		t.Fatal(err)
	}
	if err := fetcher.FetchArtifact(context.Background(), m, filepath.Join(root, "out.bin")); err != nil {
		t.Fatal(err)
	}
	if !reflect.DeepEqual(calls, []string{"peer", "peer", "origin"}) {
		t.Fatalf("origin was not last fallback: %#v", calls)
	}
}

func TestCancellationLeavesNoCompleteOutput(t *testing.T) {
	root := t.TempDir()
	m, _ := buildArtifact(t, root, []byte("abcd"), 4)
	destination, _ := cas.New(filepath.Join(root, "destination"))
	inventory := peer.NewInventory([]peer.Peer{allChunksPeer("peer", "peer", m)})
	started := make(chan struct{})
	var once sync.Once
	client := chunkClientFunc(func(ctx context.Context, _ string, _ string) ([]byte, error) {
		once.Do(func() { close(started) })
		<-ctx.Done()
		return nil, ctx.Err()
	})
	fetcher, _ := swarm.NewFetcher(destination, inventory, client, 1)
	ctx, cancel := context.WithCancel(context.Background())
	output := filepath.Join(root, "out.bin")
	done := make(chan error, 1)
	go func() { done <- fetcher.FetchArtifact(ctx, m, output) }()
	<-started
	cancel()
	err := <-done
	if !errors.Is(err, context.Canceled) {
		t.Fatalf("expected context.Canceled, got %v", err)
	}
	if _, statErr := os.Stat(output); !errors.Is(statErr, os.ErrNotExist) {
		t.Fatalf("cancelled fetch left output artifact: %v", statErr)
	}
}
