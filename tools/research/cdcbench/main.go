package main

import (
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"sort"
	"time"
)

type Algo struct {
	Name  string
	Fixed int
	Min   int
	Max   int
	Mask  uint64
}
type Chunk struct {
	Hash string
	Data []byte
}
type Artifact struct {
	Name string
	Data []byte
}
type ScenarioResult struct {
	Scenario           string  `json:"scenario"`
	Algorithm          string  `json:"algorithm"`
	ArtifactCount      int     `json:"artifact_count"`
	RawBytes           int64   `json:"raw_bytes"`
	UniqueBytes        int64   `json:"unique_bytes"`
	DedupSavingsPct    float64 `json:"dedup_savings_percent"`
	ChunkRefs          int     `json:"chunk_references"`
	UniqueChunks       int     `json:"unique_chunks"`
	IndexBytesEstimate int64   `json:"index_bytes_estimate"`
	PackMedianMS       float64 `json:"pack_median_ms"`
	ReassemblyMedianMS float64 `json:"reassembly_median_ms"`
}
type Report struct {
	SchemaVersion int              `json:"schema_version"`
	GeneratedUTC  string           `json:"generated_at_utc"`
	Corpus        string           `json:"corpus"`
	Runs          int              `json:"runs"`
	Algorithms    []string         `json:"algorithms"`
	Results       []ScenarioResult `json:"results"`
}

var gear [256]uint64

func init() {
	var x uint64 = 0x9e3779b97f4a7c15
	for i := 0; i < 256; i++ {
		x ^= x << 13
		x ^= x >> 7
		x ^= x << 17
		gear[i] = x
	}
}
func pseudoBytes(n int, seed uint64) []byte {
	out := make([]byte, n)
	x := seed
	for i := 0; i < n; i += 8 {
		x ^= x << 13
		x ^= x >> 7
		x ^= x << 17
		var b [8]byte
		binary.LittleEndian.PutUint64(b[:], x)
		copy(out[i:], b[:])
	}
	return out
}
func clone(b []byte) []byte { x := make([]byte, len(b)); copy(x, b); return x }
func makeArtifacts() map[string][]Artifact {
	const MiB = 1024 * 1024
	base := pseudoBytes(8*MiB, 0x1234567812345678)
	identical := clone(base)
	meta := pseudoBytes(64*1024, 0xa1a2a3a4a5a6a7a8)
	shifted := make([]byte, 0, len(base)+len(meta))
	shifted = append(shifted, base[:1*MiB]...)
	shifted = append(shifted, meta...)
	shifted = append(shifted, base[1*MiB:]...)
	replaced := clone(base)
	copy(replaced[3*MiB:4*MiB], pseudoBytes(1*MiB, 0xb1b2b3b4b5b6b7b8))
	appended := append(clone(base), pseudoBytes(1*MiB, 0xc1c2c3c4c5c6c7c8)...)
	sparse := clone(base)
	positions := []int{1*MiB + 17, 2*MiB + 12345, 4*MiB + 777, 6*MiB + 9999, 7*MiB + 42}
	for j, p := range positions {
		copy(sparse[p:p+4096], pseudoBytes(4096, uint64(0xd000+j)))
	}
	return map[string][]Artifact{
		"identical":             {{"base", base}, {"identical", identical}},
		"metadata-shift":        {{"base", base}, {"shifted", shifted}},
		"region-replacement":    {{"base", base}, {"replaced", replaced}},
		"append-only":           {{"base", base}, {"appended", appended}},
		"sparse-edits":          {{"base", base}, {"sparse", sparse}},
		"combined-five-version": {{"base", base}, {"shifted", shifted}, {"replaced", replaced}, {"appended", appended}, {"sparse", sparse}},
	}
}
func split(data []byte, a Algo) []Chunk {
	chunks := []Chunk{}
	if a.Fixed > 0 {
		for i := 0; i < len(data); i += a.Fixed {
			e := i + a.Fixed
			if e > len(data) {
				e = len(data)
			}
			d := data[i:e]
			h := sha256.Sum256(d)
			chunks = append(chunks, Chunk{hex.EncodeToString(h[:]), d})
		}
		return chunks
	}
	start := 0
	var h uint64
	for i, b := range data {
		h = (h << 1) + gear[b]
		size := i - start + 1
		if size >= a.Min && ((h&a.Mask) == 0 || size >= a.Max) {
			d := data[start : i+1]
			s := sha256.Sum256(d)
			chunks = append(chunks, Chunk{hex.EncodeToString(s[:]), d})
			start = i + 1
			h = 0
		}
	}
	if start < len(data) {
		d := data[start:]
		s := sha256.Sum256(d)
		chunks = append(chunks, Chunk{hex.EncodeToString(s[:]), d})
	}
	return chunks
}
func median(xs []float64) float64 {
	ys := append([]float64(nil), xs...)
	sort.Float64s(ys)
	n := len(ys)
	if n%2 == 1 {
		return ys[n/2]
	}
	return (ys[n/2-1] + ys[n/2]) / 2
}
func runScenario(name string, arts []Artifact, a Algo, runs int) ScenarioResult {
	var raw int64
	for _, art := range arts {
		raw += int64(len(art.Data))
	}
	packTimes := []float64{}
	reTimes := []float64{}
	var finalUnique int64
	var finalRefs, finalUniqueChunks int
	for r := 0; r < runs; r++ {
		t0 := time.Now()
		store := map[string][]byte{}
		manifests := make([][]string, 0, len(arts))
		refs := 0
		for _, art := range arts {
			cs := split(art.Data, a)
			m := make([]string, 0, len(cs))
			for _, c := range cs {
				refs++
				m = append(m, c.Hash)
				if _, ok := store[c.Hash]; !ok {
					cp := clone(c.Data)
					store[c.Hash] = cp
				}
			}
			manifests = append(manifests, m)
		}
		packTimes = append(packTimes, float64(time.Since(t0).Microseconds())/1000)
		t1 := time.Now()
		for idx, m := range manifests {
			out := make([]byte, 0, len(arts[idx].Data))
			for _, h := range m {
				out = append(out, store[h]...)
			}
			got := sha256.Sum256(out)
			want := sha256.Sum256(arts[idx].Data)
			if got != want {
				panic("reassembly hash mismatch")
			}
		}
		reTimes = append(reTimes, float64(time.Since(t1).Microseconds())/1000)
		if r == 0 {
			for _, b := range store {
				finalUnique += int64(len(b))
			}
			finalRefs = refs
			finalUniqueChunks = len(store)
		}
	}
	savings := 100 * (1 - float64(finalUnique)/float64(raw))
	return ScenarioResult{name, a.Name, len(arts), raw, finalUnique, savings, finalRefs, finalUniqueChunks, int64(finalRefs * 64), median(packTimes), median(reTimes)}
}
func main() {
	const MiB = 1024 * 1024
	algos := []Algo{{Name: "fixed-4m", Fixed: 4 * MiB}, {Name: "gear-cdc-2m", Min: 1 * MiB, Max: 4 * MiB, Mask: (1 << 21) - 1}, {Name: "gear-cdc-4m", Min: 2 * MiB, Max: 8 * MiB, Mask: (1 << 22) - 1}}
	scenarios := makeArtifacts()
	names := []string{"identical", "metadata-shift", "region-replacement", "append-only", "sparse-edits", "combined-five-version"}
	results := []ScenarioResult{}
	for _, n := range names {
		runs := 1
		if n == "combined-five-version" {
			runs = 3
		}
		for _, a := range algos {
			results = append(results, runScenario(n, scenarios[n], a, runs))
		}
	}
	rep := Report{1, time.Now().UTC().Format(time.RFC3339), "deterministic synthetic checkpoint-like corpus; 8 MiB base; independent mutation seeds; per-scenario dedup measured once, combined timing median over 3 runs", 3, []string{"fixed-4m", "gear-cdc-2m", "gear-cdc-4m"}, results}
	enc, _ := json.MarshalIndent(rep, "", "  ")
	enc = append(enc, '\n')
	if len(os.Args) > 1 {
		if err := os.WriteFile(os.Args[1], enc, 0644); err != nil {
			panic(err)
		}
	}
	fmt.Print(string(enc))
}
