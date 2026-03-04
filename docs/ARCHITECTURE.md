# SyncNSweat Backend Architecture

## Overview

SyncNSweat is a fitness application that synchronizes workouts with Spotify playlists. The backend is a FastAPI service that currently runs workout generation in-process and persists results to PostgreSQL.

This document has two parts:

- **Current Architecture**: what exists in this repository today.
- **Target Distributed Architecture (Planned)**: the intended event-driven design, implemented incrementally via strangler migration.

For rollout details, see [DISTRIBUTED_MIGRATION_PLAN.md](./DISTRIBUTED_MIGRATION_PLAN.md).

## Tech Stack

| Layer | Technology |
|-------|------------|
| Framework | FastAPI 0.115 |
| Server | Uvicorn |
| Database | PostgreSQL |
| ORM | SQLAlchemy 2.0 |
| Migrations | Alembic |
| Authentication | JWT (`python-jose`) |
| AI Integration | Google Gemini |
| External APIs | Spotify Web API, Exercise API |

## Current Architecture

### Project Structure

```text
SyncNSweat-BE/
├── app/
│   ├── api/
│   │   └── endpoints/
│   │       ├── auth.py
│   │       ├── users.py
│   │       ├── profiles.py
│   │       ├── workouts.py
│   │       ├── exercises.py
│   │       ├── playlists.py
│   │       ├── health.py
│   │       └── database.py
│   ├── core/
│   │   ├── config.py
│   │   └── security.py
│   ├── db/
│   │   └── session.py
│   ├── models/
│   │   ├── user.py
│   │   ├── workout.py
│   │   ├── profile.py
│   │   ├── preferences.py
│   │   └── refresh_token.py
│   ├── repositories/
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── workout.py
│   │   ├── workout_exercise.py
│   │   ├── exercise.py
│   │   ├── profile.py
│   │   ├── preferences.py
│   │   └── refresh_token.py
│   ├── schemas/
│   │   ├── user.py
│   │   ├── workout.py
│   │   ├── profile.py
│   │   ├── preferences.py
│   │   ├── exercise.py
│   │   ├── token.py
│   │   └── candidate.py
│   ├── services/
│   │   ├── spotify.py
│   │   ├── spotify_interceptor.py
│   │   ├── exercise.py
│   │   ├── gemini.py
│   │   ├── profile.py
│   │   ├── preferences.py
│   │   ├── playlist_selector.py
│   │   ├── exercise_selector.py
│   │   └── scheduler.py
│   └── utils/
│       ├── constant.py
│       ├── datetime.py
│       ├── fuzzy.py
│       └── helper.py
├── tests/
├── docs/
├── requirements.txt
├── Dockerfile
├── alembic.ini
└── .env.example
```

### Layers

#### 1. API Layer (`app/api/endpoints/`)

The API layer handles HTTP requests and responses using FastAPI.

Key workout-generation endpoints:

- `POST /api/v1/workouts/today`: Generates and persists a workout (currently synchronous).
- `POST /api/v1/workouts/schedule`: Generates and persists weekly schedule (currently synchronous).
- `POST /api/v1/workouts/{workout_id}/exercises/{exercise_id}/swap`: Recommends and applies exercise swap.

#### 2. Service Layer (`app/services/`)

| Service | Responsibility |
|---------|---------------|
| `SpotifyService` | Spotify API calls, token management, playlist creation |
| `SpotifyInterceptor` | Access token refresh flow and retry guard |
| `ExerciseService` | External exercise API integration |
| `GeminiService` | AI workout and playlist generation |
| `ProfileService` | User profile management |
| `PreferencesService` | User preference management |
| `PlaylistSelectorService` | Playlist fallback/selection logic |
| `ExerciseSelectorService` | Exercise fallback/selection logic |
| `SchedulerService` | Weekly workout scheduling fallback |

#### 3. Repository Layer (`app/repositories/`)

Implements data access abstraction.

Primary repositories include:

- `UserRepository`
- `WorkoutRepository`
- `WorkoutExerciseRepository`
- `ExerciseRepository`
- `ProfileRepository`
- `PreferencesRepository`
- `RefreshTokenRepository`

#### 4. Model Layer (`app/models/`)

SQLAlchemy models define persistence entities:

- `User`
- `Workout`
- `WorkoutExercise`
- `Exercise`
- `Profile`
- `Preferences`
- `RefreshToken`

#### 5. Schema Layer (`app/schemas/`)

Pydantic models provide request/response validation and serialization.

### Current Runtime Flow for `POST /api/v1/workouts/today`

1. API validates authenticated user and loads profile/preferences.
2. API invokes `GeminiService` in-request.
3. API applies fallback logic via selector services when AI response is partial.
4. API persists workout and workout_exercises in the same request path.
5. API responds with created workout.

## Target Distributed Architecture (Planned)

### Planned New Modules

```text
app/
├── messaging/
│   ├── connection.py
│   ├── publisher.py
│   ├── consumer.py
│   └── events.py
└── workers/
    ├── context_worker.py
    ├── ai_generation_worker.py
    ├── exercise_worker.py
    ├── playlist_worker.py
    ├── aggregation_worker.py
    └── notification_worker.py
```

### Current vs Target

| Dimension | Current | Target (Planned) |
|-----------|---------|------------------|
| Workout generation execution | In-request synchronous flow | Event-driven, multi-worker pipeline |
| First migrated endpoint | N/A | `POST /api/v1/workouts/today` |
| AI latency handling | Client waits for full generation | API returns immediately with processing status |
| Failure isolation | Failures occur inside request lifecycle | Worker-level retries and failure handling |
| Horizontal scale | API process scaling | Independent API and worker scaling |
| Pipeline tracing | Request logs only | End-to-end trace via `saga_id` and `correlation_id` |

### Planned Event Pipeline

`WorkoutPlanRequested` -> `ContextPrepared` -> `WorkoutDraftGenerated` -> (`WorkoutExercisesReady` and `PlaylistReady` in parallel) -> `WorkoutPlanCompleted`

### Compatibility and Rollout

- Synchronous behavior remains available during rollout.
- Feature flag `USE_ASYNC_WORKOUT_PIPELINE` controls opt-in cutover.
- Initial migration scope is only `POST /api/v1/workouts/today`.
- `POST /api/v1/workouts/schedule` migration is deferred to a later phase.

## Database Schema (Current)

```text
users
├── id (PK)
├── email (unique)
├── hashed_password
├── spotify_user_id (unique, nullable)
├── is_active
├── created_at
└── updated_at

profiles
├── id (PK)
├── user_id (FK)
├── name
├── age
├── fitness_goal
├── fitness_level
├── weekly_workout_days
├── workout_duration_minutes
├── preferred_genres (array)
├── favorite_workouts (array)
└── created_at

preferences
├── id (PK)
├── profile_id (FK)
├── spotify_data (JSON)
├── notifications_enabled
└── created_at

workouts
├── id (PK)
├── user_id (FK)
├── date
├── focus
├── duration_minutes
├── playlist_id (nullable)
├── playlist_name (nullable)
├── playlist_url (nullable)
├── completed
└── created_at

workout_exercises
├── workout_id (FK, PK)
├── exercise_id (FK, PK)
├── sets
├── reps
├── order
├── rest_seconds
├── completed_sets
└── weights_used (array)

exercises
├── id (PK)
├── name
├── body_part
├── target
├── secondary_muscles (array)
├── equipment
├── gif_url
└── instructions (array)

refresh_tokens
├── id (PK)
├── user_id (FK)
├── token_hash
├── expires_at
├── revoked_at
├── created_at
└── updated_at
```

## Authentication Flow

1. Registration: user creates account with email/password.
2. Login: JWT access token + refresh token are issued.
3. Spotify OAuth: user authorizes Spotify access.
4. Refresh flow: token refresh and persistence via interceptor/repository path.

## Deployment

- Container: Docker
- CI/CD: GitHub Actions
- Cloud: Google Cloud Platform (Cloud Run)

## Environment Variables

| Variable | Description |
|----------|-------------|
| `DATABASE_URI` | PostgreSQL connection string |
| `SECRET_KEY` | JWT signing key |
| `SPOTIFY_CLIENT_ID` | Spotify app client ID |
| `SPOTIFY_CLIENT_SECRET` | Spotify app client secret |
| `EXERCISE_API_KEY` | Exercise API key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiration (default: 60) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token expiration (default: 7) |
| `USE_ASYNC_WORKOUT_PIPELINE` | Feature flag for async `POST /workouts/today` path (planned) |
