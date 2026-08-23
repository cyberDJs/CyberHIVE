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
