SHELL := bash
MAKEFLAGS += --warn-undefined-variables
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

.PHONY: security/dependency
security/dependency: ## Check if dependencies contain any vulnerabilities
	go run github.com/google/osv-scanner/v2/cmd/osv-scanner@latest scan source --lockfile=uv.lock --all-packages --format=vertical


.PHONY: security/sast
security/sast: ## Run Static Analysis testing
security/sast: security/semgrep
security/sast: security/bandit

.PHONY: security/bandit
security/bandit: ## Run Bandit for Med/High Static Analysis testing
	bandit -r . -ll

.PHONY: security/semgrep
security/semgrep: ## Run Semgrep Static Analysis testing
	docker run --rm -v "${PWD}:/src" returntocorp/semgrep semgrep scan \
		--error \
		--config=p/security-audit \
		--config=p/secrets \
		--config=p/python-command-injection \
		--config=p/python

.PHONY: security/all
security/all: ## Run all security targets
security/all: security/dependency
security/all: security/sast

.PHONY: security/secrets
security/secrets: ## Run Detect Secrets to find hardcoded secrets
	@detect-secrets scan \
		--baseline .secrets.baseline \
		--exclude-files "docs/examples/cancer_image.*.ipynb" \
		--exclude-files "tests/resources/*"

.PHONY: security/secrets-audit
security/secrets-audit: ## Audit Detect Secrets baseline file
	@detect-secrets audit .secrets.baseline

.PHONY: security/secrets-ci
security/secrets-ci: ## CI step to audit Detect Secrets baseline file, fails if any unverified secrets
secrets/secrets-ci: security/secrets
secrets/secrets-ci:
	@result=$$(detect-secrets audit .secrets.baseline --stats --json | jq '[.[].stats.raw] | any(.unknown > 0 or ."true-positives" > 0)'); \
	if [ "$$result" = "true" ]; then \
	    echo "Secrets found – failing the build"; \
	    exit 1; \
	else \
	    echo "No secrets found – continuing"; \
	    exit 0; \
	fi

.PHONY: semantic-release/install
semantic-release/install: ## Install semantic-release dependencies (nvm use + npm install)
	@echo "Setting up Node.js environment for semantic-release..."
	@command -v nvm >/dev/null 2>&1 && . ~/.nvm/nvm.sh && nvm use || echo "⚠ nvm not found, skipping nvm use"
	@echo "Installing dependencies..."
	@npm install
	@echo "✓ Setup complete"

.PHONY: semantic-release/dry-run
semantic-release/dry-run: ## Perform a dry-run of semantic-release (no changes made)
	@echo "Running semantic-release dry-run..."
	@npx semantic-release --dry-run --no-ci --branches main
	@echo "✓ Dry-run complete"

.PHONY: semantic-release/publish
semantic-release/publish: ## Publish a release using semantic-release
	@echo "Publishing release..."
	@npx semantic-release --branches main
	@echo "✓ Release published"


.PHONY: help
help: ## Shows all targets and help from the Makefile (this message).
	@grep --no-filename -E '^([a-zA-Z0-9_.%/-]+:.*?)##' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?(## ?)"}; { \
			if (length($$1) > 0) { \
				printf "  \033[36m%-30s\033[0m %s\n", $$1, $$2; \
			} else { \
				printf "%s\n", $$2; \
			} \
		}'
