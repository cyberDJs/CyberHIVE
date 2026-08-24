package cas_test

import (
	"bytes"
	"os"
	"path/filepath"
	"testing"

	"github.com/cyberDJs/CyberHIVE/internal/cas"
)

func TestPutRepairsCorruptExistingChunk(t *testing.T) {
	store, err := cas.New(filepath.Join(t.TempDir(), "cas"))
	if err != nil {
		t.Fatal(err)
	}
	good := []byte("verified-chunk")
	hash := cas.Hash(good)
	if err := store.Put(hash, good); err != nil {
		t.Fatal(err)
	}
	path, err := store.Path(hash)
	if err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte("corrupt"), 0o640); err != nil {
		t.Fatal(err)
	}
	if !store.Has(hash) {
		t.Fatal("corrupt object should still physically exist")
	}
	if store.HasVerified(hash) {
		t.Fatal("corrupt object must not be treated as verified")
	}
	if err := store.Put(hash, good); err != nil {
		t.Fatal(err)
	}
	got, err := store.Read(hash)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, good) {
		t.Fatal("repaired chunk differs from expected content")
	}
}
