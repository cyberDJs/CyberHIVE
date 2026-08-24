package swarmbench

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"sort"
	"time"

	"github.com/cyberDJs/CyberHIVE/internal/cas"
	"github.com/cyberDJs/CyberHIVE/internal/manifest"
	"github.com/cyberDJs/CyberHIVE/internal/peer"
	"github.com/cyberDJs/CyberHIVE/internal/scheduler"
	"github.com/cyberDJs/CyberHIVE/internal/swarm"
	"github.com/cyberDJs/CyberHIVE/internal/telemetry"
)

const mebibyte = 1024 * 1024

type Config struct {
	ArtifactMiB  int    `json:"artifact_mib"`
	ChunkMiB     int    `json:"chunk_mib"`
	Concurrency  int    `json:"concurrency"`
	Strategy     string `json:"strategy"`
	Scenario     string `json:"scenario"`
	CachePercent int    `json:"cache_percent"`
}

type PeerAssumption struct {
	PeerID                       string  `json:"peer_id"`
	NominalThroughputBytesSecond float64 `json:"nominal_throughput_bytes_per_second"`
	NominalRTTMS                 float64 `json:"nominal_rtt_ms"`
	MaxConcurrentUploads         int     `json:"max_concurrent_uploads,omitempty"`
	Fails                        bool    `json:"fails"`
	Role                         string  `json:"role"`
}

type SchedulerInput struct {
	PeerID                        string  `json:"peer_id"`
	MeasuredThroughputBytesSecond float64 `json:"measured_throughput_bytes_per_second"`
	MeasuredRTTMS                 float64 `json:"measured_rtt_ms"`
}

type Result struct {
	SchemaVersion      int                `json:"schema_version"`
	Run                int                `json:"run"`
	Environment        string             `json:"environment"`
	GoVersion          string             `json:"go_version"`
	GOOS               string             `json:"goos"`
	GOARCH             string             `json:"goarch"`
	RealHardwareStatus string             `json:"real_rtx_lan_validation"`
	Config             Config             `json:"config"`
	Assumptions        []PeerAssumption   `json:"peer_assumptions"`
	SchedulerInputs    []SchedulerInput   `json:"scheduler_inputs,omitempty"`
	Metrics            telemetry.Snapshot `json:"metrics"`
}

type profile struct {
	id            string
	baseURL       string
	throughput    float64
	rtt           time.Duration
	maxConcurrent int
	fail          bool
	origin        bool
}

type syntheticClient struct {
	data     map[string][]byte
	profiles map[string]profile
	gates    map[string]chan struct{}
}

func (c *syntheticClient) Fetch(ctx context.Context, baseURL, hash string) ([]byte, error) {
	p, ok := c.profiles[baseURL]
	if !ok {
		return nil, fmt.Errorf("unknown synthetic endpoint %q", baseURL)
	}
	data, ok := c.data[hash]
	if !ok {
		return nil, fmt.Errorf("unknown chunk %s", hash)
	}
	if gate := c.gates[baseURL]; gate != nil {
		select {
		case gate <- struct{}{}:
			defer func() { <-gate }()
		case <-ctx.Done():
			return nil, ctx.Err()
		}
	}
	delay := p.rtt
	if p.throughput > 0 {
		delay += time.Duration(float64(len(data)) / p.throughput * float64(time.Second))
	}
	if err := wait(ctx, delay); err != nil {
		return nil, err
	}
	if p.fail {
		return nil, errors.New("synthetic peer failure")
	}
	return append([]byte(nil), data...), nil
}

func (c *syntheticClient) probeRTT(ctx context.Context, baseURL string) (time.Duration, error) {
	p, ok := c.profiles[baseURL]
	if !ok {
		return 0, fmt.Errorf("unknown synthetic endpoint %q", baseURL)
	}
	started := time.Now()
	if err := wait(ctx, p.rtt); err != nil {
		return 0, err
	}
	return time.Since(started), nil
}

func wait(ctx context.Context, delay time.Duration) error {
	if delay <= 0 {
		return nil
	}
	timer := time.NewTimer(delay)
	defer timer.Stop()
	select {
	case <-ctx.Done():
		return ctx.Err()
	case <-timer.C:
		return nil
	}
}

func Run(ctx context.Context, cfg Config) (Result, error) {
	cfg = normalize(cfg)
	if err := validate(cfg); err != nil {
		return Result{}, err
	}
	root, err := os.MkdirTemp("", "cyberhive-swarmbench-*")
	if err != nil {
		return Result{}, fmt.Errorf("create benchmark tempdir: %w", err)
	}
	defer os.RemoveAll(root)

	artifact := deterministicBytes(cfg.ArtifactMiB * mebibyte)
	artifactPath := filepath.Join(root, "artifact.bin")
	if err := os.WriteFile(artifactPath, artifact, 0o600); err != nil {
		return Result{}, fmt.Errorf("write benchmark artifact: %w", err)
	}
	sourceStore, err := cas.New(filepath.Join(root, "source-cas"))
	if err != nil {
		return Result{}, err
	}
	m, err := manifest.BuildFile(artifactPath, sourceStore, int64(cfg.ChunkMiB*mebibyte))
	if err != nil {
		return Result{}, err
	}
	chunkData := make(map[string][]byte, len(m.Chunks))
	for _, chunk := range m.Chunks {
		data, readErr := sourceStore.Read(chunk.SHA256)
		if readErr != nil {
			return Result{}, readErr
		}
		chunkData[chunk.SHA256] = data
	}

	profiles, origin := scenarioProfiles(cfg.Scenario)
	profileMap := make(map[string]profile, len(profiles)+1)
	peers := make([]peer.Peer, 0, len(profiles))
	allHashes := make(map[string]struct{}, len(m.Chunks))
	for _, chunk := range m.Chunks {
		allHashes[chunk.SHA256] = struct{}{}
	}
	for _, p := range profiles {
		profileMap[p.baseURL] = p
		chunks := make(map[string]struct{}, len(allHashes))
		for hash := range allHashes {
			chunks[hash] = struct{}{}
		}
		peers = append(peers, peer.Peer{ID: p.id, BaseURL: p.baseURL, Chunks: chunks})
	}
	if origin != nil {
		profileMap[origin.baseURL] = *origin
	}
	gates := make(map[string]chan struct{}, len(profileMap))
	for baseURL, p := range profileMap {
		if p.maxConcurrent > 0 {
			gates[baseURL] = make(chan struct{}, p.maxConcurrent)
		}
	}
	client := &syntheticClient{data: chunkData, profiles: profileMap, gates: gates}
	inventory := peer.NewInventory(peers)

	measured, outputInputs := measureSchedulerInputs(ctx, client, profiles, m)
	if cfg.Scenario == "contended-multi" {
		// This acceptance scenario isolates scheduler spreading from wall-clock
		// probe jitter by feeding the controlled synthetic profile as stable
		// telemetry. Other scenarios continue to exercise timed probes.
		measured, outputInputs = controlledSchedulerInputs(profiles)
	}
	var source peer.Source = inventory
	if cfg.Strategy == "scheduler" {
		source = scheduler.NewSource(inventory, measured, 30*time.Second)
	}

	destination, err := cas.New(filepath.Join(root, "destination-cas"))
	if err != nil {
		return Result{}, err
	}
	if err := seedCache(destination, sourceStore, m, cfg.CachePercent); err != nil {
		return Result{}, err
	}
	recorder := telemetry.NewRecorder(64)
	options := []swarm.Option{swarm.WithObserver(recorder)}
	if origin != nil {
		options = append(options, swarm.WithOrigin(origin.baseURL))
	}
	fetcher, err := swarm.NewFetcher(destination, source, client, cfg.Concurrency, options...)
	if err != nil {
		return Result{}, err
	}
	outputPath := filepath.Join(root, "output.bin")
	if err := fetcher.FetchArtifact(ctx, m, outputPath); err != nil {
		return Result{}, err
	}
	got, err := os.ReadFile(outputPath)
	if err != nil {
		return Result{}, err
	}
	if !bytes.Equal(got, artifact) {
		return Result{}, errors.New("benchmark output differs from source artifact")
	}

	assumptions := assumptions(profiles, origin)
	return Result{
		SchemaVersion:      1,
		Environment:        "synthetic-local",
		GoVersion:          runtime.Version(),
		GOOS:               runtime.GOOS,
		GOARCH:             runtime.GOARCH,
		RealHardwareStatus: "UNVERIFIED",
		Config:             cfg,
		Assumptions:        assumptions,
		SchedulerInputs:    outputInputs,
		Metrics:            recorder.Snapshot(),
	}, nil
}

func normalize(cfg Config) Config {
	if cfg.ArtifactMiB == 0 {
		cfg.ArtifactMiB = 8
	}
	if cfg.ChunkMiB == 0 {
		cfg.ChunkMiB = 1
	}
	if cfg.Concurrency == 0 {
		cfg.Concurrency = 4
	}
	if cfg.Strategy == "" {
		cfg.Strategy = "first"
	}
	if cfg.Scenario == "" {
		cfg.Scenario = "heterogeneous"
	}
	return cfg
}

func validate(cfg Config) error {
	if cfg.ArtifactMiB <= 0 || cfg.ChunkMiB <= 0 || cfg.Concurrency <= 0 {
		return errors.New("artifact size, chunk size and concurrency must be positive")
	}
	if cfg.CachePercent < 0 || cfg.CachePercent > 100 {
		return errors.New("cache percent must be between 0 and 100")
	}
	if cfg.Strategy != "first" && cfg.Strategy != "scheduler" {
		return fmt.Errorf("unsupported strategy %q", cfg.Strategy)
	}
	switch cfg.Scenario {
	case "single", "multi", "contended-multi", "heterogeneous", "origin-fallback":
		return nil
	default:
		return fmt.Errorf("unsupported scenario %q", cfg.Scenario)
	}
}

func deterministicBytes(size int) []byte {
	out := make([]byte, size)
	for i := range out {
		out[i] = byte((i*31 + 17) % 251)
	}
	return out
}

func scenarioProfiles(name string) ([]profile, *profile) {
	mib := float64(mebibyte)
	switch name {
	case "single":
		return []profile{{id: "peer-a", baseURL: "peer-a", throughput: 1024 * mib, rtt: 500 * time.Microsecond}}, nil
	case "multi":
		return []profile{
			{id: "peer-a", baseURL: "peer-a", throughput: 1024 * mib, rtt: 500 * time.Microsecond},
			{id: "peer-b", baseURL: "peer-b", throughput: 1024 * mib, rtt: 500 * time.Microsecond},
		}, nil
	case "contended-multi":
		return []profile{
			{id: "peer-a", baseURL: "peer-a", throughput: 64 * mib, rtt: 2 * time.Millisecond, maxConcurrent: 1},
			{id: "peer-b", baseURL: "peer-b", throughput: 64 * mib, rtt: 2 * time.Millisecond, maxConcurrent: 1},
		}, nil
	case "origin-fallback":
		origin := &profile{id: "origin", baseURL: "origin", throughput: 512 * mib, rtt: 2 * time.Millisecond, origin: true}
		return []profile{{id: "peer-a", baseURL: "peer-a", throughput: 512 * mib, rtt: time.Millisecond, fail: true}}, origin
	default:
		return []profile{
			{id: "peer-a", baseURL: "peer-a", throughput: 128 * mib, rtt: 8 * time.Millisecond},
			{id: "peer-b", baseURL: "peer-b", throughput: 1024 * mib, rtt: 500 * time.Microsecond},
		}, nil
	}
}

func measureSchedulerInputs(ctx context.Context, client *syntheticClient, profiles []profile, m manifest.Manifest) (scheduler.StaticTelemetry, []SchedulerInput) {
	const probeCount = 5
	measured := make(scheduler.StaticTelemetry, len(profiles))
	out := make([]SchedulerInput, 0, len(profiles))
	if len(m.Chunks) == 0 {
		return measured, out
	}
	sample := m.Chunks[0]
	for _, p := range profiles {
		if p.fail {
			continue
		}
		rtts := make([]time.Duration, 0, probeCount)
		throughputs := make([]float64, 0, probeCount)
		for probe := 0; probe < probeCount; probe++ {
			rtt, err := client.probeRTT(ctx, p.baseURL)
			if err != nil {
				continue
			}
			started := time.Now()
			data, err := client.Fetch(ctx, p.baseURL, sample.SHA256)
			elapsed := time.Since(started)
			if err != nil || len(data) == 0 {
				continue
			}
			transfer := elapsed - rtt
			if transfer <= 0 {
				transfer = elapsed
			}
			rtts = append(rtts, rtt)
			throughputs = append(throughputs, float64(len(data))/transfer.Seconds())
		}
		if len(rtts) == 0 || len(throughputs) == 0 {
			continue
		}
		rtt := medianDuration(rtts)
		bps := medianFloat64(throughputs)
		measured[p.id] = scheduler.Telemetry{
			ThroughputBytesPerSecond: bps,
			RTT:                      rtt,
			UploadUtilization:        0,
			Locality:                 scheduler.LocalityLAN,
			ObservedAt:               time.Now(),
		}
		out = append(out, SchedulerInput{PeerID: p.id, MeasuredThroughputBytesSecond: bps, MeasuredRTTMS: float64(rtt) / float64(time.Millisecond)})
	}
	sort.Slice(out, func(i, j int) bool { return out[i].PeerID < out[j].PeerID })
	return measured, out
}

func medianDuration(values []time.Duration) time.Duration {
	cp := append([]time.Duration(nil), values...)
	sort.Slice(cp, func(i, j int) bool { return cp[i] < cp[j] })
	return cp[len(cp)/2]
}

func medianFloat64(values []float64) float64 {
	cp := append([]float64(nil), values...)
	sort.Float64s(cp)
	return cp[len(cp)/2]
}

func controlledSchedulerInputs(profiles []profile) (scheduler.StaticTelemetry, []SchedulerInput) {
	measured := make(scheduler.StaticTelemetry, len(profiles))
	out := make([]SchedulerInput, 0, len(profiles))
	now := time.Now()
	for _, p := range profiles {
		if p.fail || p.origin {
			continue
		}
		measured[p.id] = scheduler.Telemetry{
			ThroughputBytesPerSecond: p.throughput,
			RTT:                      p.rtt,
			UploadUtilization:        0,
			Locality:                 scheduler.LocalityLAN,
			ObservedAt:               now,
		}
		out = append(out, SchedulerInput{PeerID: p.id, MeasuredThroughputBytesSecond: p.throughput, MeasuredRTTMS: float64(p.rtt) / float64(time.Millisecond)})
	}
	sort.Slice(out, func(i, j int) bool { return out[i].PeerID < out[j].PeerID })
	return measured, out
}

func seedCache(destination, source *cas.Store, m manifest.Manifest, percent int) error {
	count := len(m.Chunks) * percent / 100
	for i := 0; i < count; i++ {
		data, err := source.Read(m.Chunks[i].SHA256)
		if err != nil {
			return err
		}
		if err := destination.Put(m.Chunks[i].SHA256, data); err != nil {
			return err
		}
	}
	return nil
}

func assumptions(peers []profile, origin *profile) []PeerAssumption {
	out := make([]PeerAssumption, 0, len(peers)+1)
	for _, p := range peers {
		out = append(out, PeerAssumption{PeerID: p.id, NominalThroughputBytesSecond: p.throughput, NominalRTTMS: float64(p.rtt) / float64(time.Millisecond), MaxConcurrentUploads: p.maxConcurrent, Fails: p.fail, Role: "peer"})
	}
	if origin != nil {
		out = append(out, PeerAssumption{PeerID: origin.id, NominalThroughputBytesSecond: origin.throughput, NominalRTTMS: float64(origin.rtt) / float64(time.Millisecond), Fails: origin.fail, Role: "origin"})
	}
	sort.Slice(out, func(i, j int) bool { return out[i].PeerID < out[j].PeerID })
	return out
}
