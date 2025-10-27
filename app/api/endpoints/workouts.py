from datetime import datetime, timedelta
from typing import  Any, Dict, List, cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.preferences import Preferences
from app.models.profile import Profile
from app.models.user import User
from app.models.workout import Exercise, Workout, WorkoutExercise
from app.schemas.exercise import (WorkoutExerciseCreate,
                                  WorkoutExerciseResponse,
                                  WorkoutExerciseUpdate)
from app.schemas.workout import (ScheduleRequest, ScheduleResponse,
                                 WorkoutCreate, WorkoutResponse,
                                 WorkoutSuggest, WorkoutUpdate)
from app.services.exercise_selector import ExerciseSelectorService
from app.services.gemini import GeminiService
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
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all workouts for the current user.
    """
    query = db.query(Workout).options(selectinload(Workout.workout_exercises).selectinload(WorkoutExercise.exercise)).filter(Workout.user_id == current_user.id)

    if start_date:
        query = query.filter(Workout.date >= start_date)
    if end_date:
        query = query.filter(Workout.date <= end_date)

    workouts = query.order_by(Workout.date.desc()).offset(skip).limit(limit).all()
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
    # Load profile and preferences
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PROFILE_NOT_FOUND)

    preferences = db.query(Preferences).filter(Preferences.profile_id == profile.id).first()
    if not preferences:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=PREFERENCES_NOT_FOUND)


    # Instantiate GeminiService directly so we can pass db/current_user
    gemini_service = GeminiService()


    try:
        ai_plan = await gemini_service.get_workout_and_playlist(profile, preferences)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating AI recommendations: {str(e)}")

    # Create workout record
    workout_plan: Dict[str, Any] = ai_plan.get("workout_plan") or {}
    playlist: Dict[str, str] = ai_plan.get("playlist") or {}
    playlist_id = playlist.get("playlist_id")
    playlist_name = playlist.get("playlist_name")
    playlist_url = playlist.get("playlist_url")

    db_workout = Workout(
        user_id=current_user.id,
        duration_minutes=profile.workout_duration_minutes,
        date=datetime.now(),
        playlist_id=playlist_id,
        playlist_name=playlist_name,
        playlist_url=playlist_url
    )

    db.add(db_workout)
    db.flush()  # get id for FK relationships

    workout_exercises = workout_plan.get("exercises", [])
    created_workout_exercises: List[WorkoutExercise] = []

    for idx, workout_ex in enumerate(workout_exercises):
        # Extract fields from AI response with safe fallbacks
        name = workout_ex.get("name") or workout_ex.get("exercise") 
        sets = workout_ex.get("sets") or 1
        reps = workout_ex.get("reps") or ""
        # AI may return rest in minutes; store seconds in DB
        rest_minutes = workout_ex.get("rest") if workout_ex.get("rest") is not None else workout_ex.get("rest_minutes")
        try:
            rest_seconds = int(float(rest_minutes) * 60) if rest_minutes is not None else None
        except Exception:
            rest_seconds = None

        if not name:
            # Skip malformed entry
            continue

        # Find existing exercise by name (case-insensitive).
        # First try an exact case-insensitive match, then fall back to a contains match
        # (useful when AI returns slightly different spacing/casing).
        name_clean = str(name).strip()
        exercise_obj = db.query(Exercise).filter(Exercise.name.ilike(name_clean)).first()
        if not exercise_obj:
            pattern = f"%{name_clean}%"
            exercise_obj = db.query(Exercise).filter(Exercise.name.ilike(pattern)).first()
        if not exercise_obj:
            exercise_obj = Exercise(
                name=name,
                target=workout_ex.get("target") or "General",
                body_part=workout_ex.get("body_part") or workout_ex.get("bodyPart") or "General",
                secondary_muscles=workout_ex.get("secondary_muscles") if isinstance(workout_ex.get("secondary_muscles"), list) else None,
                equipment=workout_ex.get("machine") or workout_ex.get("equipment") or None,
                instructions=workout_ex.get("instructions") if isinstance(workout_ex.get("instructions"), list) else None,
            )
            db.add(exercise_obj)
            db.flush()

        workout_ex_to_create = WorkoutExercise(
            workout_id=db_workout.id,
            exercise_id=exercise_obj.id,
            sets=int(sets) if sets is not None else None,
            reps=str(reps) if reps is not None else None,
            order=idx + 1,
            rest_seconds=rest_seconds
        )
        db.add(workout_ex_to_create)
        created_workout_exercises.append(workout_ex_to_create)

    # Commit everything and return the persisted workout
    db.commit()
    db.refresh(db_workout)

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
    db_workout = Workout(
        user_id=current_user.id,
        **workout_in.model_dump(exclude={"exercises"})
    )
    db.add(db_workout)
    db.commit()
    db.refresh(db_workout)

    # Add exercises if provided
    if workout_in.exercises:
        for i, exercise_in in enumerate(workout_in.exercises):
            db_exercise = WorkoutExercise(
                workout_id=db_workout.id,
                order=i + 1,
                **exercise_in.model_dump()
            )
            db.add(db_exercise)

        db.commit()
        db.refresh(db_workout)

    return db_workout

@router.get("/today", response_model=WorkoutResponse)
def get_today_workout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get today's workout.
    """
    today = datetime.now().date()

    # Get workout for today
    workout = db.query(Workout).filter(
        Workout.user_id == current_user.id,
        Workout.date >= datetime.combine(today, datetime.min.time()),
        Workout.date <= datetime.combine(today, datetime.max.time())
    ).first()

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
    workout = db.query(Workout).filter(
        Workout.id == workout_id,
        Workout.user_id == current_user.id
    ).first()

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
    workout = db.query(Workout).filter(
        Workout.id == workout_id,
        Workout.user_id == current_user.id
    ).first()

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_NOT_FOUND
        )

    # Update workout fields
    for field, value in workout_in.model_dump(exclude_unset=True, exclude={"exercises"}).items():
        setattr(workout, field, value)

    db.add(workout)
    db.commit()
    db.refresh(workout)
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
    workout = db.query(Workout).filter(
        Workout.id == workout_id,
        Workout.user_id == current_user.id
    ).first()

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_NOT_FOUND
        )

    db.delete(workout)
    db.commit()
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
    # Check if workout exists and belongs to user
    workout = db.query(Workout).filter(
        Workout.id == workout_id,
        Workout.user_id == current_user.id
    ).first()

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_NOT_FOUND
        )

    exercises = db.query(WorkoutExercise).filter(
        WorkoutExercise.workout_id == workout_id
    ).order_by(WorkoutExercise.order).all()

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
    # Check if workout exists and belongs to user
    workout = db.query(Workout).filter(
        Workout.id == workout_id,
        Workout.user_id == current_user.id
    ).first()

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_NOT_FOUND
        )

    # Get the highest order value
    last_exercise = db.query(WorkoutExercise).filter(
        WorkoutExercise.workout_id == workout_id
    ).order_by(WorkoutExercise.order.desc()).first()

    next_order = 1
    if last_exercise:
        next_order = last_exercise.order + 1

    # Create new exercise
    db_exercise = WorkoutExercise(
        workout_id=workout_id,
        order=next_order,
        **exercise_in.model_dump()
    )
    db.add(db_exercise)
    db.commit()
    db.refresh(db_exercise)

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
    # Check if workout exists and belongs to user
    workout = db.query(Workout).filter(
        Workout.id == workout_id,
        Workout.user_id == current_user.id
    ).first()

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_NOT_FOUND
        )

    # Get the exercise
    exercise = db.query(WorkoutExercise).filter(
        WorkoutExercise.id == exercise_id,
        WorkoutExercise.workout_id == workout_id
    ).first()

    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EXERCISE_NOT_FOUND
        )

    # Update exercise fields
    for field, value in exercise_in.model_dump(exclude_unset=True).items():
        setattr(exercise, field, value)

    db.add(exercise)
    db.commit()
    db.refresh(exercise)
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
    # Check if workout exists and belongs to user
    workout = db.query(Workout).filter(
        Workout.id == workout_id,
        Workout.user_id == current_user.id
    ).first()

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_NOT_FOUND
        )

    # Get the exercise
    exercise = db.query(WorkoutExercise).filter(
        WorkoutExercise.id == exercise_id,
        WorkoutExercise.workout_id == workout_id
    ).first()

    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EXERCISE_NOT_FOUND
        )

    db.delete(exercise)
    db.commit()
    return None

@router.post("/schedule", response_model=ScheduleResponse)
def generate_workout_schedule(
    schedule_request: ScheduleRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a weekly workout schedule based on user preferences.
    """
    # Get user profile
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=PROFILE_NOT_FOUND
        )

    # Get user preferences
    preferences = db.query(Preferences).filter(Preferences.profile_id == profile.id).first()
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

    existing_workouts = db.query(Workout).filter(
        Workout.user_id == current_user.id,
        Workout.date >= datetime.combine(start_of_week, datetime.min.time()),
        Workout.date <= datetime.combine(end_of_week, datetime.max.time())
    ).all()

    if existing_workouts and not regenerate:
        # Return existing workouts
        return ScheduleResponse(
            workouts=cast(List[WorkoutResponse], existing_workouts),
            message="Returning existing workout schedule"
        )

    # If regenerate flag is set, delete existing workouts
    if existing_workouts and regenerate:
        for workout in existing_workouts:
            db.delete(workout)
        db.commit()

    # Generate new workout schedule
    scheduler_service = SchedulerService(db)
    workouts_data = scheduler_service.generate_weekly_schedule(
        user_id=cast(int, current_user.id),
        available_days=cast(List[str], profile.available_days) if schedule_request else [],
        fitness_goal=profile.fitness_goal.value,
        fitness_level=profile.fitness_level.value,
        available_equipment=cast(List[str], preferences.available_equipment) if schedule_request else [],
        target_muscle_groups=cast(List[str], preferences.target_muscle_groups) if schedule_request else [],
        workout_duration_minutes=cast(int, profile.workout_duration_minutes) if schedule_request else 0
    )

    # Create workouts in the database
    created_workouts: List[Workout] = []
    for workout_data in workouts_data:
        exercises = workout_data.pop("exercises", [])

        # Create workout
        workout = Workout(**workout_data)
        db.add(workout)
        db.commit()
        db.refresh(workout)

        # Add exercises to workout
        for i, exercise_data in enumerate(exercises):
            exercise = WorkoutExercise(
                workout_id=workout.id,
                order=i + 1,
                **exercise_data
            )
            db.add(exercise)

        db.commit()
        db.refresh(workout)
        created_workouts.append(workout)

    return ScheduleResponse(
        workouts=cast(List[WorkoutResponse], created_workouts),
        message="Generated new workout schedule"
    )

@router.post("/{workout_id}/exercises/{exercise_id}/swap", response_model=WorkoutExerciseResponse)
def swap_workout_exercise(
    workout_id: int,
    exercise_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Swap an exercise in a workout with a similar one.
    """
    # Check if workout exists and belongs to user
    workout = db.query(Workout).filter(
        Workout.id == workout_id,
        Workout.user_id == current_user.id
    ).first()

    if not workout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=WORKOUT_NOT_FOUND
        )

    # Get the exercise
    exercise = db.query(WorkoutExercise).filter(
        WorkoutExercise.id == exercise_id,
        WorkoutExercise.workout_id == workout_id
    ).first()

    if not exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EXERCISE_NOT_FOUND
        )

    # Get user profile and preferences
    profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=PROFILE_NOT_FOUND
        )

    preferences = db.query(Preferences).filter(Preferences.profile_id == profile.id).first()
    if not preferences:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=PREFERENCES_NOT_FOUND
        )

    # Get all exercises in the workout to avoid duplicates
    workout_exercises = db.query(WorkoutExercise).filter(
        WorkoutExercise.workout_id == workout_id
    ).all()

    recently_used_exercises = [ex.exercise_id for ex in workout_exercises if ex.id != exercise_id]

    # Use the exercise selector service to find a replacement
    exercise_selector = ExerciseSelectorService(db)
    new_exercise_data = exercise_selector.swap_exercise(
        exercise_id=cast(int, exercise.exercise_id),
        muscle_group=exercise.muscle_group,
        equipment=exercise.equipment,
        fitness_level=profile.fitness_level.value,
        available_equipment=cast(List[str], preferences.available_equipment),
        recently_used_exercises=cast(List[int],recently_used_exercises)
    )

    # Update the exercise with the new data
    exercise.exercise_id = new_exercise_data["exercise_id"]
    exercise.name = new_exercise_data["name"]
    exercise.description = new_exercise_data["description"]
    exercise.muscle_group = new_exercise_data["muscle_group"]
    exercise.equipment = new_exercise_data["equipment"]
    exercise.sets = new_exercise_data["sets"]
    exercise.reps = new_exercise_data["reps"]
    exercise.rest_seconds = new_exercise_data["rest_seconds"]
    setattr(exercise, "completed_sets", 0)
    setattr(exercise, "weights_used", [])

    db.add(exercise)
    db.commit()
    db.refresh(exercise)

    return exercise


