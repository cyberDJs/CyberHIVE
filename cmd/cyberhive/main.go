package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/cyberDJs/CyberHIVE/internal/cas"
	"github.com/cyberDJs/CyberHIVE/internal/manifest"
	"github.com/cyberDJs/CyberHIVE/internal/peer"
	"github.com/cyberDJs/CyberHIVE/internal/security/authz"
	"github.com/cyberDJs/CyberHIVE/internal/security/identity"
	"github.com/cyberDJs/CyberHIVE/internal/security/ratelimit"
	"github.com/cyberDJs/CyberHIVE/internal/swarm"
	httptransport "github.com/cyberDJs/CyberHIVE/internal/transport/http"
)

func main() {
	if err := run(context.Background(), os.Args[1:], os.Stdout, os.Stderr); err != nil {
		log.Printf("error: %v", err)
		os.Exit(1)
	}
}

func run(ctx context.Context, args []string, stdout, stderr io.Writer) error {
	if stdout == nil || stderr == nil {
		return errors.New("stdout and stderr writers are required")
	}
	if len(args) == 0 {
		return usage(stderr)
	}
	switch args[0] {
	case "pack":
		if len(args) != 3 {
			return errors.New("usage: cyberhive pack <artifact> <cas-dir>")
		}
		store, err := cas.New(args[2])
		if err != nil {
			return err
		}
		m, err := manifest.BuildFile(args[1], store, manifest.DefaultChunkSize)
		if err != nil {
			return err
		}
		return json.NewEncoder(stdout).Encode(m)
	case "inventory":
		if len(args) != 4 {
			return errors.New("usage: cyberhive inventory <peer-id> <base-url> <manifest>")
		}
		m, err := manifest.LoadFile(args[3])
		if err != nil {
			return err
		}
		cfg, err := peer.ConfigForManifest(args[1], args[2], m)
		if err != nil {
			return err
		}
		return encodeIndented(stdout, cfg)
	case "policy":
		if len(args) < 3 {
			return errors.New("usage: cyberhive policy <manifest> <peer-id> [peer-id...]")
		}
		m, err := manifest.LoadFile(args[1])
		if err != nil {
			return err
		}
		cfg, err := authz.ConfigForManifest(m, args[2:])
		if err != nil {
			return err
		}
		return encodeIndented(stdout, cfg)
	case "identity-init-ca":
		if len(args) != 3 {
			return errors.New("usage: cyberhive identity-init-ca <ca-dir> <common-name>")
		}
		paths, err := identity.InitCA(args[1], args[2])
		if err != nil {
			return err
		}
		_, _ = fmt.Fprintf(stdout, "created CA certificate %s and protected private key %s\n", paths.Certificate, paths.PrivateKey)
		return nil
	case "identity-issue-node":
		if len(args) < 4 {
			return errors.New("usage: cyberhive identity-issue-node <ca-dir> <node-dir> <node-id> [dns-or-ip...]")
		}
		paths, err := identity.IssueNode(args[1], args[2], args[3], args[4:])
		if err != nil {
			return err
		}
		_, _ = fmt.Fprintf(stdout, "issued node certificate %s; private key stored at %s\n", paths.Certificate, paths.PrivateKey)
		return nil
	case "fetch":
		if len(args) != 5 && len(args) != 6 {
			return errors.New("usage: cyberhive fetch <manifest> <peers.json> <cas-dir> <output> [origin-url]")
		}
		options := []swarm.Option{}
		if len(args) == 6 {
			options = append(options, swarm.WithOrigin(args[5]))
		}
		return fetchArtifact(ctx, args[1], args[2], args[3], args[4], httptransport.NewClient(30*time.Second), stdout, options...)
	case "secure-fetch":
		if len(args) != 8 {
			return errors.New("usage: cyberhive secure-fetch <manifest> <peers.json> <cas-dir> <output> <client-cert> <client-key> <server-ca>")
		}
		tlsConfig, err := httptransport.LoadClientTLSConfig(args[5], args[6], args[7])
		if err != nil {
			return err
		}
		client, err := httptransport.NewMTLSClient(30*time.Second, tlsConfig)
		if err != nil {
			return err
		}
		return fetchArtifact(ctx, args[1], args[2], args[3], args[4], client, stdout)
	case "serve":
		if len(args) != 3 {
			return errors.New("usage: cyberhive serve <cas-dir> <listen-addr>")
		}
		if !loopbackListenAddr(args[2]) {
			return errors.New("development serve is restricted to loopback; use secure-serve for LAN access")
		}
		store, err := cas.New(args[1])
		if err != nil {
			return err
		}
		srv := httptransport.NewServer(store)
		server := &http.Server{Addr: args[2], Handler: srv.Handler(), ReadHeaderTimeout: 5 * time.Second}
		log.Printf("serving development CyberHIVE chunks on %s", args[2])
		return server.ListenAndServe()
	case "secure-serve":
		if len(args) != 7 {
			return errors.New("usage: cyberhive secure-serve <cas-dir> <listen-addr> <server-cert> <server-key> <client-ca> <policy.json>")
		}
		store, err := cas.New(args[1])
		if err != nil {
			return err
		}
		policy, err := authz.LoadFile(args[6])
		if err != nil {
			return err
		}
		limiter, err := ratelimit.New(ratelimit.Config{MaxConcurrent: 8, RatePerSecond: 32, Burst: 64})
		if err != nil {
			return err
		}
		tlsConfig, err := httptransport.LoadServerTLSConfig(args[5])
		if err != nil {
			return err
		}
		srv := httptransport.NewSecureServer(store, policy, limiter)
		server := &http.Server{Addr: args[2], Handler: srv.Handler(), ReadHeaderTimeout: 5 * time.Second, TLSConfig: tlsConfig}
		log.Printf("serving authenticated CyberHIVE chunks on %s", args[2])
		return server.ListenAndServeTLS(args[3], args[4])
	case "help", "-h", "--help":
		return usage(stderr)
	default:
		return fmt.Errorf("unknown command %q", args[0])
	}
}

func fetchArtifact(ctx context.Context, manifestPath, peersPath, casDir, output string, client swarm.ChunkClient, stdout io.Writer, options ...swarm.Option) error {
	m, err := manifest.LoadFile(manifestPath)
	if err != nil {
		return err
	}
	inventory, err := peer.LoadFile(peersPath)
	if err != nil {
		return err
	}
	store, err := cas.New(casDir)
	if err != nil {
		return err
	}
	fetcher, err := swarm.NewFetcher(store, inventory, client, 4, options...)
	if err != nil {
		return err
	}
	if err := fetcher.FetchArtifact(ctx, m, output); err != nil {
		return err
	}
	_, _ = fmt.Fprintf(stdout, "verified %s -> %s\n", m.SHA256, output)
	return nil
}

func encodeIndented(w io.Writer, value any) error {
	encoder := json.NewEncoder(w)
	encoder.SetIndent("", "  ")
	return encoder.Encode(value)
}

func loopbackListenAddr(addr string) bool {
	host, _, err := net.SplitHostPort(addr)
	if err != nil {
		return false
	}
	if strings.EqualFold(host, "localhost") {
		return true
	}
	ip := net.ParseIP(host)
	return ip != nil && ip.IsLoopback()
}

func usage(w io.Writer) error {
	_, _ = fmt.Fprintln(w, "CyberHIVE Model Swarm v0.1")
	_, _ = fmt.Fprintln(w, "  cyberhive pack <artifact> <cas-dir>")
	_, _ = fmt.Fprintln(w, "  cyberhive inventory <peer-id> <base-url> <manifest>")
	_, _ = fmt.Fprintln(w, "  cyberhive policy <manifest> <peer-id> [peer-id...]")
	_, _ = fmt.Fprintln(w, "  cyberhive identity-init-ca <ca-dir> <common-name>")
	_, _ = fmt.Fprintln(w, "  cyberhive identity-issue-node <ca-dir> <node-dir> <node-id> [dns-or-ip...]")
	_, _ = fmt.Fprintln(w, "  cyberhive serve <cas-dir> <listen-addr>                 # loopback development only")
	_, _ = fmt.Fprintln(w, "  cyberhive fetch <manifest> <peers.json> <cas-dir> <output> [origin-url]")
	_, _ = fmt.Fprintln(w, "  cyberhive secure-serve <cas-dir> <listen-addr> <server-cert> <server-key> <client-ca> <policy.json>")
	_, _ = fmt.Fprintln(w, "  cyberhive secure-fetch <manifest> <peers.json> <cas-dir> <output> <client-cert> <client-key> <server-ca>")
	return nil
}
