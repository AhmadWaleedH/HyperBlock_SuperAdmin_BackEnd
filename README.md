# HyperBlock Super Admin API

A backend API for HyperBlock super admins, built with FastAPI and MongoDB.

## Features

- User management endpoints 
- Authentication for admin users
- Filter and search functionality
- MongoDB integration

## Setup

### Prerequisites

- Python 3.8+
- MongoDB

### Installation

1. Clone the repository
```bash
git clone <repository-url>
cd hyperblock-api
```

2. Create and activate a virtual environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows
venv\Scripts\activate
# On Unix or MacOS
source venv/bin/activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Configure environment variables
   - Copy `.env.example` to `.env`
   - Update the values in `.env` with your configuration
```bash
cp .env.example .env
```

### Running the API

You can start the API server using either **Docker Compose** or a Python script.

#### 1. Start the server manually
```bash
# Development with auto-reload
uvicorn app.main:app --reload

# Production
uvicorn app.main:app
```

#### 2. Start the server using `run.py`
```bash
python run.py
```

#### 3. Start the server using Docker Compose
```bash
docker-compose up --build
```

2. Access the API documentation
   - Swagger UI: `http://localhost:8000/api/v1/docs`
   - ReDoc: `http://localhost:8000/api/v1/redoc`

## API Endpoints

### Authentication

- `POST /api/v1/auth/login` - Login for admin users

### User Management

- `GET /api/v1/users` - List all users (with filtering)
- `POST /api/v1/users` - Create a new user
- `GET /api/v1/users/{user_id}` - Get a user by ID
- `GET /api/v1/users/discord/{discord_id}` - Get a user by Discord ID
- `PATCH /api/v1/users/{user_id}` - Update a user
- `DELETE /api/v1/users/{user_id}` - Delete a user
- `GET /api/v1/users/search` - Search users

## Project Structure

```
hyperblock-api/
│
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI application entry point
│   ├── config.py             # Configuration settings
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── users.py      # User-related endpoints
│   │   │   └── auth.py       # Authentication endpoints
│   │   │
│   │   └── dependencies.py   # Shared dependencies
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py       # Authentication and authorization
│   │   └── exceptions.py     # Custom exceptions
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── database.py       # Database connection
│   │   └── repositories/
│   │       ├── __init__.py
│   │       └── users.py      # User data access layer
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py           # User models (Pydantic)
│   │   └── common.py         # Shared models
│   │
│   └── services/
│       ├── __init__.py
│       └── user_service.py   # Business logic for users
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_users.py
│
├── .env                      # Environment variables
├── .gitignore
├── README.md
└── requirements.txt
```

## License

[MIT License](LICENSE)