.PHONY: test go-test python-test vet python-compile check build

go-test:
	go test ./...

python-test:
	python3 -m unittest discover -s tests -v

test: go-test python-test

vet:
	go vet ./...

python-compile:
	python3 -m py_compile scripts/collect_host_facts.py scripts/benchmark_openai.py

check: vet python-compile test

build:
	go build ./cmd/cyberhive
