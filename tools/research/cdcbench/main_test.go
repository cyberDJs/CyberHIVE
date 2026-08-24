package main

import (
	"bytes"
	"crypto/sha256"
	"testing"
)

func TestSplitReassemblesExactly(t *testing.T) {
	data := pseudoBytes(768*1024, 0x1111222233334444)
	algos := []Algo{
		{Name: "fixed", Fixed: 128 * 1024},
		{Name: "gear", Min: 32 * 1024, Max: 128 * 1024, Mask: (1 << 16) - 1},
	}
	for _, algo := range algos {
		chunks := split(data, algo)
		var out []byte
		for _, chunk := range chunks {
			out = append(out, chunk.Data...)
		}
		if !bytes.Equal(out, data) {
			t.Fatalf("%s reassembly mismatch", algo.Name)
		}
		got := sha256.Sum256(out)
		want := sha256.Sum256(data)
		if got != want {
			t.Fatalf("%s sha256 mismatch", algo.Name)
		}
	}
}

func TestCDCResynchronizesAfterInsertion(t *testing.T) {
	base := pseudoBytes(1024*1024, 0x5555666677778888)
	insert := pseudoBytes(8*1024, 0x9999aaaabbbbcccc)
	shifted := make([]byte, 0, len(base)+len(insert))
	shifted = append(shifted, base[:128*1024]...)
	shifted = append(shifted, insert...)
	shifted = append(shifted, base[128*1024:]...)
	arts := []Artifact{{Name: "base", Data: base}, {Name: "shifted", Data: shifted}}
	fixed := runScenario("shift", arts, Algo{Name: "fixed", Fixed: 128 * 1024}, 1)
	cdc := runScenario("shift", arts, Algo{Name: "gear", Min: 32 * 1024, Max: 128 * 1024, Mask: (1 << 16) - 1}, 1)
	if cdc.DedupSavingsPct <= fixed.DedupSavingsPct {
		t.Fatalf("cdc savings=%f must exceed fixed=%f after insertion shift", cdc.DedupSavingsPct, fixed.DedupSavingsPct)
	}
}
