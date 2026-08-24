package telemetry

import (
	"sort"
	"sync"
	"time"

	"github.com/cyberDJs/CyberHIVE/internal/swarm"
)

const DefaultMaxPeers = 64

const overflowPeerID = "__other__"

type PeerMetrics struct {
	PeerID                   string  `json:"peer_id"`
	Attempts                 uint64  `json:"attempts"`
	Failures                 uint64  `json:"failures"`
	Bytes                    int64   `json:"bytes"`
	AverageLatencyMS         float64 `json:"average_latency_ms"`
	EffectiveThroughputBytes float64 `json:"effective_throughput_bytes_per_second"`
}

type Snapshot struct {
	SchemaVersion        int           `json:"schema_version"`
	ArtifactBytes        int64         `json:"artifact_bytes"`
	PeerBytes            int64         `json:"peer_bytes"`
	OriginBytes          int64         `json:"origin_bytes"`
	CacheHitBytes        int64         `json:"cache_hit_bytes"`
	CacheMissBytes       int64         `json:"cache_miss_bytes"`
	CacheHitRatio        float64       `json:"cache_hit_ratio"`
	PeerFailures         uint64        `json:"peer_failures"`
	VerificationFailures uint64        `json:"verification_failures"`
	Retries              uint64        `json:"retries"`
	Fallbacks            uint64        `json:"fallbacks"`
	ArtifactCompletionMS float64       `json:"artifact_completion_ms"`
	ArtifactSuccess      bool          `json:"artifact_success"`
	ObservedPeerCount    int           `json:"observed_peer_count"`
	OverflowPeerCount    uint64        `json:"overflow_peer_count"`
	Peers                []PeerMetrics `json:"peers"`
}

type peerState struct {
	attempts  uint64
	failures  uint64
	bytes     int64
	latencyNS int64
}

type Recorder struct {
	mu sync.Mutex

	maxPeers int
	peers    map[string]*peerState
	overflow uint64

	artifactBytes        int64
	peerBytes            int64
	originBytes          int64
	cacheHitBytes        int64
	cacheMissBytes       int64
	peerFailures         uint64
	verificationFailures uint64
	retries              uint64
	fallbacks            uint64
	completion           time.Duration
	success              bool
}

func NewRecorder(maxPeers int) *Recorder {
	if maxPeers <= 0 {
		maxPeers = DefaultMaxPeers
	}
	return &Recorder{maxPeers: maxPeers, peers: make(map[string]*peerState, maxPeers+1)}
}

func (r *Recorder) ArtifactStarted(size int64) {
	if r == nil {
		return
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	r.artifactBytes = max64(size, 0)
}

func (r *Recorder) CacheHit(bytes int64) {
	if r == nil {
		return
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	r.cacheHitBytes += max64(bytes, 0)
}

func (r *Recorder) CacheMiss(bytes int64) {
	if r == nil {
		return
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	r.cacheMissBytes += max64(bytes, 0)
}

func (r *Recorder) Attempt(event swarm.AttemptEvent) {
	if r == nil {
		return
	}
	r.mu.Lock()
	defer r.mu.Unlock()

	bytes := max64(event.Bytes, 0)
	switch event.Kind {
	case swarm.SourceOrigin:
		r.originBytes += bytes
	default:
		r.peerBytes += bytes
	}
	if event.VerificationFailure {
		r.verificationFailures++
	}
	if !event.Success && event.Kind == swarm.SourcePeer {
		r.peerFailures++
	}
	if event.Kind != swarm.SourcePeer {
		return
	}

	id := event.SourceID
	if id == "" {
		id = overflowPeerID
	}
	state, ok := r.peers[id]
	if !ok {
		if len(r.peers) >= r.maxPeers {
			id = overflowPeerID
			r.overflow++
			state = r.peers[id]
			if state == nil {
				state = &peerState{}
				r.peers[id] = state
			}
		} else {
			state = &peerState{}
			r.peers[id] = state
		}
	}
	state.attempts++
	if !event.Success {
		state.failures++
	}
	state.bytes += bytes
	if event.Duration > 0 {
		state.latencyNS += event.Duration.Nanoseconds()
	}
}

func (r *Recorder) Retry() {
	if r == nil {
		return
	}
	r.mu.Lock()
	r.retries++
	r.mu.Unlock()
}

func (r *Recorder) Fallback() {
	if r == nil {
		return
	}
	r.mu.Lock()
	r.fallbacks++
	r.mu.Unlock()
}

func (r *Recorder) ArtifactFinished(duration time.Duration, success bool) {
	if r == nil {
		return
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	if duration < 0 {
		duration = 0
	}
	r.completion = duration
	r.success = success
}

func (r *Recorder) Snapshot() Snapshot {
	if r == nil {
		return Snapshot{SchemaVersion: 1}
	}
	r.mu.Lock()
	defer r.mu.Unlock()

	peers := make([]PeerMetrics, 0, len(r.peers))
	for id, state := range r.peers {
		latencySeconds := float64(state.latencyNS) / float64(time.Second)
		avgLatencyMS := 0.0
		if state.attempts > 0 {
			avgLatencyMS = (float64(state.latencyNS) / float64(time.Millisecond)) / float64(state.attempts)
		}
		throughput := 0.0
		if latencySeconds > 0 {
			throughput = float64(state.bytes) / latencySeconds
		}
		peers = append(peers, PeerMetrics{
			PeerID:                   id,
			Attempts:                 state.attempts,
			Failures:                 state.failures,
			Bytes:                    state.bytes,
			AverageLatencyMS:         avgLatencyMS,
			EffectiveThroughputBytes: throughput,
		})
	}
	sort.Slice(peers, func(i, j int) bool { return peers[i].PeerID < peers[j].PeerID })

	totalCache := r.cacheHitBytes + r.cacheMissBytes
	ratio := 0.0
	if totalCache > 0 {
		ratio = float64(r.cacheHitBytes) / float64(totalCache)
	}
	return Snapshot{
		SchemaVersion:        1,
		ArtifactBytes:        r.artifactBytes,
		PeerBytes:            r.peerBytes,
		OriginBytes:          r.originBytes,
		CacheHitBytes:        r.cacheHitBytes,
		CacheMissBytes:       r.cacheMissBytes,
		CacheHitRatio:        ratio,
		PeerFailures:         r.peerFailures,
		VerificationFailures: r.verificationFailures,
		Retries:              r.retries,
		Fallbacks:            r.fallbacks,
		ArtifactCompletionMS: float64(r.completion) / float64(time.Millisecond),
		ArtifactSuccess:      r.success,
		ObservedPeerCount:    len(r.peers),
		OverflowPeerCount:    r.overflow,
		Peers:                peers,
	}
}

func max64(value, floor int64) int64 {
	if value < floor {
		return floor
	}
	return value
}
