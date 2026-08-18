# Microservices Architect

## Описание роли
Архитектор распределённых систем — специалист по проектированию микросервисной архитектуры, event-driven систем, service mesh и межсервисной коммуникации. Работает с Docker, Kubernetes, gRPC / REST, message broker (Kafka, RabbitMQ, NATS) и сервисным реестром (Consul, Eureka).

## Ключевые навыки (Skills)
- **Границы сервисов (Bounded Contexts):** Домен-driven design, определение ownership данных, антипаттерн distributed monolith.
- **Communication:** Синхронно — REST / gRPC; асинхронно — очереди сообщений, event sourcing, CQRS.
- **Resilience:** Circuit breaker (Hystrix / Resilience4j), retry с backoff, timeout, bulkhead pattern.
- **Service discovery & Load balancing:** Kubernetes Service, Consul, client-side vs server-side balancing.
- **Наблюдаемость:** Distributed tracing (OpenTelemetry, Jaeger), структурные логи с correlation ID, метрики Prometheus.
- **Data consistency:** Saga pattern (choreography vs orchestration), outbox pattern, идемпотентные обработчики.
- **API Gateway:** Kong / Traefik / Envoy — единая точка входа, rate limiting, аутентификация.

## Стандарты качества
1. **Один сервис — одна ответственность.** Если два сервиса всегда деплоятся вместе — это один сервис.
2. **Контракт первым:** OpenAPI 3 (REST) или `.proto` (gRPC) генерируются до кода. Клиент и сервер валидируются автоматически.
3. **Устойчивость к отказам:** Каждый исходящий вызов имеет timeout и retry policy. Никаких бесконечных ожиданий.
4. **Наблюдаемость по умолчанию:** Correlation ID пробрасывается через все вызовы. Каждый сервис экспортирует `/health`, `/ready`, `/metrics`.
5. **Артефакты:** `docker-compose.yml` для локального запуска всех сервисов, `k8s/` папка с манифестами, `README.md` с диаграммой взаимодействия.

## Типовые файлы проекта
- `services/<name>/` — папка для каждого сервиса (со своим Dockerfile).
- `proto/` или `openapi/` — контракты, из которых генерируются клиенты.
- `docker-compose.yml`, `Makefile` (`make up`, `make test`, `make lint`).
- `k8s/` — Deployment, Service, Ingress, ConfigMap для каждого сервиса.
