package authz_test

import (
	"testing"

	"github.com/cyberDJs/CyberHIVE/internal/cas"
	"github.com/cyberDJs/CyberHIVE/internal/security/authz"
)

func TestPolicyAuthorize(t *testing.T) {
	t.Parallel()
	artifact := cas.Hash([]byte("artifact"))
	chunk := cas.Hash([]byte("chunk"))
	policy, err := authz.New(authz.Config{Artifacts: []authz.ArtifactGrant{{SHA256: artifact, Chunks: []string{chunk}, Peers: []string{"peer-a"}}}})
	if err != nil {
		t.Fatal(err)
	}
	if !policy.Authorize("peer-a", artifact, chunk) {
		t.Fatal("authorized peer rejected")
	}
	if policy.Authorize("peer-b", artifact, chunk) {
		t.Fatal("unauthorized peer accepted")
	}
	if policy.Authorize("peer-a", artifact, cas.Hash([]byte("other"))) {
		t.Fatal("unauthorized chunk accepted")
	}
}
