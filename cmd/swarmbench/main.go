package main

import (
	"context"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"time"

	"github.com/cyberDJs/CyberHIVE/internal/swarmbench"
)

type report struct {
	SchemaVersion  int                 `json:"schema_version"`
	GeneratedAtUTC string              `json:"generated_at_utc"`
	Mode           string              `json:"mode"`
	Results        []swarmbench.Result `json:"results"`
}

func main() {
	if err := run(context.Background(), os.Args[1:], os.Stdout, os.Stderr); err != nil {
		_, _ = fmt.Fprintf(os.Stderr, "swarmbench: %v\n", err)
		os.Exit(1)
	}
}

func run(ctx context.Context, args []string, stdout, stderr io.Writer) error {
	if stdout == nil || stderr == nil {
		return errors.New("stdout and stderr are required")
	}
	fs := flag.NewFlagSet("swarmbench", flag.ContinueOnError)
	fs.SetOutput(stderr)
	artifactMiB := fs.Int("artifact-mib", 8, "synthetic artifact size in MiB")
	chunkMiB := fs.Int("chunk-mib", 1, "chunk size in MiB")
	concurrency := fs.Int("concurrency", 4, "fetch worker count")
	strategy := fs.String("strategy", "first", "source strategy: first or scheduler")
	scenario := fs.String("scenario", "heterogeneous", "scenario: single, multi, contended-multi, heterogeneous, origin-fallback")
	cachePercent := fs.Int("cache-percent", 0, "percentage of chunks pre-seeded in local CAS")
	runs := fs.Int("runs", 1, "repeat count per benchmark configuration")
	matrix := fs.Bool("matrix", false, "run the issue #6 synthetic matrix")
	output := fs.String("output", "", "optional JSON output path")
	if err := fs.Parse(args); err != nil {
		return err
	}
	if fs.NArg() != 0 {
		return fmt.Errorf("unexpected positional arguments: %v", fs.Args())
	}
	if *runs <= 0 {
		return errors.New("runs must be positive")
	}

	results := make([]swarmbench.Result, 0, *runs)
	mode := "single"
	if *matrix {
		mode = "matrix"
		for _, scenarioName := range []string{"single", "multi", "heterogeneous"} {
			for _, chunk := range []int{1, 4, 16} {
				for _, workers := range []int{1, 4, 8, 16} {
					for _, sourceStrategy := range []string{"first", "scheduler"} {
						for runIndex := 1; runIndex <= *runs; runIndex++ {
							result, err := swarmbench.Run(ctx, swarmbench.Config{
								ArtifactMiB:  *artifactMiB,
								ChunkMiB:     chunk,
								Concurrency:  workers,
								Strategy:     sourceStrategy,
								Scenario:     scenarioName,
								CachePercent: *cachePercent,
							})
							if err != nil {
								return fmt.Errorf("matrix %s chunk=%d concurrency=%d strategy=%s run=%d: %w", scenarioName, chunk, workers, sourceStrategy, runIndex, err)
							}
							result.Run = runIndex
							results = append(results, result)
						}
					}
				}
			}
		}
	} else {
		for runIndex := 1; runIndex <= *runs; runIndex++ {
			result, err := swarmbench.Run(ctx, swarmbench.Config{
				ArtifactMiB:  *artifactMiB,
				ChunkMiB:     *chunkMiB,
				Concurrency:  *concurrency,
				Strategy:     *strategy,
				Scenario:     *scenario,
				CachePercent: *cachePercent,
			})
			if err != nil {
				return err
			}
			result.Run = runIndex
			results = append(results, result)
		}
	}

	payload := report{
		SchemaVersion:  1,
		GeneratedAtUTC: time.Now().UTC().Format(time.RFC3339),
		Mode:           mode,
		Results:        results,
	}
	encoded, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return fmt.Errorf("encode report: %w", err)
	}
	encoded = append(encoded, '\n')
	if *output != "" {
		if err := os.MkdirAll(filepath.Dir(*output), 0o750); err != nil && filepath.Dir(*output) != "." {
			return fmt.Errorf("create output directory: %w", err)
		}
		if err := os.WriteFile(*output, encoded, 0o640); err != nil {
			return fmt.Errorf("write report: %w", err)
		}
	}
	_, err = stdout.Write(encoded)
	return err
}
