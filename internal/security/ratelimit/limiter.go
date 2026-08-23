package ratelimit

import (
	"errors"
	"sync"
	"time"
)

type Config struct {
	MaxConcurrent int
	RatePerSecond float64
	Burst         int
}

type state struct {
	active int
	tokens float64
	last   time.Time
}

type Limiter struct {
	mu     sync.Mutex
	config Config
	peers  map[string]*state
}

func New(config Config) (*Limiter, error) {
	if config.MaxConcurrent <= 0 || config.RatePerSecond <= 0 || config.Burst <= 0 {
		return nil, errors.New("positive concurrency, rate and burst limits are required")
	}
	return &Limiter{config: config, peers: make(map[string]*state)}, nil
}

func (l *Limiter) Acquire(peerID string, now time.Time) (func(), bool) {
	l.mu.Lock()
	st, ok := l.peers[peerID]
	if !ok {
		st = &state{tokens: float64(l.config.Burst), last: now}
		l.peers[peerID] = st
	}
	elapsed := now.Sub(st.last).Seconds()
	if elapsed > 0 {
		st.tokens += elapsed * l.config.RatePerSecond
		if st.tokens > float64(l.config.Burst) {
			st.tokens = float64(l.config.Burst)
		}
		st.last = now
	}
	if st.active >= l.config.MaxConcurrent || st.tokens < 1 {
		l.mu.Unlock()
		return func() {}, false
	}
	st.active++
	st.tokens--
	l.mu.Unlock()

	var once sync.Once
	return func() {
		once.Do(func() {
			l.mu.Lock()
			if current := l.peers[peerID]; current != nil && current.active > 0 {
				current.active--
			}
			l.mu.Unlock()
		})
	}, true
}
