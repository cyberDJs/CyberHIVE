package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/cyberDJs/CyberHIVE/internal/cas"
	"github.com/cyberDJs/CyberHIVE/internal/manifest"
	"github.com/cyberDJs/CyberHIVE/internal/peer"
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
		encoder := json.NewEncoder(stdout)
		encoder.SetIndent("", "  ")
		return encoder.Encode(cfg)
	case "fetch":
		if len(args) != 5 {
			return errors.New("usage: cyberhive fetch <manifest> <peers.json> <cas-dir> <output>")
		}
		m, err := manifest.LoadFile(args[1])
		if err != nil {
			return err
		}
		inventory, err := peer.LoadFile(args[2])
		if err != nil {
			return err
		}
		store, err := cas.New(args[3])
		if err != nil {
			return err
		}
		fetcher, err := swarm.NewFetcher(store, inventory, httptransport.NewClient(30*time.Second), 4)
		if err != nil {
			return err
		}
		if err := fetcher.FetchArtifact(ctx, m, args[4]); err != nil {
			return err
		}
		_, _ = fmt.Fprintf(stdout, "verified %s -> %s\n", m.SHA256, args[4])
		return nil
	case "serve":
		if len(args) != 3 {
			return errors.New("usage: cyberhive serve <cas-dir> <listen-addr>")
		}
		store, err := cas.New(args[1])
		if err != nil {
			return err
		}
		srv := httptransport.NewServer(store)
		server := &http.Server{Addr: args[2], Handler: srv.Handler(), ReadHeaderTimeout: 5 * time.Second}
		log.Printf("serving CyberHIVE chunks on %s", args[2])
		return server.ListenAndServe()
	case "help", "-h", "--help":
		return usage(stderr)
	default:
		return fmt.Errorf("unknown command %q", args[0])
	}
}

func usage(w io.Writer) error {
	_, _ = fmt.Fprintln(w, "CyberHIVE Model Swarm v0.1")
	_, _ = fmt.Fprintln(w, "  cyberhive pack <artifact> <cas-dir>")
	_, _ = fmt.Fprintln(w, "  cyberhive inventory <peer-id> <base-url> <manifest>")
	_, _ = fmt.Fprintln(w, "  cyberhive serve <cas-dir> <listen-addr>")
	_, _ = fmt.Fprintln(w, "  cyberhive fetch <manifest> <peers.json> <cas-dir> <output>")
	return nil
}
