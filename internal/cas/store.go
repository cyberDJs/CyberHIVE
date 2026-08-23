package cas

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
)

var ErrInvalidHash = errors.New("invalid sha256 hash")

type Store struct {
	root string
}

func New(root string) (*Store, error) {
	if root == "" {
		return nil, errors.New("CAS root is required")
	}
	if err := os.MkdirAll(root, 0o750); err != nil {
		return nil, fmt.Errorf("create CAS root: %w", err)
	}
	return &Store{root: root}, nil
}

func Hash(data []byte) string {
	sum := sha256.Sum256(data)
	return hex.EncodeToString(sum[:])
}

func ValidateHash(hash string) error {
	if len(hash) != 64 {
		return ErrInvalidHash
	}
	decoded, err := hex.DecodeString(hash)
	if err != nil || len(decoded) != sha256.Size {
		return ErrInvalidHash
	}
	return nil
}

func (s *Store) Path(hash string) (string, error) {
	if err := ValidateHash(hash); err != nil {
		return "", err
	}
	return filepath.Join(s.root, "sha256", hash[:2], hash[2:]), nil
}

func (s *Store) Has(hash string) bool {
	path, err := s.Path(hash)
	if err != nil {
		return false
	}
	st, err := os.Stat(path)
	return err == nil && st.Mode().IsRegular()
}

func (s *Store) Put(hash string, data []byte) error {
	if err := ValidateHash(hash); err != nil {
		return err
	}
	if actual := Hash(data); actual != hash {
		return fmt.Errorf("chunk hash mismatch: expected %s got %s", hash, actual)
	}
	path, err := s.Path(hash)
	if err != nil {
		return err
	}
	if s.Has(hash) {
		return nil
	}
	if err := os.MkdirAll(filepath.Dir(path), 0o750); err != nil {
		return fmt.Errorf("create CAS shard: %w", err)
	}
	tmp, err := os.CreateTemp(filepath.Dir(path), ".chunk-*")
	if err != nil {
		return fmt.Errorf("create temp chunk: %w", err)
	}
	tmpName := tmp.Name()
	defer os.Remove(tmpName)
	if err := tmp.Chmod(0o640); err != nil {
		_ = tmp.Close()
		return fmt.Errorf("chmod temp chunk: %w", err)
	}
	if _, err := tmp.Write(data); err != nil {
		_ = tmp.Close()
		return fmt.Errorf("write temp chunk: %w", err)
	}
	if err := tmp.Sync(); err != nil {
		_ = tmp.Close()
		return fmt.Errorf("sync temp chunk: %w", err)
	}
	if err := tmp.Close(); err != nil {
		return fmt.Errorf("close temp chunk: %w", err)
	}
	if err := os.Rename(tmpName, path); err != nil {
		if s.Has(hash) {
			return nil
		}
		return fmt.Errorf("commit chunk: %w", err)
	}
	return nil
}

func (s *Store) Read(hash string) ([]byte, error) {
	path, err := s.Path(hash)
	if err != nil {
		return nil, err
	}
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read chunk: %w", err)
	}
	if actual := Hash(data); actual != hash {
		return nil, fmt.Errorf("stored chunk failed verification: expected %s got %s", hash, actual)
	}
	return data, nil
}

func (s *Store) CopyTo(hash string, w io.Writer) error {
	data, err := s.Read(hash)
	if err != nil {
		return err
	}
	if _, err := w.Write(data); err != nil {
		return fmt.Errorf("write chunk: %w", err)
	}
	return nil
}
