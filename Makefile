.PHONY: test-unit test-api test-worker test-mcp test-e2e test-ios-unit test-all

test-unit:
	pnpm -F @kos/web test:run

test-api:
	cd tests && PYTHONPATH=../services/api uv run pytest api/ unit/ -q

test-worker:
	cd tests && PYTHONPATH=../services/api:../services/worker uv run pytest worker/ -q

test-mcp:
	cd services/mcp && uv run --extra dev pytest tests/ -q

test-e2e:
	pnpm test:e2e

test-ios-unit:
	cd apps/ios && xcodegen generate
	cd apps/ios && xcodebuild \
		-project KnowledgeOS.xcodeproj \
		-scheme KnowledgeOS \
		-destination 'platform=iOS Simulator,name=iPhone 16' \
		-only-testing:KnowledgeOSTests \
		test

test-all: test-unit test-api test-worker test-mcp test-e2e

