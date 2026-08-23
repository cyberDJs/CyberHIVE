package httptransport

import (
	"context"
	"crypto/tls"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

type Client struct {
	httpClient *http.Client
	secure     bool
}

func NewClient(timeout time.Duration) *Client {
	return &Client{httpClient: &http.Client{Timeout: timeout}}
}

func NewMTLSClient(timeout time.Duration, tlsConfig *tls.Config) (*Client, error) {
	if tlsConfig == nil {
		return nil, fmt.Errorf("TLS config is required")
	}
	transport := &http.Transport{TLSClientConfig: tlsConfig.Clone()}
	return &Client{httpClient: &http.Client{Timeout: timeout, Transport: transport}, secure: true}, nil
}

func (c *Client) Fetch(ctx context.Context, baseURL, artifactHash, hash string) ([]byte, error) {
	base, err := url.Parse(strings.TrimRight(baseURL, "/"))
	if err != nil {
		return nil, fmt.Errorf("parse peer URL: %w", err)
	}
	if c.secure {
		if base.Scheme != "https" {
			return nil, fmt.Errorf("secure peer URL must use https")
		}
		base.Path = strings.TrimRight(base.Path, "/") + "/v1/artifacts/" + artifactHash + "/chunks/" + hash
	} else {
		base.Path = strings.TrimRight(base.Path, "/") + "/v1/chunks/" + hash
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, base.String(), nil)
	if err != nil {
		return nil, fmt.Errorf("create chunk request: %w", err)
	}
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("fetch chunk: %w", err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		_, _ = io.Copy(io.Discard, resp.Body)
		return nil, fmt.Errorf("peer returned %s", resp.Status)
	}
	data, err := io.ReadAll(io.LimitReader(resp.Body, 64*1024*1024))
	if err != nil {
		return nil, fmt.Errorf("read chunk response: %w", err)
	}
	return data, nil
}
