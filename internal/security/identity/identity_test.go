package identity_test

import (
	"crypto/x509"
	"encoding/pem"
	"os"
	"path/filepath"
	"testing"

	"github.com/cyberDJs/CyberHIVE/internal/security/identity"
)

func TestIssueNodeCreatesStableIdentityAndPrivateKeyPermissions(t *testing.T) {
	t.Parallel()
	root := t.TempDir()
	caDir := filepath.Join(root, "ca")
	if _, err := identity.InitCA(caDir, "test CA"); err != nil {
		t.Fatal(err)
	}
	nodeDir := filepath.Join(root, "node")
	paths, err := identity.IssueNode(caDir, nodeDir, "peer-a", []string{"127.0.0.1", "localhost"})
	if err != nil {
		t.Fatal(err)
	}
	info, err := os.Stat(paths.PrivateKey)
	if err != nil {
		t.Fatal(err)
	}
	if info.Mode().Perm() != 0o600 {
		t.Fatalf("private key mode=%o want 600", info.Mode().Perm())
	}
	data, err := os.ReadFile(paths.Certificate)
	if err != nil {
		t.Fatal(err)
	}
	block, _ := pem.Decode(data)
	if block == nil {
		t.Fatal("certificate PEM missing")
	}
	cert, err := x509.ParseCertificate(block.Bytes)
	if err != nil {
		t.Fatal(err)
	}
	got, err := identity.NodeIDFromCertificate(cert)
	if err != nil {
		t.Fatal(err)
	}
	if got != "peer-a" {
		t.Fatalf("node id=%q want peer-a", got)
	}
	if _, err := identity.IssueNode(caDir, nodeDir, "peer-a", nil); err == nil {
		t.Fatal("expected overwrite refusal")
	}
}
