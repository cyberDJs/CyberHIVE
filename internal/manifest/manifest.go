package manifest

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"

	"github.com/cyberDJs/CyberHIVE/internal/cas"
)

const DefaultChunkSize int64 = 4 * 1024 * 1024

type Chunk struct {
	Index  int    `json:"index"`
	Offset int64  `json:"offset"`
	Size   int64  `json:"size"`
	SHA256 string `json:"sha256"`
}

type Manifest struct {
	SchemaVersion int     `json:"schema_version"`
	Name          string  `json:"name"`
	Size          int64   `json:"size"`
	ChunkSize     int64   `json:"chunk_size"`
	SHA256        string  `json:"sha256"`
	Chunks        []Chunk `json:"chunks"`
}

func BuildFile(path string, store *cas.Store, chunkSize int64) (Manifest, error) {
	if store == nil {
		return Manifest{}, errors.New("CAS store is required")
	}
	if chunkSize <= 0 {
		return Manifest{}, errors.New("chunk size must be positive")
	}
	file, err := os.Open(path)
	if err != nil {
		return Manifest{}, fmt.Errorf("open artifact: %w", err)
	}
	defer file.Close()

	st, err := file.Stat()
	if err != nil {
		return Manifest{}, fmt.Errorf("stat artifact: %w", err)
	}

	artifactHash := sha256.New()
	chunks := make([]Chunk, 0, (st.Size()+chunkSize-1)/chunkSize)
	var offset int64
	index := 0

	for {
		buf := make([]byte, chunkSize)
		n, readErr := io.ReadFull(file, buf)
		if readErr != nil && readErr != io.EOF && readErr != io.ErrUnexpectedEOF {
			return Manifest{}, fmt.Errorf("read artifact: %w", readErr)
		}
		if n == 0 {
			break
		}
		buf = buf[:n]
		if _, err := artifactHash.Write(buf); err != nil {
			return Manifest{}, fmt.Errorf("hash artifact: %w", err)
		}
		hash := cas.Hash(buf)
		if err := store.Put(hash, buf); err != nil {
			return Manifest{}, fmt.Errorf("store chunk %d: %w", index, err)
		}
		chunks = append(chunks, Chunk{Index: index, Offset: offset, Size: int64(n), SHA256: hash})
		offset += int64(n)
		index++
		if readErr == io.ErrUnexpectedEOF {
			break
		}
	}

	return Manifest{
		SchemaVersion: 1,
		Name:          filepath.Base(path),
		Size:          st.Size(),
		ChunkSize:     chunkSize,
		SHA256:        hex.EncodeToString(artifactHash.Sum(nil)),
		Chunks:        chunks,
	}, nil
}

func LoadFile(path string) (Manifest, error) {
	file, err := os.Open(path)
	if err != nil {
		return Manifest{}, fmt.Errorf("open manifest: %w", err)
	}
	defer file.Close()
	return Decode(file)
}

func Decode(r io.Reader) (Manifest, error) {
	if r == nil {
		return Manifest{}, errors.New("manifest reader is required")
	}
	decoder := json.NewDecoder(r)
	decoder.DisallowUnknownFields()
	var m Manifest
	if err := decoder.Decode(&m); err != nil {
		return Manifest{}, fmt.Errorf("decode manifest: %w", err)
	}
	var trailing any
	if err := decoder.Decode(&trailing); err != io.EOF {
		if err == nil {
			return Manifest{}, errors.New("manifest contains trailing JSON value")
		}
		return Manifest{}, fmt.Errorf("decode trailing manifest data: %w", err)
	}
	if err := m.Validate(); err != nil {
		return Manifest{}, err
	}
	return m, nil
}

func (m Manifest) Validate() error {
	if m.SchemaVersion != 1 {
		return fmt.Errorf("unsupported manifest schema version %d", m.SchemaVersion)
	}
	if m.Name == "" || m.Size < 0 || m.ChunkSize <= 0 {
		return errors.New("invalid manifest metadata")
	}
	if err := cas.ValidateHash(m.SHA256); err != nil {
		return fmt.Errorf("invalid artifact sha256: %w", err)
	}
	var total int64
	for i, chunk := range m.Chunks {
		if chunk.Index != i || chunk.Offset != total || chunk.Size <= 0 || chunk.Size > m.ChunkSize {
			return fmt.Errorf("invalid chunk metadata at index %d", i)
		}
		if err := cas.ValidateHash(chunk.SHA256); err != nil {
			return fmt.Errorf("invalid chunk sha256 at index %d: %w", i, err)
		}
		total += chunk.Size
	}
	if total != m.Size {
		return fmt.Errorf("manifest size mismatch: chunks=%d artifact=%d", total, m.Size)
	}
	if m.Size > 0 && len(m.Chunks) == 0 {
		return errors.New("non-empty artifact has no chunks")
	}
	return nil
}

func (m Manifest) JSON() ([]byte, error) {
	return json.MarshalIndent(m, "", "  ")
}
