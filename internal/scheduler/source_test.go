package scheduler_test

import (
	"fmt"
	"testing"
	"time"

	"github.com/cyberDJs/CyberHIVE/internal/cas"
	"github.com/cyberDJs/CyberHIVE/internal/peer"
	"github.com/cyberDJs/CyberHIVE/internal/scheduler"
)

func TestSourcePrefersMeasuredFastLocalPeer(t *testing.T) {
	t.Parallel()
	now := time.Now()
	chunk := cas.Hash([]byte("chunk"))
	inventory := allPeers(chunk, "fast", "slow")
	telemetry := scheduler.StaticTelemetry{
		"fast": {ThroughputBytesPerSecond: 1_000_000_000, RTT: time.Millisecond, UploadUtilization: 0.1, Locality: scheduler.LocalityLAN, ObservedAt: now},
		"slow": {ThroughputBytesPerSecond: 50_000_000, RTT: 40 * time.Millisecond, UploadUtilization: 0.8, Locality: scheduler.LocalityVPN, ObservedAt: now},
	}
	source := scheduler.NewSource(inventory, telemetry, time.Minute)
	ranked := source.Rank(chunk)
	if len(ranked) != 2 || ranked[0].Peer.ID != "fast" {
		t.Fatalf("unexpected ranking: %#v", ranked)
	}
	if ranked[0].Score <= ranked[1].Score {
		t.Fatalf("fast peer score=%f slow=%f", ranked[0].Score, ranked[1].Score)
	}
}

func TestSourceSpreadsEquivalentPeersAcrossChunks(t *testing.T) {
	t.Parallel()
	now := time.Now()
	peers := []string{"peer-a", "peer-b", "peer-c"}
	selected := map[string]int{}
	for i := 0; i < 128; i++ {
		chunk := cas.Hash([]byte(fmt.Sprintf("chunk-%d", i)))
		inventory := allPeers(chunk, peers...)
		telemetry := scheduler.StaticTelemetry{}
		for _, id := range peers {
			telemetry[id] = scheduler.Telemetry{ThroughputBytesPerSecond: 100_000_000, RTT: 3 * time.Millisecond, UploadUtilization: 0.2, Locality: scheduler.LocalityLAN, ObservedAt: now}
		}
		source := scheduler.NewSource(inventory, telemetry, time.Minute)
		selected[source.Candidates(chunk)[0].ID]++
	}
	if len(selected) < 2 {
		t.Fatalf("equivalent peers were not spread: %#v", selected)
	}
}

func TestStaleTelemetryFallsBackDeterministically(t *testing.T) {
	t.Parallel()
	now := time.Now()
	chunk := cas.Hash([]byte("stale"))
	inventory := allPeers(chunk, "peer-a", "peer-b")
	telemetry := scheduler.StaticTelemetry{
		"peer-a": {ThroughputBytesPerSecond: 9e9, ObservedAt: now.Add(-10 * time.Minute)},
		"peer-b": {ThroughputBytesPerSecond: 1, ObservedAt: now.Add(-10 * time.Minute)},
	}
	source := scheduler.NewSource(inventory, telemetry, 30*time.Second)
	first := source.Candidates(chunk)
	second := source.Candidates(chunk)
	if first[0].ID != second[0].ID || first[1].ID != second[1].ID {
		t.Fatalf("fallback ranking is not deterministic: %#v %#v", first, second)
	}
}

func allPeers(chunk string, ids ...string) peer.Inventory {
	peers := make([]peer.Peer, 0, len(ids))
	for _, id := range ids {
		peers = append(peers, peer.Peer{ID: id, BaseURL: "http://" + id, Chunks: map[string]struct{}{chunk: {}}})
	}
	return peer.NewInventory(peers)
}

type mutableSource struct {
	peers []peer.Peer
}

func (m *mutableSource) Candidates(string) []peer.Peer {
	return append([]peer.Peer(nil), m.peers...)
}

func TestRankThreePeersExposesExplainableComponents(t *testing.T) {
	now := time.Now()
	chunk := cas.Hash([]byte("explainable-three-peer-ranking"))
	inventory := allPeers(chunk, "peer-a", "peer-b", "peer-c")
	telemetry := scheduler.StaticTelemetry{
		"peer-a": {ThroughputBytesPerSecond: 800_000_000, RTT: 2 * time.Millisecond, UploadUtilization: 0.1, Locality: scheduler.LocalityLAN, ObservedAt: now},
		"peer-b": {ThroughputBytesPerSecond: 500_000_000, RTT: 5 * time.Millisecond, UploadUtilization: 0.2, Locality: scheduler.LocalityLAN, ObservedAt: now},
		"peer-c": {ThroughputBytesPerSecond: 100_000_000, RTT: 30 * time.Millisecond, UploadUtilization: 0.6, Locality: scheduler.LocalityVPN, ObservedAt: now},
	}
	ranked := scheduler.NewSource(inventory, telemetry, time.Minute).Rank(chunk)
	if len(ranked) != 3 {
		t.Fatalf("expected three ranked candidates, got %d", len(ranked))
	}
	for _, candidate := range ranked {
		if !candidate.Fresh {
			t.Fatalf("candidate %s unexpectedly lacks fresh telemetry", candidate.Peer.ID)
		}
		components := []float64{candidate.Throughput, candidate.Latency, candidate.Load, candidate.Locality, candidate.Affinity, candidate.Score}
		for _, value := range components {
			if value < 0 || value > 1 {
				t.Fatalf("candidate %s has non-normalized explainable component %f", candidate.Peer.ID, value)
			}
		}
	}
}

func TestSourceReflectsPeerDisappearance(t *testing.T) {
	now := time.Now()
	chunk := cas.Hash([]byte("peer-disappearance"))
	upstream := &mutableSource{peers: []peer.Peer{
		{ID: "peer-a", BaseURL: "http://peer-a", Chunks: map[string]struct{}{chunk: {}}},
		{ID: "peer-b", BaseURL: "http://peer-b", Chunks: map[string]struct{}{chunk: {}}},
	}}
	telemetry := scheduler.StaticTelemetry{
		"peer-a": {ThroughputBytesPerSecond: 100_000_000, RTT: time.Millisecond, Locality: scheduler.LocalityLAN, ObservedAt: now},
		"peer-b": {ThroughputBytesPerSecond: 100_000_000, RTT: time.Millisecond, Locality: scheduler.LocalityLAN, ObservedAt: now},
	}
	source := scheduler.NewSource(upstream, telemetry, time.Minute)
	if got := source.Candidates(chunk); len(got) != 2 {
		t.Fatalf("expected two initial peers, got %#v", got)
	}
	upstream.peers = upstream.peers[1:]
	got := source.Candidates(chunk)
	if len(got) != 1 || got[0].ID != "peer-b" {
		t.Fatalf("scheduler retained disappeared peer: %#v", got)
	}
}

func TestEquivalentPeerTieHandlingIsDeterministic(t *testing.T) {
	now := time.Now()
	chunk := cas.Hash([]byte("equivalent-tie"))
	inventory := allPeers(chunk, "peer-a", "peer-b", "peer-c")
	telemetry := scheduler.StaticTelemetry{}
	for _, id := range []string{"peer-a", "peer-b", "peer-c"} {
		telemetry[id] = scheduler.Telemetry{ThroughputBytesPerSecond: 100_000_000, RTT: 3 * time.Millisecond, UploadUtilization: 0.2, Locality: scheduler.LocalityLAN, ObservedAt: now}
	}
	source := scheduler.NewSource(inventory, telemetry, time.Minute)
	first := source.Rank(chunk)
	second := source.Rank(chunk)
	if len(first) != len(second) {
		t.Fatalf("ranking length changed: %d vs %d", len(first), len(second))
	}
	for i := range first {
		if first[i].Peer.ID != second[i].Peer.ID || first[i].Score != second[i].Score {
			t.Fatalf("equivalent-peer ranking is not deterministic: %#v %#v", first, second)
		}
	}
}
