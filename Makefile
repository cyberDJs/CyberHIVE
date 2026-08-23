.PHONY: test vet check build

test:
	go test ./...

vet:
	go vet ./...

check: vet test

build:
	go build ./cmd/cyberhive
