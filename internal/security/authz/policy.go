package authz

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"

	"github.com/cyberDJs/CyberHIVE/internal/cas"
	"github.com/cyberDJs/CyberHIVE/internal/manifest"
	"github.com/cyberDJs/CyberHIVE/internal/security/identity"
)

type Config struct {
	Artifacts []ArtifactGrant `json:"artifacts"`
}

type ArtifactGrant struct {
	SHA256 string   `json:"sha256"`
	Chunks []string `json:"chunks"`
	Peers  []string `json:"peers"`
}

type artifactRule struct {
	chunks map[string]struct{}
	peers  map[string]struct{}
}

type Policy struct {
	artifacts map[string]artifactRule
}

func ConfigForManifest(m manifest.Manifest, peers []string) (Config, error) {
	if err := m.Validate(); err != nil {
		return Config{}, fmt.Errorf("validate manifest: %w", err)
	}
	if len(peers) == 0 {
		return Config{}, errors.New("at least one authorized peer is required")
	}
	for _, peerID := range peers {
		if err := identity.ValidateNodeID(peerID); err != nil {
			return Config{}, fmt.Errorf("invalid peer id %q: %w", peerID, err)
		}
	}
	chunks := make([]string, 0, len(m.Chunks))
	for _, chunk := range m.Chunks {
		chunks = append(chunks, chunk.SHA256)
	}
	return Config{Artifacts: []ArtifactGrant{{SHA256: m.SHA256, Chunks: chunks, Peers: append([]string(nil), peers...)}}}, nil
}

func LoadFile(path string) (*Policy, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("open authorization policy: %w", err)
	}
	defer file.Close()
	return Decode(file)
}

func Decode(r io.Reader) (*Policy, error) {
	if r == nil {
		return nil, errors.New("authorization policy reader is required")
	}
	decoder := json.NewDecoder(r)
	decoder.DisallowUnknownFields()
	var cfg Config
	if err := decoder.Decode(&cfg); err != nil {
		return nil, fmt.Errorf("decode authorization policy: %w", err)
	}
	var trailing any
	if err := decoder.Decode(&trailing); err != io.EOF {
		if err == nil {
			return nil, errors.New("authorization policy contains trailing JSON value")
		}
		return nil, fmt.Errorf("decode trailing authorization policy data: %w", err)
	}
	return New(cfg)
}

func New(cfg Config) (*Policy, error) {
	if len(cfg.Artifacts) == 0 {
		return nil, errors.New("authorization policy must contain at least one artifact")
	}
	policy := &Policy{artifacts: make(map[string]artifactRule, len(cfg.Artifacts))}
	for _, grant := range cfg.Artifacts {
		if err := cas.ValidateHash(grant.SHA256); err != nil {
			return nil, fmt.Errorf("invalid artifact hash: %w", err)
		}
		if _, exists := policy.artifacts[grant.SHA256]; exists {
			return nil, fmt.Errorf("duplicate artifact grant %s", grant.SHA256)
		}
		if len(grant.Chunks) == 0 || len(grant.Peers) == 0 {
			return nil, fmt.Errorf("artifact %s requires chunks and peers", grant.SHA256)
		}
		rule := artifactRule{chunks: make(map[string]struct{}, len(grant.Chunks)), peers: make(map[string]struct{}, len(grant.Peers))}
		for _, hash := range grant.Chunks {
			if err := cas.ValidateHash(hash); err != nil {
				return nil, fmt.Errorf("artifact %s has invalid chunk hash: %w", grant.SHA256, err)
			}
			rule.chunks[hash] = struct{}{}
		}
		for _, peerID := range grant.Peers {
			if err := identity.ValidateNodeID(peerID); err != nil {
				return nil, fmt.Errorf("artifact %s has invalid peer id: %w", grant.SHA256, err)
			}
			rule.peers[peerID] = struct{}{}
		}
		policy.artifacts[grant.SHA256] = rule
	}
	return policy, nil
}

func (p *Policy) Authorize(peerID, artifactHash, chunkHash string) bool {
	if p == nil {
		return false
	}
	rule, ok := p.artifacts[artifactHash]
	if !ok {
		return false
	}
	if _, ok := rule.peers[peerID]; !ok {
		return false
	}
	_, ok = rule.chunks[chunkHash]
	return ok
}
