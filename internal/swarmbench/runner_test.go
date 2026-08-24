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

func TestContendedMultiSchedulerUsesMultiplePeersAndFinishesFaster(t *testing.T) {
	ctx := context.Background()
	base := swarmbench.Config{ArtifactMiB: 8, ChunkMiB: 1, Concurrency: 4, Scenario: "contended-multi"}

	firstConfig := base
	firstConfig.Strategy = "first"
	first, err := swarmbench.Run(ctx, firstConfig)
	if err != nil {
		t.Fatal(err)
	}

	schedulerConfig := base
	schedulerConfig.Strategy = "scheduler"
	scheduled, err := swarmbench.Run(ctx, schedulerConfig)
	if err != nil {
		t.Fatal(err)
	}

	usedPeers := 0
	for _, metric := range scheduled.Metrics.Peers {
		if metric.Bytes > 0 {
			usedPeers++
		}
	}
	if usedPeers < 2 {
		t.Fatalf("scheduler did not use multiple useful peers: %+v", scheduled.Metrics.Peers)
	}
	if scheduled.Metrics.ArtifactCompletionMS >= first.Metrics.ArtifactCompletionMS*0.85 {
		t.Fatalf("scheduler did not materially improve contended multi-peer completion: first=%fms scheduler=%fms", first.Metrics.ArtifactCompletionMS, scheduled.Metrics.ArtifactCompletionMS)
	}
}
