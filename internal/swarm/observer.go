package swarm

import "time"

type SourceKind string

const (
	SourcePeer   SourceKind = "peer"
	SourceOrigin SourceKind = "origin"
)

type AttemptEvent struct {
	SourceID            string
	Kind                SourceKind
	Bytes               int64
	Duration            time.Duration
	Success             bool
	VerificationFailure bool
}

// Observer receives bounded operational events from a Fetcher. Implementations
// must be safe for concurrent calls and must not depend on chunk/model content.
type Observer interface {
	ArtifactStarted(size int64)
	CacheHit(bytes int64)
	CacheMiss(bytes int64)
	Attempt(event AttemptEvent)
	Retry()
	Fallback()
	ArtifactFinished(duration time.Duration, success bool)
}

func WithObserver(observer Observer) Option {
	return func(f *Fetcher) error {
		f.observer = observer
		return nil
	}
}
