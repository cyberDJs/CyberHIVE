package main

import (
	"bytes"
	"context"
	"encoding/json"
	"testing"
)

func TestRunEmitsStructuredSyntheticReport(t *testing.T) {
	var stdout, stderr bytes.Buffer
	if err := run(context.Background(), []string{"--artifact-mib=1", "--chunk-mib=1", "--concurrency=1", "--strategy=scheduler", "--scenario=heterogeneous"}, &stdout, &stderr); err != nil {
		t.Fatalf("run failed: %v stderr=%s", err, stderr.String())
	}
	var payload map[string]any
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["mode"] != "single" {
		t.Fatalf("unexpected report: %v", payload)
	}
}
