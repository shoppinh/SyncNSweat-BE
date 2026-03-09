# SyncNSweat Distributed Architecture Migration Plan

## Purpose

This plan migrates workout generation from synchronous API execution to an event-driven worker pipeline using a strangler pattern.

- Existing API behavior remains available during rollout.
- Async migration starts with `POST /api/v1/workouts/today` only.
- `POST /api/v1/workouts/schedule` is intentionally deferred.

Reference architecture: [ARCHITECTURE.md](./ARCHITECTURE.md)

## Migration Strategy

The migration is implemented in 11 phases. Each phase must be independently testable and deployable.

1. Messaging Infrastructure
2. Outbox Pattern Foundation
3. Event Contract Definition
4. Async API Entry for `POST /api/v1/workouts/today`
5. Context Builder Worker
6. AI Generation Worker
7. Parallel Exercise + Playlist Workers
8. Aggregator Worker
9. Notification Worker
10. Observability and Tracing
11. Gradual Cutover and Rollback

## Scope

### In Scope

- Async pipeline for `POST /api/v1/workouts/today`
- RabbitMQ topic exchange and worker consumers
- New persistence records for pipeline progress
- Feature-flag-based cutover

### Out of Scope (for this migration wave)

- Async migration for `POST /api/v1/workouts/schedule`
- Re-architecture of unrelated endpoints
- Broker replacement (RabbitMQ remains default)

## Canonical Event Envelope

All emitted events must conform to this envelope:

```json
{
  "event_id": "uuid",
  "event_type": "WorkoutPlanRequested",
  "saga_id": "uuid",
  "correlation_id": "uuid",
  "source": "api.workouts",
  "version": 1,
  "timestamp": "2026-03-04T10:00:00Z",
  "payload": {}
}
```

Required fields:

- `event_id`: unique per published event.
- `saga_id`: shared across the full workout generation workflow.
- `correlation_id`: trace correlation across retries and services.
- `version`: schema version for backward compatibility.

## Event Types and Routing Keys

| Event Type | Routing Key | Emitted By |
|------------|-------------|------------|
| `WorkoutPlanRequested` | `workout.requested` | Outbox publisher worker (origin: API endpoint) |
| `ContextPrepared` | `workout.context.ready` | Context worker |
| `WorkoutDraftGenerated` | `workout.draft.generated` | AI worker |
| `WorkoutExercisesReady` | `workout.exercises.ready` | Exercise worker |
| `PlaylistReady` | `playlist.ready` | Playlist worker |
| `WorkoutPlanCompleted` | `workout.completed` | Aggregator worker |
| `WorkoutPlanFailed` | `workout.failed` | Any worker or aggregator |

## Persistence Additions

### `workout_requests`

Tracks client-visible status for async workout creation.

Suggested columns:

- `id` (PK)
- `user_id` (FK)
- `profile_id` (FK)
- `saga_id` (unique)
- `status` (`PENDING`, `CONTEXT_READY`, `DRAFT_READY`, `PARTIAL_READY`, `COMPLETED`, `FAILED`)
- `error_code` (nullable)
- `error_message` (nullable)
- `created_at`
- `updated_at`

### `workflow_state`

Tracks branch completion for aggregation.

Suggested columns:

- `saga_id` (PK)
- `request_id` (FK to `workout_requests.id`)
- `exercises_ready` (bool default false)
- `playlist_ready` (bool default false)
- `exercises_event_id` (nullable)
- `playlist_event_id` (nullable)
- `completed_at` (nullable)
- `updated_at`

### `outbox_events`

Tracks pending integration events that must be published to RabbitMQ.

Suggested columns:

- `id` (PK)
- `event_id` (unique)
- `routing_key`
- `exchange_name`
- `payload` (JSON/JSONB)
- `status` (`PENDING`, `FAILED`, `PUBLISHED`)
- `attempt_count`
- `next_retry_at` (nullable)
- `published_at` (nullable)
- `last_error` (nullable)
- `created_at`
- `updated_at`

## Feature Flag

`USE_ASYNC_WORKOUT_PIPELINE`

- `false` (default during migration): keep synchronous behavior.
- `true`: route `POST /api/v1/workouts/today` to async path.

## Phase Plan

### Phase 1 - Introduce Messaging Infrastructure

Goal: add RabbitMQ connectivity without changing business behavior.

Tasks:

- Add dependency: `aio-pika`.
- Create `app/messaging/` with:
  - `connection.py`
  - `publisher.py`
  - `consumer.py`
  - `events.py`
- Configure topic exchange:
  - Exchange name: `syncnsweat.events`
  - Exchange type: `topic`

Acceptance:

- API process can connect and publish a test event.
- Worker process can consume a test event from bound queue.

### Phase 2 - Implement Outbox Pattern Foundation

Goal: guarantee reliable event publication for DB-backed state changes.

Tasks:

- Add `outbox_events` table for pending integration events.
- Write outbox records in the same DB transaction as business writes (for example, `workout_requests` insert/update).
- Add outbox publisher job/worker to read unpublished outbox rows and publish to RabbitMQ.
- Mark outbox rows as published only after broker publish acknowledgement.
- Add retry fields (`attempt_count`, `next_retry_at`, `last_error`) for safe reprocessing.

Acceptance:

- API transaction can commit while event dispatch is temporarily unavailable.
- Unpublished outbox rows are eventually published once broker connectivity recovers.
- Duplicate publish attempts are guarded by idempotency key (`event_id`).

### Phase 3 - Define Event Contracts

Goal: standardize schema and serialization behavior.

Tasks:

- Define event envelope model in `app/messaging/events.py`.
- Add helper utilities for `event_id`, `saga_id`, timestamps.
- Document versioning rule (`version` field required).
- Confirm outbox payload serialization uses this exact envelope.

Acceptance:

- Contract tests validate required fields and schema shape.
- Invalid events are rejected before publish.

### Phase 4 - Convert `POST /api/v1/workouts/today` to Async Entry

Goal: API no longer executes AI generation inline when feature flag is enabled.

Tasks:

- Keep existing validation logic (auth, profile, preferences checks).
- Generate `saga_id`.
- In a single DB transaction:
  - Create `workout_requests` record with `PENDING`.
  - Create outbox row in `outbox_events` containing `WorkoutPlanRequested`.
- Do not publish to RabbitMQ directly from API endpoint.
- Return immediate response:

```json
{
  "status": "processing",
  "request_id": "...",
  "saga_id": "..."
}
```

Acceptance:

- Endpoint returns quickly without calling Gemini in-request.
- `workout_requests` and `outbox_events` are committed atomically.
- Async path returns HTTP `202` with `status`, `request_id`, and `saga_id`.
- Existing synchronous flow still works when flag is disabled.

### Phase 5 - Implement Context Builder Worker

Worker path: `app/workers/context_worker.py`

Queue/binding:

- Queue: `context-builder`
- Binding: `workout.requested`

Responsibilities:

- Consume `WorkoutPlanRequested`.
- Load profile, preferences, and workout history.
- Build normalized context payload.
- Publish `ContextPrepared`.

Failure behavior:

- Mark request `FAILED` on unrecoverable validation/data errors.
- Publish `WorkoutPlanFailed` for terminal failures.

### Phase 6 - Implement AI Generation Worker

Worker path: `app/workers/ai_generation_worker.py`

Queue/binding:

- Queue: `ai-generation`
- Binding: `workout.context.ready`

Responsibilities:

- Build Gemini prompt from context.
- Call `GeminiService`.
- Normalize output to workout draft format.
- Publish `WorkoutDraftGenerated`.

Failure behavior:

- Retry transient provider/network failures with bounded retries.
- Publish `WorkoutPlanFailed` on terminal failures.

### Phase 7 - Implement Parallel Exercise and Playlist Workers

#### Exercise Worker

Worker path: `app/workers/exercise_worker.py`

Queue/binding:

- Queue: `exercise-pipeline`
- Binding: `workout.draft.generated`

Responsibilities:

- Validate and map exercises to catalog.
- Apply sets/reps/rest normalization.
- Publish `WorkoutExercisesReady`.

#### Playlist Worker

Worker path: `app/workers/playlist_worker.py`

Queue/binding:

- Queue: `playlist-generation`
- Binding: `workout.draft.generated`

Responsibilities:

- Select playlist/tracks via Spotify logic.
- Create or attach playlist metadata.
- Publish `PlaylistReady`.

Acceptance:

- Both workers can run independently and in parallel.
- Partial branch completion is persisted for aggregation.

### Phase 8 - Implement Aggregator Worker

Worker path: `app/workers/aggregation_worker.py`

Queues/bindings:

- Queue A: bound to `workout.exercises.ready`
- Queue B: bound to `playlist.ready`

Responsibilities:

- Upsert `workflow_state` for each incoming branch event.
- Detect completion when both `exercises_ready` and `playlist_ready` are true.
- Persist finalized workout data.
- Publish `WorkoutPlanCompleted`.

Idempotency requirements:

- Reprocessing same event must not duplicate workout creation.
- Use `event_id` and saga-level uniqueness safeguards.

### Phase 9 - Implement Notification Worker

Worker path: `app/workers/notification_worker.py`

Queue/binding:

- Queue: `notification`
- Binding: `workout.completed`, `workout.failed`

Responsibilities:

- Update `workout_requests.status` to `COMPLETED` or `FAILED`.
- Store final references (e.g., created workout id) for API retrieval.
- Optionally emit websocket/push notification events.

### Phase 10 - Add Observability and Tracing

Metrics (minimum):

- `workout_pipeline_duration`
- `context_build_latency`
- `ai_generation_latency`
- `exercise_mapping_latency`
- `playlist_generation_latency`
- `pipeline_failure_count`

Tracing requirements:

- Every event must carry `saga_id` and `correlation_id`.
- Logs and metrics must include request and saga dimensions.

Acceptance:

- A single saga timeline can be reconstructed across all workers.

### Phase 11 - Gradual Cutover, Safeguards, and Rollback

Rollout:

- Keep synchronous path active while async path stabilizes.
- Enable `USE_ASYNC_WORKOUT_PIPELINE` progressively by environment.
- Monitor error rate and p95 pipeline duration before broad enablement.

Rollback:

- Disable flag to immediately restore synchronous behavior.
- No API contract break for existing clients.

## Idempotency, Retry, and Failure Policy

- Consumers must be at-least-once safe.
- Retried messages must not create duplicate workout records.
- Non-retryable failures transition request to `FAILED`.
- Retryable failures use bounded exponential backoff.

## API Contract During Migration

For `POST /api/v1/workouts/today`:

- Flag off: existing synchronous response behavior.
- Flag on: async processing response (`processing`, `request_id`, `saga_id`).

A status/read endpoint may be added in a follow-up change for request polling; this plan does not require introducing it in the first migration wave.

## Acceptance Criteria (End-to-End)

1. With feature flag enabled, `POST /api/v1/workouts/today` no longer calls Gemini inline.
2. Complete saga produces exactly one final workout artifact per request.
3. Duplicate delivery of any worker event does not duplicate final output.
4. `workout_requests.status` reaches terminal state (`COMPLETED` or `FAILED`) for every started request.
5. `saga_id` and `correlation_id` are present in all stage logs and emitted events.
6. Turning off the feature flag restores synchronous behavior immediately.
