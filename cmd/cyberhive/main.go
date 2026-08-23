package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"log"
	"net/http"
	"os"

	"github.com/cyberDJs/CyberHIVE/internal/cas"
	"github.com/cyberDJs/CyberHIVE/internal/manifest"
	httptransport "github.com/cyberDJs/CyberHIVE/internal/transport/http"
)

func main() {
	if err := run(os.Args[1:]); err != nil {
		log.Printf("error: %v", err)
		os.Exit(1)
	}
}

func run(args []string) error {
	if len(args) == 0 {
		return usage()
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
		return json.NewEncoder(os.Stdout).Encode(m)
	case "serve":
		if len(args) != 3 {
			return errors.New("usage: cyberhive serve <cas-dir> <listen-addr>")
		}
		store, err := cas.New(args[1])
		if err != nil {
			return err
		}
		srv := httptransport.NewServer(store)
		server := &http.Server{Addr: args[2], Handler: srv.Handler(), ReadHeaderTimeout: 5_000_000_000}
		log.Printf("serving CyberHIVE chunks on %s", args[2])
		return server.ListenAndServe()
	case "help", "-h", "--help":
		return usage()
	default:
		return fmt.Errorf("unknown command %q", args[0])
	}
}

func usage() error {
	_, _ = fmt.Fprintln(os.Stderr, "CyberHIVE Model Swarm v0.1")
	_, _ = fmt.Fprintln(os.Stderr, "  cyberhive pack <artifact> <cas-dir>")
	_, _ = fmt.Fprintln(os.Stderr, "  cyberhive serve <cas-dir> <listen-addr>")
	return nil
}
