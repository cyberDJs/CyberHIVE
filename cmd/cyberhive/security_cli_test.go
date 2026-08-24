package main

import "testing"

func TestLoopbackListenAddr(t *testing.T) {
	for _, addr := range []string{"127.0.0.1:8080", "[::1]:8080", "localhost:8080"} {
		if !loopbackListenAddr(addr) {
			t.Fatalf("expected loopback address %q to be allowed", addr)
		}
	}
	for _, addr := range []string{"0.0.0.0:8080", "[::]:8080", "192.168.1.10:8080", ":8080"} {
		if loopbackListenAddr(addr) {
			t.Fatalf("expected non-loopback address %q to be rejected", addr)
		}
	}
}
