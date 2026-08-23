package identity

import (
	"crypto/ed25519"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"errors"
	"fmt"
	"math/big"
	"net"
	"net/url"
	"os"
	"path/filepath"
	"regexp"
	"time"
)

const trustDomain = "cyberhive.local"

var nodeIDPattern = regexp.MustCompile(`^[A-Za-z0-9._-]{1,64}$`)

type Paths struct {
	Certificate string
	PrivateKey  string
}

func ValidateNodeID(nodeID string) error {
	if !nodeIDPattern.MatchString(nodeID) {
		return errors.New("node id must match [A-Za-z0-9._-]{1,64}")
	}
	return nil
}

func InitCA(dir, commonName string) (Paths, error) {
	if dir == "" {
		return Paths{}, errors.New("CA directory is required")
	}
	if commonName == "" {
		commonName = "CyberHIVE Local CA"
	}
	if err := os.MkdirAll(dir, 0o700); err != nil {
		return Paths{}, fmt.Errorf("create CA directory: %w", err)
	}
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return Paths{}, fmt.Errorf("generate CA key: %w", err)
	}
	serial, err := randomSerial()
	if err != nil {
		return Paths{}, err
	}
	now := time.Now().UTC()
	tmpl := &x509.Certificate{SerialNumber: serial, Subject: pkix.Name{CommonName: commonName}, NotBefore: now.Add(-5 * time.Minute), NotAfter: now.AddDate(10, 0, 0), KeyUsage: x509.KeyUsageCertSign | x509.KeyUsageCRLSign, BasicConstraintsValid: true, IsCA: true}
	der, err := x509.CreateCertificate(rand.Reader, tmpl, tmpl, pub, priv)
	if err != nil {
		return Paths{}, fmt.Errorf("create CA certificate: %w", err)
	}
	paths := Paths{Certificate: filepath.Join(dir, "ca.crt"), PrivateKey: filepath.Join(dir, "ca.key")}
	if err := writeCert(paths.Certificate, der); err != nil {
		return Paths{}, err
	}
	if err := writePrivateKey(paths.PrivateKey, priv); err != nil {
		_ = os.Remove(paths.Certificate)
		return Paths{}, err
	}
	return paths, nil
}

func IssueNode(caDir, outDir, nodeID string, hosts []string) (Paths, error) {
	if err := ValidateNodeID(nodeID); err != nil {
		return Paths{}, err
	}
	if caDir == "" || outDir == "" {
		return Paths{}, errors.New("CA and output directories are required")
	}
	caCert, caKey, err := loadCA(filepath.Join(caDir, "ca.crt"), filepath.Join(caDir, "ca.key"))
	if err != nil {
		return Paths{}, err
	}
	if err := os.MkdirAll(outDir, 0o700); err != nil {
		return Paths{}, fmt.Errorf("create node identity directory: %w", err)
	}
	pub, priv, err := ed25519.GenerateKey(rand.Reader)
	if err != nil {
		return Paths{}, fmt.Errorf("generate node key: %w", err)
	}
	serial, err := randomSerial()
	if err != nil {
		return Paths{}, err
	}
	identityURI, err := url.Parse("spiffe://" + trustDomain + "/node/" + url.PathEscape(nodeID))
	if err != nil {
		return Paths{}, fmt.Errorf("build node identity URI: %w", err)
	}
	now := time.Now().UTC()
	tmpl := &x509.Certificate{SerialNumber: serial, Subject: pkix.Name{CommonName: "CyberHIVE node " + nodeID}, NotBefore: now.Add(-5 * time.Minute), NotAfter: now.AddDate(1, 0, 0), KeyUsage: x509.KeyUsageDigitalSignature, ExtKeyUsage: []x509.ExtKeyUsage{x509.ExtKeyUsageClientAuth, x509.ExtKeyUsageServerAuth}, URIs: []*url.URL{identityURI}}
	for _, host := range hosts {
		if host == "" {
			continue
		}
		if ip := net.ParseIP(host); ip != nil {
			tmpl.IPAddresses = append(tmpl.IPAddresses, ip)
		} else {
			tmpl.DNSNames = append(tmpl.DNSNames, host)
		}
	}
	der, err := x509.CreateCertificate(rand.Reader, tmpl, caCert, pub, caKey)
	if err != nil {
		return Paths{}, fmt.Errorf("create node certificate: %w", err)
	}
	paths := Paths{Certificate: filepath.Join(outDir, "node.crt"), PrivateKey: filepath.Join(outDir, "node.key")}
	if err := writeCert(paths.Certificate, der); err != nil {
		return Paths{}, err
	}
	if err := writePrivateKey(paths.PrivateKey, priv); err != nil {
		_ = os.Remove(paths.Certificate)
		return Paths{}, err
	}
	return paths, nil
}

func NodeIDFromCertificate(cert *x509.Certificate) (string, error) {
	if cert == nil {
		return "", errors.New("peer certificate is required")
	}
	for _, uri := range cert.URIs {
		if uri.Scheme != "spiffe" || uri.Host != trustDomain {
			continue
		}
		const prefix = "/node/"
		if len(uri.Path) <= len(prefix) || uri.Path[:len(prefix)] != prefix {
			continue
		}
		nodeID, err := url.PathUnescape(uri.Path[len(prefix):])
		if err != nil {
			return "", fmt.Errorf("decode node id: %w", err)
		}
		if err := ValidateNodeID(nodeID); err != nil {
			return "", err
		}
		return nodeID, nil
	}
	return "", errors.New("certificate has no CyberHIVE node identity URI")
}

func LoadCertificate(certPath, keyPath string) (tls.Certificate, error) {
	cert, err := tls.LoadX509KeyPair(certPath, keyPath)
	if err != nil {
		return tls.Certificate{}, fmt.Errorf("load node certificate: %w", err)
	}
	return cert, nil
}

func LoadCertPool(path string) (*x509.CertPool, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read CA certificate: %w", err)
	}
	pool := x509.NewCertPool()
	if !pool.AppendCertsFromPEM(data) {
		return nil, errors.New("CA file contains no valid certificates")
	}
	return pool, nil
}

func loadCA(certPath, keyPath string) (*x509.Certificate, ed25519.PrivateKey, error) {
	certPEM, err := os.ReadFile(certPath)
	if err != nil {
		return nil, nil, fmt.Errorf("read CA certificate: %w", err)
	}
	block, _ := pem.Decode(certPEM)
	if block == nil || block.Type != "CERTIFICATE" {
		return nil, nil, errors.New("invalid CA certificate PEM")
	}
	cert, err := x509.ParseCertificate(block.Bytes)
	if err != nil || !cert.IsCA {
		return nil, nil, errors.New("invalid CA certificate")
	}
	keyPEM, err := os.ReadFile(keyPath)
	if err != nil {
		return nil, nil, fmt.Errorf("read CA private key: %w", err)
	}
	keyBlock, _ := pem.Decode(keyPEM)
	if keyBlock == nil || keyBlock.Type != "PRIVATE KEY" {
		return nil, nil, errors.New("invalid CA private key PEM")
	}
	parsed, err := x509.ParsePKCS8PrivateKey(keyBlock.Bytes)
	if err != nil {
		return nil, nil, fmt.Errorf("parse CA private key: %w", err)
	}
	key, ok := parsed.(ed25519.PrivateKey)
	if !ok {
		return nil, nil, errors.New("CA private key is not Ed25519")
	}
	return cert, key, nil
}

func randomSerial() (*big.Int, error) {
	limit := new(big.Int).Lsh(big.NewInt(1), 128)
	serial, err := rand.Int(rand.Reader, limit)
	if err != nil {
		return nil, fmt.Errorf("generate certificate serial: %w", err)
	}
	return serial, nil
}

func writeCert(path string, der []byte) error {
	return writeExclusive(path, 0o644, pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: der}))
}

func writePrivateKey(path string, key ed25519.PrivateKey) error {
	der, err := x509.MarshalPKCS8PrivateKey(key)
	if err != nil {
		return fmt.Errorf("marshal private key: %w", err)
	}
	return writeExclusive(path, 0o600, pem.EncodeToMemory(&pem.Block{Type: "PRIVATE KEY", Bytes: der}))
}

func writeExclusive(path string, mode os.FileMode, data []byte) error {
	file, err := os.OpenFile(path, os.O_WRONLY|os.O_CREATE|os.O_EXCL, mode)
	if err != nil {
		return fmt.Errorf("create %s: %w", filepath.Base(path), err)
	}
	name := file.Name()
	ok := false
	defer func() {
		_ = file.Close()
		if !ok {
			_ = os.Remove(name)
		}
	}()
	if _, err := file.Write(data); err != nil {
		return fmt.Errorf("write %s: %w", filepath.Base(path), err)
	}
	if err := file.Sync(); err != nil {
		return fmt.Errorf("sync %s: %w", filepath.Base(path), err)
	}
	if err := file.Close(); err != nil {
		return fmt.Errorf("close %s: %w", filepath.Base(path), err)
	}
	ok = true
	return nil
}
