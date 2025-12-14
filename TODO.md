# TODO

This TODO lists the work to implement Gemini fallback behavior and to refactor API endpoints to use service/repository methods.

## Tasks

1. Create this `TODO.md` with the plan. (in-progress)

2. Update `app/services/workout_selector.py` — fallback behavior
   - Detect when `app/services/gemini.py` is unavailable or returns errors.
   - Use local workout selector logic as a deterministic fallback.
   - Export a clear API (e.g., `select_workout(...)`) that endpoints can call.

3. Update `app/services/playlist_selector.py` — fallback behavior
   - Detect `gemini` unavailability and fall back to the local playlist selector.
   - Export a clear API (e.g., `select_playlist(...)`) that endpoints can call.

4. Refactor `app/api/endpoints/workouts.py` to remove direct DB queries
   - Remove any raw DB queries or session usage from the endpoint file.
   - Call exported service methods (from services and/or repositories) instead.
   - Prefer the Repository pattern: create or reuse repository classes that encapsulate DB access and export repository methods.

5. Sweep other endpoint files for DB queries and replace with service/repository methods
   - Search `app/api/endpoints/*.py` for direct DB/session usage.
   - Replace with calls to corresponding service/repository exports.

6. Run tests and linting
   - Run the test suite and fix any regressions caused by refactors.
   - Ensure formatting and lint rules are satisfied.

---

Next step: I can implement the first code changes (services fallback or endpoint refactor). Which should I start with? (I recommend starting with the service fallback changes so endpoints can call a stable exported API.)
