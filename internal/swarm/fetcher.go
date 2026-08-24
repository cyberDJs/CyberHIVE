package swarm

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/cyberDJs/CyberHIVE/internal/cas"
	"github.com/cyberDJs/CyberHIVE/internal/manifest"
	"github.com/cyberDJs/CyberHIVE/internal/peer"
)

type ChunkClient interface {
	Fetch(ctx context.Context, baseURL, hash string) ([]byte, error)
}

type Option func(*Fetcher) error

func WithOrigin(baseURL string) Option {
	return func(f *Fetcher) error {
		baseURL = strings.TrimSpace(baseURL)
		if baseURL == "" {
			return errors.New("origin base URL is required")
		}
		f.originBaseURL = baseURL
		return nil
	}
}

func WithPeerRounds(rounds int) Option {
	return func(f *Fetcher) error {
		if rounds <= 0 {
			return errors.New("peer retry rounds must be positive")
		}
		f.peerRounds = rounds
		return nil
	}
}

type Fetcher struct {
	store         *cas.Store
	source        peer.Source
	client        ChunkClient
	concurrency   int
	peerRounds    int
	originBaseURL string
	observer      Observer
}

func NewFetcher(store *cas.Store, source peer.Source, client ChunkClient, concurrency int, options ...Option) (*Fetcher, error) {
	if store == nil || source == nil || client == nil {
		return nil, errors.New("store, peer source and client are required")
	}
	if concurrency <= 0 {
		concurrency = 4
	}
	f := &Fetcher{store: store, source: source, client: client, concurrency: concurrency, peerRounds: 1}
	for _, option := range options {
		if option == nil {
			continue
		}
		if err := option(f); err != nil {
			return nil, err
		}
	}
	return f, nil
}

func (f *Fetcher) FetchArtifact(ctx context.Context, m manifest.Manifest, outputPath string) (resultErr error) {
	if ctx == nil {
		return errors.New("context is required")
	}
	if err := m.Validate(); err != nil {
		return fmt.Errorf("validate manifest: %w", err)
	}
	if outputPath == "" {
		return errors.New("output path is required")
	}

	started := time.Now()
	if f.observer != nil {
		f.observer.ArtifactStarted(m.Size)
		defer func() {
			f.observer.ArtifactFinished(time.Since(started), resultErr == nil)
		}()
	}

	parentCtx := ctx
	workCtx, cancel := context.WithCancel(ctx)
	defer cancel()

	jobs := make(chan manifest.Chunk)
	errCh := make(chan error, 1)
	var wg sync.WaitGroup

	worker := func() {
		defer wg.Done()
		for chunk := range jobs {
			if f.store.HasVerified(chunk.SHA256) {
				if f.observer != nil {
					f.observer.CacheHit(chunk.Size)
				}
				continue
			}
			if f.observer != nil {
				f.observer.CacheMiss(chunk.Size)
			}
			if err := f.fetchChunk(workCtx, m.SHA256, chunk); err != nil {
				if parentCtx.Err() != nil {
					return
				}
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
			case <-workCtx.Done():
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
	if err := parentCtx.Err(); err != nil {
		return err
	}
	return f.assemble(parentCtx, m, outputPath)
}

func (f *Fetcher) fetchChunk(ctx context.Context, artifactHash string, chunk manifest.Chunk) error {
	candidates := f.source.Candidates(chunk.SHA256)
	var errs []error
	attempted := false

	for round := 0; round < f.peerRounds && len(candidates) > 0; round++ {
		if round > 0 && f.observer != nil {
			f.observer.Retry()
		}
		start := round % len(candidates)
		for step := 0; step < len(candidates); step++ {
			if err := ctx.Err(); err != nil {
				return err
			}
			candidate := candidates[(start+step)%len(candidates)]
			if attempted && f.observer != nil {
				f.observer.Fallback()
			}
			attempted = true
			data, err := f.fetchVerified(ctx, artifactHash, candidate.ID, candidate.BaseURL, SourcePeer, chunk)
			if err != nil {
				errs = append(errs, fmt.Errorf("peer %s round %d: %w", candidate.ID, round+1, err))
				continue
			}
			if err := f.store.Put(chunk.SHA256, data); err != nil {
				return fmt.Errorf("cache chunk from peer %s: %w", candidate.ID, err)
			}
			return nil
		}
	}

	if f.originBaseURL != "" {
		if err := ctx.Err(); err != nil {
			return err
		}
		if attempted && f.observer != nil {
			f.observer.Fallback()
		}
		data, err := f.fetchVerified(ctx, artifactHash, "origin", f.originBaseURL, SourceOrigin, chunk)
		if err != nil {
			errs = append(errs, fmt.Errorf("origin: %w", err))
		} else {
			if err := f.store.Put(chunk.SHA256, data); err != nil {
				return fmt.Errorf("cache chunk from origin: %w", err)
			}
			return nil
		}
	}

	if len(candidates) == 0 && f.originBaseURL == "" {
		return fmt.Errorf("no source has chunk %s", chunk.SHA256)
	}
	return fmt.Errorf("all sources failed for chunk %s: %w", chunk.SHA256, errors.Join(errs...))
}

func (f *Fetcher) fetchVerified(ctx context.Context, artifactHash, sourceID, baseURL string, kind SourceKind, chunk manifest.Chunk) ([]byte, error) {
	started := time.Now()
	var data []byte
	var err error
	if artifactClient, ok := f.client.(ArtifactChunkClient); ok {
		data, err = artifactClient.FetchArtifactChunk(ctx, baseURL, artifactHash, chunk.SHA256)
	} else {
		data, err = f.client.Fetch(ctx, baseURL, chunk.SHA256)
	}
	event := AttemptEvent{SourceID: sourceID, Kind: kind, Duration: time.Since(started)}
	if len(data) > 0 {
		event.Bytes = int64(len(data))
	}
	if err != nil {
		f.observeAttempt(event)
		return nil, err
	}
	if int64(len(data)) != chunk.Size {
		event.VerificationFailure = true
		f.observeAttempt(event)
		return nil, fmt.Errorf("chunk size mismatch: expected %d got %d", chunk.Size, len(data))
	}
	if actual := cas.Hash(data); actual != chunk.SHA256 {
		event.VerificationFailure = true
		f.observeAttempt(event)
		return nil, fmt.Errorf("chunk hash mismatch: expected %s got %s", chunk.SHA256, actual)
	}
	event.Success = true
	f.observeAttempt(event)
	return data, nil
}

func (f *Fetcher) observeAttempt(event AttemptEvent) {
	if f.observer != nil {
		f.observer.Attempt(event)
	}
}

func (f *Fetcher) assemble(ctx context.Context, m manifest.Manifest, outputPath string) error {
	if err := ctx.Err(); err != nil {
		return err
	}
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
		if err := ctx.Err(); err != nil {
			_ = tmp.Close()
			return err
		}
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
	if err := ctx.Err(); err != nil {
		return err
	}
	if err := os.Rename(tmpName, outputPath); err != nil {
		return fmt.Errorf("commit assembled artifact: %w", err)
	}
	return nil
}
