from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.workout import Workout, WorkoutExercise
from app.repositories.exercise import ExerciseRepository
from app.repositories.preferences import PreferencesRepository
from app.repositories.profile import ProfileRepository
from app.repositories.workout import WorkoutRepository
from app.repositories.workout_exercise import WorkoutExerciseRepository
from app.schemas.exercise import (WorkoutExerciseCreate,
                                  WorkoutExerciseResponse,
                                  WorkoutExerciseUpdate)
from app.schemas.workout import (ScheduleRequest, ScheduleResponse,
                                 WorkoutCreate, WorkoutResponse, WorkoutUpdate)
from app.services.exercise_selector import ExerciseSelectorService
from app.services.gemini import GeminiService
from app.services.playlist_selector import PlaylistSelectorService
from app.services.scheduler import SchedulerService

# Define constants for error messages
WORKOUT_NOT_FOUND = "Workout not found"
EXERCISE_NOT_FOUND = "Exercise not found"
PROFILE_NOT_FOUND = "Profile not found"
PREFERENCES_NOT_FOUND = "Preferences not found"
NO_WORKOUT_TODAY = "No workout scheduled for today"

router = APIRouter()

@router.get("/", response_model=List[WorkoutResponse])
def read_workouts(
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all workouts for the current user.
    """
    workout_repo = WorkoutRepository(db)
    
    if start_date and end_date:
        workouts = workout_repo.get_by_date_range(getattr(current_user, "id"), start_date.date(), end_date.date())
    else:
        workouts = workout_repo.get_all_with_exercises(getattr(current_user, "id"), skip, limit)
    
    return workouts

@router.post("/suggest-workout-schedule", response_model=WorkoutResponse, status_code=status.HTTP_201_CREATED)
async def suggest_workout_schedule(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a workout with spotify playlist for the current user using AI recommendations and persist it.

    This endpoint will call the Gemini AI to generate a workout plan, then save a
    `Workout` and associated `WorkoutExercise` rows. If an exercise name returned
    by the AI doesn't exist in the `exercises` table, a minimal `Exercise` row
    will be created.
    """
    # Initialize repositories
    profile_repo = ProfileRepository(db)
    preferences_repo = PreferencesRepository(db)
    workout_repo = WorkoutRepository(db)
    exercise_repo = ExerciseRepository(db)
    
    # Load profile and preferences
    profile = profile_repo.get_by_user_id(getattr(current_user, "id"))
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PROFILE_NOT_FOUND)

    preferences = preferences_repo.get_by_profile_id(getattr(profile, "id"))
    if not preferences:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PREFERENCES_NOT_FOUND)


    # Instantiate GeminiService directly so we can pass db/current_user
    gemini_service = GeminiService(db,profile, preferences)


    try:
        ai_plan = await gemini_service.get_workout_and_playlist()
    except Exception as e:
        print(f"Error generating AI recommendations: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating AI recommendations: {str(e)}")

    # Create workout record
    playlist: Dict[str, str] = ai_plan.get("playlist") or {}
    playlist_id = playlist.get("playlist_id")
    playlist_name = playlist.get("playlist_name")
    playlist_url = playlist.get("playlist_url")

    if not playlist_url:
        print("AI did not return a playlist URL, proceeding without playlist.")
        playlist_selector = PlaylistSelectorService(db,profile, preferences)
        playlist_data = playlist_selector.select_playlist_for_workout(
            fitness_goal=profile.fitness_goal.value,
            music_genres=cast(List[str], preferences.music_genres),
            music_tempo=cast(str,preferences.music_tempo),
        )
        playlist_id = playlist_data.get("playlist_id")
        playlist_name = playlist_data.get("playlist_name")
        playlist_url = playlist_data.get("playlist_url")
        

    # Workout creation flow
    workout_plan: Dict[str, Any] = ai_plan.get("workout_plan", {})
    workout_exercises = workout_plan.get("exercises", [])
    # If workout_plan's exercises is missing or empty, use the fallback exercises selector
    
    if len(workout_exercises) == 0: 
        print("AI did not return exercises, using ExerciseSelectorService as fallback.")
        exercise_selector = ExerciseSelectorService(db)
        selected_exercises = exercise_selector.select_exercises_for_workout(
            fitness_goal=profile.fitness_goal.value,
            fitness_level=profile.fitness_level.value,
            available_equipment=cast(List[str], preferences.available_equipment),
            target_muscle_groups=cast(List[str], preferences.target_muscle_groups),
            workout_duration_minutes=cast(int, profile.workout_duration_minutes),
            recently_used_exercises=[]
        )
        workout_exercises = selected_exercises
    
    db_workout = workout_repo.create({
        "user_id": current_user.id,
        "duration_minutes": profile.workout_duration_minutes,
        "date": datetime.now(),
        "playlist_id": playlist_id,
        "playlist_name": playlist_name,
        "playlist_url": playlist_url
    })

    created_workout_exercises: List[WorkoutExercise] = []

    for idx, workout_ex in enumerate(workout_exercises):
        # Extract fields from AI response with safe fallbacks
        name = workout_ex.get("name") or workout_ex.get("exercise") 
        sets = workout_ex.get("sets") or 1
        reps = workout_ex.get("reps") or ""
        # AI may return rest in seconds; store seconds in DB
        rest_seconds = workout_ex.get("rest_seconds") if workout_ex.get("rest_seconds") is not None else 180 

        if not name:
            # Skip malformed entry
            continue

        # Find existing exercise by name (case-insensitive).
        # First try an exact case-insensitive match, then fall back to a contains match
        # (useful when AI returns slightly different spacing/casing).
        name_clean = str(name).strip()
        exercise_obj = exercise_repo.get_by_name_exact(name_clean)
        if not exercise_obj:
            results = exercise_repo.search_by_name(name_clean, limit=1)
            exercise_obj = results[0] if results else None
        if not exercise_obj:
            exercise_obj = exercise_repo.create({
                "name": name,
                "target": workout_ex.get("target") or "General",
                "body_part": workout_ex.get("body_part") or workout_ex.get("bodyPart") or "General",
                "secondary_muscles": workout_ex.get("secondary_muscles") if isinstance(workout_ex.get("secondary_muscles"), list) else None,
                "equipment": workout_ex.get("machine") or workout_ex.get("equipment") or None,
                "gif_url": workout_ex.get("gif_url") or workout_ex.get("gifUrl") or None,
                "instructions": workout_ex.get("instructions") if isinstance(workout_ex.get("instructions"), list) else None,
            })

        workout_ex_repo = WorkoutExerciseRepository(db)
        workout_ex_to_create = workout_ex_repo.create_with_composite_key(
            workout_id=getattr(db_workout, "id"),
            exercise_id=getattr(exercise_obj, "id"),
            sets=int(sets) if sets is not None else None,
            reps=str(reps) if reps is not None else None,
            order=idx + 1,
            rest_seconds=rest_seconds
        )
        created_workout_exercises.append(workout_ex_to_create)

    return db_workout

@router.post("/", response_model=WorkoutResponse, status_code=status.HTTP_201_CREATED)
def create_workout(
    workout_in: WorkoutCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new workout for the current user.
    """
    workout_repo = WorkoutRepository(db)
    workout_exercise_repo = WorkoutExerciseRepository(db)
    
    workout_data = workout_in.model_dump(exclude={"exercises"})
    workout_data["user_id"] = current_user.id
    db_workout = workout_repo.create(workout_data)

    # Add exercises if provided
    if workout_in.exercises:
        for i, exercise_in in enumerate(workout_in.exercises):
            exercise_data = exercise_in.model_dump()
            workout_exercise_repo.create_with_composite_key(
                workout_id=getattr(db_workout, "id"),
                exercise_id=exercise_data["exercise_id"],
                order=i + 1,
                sets=exercise_data.get("sets"),
                reps=exercise_data.get("reps"),
                rest_seconds=exercise_data.get("rest_seconds")
            )

    return db_workout

@router.get("/today", response_model=WorkoutResponse)
def get_today_workout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get today's workout.
    """
    workout_repo = WorkoutRepository(db)
    today = datetime.now().date()

    # Get workout for today
    workout = workout_repo.get_by_date(getattr(current_user, "id"), today)

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No workout scheduled for today"
        )

    return workout


@router.get("/{workout_id}", response_model=WorkoutResponse)
def read_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific workout by ID.
    """
    workout_repo = WorkoutRepository(db)
    workout = workout_repo.get_by_id_with_exercises(workout_id, getattr(current_user, "id"))

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_NOT_FOUND
        )

    return workout

@router.put("/{workout_id}", response_model=WorkoutResponse)
def update_workout(
    workout_id: int,
    workout_in: WorkoutUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a specific workout.
    """
    workout_repo = WorkoutRepository(db)
    workout = workout_repo.get_by_id_with_exercises(workout_id, getattr(current_user, "id"))

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_NOT_FOUND
        )

    # Update workout fields
    update_data = workout_in.model_dump(exclude_unset=True, exclude={"exercises"})
    workout = workout_repo.update(workout, update_data)
    return workout

@router.delete("/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a specific workout.
    """
    workout_repo = WorkoutRepository(db)
    workout = workout_repo.get_by_id_with_exercises(workout_id, getattr(current_user, "id"))

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_NOT_FOUND
        )

    workout_repo.delete(workout)
    return None

@router.get("/{workout_id}/exercises", response_model=List[WorkoutExerciseResponse])
def read_workout_exercises(
    workout_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all exercises for a specific workout.
    """
    workout_repo = WorkoutRepository(db)
    workout_exercise_repo = WorkoutExerciseRepository(db)
    
    # Check if workout exists and belongs to user
    workout = workout_repo.get_by_id_with_exercises(workout_id, getattr(current_user, "id"))

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_NOT_FOUND
        )

    exercises = workout_exercise_repo.get_by_workout_id(workout_id)

    return exercises

@router.post("/{workout_id}/exercises", response_model=WorkoutExerciseResponse, status_code=status.HTTP_201_CREATED)
def add_workout_exercise(
    workout_id: int,
    exercise_in: WorkoutExerciseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add an exercise to a specific workout.
    """
    workout_repo = WorkoutRepository(db)
    workout_exercise_repo = WorkoutExerciseRepository(db)
    
    # Check if workout exists and belongs to user
    workout = workout_repo.get_by_id_with_exercises(workout_id, getattr(current_user, "id"))

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_NOT_FOUND
        )

    # Get the highest order value
    exercises = workout_exercise_repo.get_by_workout_id(workout_id)

    next_order = 1
    if exercises:
        next_order = max(ex.order for ex in exercises) + 1

    # Create new exercise
    exercise_data = exercise_in.model_dump()
    db_exercise = workout_exercise_repo.create_with_composite_key(
        workout_id=workout_id,
        exercise_id=exercise_data["exercise_id"],
        order=next_order,
        sets=exercise_data.get("sets"),
        reps=exercise_data.get("reps"),
        rest_seconds=exercise_data.get("rest_seconds")
    )

    return db_exercise

@router.put("/{workout_id}/exercises/{exercise_id}", response_model=WorkoutExerciseResponse)
def update_workout_exercise(
    workout_id: int,
    exercise_id: int,
    exercise_in: WorkoutExerciseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a specific exercise in a workout.
    """
    workout_repo = WorkoutRepository(db)
    workout_exercise_repo = WorkoutExerciseRepository(db)
    
    # Check if workout exists and belongs to user
    workout = workout_repo.get_by_id_with_exercises(workout_id, getattr(current_user, "id"))

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_NOT_FOUND
        )

    # Get the exercise
    exercise = workout_exercise_repo.get_by_composite_key(workout_id, exercise_id)

    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EXERCISE_NOT_FOUND
        )

    # Update exercise fields
    update_data = exercise_in.model_dump(exclude_unset=True)
    exercise = workout_exercise_repo.update(exercise, update_data)
    return exercise

@router.delete("/{workout_id}/exercises/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workout_exercise(
    workout_id: int,
    exercise_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a specific exercise from a workout.
    """
    workout_repo = WorkoutRepository(db)
    workout_exercise_repo = WorkoutExerciseRepository(db)
    
    # Check if workout exists and belongs to user
    workout = workout_repo.get_by_id_with_exercises(workout_id, getattr(current_user, "id"))

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_NOT_FOUND
        )

    # Get the exercise
    exercise = workout_exercise_repo.get_by_composite_key(workout_id, exercise_id)

    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EXERCISE_NOT_FOUND
        )

    workout_exercise_repo.delete(exercise)
    return None

@router.post("/schedule", response_model=ScheduleResponse)
def generate_workout_schedule(
    schedule_request: Optional[ScheduleRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a weekly workout schedule based on user preferences.
    """
    profile_repo = ProfileRepository(db)
    preferences_repo = PreferencesRepository(db)
    workout_repo = WorkoutRepository(db)
    workout_exercise_repo = WorkoutExerciseRepository(db)
    
    # Get user profile
    profile = profile_repo.get_by_user_id(getattr(current_user, "id"))
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=PROFILE_NOT_FOUND
        )

    # Get user preferences
    preferences = preferences_repo.get_by_profile_id(getattr(profile, "id"))
    if not preferences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=PREFERENCES_NOT_FOUND
        )

    # Check if regenerate flag is set
    regenerate = schedule_request.regenerate if schedule_request else False

    # Check if user already has workouts for the current week
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    existing_workouts = workout_repo.get_by_date_range(getattr(current_user, "id"), start_of_week, end_of_week)

    if existing_workouts and not regenerate:
        # Return existing workouts
        return ScheduleResponse(
            workouts=cast(List[WorkoutResponse], existing_workouts),
            message="Returning existing workout schedule"
        )

    # If regenerate flag is set, delete existing workouts
    if existing_workouts and regenerate:
        for workout in existing_workouts:
            workout_repo.delete(workout)

    # Generate new workout schedule
    scheduler_service = SchedulerService(db)
    workouts_data = scheduler_service.generate_weekly_schedule(
        user_id=cast(int, current_user.id),
        available_days=cast(List[str], profile.available_days) if schedule_request else [],
        fitness_goal=profile.fitness_goal.value,
        fitness_level=profile.fitness_level.value,
        available_equipment=cast(List[str], preferences.available_equipment) if schedule_request else [],
        workout_duration_minutes=cast(int, profile.workout_duration_minutes) if schedule_request else 0
    )

    # Create workouts in the database
    created_workouts: List[Workout] = []
    for workout_data in workouts_data:
        exercises = workout_data.pop("exercises", [])

        # Create workout
        workout = workout_repo.create(workout_data)

        # Add exercises to workout
        for i, exercise_data in enumerate(exercises):
            workout_exercise_repo.create_with_composite_key(
                workout_id=getattr(workout, "id"),
                exercise_id=exercise_data["exercise_id"],
                order=i + 1,
                sets=exercise_data.get("sets"),
                reps=exercise_data.get("reps"),
                rest_seconds=exercise_data.get("rest_seconds")
            )

        created_workouts.append(workout)

    return ScheduleResponse(
        workouts=cast(List[WorkoutResponse], created_workouts),
        message="Generated new workout schedule"
    )

@router.post("/{workout_id}/exercises/{exercise_id}/swap", response_model=WorkoutExerciseResponse)
async def swap_workout_exercise(
    workout_id: int,
    exercise_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Swap an exercise in a workout with a similar one.
    """
    workout_repo = WorkoutRepository(db)
    workout_exercise_repo = WorkoutExerciseRepository(db)
    profile_repo = ProfileRepository(db)
    preferences_repo = PreferencesRepository(db)
    exercise_repo = ExerciseRepository(db)
    
    # Check if workout exists and belongs to user
    workout = workout_repo.get_by_id_with_exercises(workout_id, getattr(current_user, "id"))

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_NOT_FOUND
        )

    # Get the exercise
    workout_exercise = workout_exercise_repo.get_by_composite_key(workout_id, exercise_id)

    if not workout_exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EXERCISE_NOT_FOUND
        )

    # Get user profile and preferences
    profile = profile_repo.get_by_user_id(getattr(current_user, "id"))
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=PROFILE_NOT_FOUND
        )

    preferences = preferences_repo.get_by_profile_id(getattr(profile, "id"))
    if not preferences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=PREFERENCES_NOT_FOUND
        )

    # Get all exercises in the workout to avoid duplicates
    workout_exercises = workout_exercise_repo.get_by_workout_id(workout_id)

    recently_used_exercises_name = [ex.exercise.name for ex in workout_exercises if cast(int, ex.exercise_id) != exercise_id]
    recently_used_exercise_ids = [ex.exercise.id for ex in workout_exercises if cast(int, ex.exercise_id) != exercise_id]
    
    # Will use GeminiService to get suggestions to replace the exercise
    gemini_service = GeminiService(db,profile, preferences)
    try:
        new_exercise_data = await gemini_service.get_exercise_swap(
            current_exercise=workout_exercise.exercise,
            fitness_level=profile.fitness_level.value,
            target_muscle_groups=cast(List[str], preferences.target_muscle_groups),
            available_equipment=cast(List[str], preferences.available_equipment),
            recently_used_exercise_names=cast(List[str],recently_used_exercises_name)
        )
    except Exception as e:
        print(f"Error getting exercise swap from Gemini: {e}")
        new_exercise_data = None
    if new_exercise_data:
        # Update the exercise with the new data from Gemini
        # Find the exercise in the database by name
        new_exercise = exercise_repo.get_by_name_exact(new_exercise_data["name"])
        if not new_exercise:
            new_exercise = exercise_repo.create({
                "name": new_exercise_data["name"],
                "target": new_exercise_data.get("target", "General"),
                "body_part": new_exercise_data.get("body_part", "General"),
                "equipment": new_exercise_data.get("equipment"),
                "instructions": new_exercise_data.get("instructions"),
            })
            # Update workout exercise to point to the new exercise
            workout_exercise_repo.update(workout_exercise, {
                "exercise_id": new_exercise.id,
                "sets": new_exercise_data["sets"],
                "reps": new_exercise_data["reps"],
                "rest_seconds": new_exercise_data["rest_seconds"],
                "completed_sets": 0,
                "weights_used": []
            })
            return workout_exercise
        # Update workout exercise to point to the existing exercise
        workout_exercise_repo.update(workout_exercise, {
            "exercise_id": new_exercise.id,
            "sets": new_exercise_data["sets"],
            "reps": new_exercise_data["reps"],
            "rest_seconds": new_exercise_data["rest_seconds"],
            "completed_sets": 0,
            "weights_used": []
        })

        return workout_exercise
    else:
        print("Gemini service did not return a swap exercise, falling back to ExerciseSelectorService.")
        
    # Fallback to ExerciseSelectorService if Gemini is not available
    # Use the exercise selector service to find a replacement
        exercise_selector = ExerciseSelectorService(db)
        new_exercise_data = exercise_selector.swap_exercise(
            exercise_id=cast(int, workout_exercise.exercise_id),
            muscle_group=workout_exercise.muscle_group,
            equipment=workout_exercise.equipment,
            fitness_level=profile.fitness_level.value,
            available_equipment=cast(List[str], preferences.available_equipment),
            recently_used_exercises=cast(List[int],recently_used_exercise_ids)
        )

        # Update the exercise with the new data
        workout_exercise_repo.update(workout_exercise, {
            "exercise_id": new_exercise_data["exercise_id"],
            "name": new_exercise_data["name"],
            "description": new_exercise_data["description"],
            "muscle_group": new_exercise_data["muscle_group"],
            "equipment": new_exercise_data["equipment"],
            "sets": new_exercise_data["sets"],
            "reps": new_exercise_data["reps"],
            "rest_seconds": new_exercise_data["rest_seconds"],
            "completed_sets": 0,
            "weights_used": []
        })
        return workout_exercise


