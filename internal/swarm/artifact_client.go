package swarm

import "context"

// ArtifactChunkClient is an optional extension for transports that require the
// artifact identity to authorize a chunk request. Existing ChunkClient
// implementations remain source-compatible.
type ArtifactChunkClient interface {
	FetchArtifactChunk(ctx context.Context, baseURL, artifactHash, hash string) ([]byte, error)
}
