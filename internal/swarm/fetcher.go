package swarm

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"sync"

	"github.com/cyberDJs/CyberHIVE/internal/cas"
	"github.com/cyberDJs/CyberHIVE/internal/manifest"
	"github.com/cyberDJs/CyberHIVE/internal/peer"
)

type ChunkClient interface {
	Fetch(ctx context.Context, baseURL, artifactHash, hash string) ([]byte, error)
}

type Fetcher struct {
	store       *cas.Store
	source      peer.Source
	client      ChunkClient
	concurrency int
}

func NewFetcher(store *cas.Store, source peer.Source, client ChunkClient, concurrency int) (*Fetcher, error) {
	if store == nil || source == nil || client == nil {
		return nil, errors.New("store, peer source and client are required")
	}
	if concurrency <= 0 {
		concurrency = 4
	}
	return &Fetcher{store: store, source: source, client: client, concurrency: concurrency}, nil
}

func (f *Fetcher) FetchArtifact(ctx context.Context, m manifest.Manifest, outputPath string) error {
	if err := m.Validate(); err != nil {
		return fmt.Errorf("validate manifest: %w", err)
	}
	if outputPath == "" {
		return errors.New("output path is required")
	}

	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	jobs := make(chan manifest.Chunk)
	errCh := make(chan error, 1)
	var wg sync.WaitGroup

	worker := func() {
		defer wg.Done()
		for chunk := range jobs {
			if f.store.Has(chunk.SHA256) {
				continue
			}
			if err := f.fetchChunk(ctx, m.SHA256, chunk); err != nil {
				select {
				case errCh <- err:
					cancel()
				default:
				}
				return
			}
		}
	}

	for i := 0; i < f.concurrency; i++ {
		wg.Add(1)
		go worker()
	}

	go func() {
		defer close(jobs)
		for _, chunk := range m.Chunks {
			select {
			case <-ctx.Done():
				return
			case jobs <- chunk:
			}
		}
	}()

	wg.Wait()
	select {
	case err := <-errCh:
		return err
	default:
	}
	if err := ctx.Err(); err != nil && !errors.Is(err, context.Canceled) {
		return err
	}
	return f.assemble(m, outputPath)
}

func (f *Fetcher) fetchChunk(ctx context.Context, artifactHash string, chunk manifest.Chunk) error {
	candidates := f.source.Candidates(chunk.SHA256)
	if len(candidates) == 0 {
		return fmt.Errorf("no peer has chunk %s", chunk.SHA256)
	}
	var errs []error
	for _, candidate := range candidates {
		data, err := f.client.Fetch(ctx, candidate.BaseURL, artifactHash, chunk.SHA256)
		if err != nil {
			errs = append(errs, fmt.Errorf("peer %s: %w", candidate.ID, err))
			continue
		}
		if int64(len(data)) != chunk.Size {
			errs = append(errs, fmt.Errorf("peer %s: chunk size mismatch", candidate.ID))
			continue
		}
		if actual := cas.Hash(data); actual != chunk.SHA256 {
			errs = append(errs, fmt.Errorf("peer %s: chunk hash mismatch", candidate.ID))
			continue
		}
		if err := f.store.Put(chunk.SHA256, data); err != nil {
			return fmt.Errorf("cache chunk from peer %s: %w", candidate.ID, err)
		}
		return nil
	}
	return fmt.Errorf("all peers failed for chunk %s: %w", chunk.SHA256, errors.Join(errs...))
}

func (f *Fetcher) assemble(m manifest.Manifest, outputPath string) error {
	dir := filepath.Dir(outputPath)
	if dir != "." {
		if err := os.MkdirAll(dir, 0o750); err != nil {
			return fmt.Errorf("create output directory: %w", err)
		}
	}
	tmp, err := os.CreateTemp(dir, ".artifact-*")
	if err != nil {
		return fmt.Errorf("create temp artifact: %w", err)
	}
	tmpName := tmp.Name()
	defer os.Remove(tmpName)

	h := sha256.New()
	for _, chunk := range m.Chunks {
		data, err := f.store.Read(chunk.SHA256)
		if err != nil {
			_ = tmp.Close()
			return fmt.Errorf("read chunk %d: %w", chunk.Index, err)
		}
		if _, err := tmp.Write(data); err != nil {
			_ = tmp.Close()
			return fmt.Errorf("assemble chunk %d: %w", chunk.Index, err)
		}
		if _, err := h.Write(data); err != nil {
			_ = tmp.Close()
			return fmt.Errorf("hash assembled artifact: %w", err)
		}
	}
	if err := tmp.Sync(); err != nil {
		_ = tmp.Close()
		return fmt.Errorf("sync assembled artifact: %w", err)
	}
	if err := tmp.Close(); err != nil {
		return fmt.Errorf("close assembled artifact: %w", err)
	}
	actual := hex.EncodeToString(h.Sum(nil))
	if actual != m.SHA256 {
		return fmt.Errorf("artifact hash mismatch: expected %s got %s", m.SHA256, actual)
	}
	if err := os.Rename(tmpName, outputPath); err != nil {
		return fmt.Errorf("commit assembled artifact: %w", err)
	}
	return nil
}
