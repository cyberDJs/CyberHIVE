package ratelimit_test

import (
	"testing"
	"time"

	"github.com/cyberDJs/CyberHIVE/internal/security/ratelimit"
)

func TestLimiterEnforcesConcurrencyAndRate(t *testing.T) {
	t.Parallel()
	limiter, err := ratelimit.New(ratelimit.Config{MaxConcurrent: 1, RatePerSecond: 1, Burst: 1})
	if err != nil {
		t.Fatal(err)
	}
	now := time.Unix(100, 0)
	release, ok := limiter.Acquire("peer-a", now)
	if !ok {
		t.Fatal("first request rejected")
	}
	if _, ok := limiter.Acquire("peer-a", now); ok {
		t.Fatal("concurrent request accepted")
	}
	release()
	if _, ok := limiter.Acquire("peer-a", now); ok {
		t.Fatal("rate limit did not consume token")
	}
	if release2, ok := limiter.Acquire("peer-a", now.Add(time.Second)); !ok {
		t.Fatal("token did not refill")
	} else {
		release2()
	}
}
