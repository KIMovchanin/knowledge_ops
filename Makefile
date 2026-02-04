COMPOSE := docker compose -f infra/docker-compose.yml

.PHONY: up down logs lint test fmt

up:
	$(COMPOSE) --profile mvp up -d --build

down:
	$(COMPOSE) down -v

logs:
	$(COMPOSE) logs -f --tail=200

lint:
	cd services/gateway-go && go vet ./...
	cd services/inference-python && poetry run ruff check . && poetry run black --check .
	cd services/frontend-web && npm run lint

test:
	cd services/gateway-go && go test ./...
	cd services/inference-python && poetry run pytest

fmt:
	cd services/gateway-go && gofmt -w ./cmd
	cd services/inference-python && poetry run black . && poetry run ruff check . --fix
	cd services/frontend-web && npm run format
