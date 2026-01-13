# 📦 Microservices Architecture Project

The Ecommerce Microservices Project is a comprehensive, scalable, and highly available ecommerce platform built using a microservices architecture. It consists of multiple independent services, each responsible for a specific domain, such as authentication, inventory, orders, and notifications. This project aims to provide a robust, flexible, and maintainable ecommerce solution that can be easily extended and customized to meet the needs of various businesses.

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
*   **Order Microservice:** 
    * Handles order management, including creating new orders, executing distributed transactions, and publishing events to notify admins and confirm orders with users.
*   **Notification Microservice:** 
    * Provides real-time notifications to users, including order updates, inventory changes, and other important events.
*   **Catalog Microservice:** 
    * Manages product data, including creating, reading, updating, and deleting products.
*   **API Gateways:** 
    * Exposes RESTful APIs for each microservice, allowing for easy integration with web and mobile applications.
* **Shared Libraries:**
    *   Reusable JWT core library for token management.
*   **Core Functionality:**
    *   Health check endpoints for monitoring service status.
    *   Configuration management using environment variables.
    *   Asynchronous database interactions.

🛠️ **Tech Stack**

*   **Backend:**
    *    Python 3.11+
    *    FastAPI: Web framework for building APIs.
    *    SQLAlchemy: ORM for database interactions.
    *    Redis: In-memory data store for caching and pub/sub.
    *    PyJWT: JSON Web Token implementation.
    *   ️ Pydantic: Data validation and settings management.
    *    Pydantic Settings: Load settings from `.env` files.
    *    Python-jose: JWT signing and encryption.
    *    asyncio: For asynchronous programming
    *    contextlib: For defining async context managers
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

```markdown
.
├── microservices
│   ├── auth
│   │   ├── src
│   │   │   ├── main.py
│   │   │   ├── api
│   │   │   │   ├── auth_routes.py
│   │   │   ├── core
│   │   │   │   ├── config.py
│   │   ├── tests
│   │   ├── Dockerfile
│   ├── inventory
│   │   ├── src
│   │   │   ├── main.py
│   │   │   ├── api
│   │   │   │   ├── inventory_routes.py
│   │   │   ├── core
│   │   │   │   ├── config.py
│   │   ├── tests
│   │   ├── Dockerfile
│   ├── order
│   │   ├── src
│   │   │   ├── main.py
│   │   │   ├── api
│   │   │   │   ├── order_routers.py
│   │   │   ├── core
│   │   │   │   ├── config.py
│   │   ├── tests
│   │   ├── Dockerfile
│   ├── notification
│   │   ├── src
│   │   │   ├── main.py
│   │   │   ├── api
│   │   │   │   ├── ws.py
│   │   │   ├── core
│   │   │   │   ├── config.py
│   │   ├── tests
│   │   ├── Dockerfile
│   ├── catalog
│   │   ├── src
│   │   │   ├── main.py
│   │   │   ├── api
│   │   │   │   ├── products.py
│   │   │   ├── core
│   │   │   │   ├── config.py
│   │   ├── tests
│   │   ├── Dockerfile
├── docker-compose.yml
├── requirements.txt
```