.PHONY: help install 01-simplest-bot 02-persistent-sessions 03-personality-soul 04-tools-agent-loop 05-permission-controls 06-gateway 07-context-compaction 08-long-term-memory 09-concurrency-scheduling 10-multi-agent-integration test clean

help: ## Show this help message
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies using uv
	@echo "Installing dependencies..."
	@uv sync

run: 01-simplest-bot ## Run the first module — start here!

# =============================================================================
# Workshop Modules
# =============================================================================

01-simplest-bot: ## 01 Simplest Bot — 20-line Telegram bot (start here!)
	@echo "Running 01: Simplest Bot..."
	@uv run python 01-simplest-bot/bot.py

02-persistent-sessions: ## 02 Persistent Sessions — JSONL per-user storage
	@echo "Running 02: Persistent Sessions..."
	@uv run python 02-persistent-sessions/bot.py

03-personality-soul: ## 03 Personality & Soul — System prompt identity
	@echo "Running 03: Personality & Soul..."
	@uv run python 03-personality-soul/bot.py

04-tools-agent-loop: ## 04 Tools & Agent Loop — 4 tools + agent loop
	@echo "Running 04: Tools & Agent Loop..."
	@uv run python 04-tools-agent-loop/bot.py

05-permission-controls: ## 05 Permission Controls — Three-tier safety model
	@echo "Running 05: Permission Controls..."
	@uv run python 05-permission-controls/bot.py

06-gateway: ## 06 Gateway — HTTP + Telegram channels
	@echo "Running 06: Gateway..."
	@uv run python 06-gateway/bot.py

07-context-compaction: ## 07 Context Compaction — Automatic summarization
	@echo "Running 07: Context Compaction..."
	@uv run python 07-context-compaction/bot.py

08-long-term-memory: ## 08 Long-Term Memory — File-based persistent memory
	@echo "Running 08: Long-Term Memory..."
	@uv run python 08-long-term-memory/bot.py

09-concurrency-scheduling: ## 09 Concurrency & Scheduling — Locks + cron
	@echo "Running 09: Concurrency & Scheduling..."
	@uv run python 09-concurrency-scheduling/bot.py

10-multi-agent-integration: ## 10 Multi-Agent Integration — Full system
	@echo "Running 10: Multi-Agent Integration..."
	@uv run python 10-multi-agent-integration/mini-openclaw.py

# =============================================================================
# Utilities
# =============================================================================

test: ## Run automated tests to verify all modules
	@echo "Running workshop tests..."
	@uv run python tests.py

clean: ## Clean up artifacts
	@echo "Cleaning up..."
	@rm -rf .venv
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type d -name "sessions" -exec rm -rf {} +
	@find . -type d -name "memory" -exec rm -rf {} +
	@find . -name "exec-approvals.json" -delete
