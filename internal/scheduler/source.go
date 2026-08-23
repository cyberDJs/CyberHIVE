package scheduler

import (
	"crypto/sha256"
	"encoding/binary"
	"math"
	"sort"
	"time"

	"github.com/cyberDJs/CyberHIVE/internal/peer"
)

type Locality uint8

const (
	LocalityUnknown Locality = iota
	LocalityInternet
	LocalityVPN
	LocalityLAN
	LocalitySameHost
)

type Telemetry struct {
	ThroughputBytesPerSecond float64
	RTT                      time.Duration
	UploadUtilization        float64
	Locality                 Locality
	ObservedAt               time.Time
}

type TelemetryProvider interface {
	Snapshot(peerID string) (Telemetry, bool)
}

type StaticTelemetry map[string]Telemetry

func (s StaticTelemetry) Snapshot(peerID string) (Telemetry, bool) {
	value, ok := s[peerID]
	return value, ok
}

type CandidateScore struct {
	Peer       peer.Peer
	Score      float64
	Fresh      bool
	Throughput float64
	Latency    float64
	Load       float64
	Locality   float64
	Affinity   float64
}

type Source struct {
	upstream   peer.Source
	telemetry  TelemetryProvider
	staleAfter time.Duration
	now        func() time.Time
	spread     float64
}

func NewSource(upstream peer.Source, telemetry TelemetryProvider, staleAfter time.Duration) *Source {
	if staleAfter <= 0 {
		staleAfter = 30 * time.Second
	}
	return &Source{upstream: upstream, telemetry: telemetry, staleAfter: staleAfter, now: time.Now, spread: 0.12}
}

func (s *Source) Candidates(hash string) []peer.Peer {
	ranked := s.Rank(hash)
	out := make([]peer.Peer, len(ranked))
	for i := range ranked {
		out[i] = ranked[i].Peer
	}
	return out
}

func (s *Source) Rank(hash string) []CandidateScore {
	if s == nil || s.upstream == nil {
		return nil
	}
	candidates := s.upstream.Candidates(hash)
	if len(candidates) < 2 {
		out := make([]CandidateScore, len(candidates))
		for i, candidate := range candidates {
			out[i] = CandidateScore{Peer: candidate, Score: 1}
		}
		return out
	}

	now := s.now()
	telemetry := make(map[string]Telemetry, len(candidates))
	fresh := make(map[string]bool, len(candidates))
	maxThroughput := 0.0
	for _, candidate := range candidates {
		value, ok := s.snapshot(candidate.ID)
		if !ok || value.ObservedAt.IsZero() || now.Sub(value.ObservedAt) > s.staleAfter || value.ObservedAt.After(now.Add(time.Second)) {
			continue
		}
		value = sanitize(value)
		telemetry[candidate.ID] = value
		fresh[candidate.ID] = true
		if value.ThroughputBytesPerSecond > maxThroughput {
			maxThroughput = value.ThroughputBytesPerSecond
		}
	}

	ranked := make([]CandidateScore, 0, len(candidates))
	for _, candidate := range candidates {
		affinity := deterministicAffinity(hash, candidate.ID)
		score := CandidateScore{Peer: candidate, Affinity: affinity}
		if fresh[candidate.ID] {
			value := telemetry[candidate.ID]
			score.Fresh = true
			if maxThroughput > 0 {
				score.Throughput = value.ThroughputBytesPerSecond / maxThroughput
			}
			score.Latency = latencyScore(value.RTT)
			score.Load = 1 - value.UploadUtilization
			score.Locality = localityScore(value.Locality)
			base := 0.4*score.Throughput + 0.2*score.Latency + 0.2*score.Load + 0.2*score.Locality
			score.Score = (1-s.spread)*base + s.spread*affinity
		} else {
			// Unknown or stale telemetry remains usable. The hash affinity gives a
			// deterministic spread instead of concentrating every chunk on peer 0.
			score.Score = 0.25 + s.spread*affinity
		}
		ranked = append(ranked, score)
	}

	sort.SliceStable(ranked, func(i, j int) bool {
		if math.Abs(ranked[i].Score-ranked[j].Score) > 1e-12 {
			return ranked[i].Score > ranked[j].Score
		}
		return ranked[i].Peer.ID < ranked[j].Peer.ID
	})
	return ranked
}

func (s *Source) snapshot(peerID string) (Telemetry, bool) {
	if s.telemetry == nil {
		return Telemetry{}, false
	}
	return s.telemetry.Snapshot(peerID)
}

func sanitize(value Telemetry) Telemetry {
	if value.ThroughputBytesPerSecond < 0 || math.IsNaN(value.ThroughputBytesPerSecond) || math.IsInf(value.ThroughputBytesPerSecond, 0) {
		value.ThroughputBytesPerSecond = 0
	}
	if value.RTT < 0 {
		value.RTT = 0
	}
	if value.UploadUtilization < 0 || math.IsNaN(value.UploadUtilization) {
		value.UploadUtilization = 0
	}
	if value.UploadUtilization > 1 || math.IsInf(value.UploadUtilization, 0) {
		value.UploadUtilization = 1
	}
	return value
}

func latencyScore(rtt time.Duration) float64 {
	if rtt <= 0 {
		return 1
	}
	return 1 / (1 + float64(rtt)/(20*float64(time.Millisecond)))
}

func localityScore(locality Locality) float64 {
	switch locality {
	case LocalitySameHost:
		return 1
	case LocalityLAN:
		return 0.85
	case LocalityVPN:
		return 0.55
	case LocalityInternet:
		return 0.2
	default:
		return 0.4
	}
}

func deterministicAffinity(chunkHash, peerID string) float64 {
	sum := sha256.Sum256([]byte(chunkHash + ":" + peerID))
	value := binary.BigEndian.Uint64(sum[:8])
	return float64(value>>11) / float64(uint64(1)<<53)
}
