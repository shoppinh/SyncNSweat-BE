# Sync & Sweat Backend

This is the backend API for Sync & Sweat, built with FastAPI and PostgreSQL.

## Getting Started

1. Create and activate a virtual environment:

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS/Linux
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables:

Create a `.env` file with the following variables:
```
DATABASE_URL=postgresql://username:password@localhost:5432/syncnsweat
SECRET_KEY=your_secret_key
SPOTIFY_CLIENT_ID=your_spotify_client_id
SPOTIFY_CLIENT_SECRET=your_spotify_client_secret
EXERCISEDB_API_KEY=your_exercisedb_api_key
```

4. Run database migrations:

```bash
alembic upgrade head
```

5. Start the development server:

```bash
uvicorn app.main:app --reload
```

## API Documentation

Once the server is running, you can access the API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Running Tests

To run the tests:

```bash
pytest
```

To run tests with coverage:

```bash
pytest --cov=app
```
