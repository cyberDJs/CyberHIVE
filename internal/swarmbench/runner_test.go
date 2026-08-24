package swarmbench_test

import (
	"context"
	"testing"

	"github.com/cyberDJs/CyberHIVE/internal/swarmbench"
)

func TestHeterogeneousSchedulerPrefersMeasuredFastPeer(t *testing.T) {
	cfg := swarmbench.Config{ArtifactMiB: 2, ChunkMiB: 1, Concurrency: 1, Strategy: "scheduler", Scenario: "heterogeneous"}
	result, err := swarmbench.Run(context.Background(), cfg)
	if err != nil {
		t.Fatal(err)
	}
	if !result.Metrics.ArtifactSuccess || result.Metrics.PeerBytes != 2*1024*1024 {
		t.Fatalf("unexpected metrics: %+v", result.Metrics)
	}
	var fastBytes int64
	for _, peer := range result.Metrics.Peers {
		if peer.PeerID == "peer-b" {
			fastBytes = peer.Bytes
		}
	}
	if fastBytes == 0 {
		t.Fatalf("scheduler did not use measured fast peer: %+v", result.Metrics.Peers)
	}
}

func TestOriginFallbackProducesOriginMetrics(t *testing.T) {
	cfg := swarmbench.Config{ArtifactMiB: 1, ChunkMiB: 1, Concurrency: 1, Strategy: "first", Scenario: "origin-fallback"}
	result, err := swarmbench.Run(context.Background(), cfg)
	if err != nil {
		t.Fatal(err)
	}
	if result.Metrics.OriginBytes == 0 || result.Metrics.PeerFailures == 0 || result.Metrics.Fallbacks == 0 {
		t.Fatalf("expected origin fallback metrics, got %+v", result.Metrics)
	}
}
