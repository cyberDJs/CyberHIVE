package httptransport

import (
	"crypto/tls"
	"fmt"

	"github.com/cyberDJs/CyberHIVE/internal/security/identity"
)

func LoadServerTLSConfig(clientCAPath string) (*tls.Config, error) {
	pool, err := identity.LoadCertPool(clientCAPath)
	if err != nil {
		return nil, err
	}
	return &tls.Config{
		MinVersion: tls.VersionTLS13,
		ClientAuth: tls.RequireAndVerifyClientCert,
		ClientCAs:  pool,
	}, nil
}

func LoadClientTLSConfig(certPath, keyPath, serverCAPath string) (*tls.Config, error) {
	cert, err := identity.LoadCertificate(certPath, keyPath)
	if err != nil {
		return nil, err
	}
	pool, err := identity.LoadCertPool(serverCAPath)
	if err != nil {
		return nil, err
	}
	if len(cert.Certificate) == 0 {
		return nil, fmt.Errorf("client certificate chain is empty")
	}
	return &tls.Config{
		MinVersion:   tls.VersionTLS13,
		Certificates: []tls.Certificate{cert},
		RootCAs:      pool,
	}, nil
}
