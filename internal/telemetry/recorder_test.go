package telemetry_test

import (
	"testing"
	"time"

	"github.com/cyberDJs/CyberHIVE/internal/swarm"
	"github.com/cyberDJs/CyberHIVE/internal/telemetry"
)

func TestRecorderAggregatesPrivacySafeMetrics(t *testing.T) {
	r := telemetry.NewRecorder(4)
	r.ArtifactStarted(100)
	r.CacheHit(25)
	r.CacheMiss(75)
	r.Attempt(swarm.AttemptEvent{SourceID: "peer-a", Kind: swarm.SourcePeer, Bytes: 50, Duration: 10 * time.Millisecond, Success: true})
	r.Attempt(swarm.AttemptEvent{SourceID: "peer-b", Kind: swarm.SourcePeer, Bytes: 25, Duration: 20 * time.Millisecond, VerificationFailure: true})
	r.Attempt(swarm.AttemptEvent{SourceID: "origin", Kind: swarm.SourceOrigin, Bytes: 25, Duration: 5 * time.Millisecond, Success: true})
	r.Retry()
	r.Fallback()
	r.ArtifactFinished(40*time.Millisecond, true)

	got := r.Snapshot()
	if got.ArtifactBytes != 100 || got.PeerBytes != 75 || got.OriginBytes != 25 {
		t.Fatalf("unexpected byte counters: %+v", got)
	}
	if got.CacheHitRatio != 0.25 {
		t.Fatalf("expected cache hit ratio .25, got %f", got.CacheHitRatio)
	}
	if got.VerificationFailures != 1 || got.PeerFailures != 1 || got.Retries != 1 || got.Fallbacks != 1 {
		t.Fatalf("unexpected failure counters: %+v", got)
	}
	if !got.ArtifactSuccess || len(got.Peers) != 2 {
		t.Fatalf("unexpected snapshot: %+v", got)
	}
}

func TestRecorderBoundsPeerCardinality(t *testing.T) {
	r := telemetry.NewRecorder(2)
	for _, id := range []string{"a", "b", "c", "d"} {
		r.Attempt(swarm.AttemptEvent{SourceID: id, Kind: swarm.SourcePeer, Bytes: 1, Duration: time.Millisecond, Success: true})
	}
	got := r.Snapshot()
	if got.ObservedPeerCount != 3 {
		t.Fatalf("expected two peers plus overflow bucket, got %d", got.ObservedPeerCount)
	}
	if got.OverflowPeerCount != 2 {
		t.Fatalf("expected two overflow peers, got %d", got.OverflowPeerCount)
	}
	foundOverflow := false
	for _, peer := range got.Peers {
		if peer.PeerID == "__other__" {
			foundOverflow = true
			break
		}
	}
	if !foundOverflow {
		t.Fatalf("expected overflow bucket, got %+v", got.Peers)
	}
}
