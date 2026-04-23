SHELL := bash
MAKEFLAGS += --warn-undefined-variables
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

.PHONY: reachy/sim
reachy/sim: ## Run the Reachy simulator
	@echo "Starting Reachy simulator..."
	mjpython -m reachy_mini.daemon.app.main --sim

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

.PHONY: npm/outdated
npm/outdated: ## Show outdated npm packages
	@npm outdated

.PHONY: npm/audit
npm/audit: ## Check for npm vulnerabilities
	@npm audit

.PHONY: npm/audit-fix
npm/audit-fix: ## Automatically fix npm vulnerabilities
	@echo "Fixing npm vulnerabilities..."
	@npm audit fix
	@echo "✓ Vulnerabilities fixed"

.PHONY: npm/update
npm/update: ## Update npm packages to latest versions within semver constraints
	@echo "Updating npm packages..."
	@npm update
	@echo "✓ Packages updated"

.PHONY: npm/upgrade
npm/upgrade: ## Upgrade all packages to latest major versions
	@echo "Upgrading npm packages to latest versions..."
	@npx npm-check-updates -u
	@npm install
	@echo "✓ Packages upgraded"

.PHONY: python/ruff-format
python/ruff-format: ## Automatically format Python code with ruff
	@ruff format

.PHONY: python/ruff-fix
python/ruff-fix: ## Automatically fix Python code with ruff
	@ruff check --fix

.PHONY: python/lock
python/lock: ## Lock Python dependencies
	@echo "Locking Python dependencies..."
	@uv lock
	@echo "✓ Dependencies locked"

.PHONY: python/lock-check
python/lock-check: ## Check if Python dependencies are up to date with lockfile
	@echo "Checking if Python dependencies are up to date with lockfile..."
	@uv lock --check

.PHONY: python/outdated
python/outdated: ## Show outdated Python packages
	@uv pip list --outdated

.PHONY: python/install
python/install: ## Install Python dependencies
	@echo "Installing Python dependencies..."
	@uv pip install . --group all
	@echo "✓ Dependencies installed"

.PHONY: python/unit-tests
python/unit-tests: ## Run Python unit tests with coverage
	@echo "Running Python unit tests with coverage..."
	@python -m pytest -v --cov=reachy_assistant tests/unit
	@echo "✓ Unit tests completed"

.PHONY: python/lint-check
python/lint-check: ## Run Python linters (flake8 and black)
	ruff check
	ruff format --check

.PHONY: pre-commit/install
pre-commit/install: ## Install pre-commit hooks
	@echo "Installing pre-commit hooks..."
	@pre-commit install
	@echo "✓ Pre-commit hooks installed"

.PHONY: pre-commit/autoupdate
pre-commit/autoupdate: ## Update pre-commit hook versions
	@pre-commit autoupdate

.PHONY: pre-commit/gc
pre-commit/gc: ## Clean unused cached repos.
	@pre-commit gc

.PHONY: pre-commit/remove-cache
pre-commit/remove-cache: ## Remove all of pre-commit's cache
	rm -rf ~/.cache/pre-commit/

.PHONY: pre-commit/run
pre-commit/run: ## Manually run pre-commit
	@pre-commit run --verbose

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
