# Asynchronous Event-Driven Microservices E-Commerce Platform

A portfolio e-commerce checkout engine built with **Clean Architecture** and **Event-Driven Architecture (EDA)**. It demonstrates eventual consistency over RabbitMQ, JWT-protected checkout, Chapa-style payment webhooks, and a React storefront deployed on Render free tier.

---

## Live demo

| Surface | URL |
| --- | --- |
| Storefront | https://sam-store.onrender.com/ |
| Product Service | https://product-service-y2y8.onrender.com/products |
| Order Service | https://order-service-3i4u.onrender.com/orders |

> **Free-tier note:** Render services sleep when idle. The first catalog request after a cold start can take up to ~60s; the UI shows skeletons and a wake banner while that happens.

---

## System architecture

Database-per-service with sync REST for catalog/pricing and async messaging for post-payment stock updates:

```text
       [ React Frontend: Vite / Render ]
         │                     │
         │ (HTTP REST)         │ (HTTP REST + JWT)
         ▼                     ▼
[ Product Service: :8001 ] <───(HTTP stock/price)─── [ Order Service: :8002 ]
   │                                                      │
   ├── PostgreSQL (product_db)                            ├── PostgreSQL (order_db)
   │                                                      │
   │ Consume: order.paid / order.failed                   ├── Publish: order.paid
   ▲                                                      │
   └─── [ RabbitMQ / CloudAMQP ] <────────────────────────┘
                                                          │
                                                          └── Webhook <── Chapa (mock)
```

### Design decisions

1. **Clean Architecture** — Domain schemas stay free of FastAPI/SQLAlchemy; use cases orchestrate repositories and clients; infrastructure owns routers, ORM models, and brokers.
2. **Eventual consistency** — Order Service never writes Product stock. On payment success it marks the order `PAID` and publishes `order.paid`; Product Service consumes and decrements inventory asynchronously.
3. **Webhook idempotency** — Replaying the same `tx_ref` after an order is already `PAID` returns success without republishing RabbitMQ events (prevents double stock decrement).
4. **JWT-scoped history** — Checkout and `GET /orders/me` require a Bearer token; public `GET /orders/{id}` remains available for the eventual-consistency demo tracker.
5. **Saga-style compensation** — Payment failure can publish `order.failed` so Product Service restores reserved stock (when that path is exercised).

---

## Tech stack

- **Backend:** FastAPI (Python 3.13), SQLAlchemy 2.0 async, Psycopg 3
- **Messaging:** RabbitMQ (local Docker) / CloudAMQP (Render)
- **Payments:** Chapa API with interactive mock webhook redirect
- **Frontend:** React (Vite) + Tailwind CSS
- **Infra:** Docker Compose (local DB + broker), Render (deploy), GitHub Actions (CI)

---

## Demo script (eventual consistency)

Use this path when walking recruiters or reviewers through the live system:

1. Open the [storefront](https://sam-store.onrender.com/) and register / sign in (JWT issued by Order Service).
2. Wait for the catalog if services are cold — skeletons + “waking free-tier” message are expected.
3. Add items to the cart and **Proceed to Secure Payment**. A new tab opens the mock Chapa success page.
4. Confirm payment in the mock tab. Order Service sets status `PAID` and publishes `order.paid`.
5. Refresh **My Orders** (or use the Live Order Status Tracker with the new order ID) — status should move `PENDING` → `PAID`.
6. Refresh the catalog — stock for purchased products should drop shortly after the consumer processes the event.
7. Optionally replay the webhook with the same `tx_ref`; stock must **not** decrement again (idempotency).

---

## Quick start (local)

### Prerequisites

- Docker Desktop
- Node.js 18+
- Python 3.13

### 1. Infrastructure

```bash
docker compose up -d
```

- RabbitMQ management UI: http://localhost:15672 (`guest` / `guest`)
- Create Postgres databases `product_db` and `order_db` on the mapped port (default `5433`)

### 2. Product Service

```bash
cd product_service
# activate venv, then:
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### 3. Order Service

```bash
cd order_service
uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Optional env overrides (otherwise production Render URLs are used as fallbacks):

```bash
# frontend/.env.local
VITE_PRODUCT_API_URL=http://127.0.0.1:8001/products
VITE_ORDER_API_URL=http://127.0.0.1:8002/orders
```

---

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs on pushes/PRs to `main`:

- `test-product-service` — install `product_service/requirements.txt`, `pytest product_service/`
- `test-order-service` — install `order_service/requirements.txt`, `pytest order_service/` (includes webhook idempotency unit tests)

```bash
PYTHONPATH=product_service pytest product_service/
PYTHONPATH=order_service pytest order_service/
```

---

## Key API surfaces

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/orders/auth/register` | — | Create account |
| `POST` | `/orders/auth/login` | — | Issue JWT |
| `POST` | `/orders/` | JWT | Create order + payment URL |
| `GET` | `/orders/me` | JWT | Current user's order history |
| `GET` | `/orders/{order_id}` | — | Lookup by id (demo tracker) |
| `POST` | `/orders/webhook/chapa` | — | Confirm payment (`tx_ref`, `status: success`) |
| `GET` | `/products` | — | Catalog |

---

## Project layout

```text
product_service/   # Catalog, stock, RabbitMQ consumer
order_service/     # Auth, checkout, webhook, RabbitMQ publisher
frontend/          # Vite React storefront (App.jsx)
.github/workflows/ # CI for both Python services
```
