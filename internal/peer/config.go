package peer

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/url"
	"os"

	"github.com/cyberDJs/CyberHIVE/internal/cas"
	"github.com/cyberDJs/CyberHIVE/internal/manifest"
)

type Config struct {
	Peers []ConfigPeer `json:"peers"`
}

type ConfigPeer struct {
	ID      string   `json:"id"`
	BaseURL string   `json:"base_url"`
	Chunks  []string `json:"chunks"`
}

func ConfigForManifest(id, baseURL string, m manifest.Manifest) (Config, error) {
	if err := m.Validate(); err != nil {
		return Config{}, fmt.Errorf("validate manifest: %w", err)
	}
	chunks := make([]string, 0, len(m.Chunks))
	for _, chunk := range m.Chunks {
		chunks = append(chunks, chunk.SHA256)
	}
	cfg := Config{Peers: []ConfigPeer{{ID: id, BaseURL: baseURL, Chunks: chunks}}}
	if _, err := cfg.Inventory(); err != nil {
		return Config{}, err
	}
	return cfg, nil
}

func LoadFile(path string) (Inventory, error) {
	file, err := os.Open(path)
	if err != nil {
		return Inventory{}, fmt.Errorf("open peer config: %w", err)
	}
	defer file.Close()
	return Decode(file)
}

func Decode(r io.Reader) (Inventory, error) {
	if r == nil {
		return Inventory{}, errors.New("peer config reader is required")
	}
	decoder := json.NewDecoder(r)
	decoder.DisallowUnknownFields()
	var cfg Config
	if err := decoder.Decode(&cfg); err != nil {
		return Inventory{}, fmt.Errorf("decode peer config: %w", err)
	}
	var trailing any
	if err := decoder.Decode(&trailing); err != io.EOF {
		if err == nil {
			return Inventory{}, errors.New("peer config contains trailing JSON value")
		}
		return Inventory{}, fmt.Errorf("decode trailing peer config data: %w", err)
	}
	return cfg.Inventory()
}

func (c Config) Inventory() (Inventory, error) {
	if len(c.Peers) == 0 {
		return Inventory{}, errors.New("peer config must contain at least one peer")
	}
	seenIDs := make(map[string]struct{}, len(c.Peers))
	peers := make([]Peer, 0, len(c.Peers))
	for index, configured := range c.Peers {
		if configured.ID == "" {
			return Inventory{}, fmt.Errorf("peer %d has empty id", index)
		}
		if _, duplicate := seenIDs[configured.ID]; duplicate {
			return Inventory{}, fmt.Errorf("duplicate peer id %q", configured.ID)
		}
		seenIDs[configured.ID] = struct{}{}
		u, err := url.Parse(configured.BaseURL)
		if err != nil || u.Host == "" || (u.Scheme != "http" && u.Scheme != "https") {
			return Inventory{}, fmt.Errorf("peer %s has invalid base_url", configured.ID)
		}
		chunks := make(map[string]struct{}, len(configured.Chunks))
		for _, hash := range configured.Chunks {
			if err := cas.ValidateHash(hash); err != nil {
				return Inventory{}, fmt.Errorf("peer %s has invalid chunk hash: %w", configured.ID, err)
			}
			chunks[hash] = struct{}{}
		}
		peers = append(peers, Peer{ID: configured.ID, BaseURL: configured.BaseURL, Chunks: chunks})
	}
	return NewInventory(peers), nil
}
