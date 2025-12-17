# 📦 Microservices Architecture Project

This project showcases a microservices architecture with a focus on authentication and inventory management. It includes a basic FastAPI application, JWT-based authentication, and a separate inventory microservice. The architecture is designed to be scalable and maintainable, with each microservice handling a specific domain of responsibility.

🚀 **Key Features**

*   **Authentication Microservice:**
    *   🔐 User authentication using OTP (One-Time Password) via Telegram.
    *   🔑 JWT (JSON Web Token) based access and refresh token generation and verification.
    *   🛡️ Role-based access control (admin).
    *   📱 Binding Telegram chat ID to user phone number.
*   **Inventory Microservice:**
    *   📦 CRUD operations for inventory items.
    *   🔄 Stock reservation and release functionality.
    *   📢 Real-time stock updates via Redis Pub/Sub.
    *   🔒 Admin-protected endpoints for inventory management.
*   **Shared Libraries:**
    *   Reusable JWT core library for token management.
*   **Core Functionality:**
    *   Health check endpoints for monitoring service status.
    *   Configuration management using environment variables.
    *   Asynchronous database interactions.

🛠️ **Tech Stack**

*   **Backend:**
    *   🐍 Python 3.11+
    *   ⚡ FastAPI: Web framework for building APIs.
    *   💾 SQLAlchemy: ORM for database interactions.
    *   🐳 Redis: In-memory data store for caching and pub/sub.
    *   🔑 PyJWT: JSON Web Token implementation.
    *   ⚙️ Pydantic: Data validation and settings management.
    *   📜 Pydantic Settings: Load settings from `.env` files.
    *   🔒 Python-jose: JWT signing and encryption.
*   **Database:**
    *   🐘 PostgreSQL (or any SQLAlchemy-supported database)
*   **Other:**
    *   📦 Docker: Containerization (optional, for deployment)
    *   📜 .env: Environment variable management
    *   🧪 pytest: Testing framework (not explicitly shown in summaries, but recommended)

📦 **Getting Started / Setup Instructions**

### Prerequisites

*   Python 3.11+
*   Poetry (recommended) or pip
*   Docker (optional, for running Redis and PostgreSQL)
*   Redis instance
*   PostgreSQL database

### Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

2.  **Set up a virtual environment (recommended):**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Linux/macOS
    venv\Scripts\activate  # On Windows
    ```

3.  **Install dependencies using Poetry (recommended):**

    ```bash
    poetry install
    ```

    Or, install dependencies using pip:

    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**

    *   Create a `.env` file in each microservice directory (`microservices/auth/src/.env`, `microservices/inventory/src/.env`).
    *   Populate the `.env` files with the necessary configuration values, such as:

        ```
        PROJECT_NAME="Your Project Name"
        DATABASE_URL="postgresql+asyncpg://user:password@host:port/database"
        REDIS_URL="redis://host:port/0"
        ELASTICSEARCH_URL="http://host:port" # Optional
        SECRET_KEY="YourSecretKey"
        ALGORITHM="HS256"
        JWT_SECRET="YourJWTSecret"
        ACCESS_TOKEN_EXPIRE_MINUTES=30
        REFRESH_TOKEN_EXPIRE_MINUTES=60 * 24 * 30  # 30 days
        ```

        Replace the placeholder values with your actual configuration.

### Running Locally

1.  **Start the Redis and PostgreSQL databases (if not already running):**

    *   Using Docker Compose (example):

        ```yaml
        version: "3.8"
        services:
          redis:
            image: "redis:latest"
            ports:
              - "6379:6379"
          db:
            image: postgres:15
            environment:
              POSTGRES_USER: youruser
              POSTGRES_PASSWORD: yourpassword
              POSTGRES_DB: yourdatabase
            ports:
              - "5432:5432"
            volumes:
              - db_data:/var/lib/postgresql/data

        volumes:
          db_data:
        ```

        ```bash
        docker-compose up -d
        ```

2.  **Run the authentication microservice:**

    ```bash
    cd microservices/auth/src
    poetry run uvicorn main:app --reload  # Using Poetry
    # or
    uvicorn main:app --reload # if you have fastapi installed globally
    ```

3.  **Run the inventory microservice:**

    ```bash
    cd microservices/inventory/src
    poetry run uvicorn main:app --reload  # Using Poetry
    # or
    uvicorn main:app --reload # if you have fastapi installed globally
    ```

4.  **Access the APIs:**

    *   Authentication microservice: `http://localhost:8000` (or the port you configured)
    *   Inventory microservice: `http://localhost:8001` (or the port you configured)

📂 **Project Structure**

| Service name:PORT | Description                                                         |
|:------------------|:--------------------------------------------------------------------|
| **Service A :81** |	Catalog/Search Service  Fast reading, search, filters (CQRS Read Model).|
| **Service B :82** |	Inventory Service	CQRS Write Model. |
| **Service C :83** |	Order Service	Saga orcherstrator, manage orders.|
| **Service D :80** |	Auth Service	Authorization,gives JWT token, bind Telegram ID.|
| **Service E :84** |	Notification Service	Centralized sending notification (Telegram Bot).|

```
├── main.py
├── microservices
│   ├── auth
│   │   ├── src
│   │   │   ├── api
│   │   │   │   ├── auth_routes.py
│   │   │   │   └── internal_routes.py
│   │   │   ├── core
│   │   │   │   ├── config.py
│   │   │   │   ├── database.py
│   │   │   │   └── redis_client.py
│   │   │   ├── schemas
│   │   │   │   └── auth.py
│   │   │   ├── main.py
│   │   │   └── tests  # (Optional)
│   ├── inventory
│   │   ├── src
│   │   │   ├── api
│   │   │   │   └── routers
│   │   │   │       ├── admin_routes.py
│   │   │   │       └── inventory_routes.py
│   │   │   ├── core
│   │   │   │   ├── config.py
│   │   │   │   └── database.py
│   │   │   ├── models
│   │   │   │   └── inventory.py
│   │   │   ├── schemas
│   │   │   │   └── inventory.py
│   │   │   ├── main.py
│   │   │   └── tests  # (Optional)
│   └── notifications # (Hypothetical)
├── shared-libs
│   ├── jwt_core_lib
│   │   ├── dependencies.py
│   │   └── utils.py
├── README.md
└── requirements.txt
```