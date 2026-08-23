package peer_test

import (
	"strings"
	"testing"

	"github.com/cyberDJs/CyberHIVE/internal/cas"
	"github.com/cyberDJs/CyberHIVE/internal/peer"
)

func TestDecodePeerConfig(t *testing.T) {
	t.Parallel()
	hash := cas.Hash([]byte("chunk"))
	inventory, err := peer.Decode(strings.NewReader(`{"peers":[{"id":"peer-a","base_url":"http://127.0.0.1:8787","chunks":["` + hash + `"]}]}`))
	if err != nil {
		t.Fatal(err)
	}
	candidates := inventory.Candidates(hash)
	if len(candidates) != 1 || candidates[0].ID != "peer-a" {
		t.Fatalf("unexpected candidates: %#v", candidates)
	}
}

func TestDecodePeerConfigRejectsUnsafeShape(t *testing.T) {
	t.Parallel()
	hash := cas.Hash([]byte("chunk"))
	cases := []string{
		`{"peers":[{"id":"peer-a","base_url":"file:///tmp/x","chunks":["` + hash + `"]}]}`,
		`{"peers":[{"id":"peer-a","base_url":"http://127.0.0.1:1","chunks":["not-a-hash"]}]}`,
		`{"peers":[{"id":"peer-a","base_url":"http://127.0.0.1:1","chunks":[]},{"id":"peer-a","base_url":"http://127.0.0.1:2","chunks":[]}]}`,
	}
	for _, input := range cases {
		if _, err := peer.Decode(strings.NewReader(input)); err == nil {
			t.Fatalf("expected config to fail: %s", input)
		}
	}
}
