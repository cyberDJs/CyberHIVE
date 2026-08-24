package httptransport

import (
	"context"
	"crypto/tls"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strings"
	"time"
)

type MTLSClient struct {
	httpClient *http.Client
}

func NewMTLSClient(timeout time.Duration, tlsConfig *tls.Config) (*MTLSClient, error) {
	if tlsConfig == nil {
		return nil, errors.New("TLS config is required")
	}
	transport := &http.Transport{TLSClientConfig: tlsConfig.Clone()}
	return &MTLSClient{httpClient: &http.Client{Timeout: timeout, Transport: transport}}, nil
}

func (c *MTLSClient) Fetch(context.Context, string, string) ([]byte, error) {
	return nil, errors.New("secure client requires artifact-scoped fetch")
}

func (c *MTLSClient) FetchArtifactChunk(ctx context.Context, baseURL, artifactHash, hash string) ([]byte, error) {
	base, err := url.Parse(strings.TrimRight(baseURL, "/"))
	if err != nil {
		return nil, fmt.Errorf("parse peer URL: %w", err)
	}
	if base.Scheme != "https" {
		return nil, errors.New("secure peer URL must use https")
	}
	if artifactHash == "" || hash == "" {
		return nil, errors.New("artifact and chunk hashes are required")
	}
	base.Path = strings.TrimRight(base.Path, "/") + "/v1/artifacts/" + artifactHash + "/chunks/" + hash
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, base.String(), nil)
	if err != nil {
		return nil, fmt.Errorf("create chunk request: %w", err)
	}
	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("fetch secure chunk: %w", err)
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
