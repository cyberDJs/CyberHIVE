package peer

import "sort"

type Peer struct {
	ID      string
	BaseURL string
	Chunks  map[string]struct{}
}

func (p Peer) Has(hash string) bool {
	_, ok := p.Chunks[hash]
	return ok
}

type Inventory struct {
	peers []Peer
}

func NewInventory(peers []Peer) Inventory {
	cp := append([]Peer(nil), peers...)
	sort.Slice(cp, func(i, j int) bool { return cp[i].ID < cp[j].ID })
	return Inventory{peers: cp}
}

func (i Inventory) Candidates(hash string) []Peer {
	out := make([]Peer, 0, len(i.peers))
	for _, p := range i.peers {
		if p.Has(hash) {
			out = append(out, p)
		}
	}
	return out
}
