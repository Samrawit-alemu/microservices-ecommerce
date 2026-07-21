# Asynchronous Event-Driven Microservices E-Commerce Platform

A production-ready e-commerce checkout engine designed using **Clean Architecture** and **Event-Driven Architecture (EDA)**. This system demonstrates eventual consistency, asynchronous messaging, distributed transactions, and secure third-party payment integrations.

---

## 🏗 System Architecture Diagram

The system is designed with a **Database-per-Service** pattern to ensure independent deployability and tight service boundaries. Inter-service communication is split into synchronous REST calls (for pricing and stock validation) and asynchronous messaging (for transactional operations).

```text
       [ React Frontend: Port 5173 ]
         │                     │
         │ (HTTP REST)         │ (HTTP REST)
         ▼                     ▼
[ Product Service: Port 8001 ] <───(HTTP Sync Validation)─── [ Order Service: Port 8002 ]
   │                                                             │
   ├── (Async PostgreSQL)                                        ├── (Async PostgreSQL)
   │     └── [ product_db ]                                      │     └── [ order_db ]
   │                                                             │
   │ (Consume event: order.paid / order.failed)                  ├── (Publish event: order.paid)
   ▲                                                             │
   └─── [ RabbitMQ Broker: Port 5672 ] <─────────────────────────┘
                                                                 │
                                                                 └─── (HTTP Webhook) <── [ Chapa Payments ]
```

---

## 🚀 Key Architectural Patterns Implemented

### 1. Clean Architecture (Onion/Hexagonal)

Each microservice is decoupled into strict layers:

- **Domain:** Contains pure business rules and data validation schemas (Pydantic) with zero framework or database dependencies.
- **Use Cases (Application):** Orchestrates domain schemas and database gateways to execute core business workflows.
- **Infrastructure:** Adapters handling framework details—FastAPI routers, database models (SQLAlchemy), repositories, and external HTTP clients.

### 2. Eventual Consistency & EDA (RabbitMQ)

To prevent network bottlenecks and single points of failure, the Order Service does not modify the Product database directly. When Chapa confirms a payment, the Order Service updates its status to `PAID` and publishes an asynchronous event (`order.paid`) to **RabbitMQ**. A background consumer running in the Product Service intercepts this event and decrements the stock in its database.

### 3. Saga Pattern (Compensating Transactions)

To maintain data integrity during payment failures (e.g., if a user cancels their Chapa checkout), the system executes a Saga compensating transaction. The Order Service publishes an `order.failed` event, and the Product Service automatically restores (increments) the locked inventory stock.

### 4. Concurrency & Threading

FastAPI runs on an asynchronous event loop. Because RabbitMQ's message listener is an infinite blocking process, the background consumer is safely isolated inside a **Daemon Thread**, preventing CPU blockages and ensuring clean OS resource management.

---

## 🛠 Tech Stack

- **Backend Framework:** FastAPI (Python 3.13)
- **Database:** PostgreSQL (Relational)
- **ORM:** SQLAlchemy 2.0 (Asynchronous)
- **Database Driver:** Psycopg 3 (Binary-packaged)
- **Message Broker:** RabbitMQ (AMQP 3-management)
- **Payment Gateway:** Chapa API (Interactive Mock Webhooks)
- **Frontend:** React (Vite, Tailwind CSS v4.0)
- **Infrastructure & DevOps:** Docker, Docker Compose
- **Testing & CI/CD:** Pytest, GitHub Actions (Automated Workflows)

---

## 💻 Quick Start & Running Locally

### Prerequisites

- Docker Desktop running on Windows/macOS/Linux
- Node.js (v18 or greater)
- Python 3.13

### 1. Start the Infrastructure (Databases & Message Broker)

From the root directory, spin up PostgreSQL and RabbitMQ inside Docker:

```bash
docker compose up -d
```

- Verify the RabbitMQ Management Dashboard is active at: `http://localhost:15672` (guest / guest).
- Create your PostgreSQL databases (`product_db` and `order_db`) on port `5433` (or your mapped local port).

### 2. Start the Product Service

```bash
cd product_service
# Activate your virtual environment and run:
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

### 3. Start the Order Service

```bash
cd order_service
# Activate your virtual environment and run:
uvicorn app.main:app --host 127.0.0.1 --port 8002 --reload
```

### 4. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```
