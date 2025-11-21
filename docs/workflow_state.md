# Workflow State & Rules (STM + Rules + Log)

*This file contains the dynamic state, embedded rules, active plan, and log for the current session.*
*It is read and updated frequently by the AI during its operational loop.*

---

## State

*Holds the current status of the workflow.*

```yaml
Phase: CONSTRUCT # Current workflow phase (ANALYZE, BLUEPRINT, CONSTRUCT, VALIDATE, BLUEPRINT_REVISE)
Status: IN_PROGRESS # Current status (READY, IN_PROGRESS, BLOCKED_*, NEEDS_*, COMPLETED)
CurrentTaskID: PHASE_1_IMPLEMENTATION # Identifier for the main task being worked on
CurrentStep: FRONTEND_IMPLEMENTATION # Identifier for the specific step in the plan being executed
CurrentSubStep: ONBOARDING_FLOW # Current sub-step being implemented
```

---

## Plan

*Contains the step-by-step implementation plan generated during the BLUEPRINT phase.*

*Task: Phase 1 Implementation - Core MVP Build*

### 1. Backend Implementation

#### 1.1 User Authentication

1. Implement User Authentication Endpoints
   - Verify existing auth endpoints in `backend/app/api/endpoints/auth.py`
   - Implement or update the following endpoints:
     - `/api/v1/auth/register` - User registration
     - `/api/v1/auth/login` - User login with JWT token generation
     - `/api/v1/auth/refresh-token` - Refresh JWT token
     - `/api/v1/auth/me` - Get current user info
   - Implement proper validation and error handling

2. Enhance Security Utilities
   - Update `backend/app/core/security.py` with additional functions:
     - Password hashing and verification
     - JWT token generation and validation
     - User authentication dependencies

#### 1.2 Profile & Preferences Storage

1. Implement Profile Endpoints
   - Verify existing profile endpoints in `backend/app/api/endpoints/profiles.py`
   - Implement or update the following endpoints:
     - `/api/v1/profiles/me` - Get current user's profile
     - `/api/v1/profiles/me` (PUT) - Update current user's profile
     - `/api/v1/profiles/me/preferences` - Get user preferences
     - `/api/v1/profiles/me/preferences` (PUT) - Update user preferences

2. Implement Data Models and Schemas
   - Verify existing models in `backend/app/models/`
   - Ensure the following models are properly implemented:
     - User model with authentication fields
     - Profile model with fitness goals, level, available days, etc.
     - Preferences model with equipment, music, and exercise preferences

#### 1.3 Spotify OAuth Integration

1. Implement Spotify OAuth Flow
   - Create or update endpoints in `backend/app/api/endpoints/playlists.py`:
     - `/api/v1/playlists/spotify/auth-url` - Generate Spotify authorization URL
     - `/api/v1/playlists/spotify/callback` - Handle Spotify OAuth callback
     - `/api/v1/playlists/spotify/refresh-token` - Refresh Spotify access token

2. Implement Spotify Service
   - Create or update `backend/app/services/spotify.py`
   - Implement methods for:
     - Getting authorization URL
     - Exchanging code for access token
     - Refreshing access token
     - Fetching user's playlists
     - Searching for playlists by genre/mood

#### 1.4 Exercise Service Integration

1. Implement Exercise API Integration
   - Create or update `backend/app/services/exercise.py`
   - Implement methods for:
     - Fetching exercises by muscle group
     - Fetching exercises by equipment
     - Fetching exercise details

2. Implement Exercise Endpoints
   - Create or update endpoints in `backend/app/api/endpoints/exercises.py`:
     - `/api/v1/exercises` - Get exercises with filters
     - `/api/v1/exercises/{id}` - Get exercise details
     - `/api/v1/exercises/random` - Get random exercises based on criteria

#### 1.5 Workout Scheduling Algorithm

1. Implement Scheduling Service
   - Create `backend/app/services/scheduler.py`
   - Implement methods for:
     - Generating weekly workout split based on user preferences
     - Assigning focus areas to workout days
     - Determining workout duration

2. Implement Workout Endpoints
   - Create or update endpoints in `backend/app/api/endpoints/workouts.py`:
     - `/api/v1/workouts/schedule` - Generate a new weekly schedule
     - `/api/v1/workouts/today` - Get today's workout
     - `/api/v1/workouts/{id}` - Get specific workout
     - `/api/v1/workouts/{id}` (PUT) - Update workout (mark as completed)

#### 1.6 Exercise Rotation Logic

1. Implement Exercise Selection Service
   - Create `backend/app/services/exercise_selector.py`
   - Implement methods for:
     - Selecting exercises for a workout based on focus
     - Ensuring variety by tracking recently used exercises
     - Balancing workout difficulty based on user level

2. Implement Exercise Selection Endpoints
   - Create or update endpoints in `backend/app/api/endpoints/workouts.py`:
     - `/api/v1/workouts/{id}/exercises` - Get exercises for a workout
     - `/api/v1/workouts/{id}/exercises/{exercise_id}/swap` - Swap an exercise

#### 1.7 Music Selection Logic

1. Implement Playlist Selection Service
   - Create `backend/app/services/playlist_selector.py`
   - Implement methods for:
     - Selecting playlists based on workout type and user preferences
     - Ensuring variety by tracking recently used playlists

2. Implement Playlist Selection Endpoints
   - Create or update endpoints in `backend/app/api/endpoints/playlists.py`:
     - `/api/v1/playlists/recommend` - Get playlist recommendations
     - `/api/v1/playlists/workout/{workout_id}` - Get playlist for a workout
     - `/api/v1/playlists/workout/{workout_id}/refresh` - Get a new playlist for a workout

### 2. Frontend Implementation

#### 2.1 Authentication Screens

1. Enhance Login Screen
   - Update `mobile/app/index.tsx` to connect to backend API
   - Implement form validation
   - Add loading state and error handling
   - Store JWT token securely

2. Enhance Signup Screen
   - Update `mobile/app/signup.tsx` to connect to backend API
   - Implement form validation
   - Add loading state and error handling

3. Create Authentication Context
   - Create `mobile/contexts/AuthContext.tsx`
   - Implement authentication state management
   - Provide login, signup, and logout functions
   - Handle token refresh and persistence

#### 2.2 Onboarding Flow

1. Create Onboarding Screens
   - Create `mobile/app/onboarding/` directory
   - Implement the following screens:
     - Welcome screen (`mobile/app/onboarding/index.tsx`)
     - Goals selection (`mobile/app/onboarding/goals.tsx`)
     - Fitness level selection (`mobile/app/onboarding/level.tsx`)
     - Available days selection (`mobile/app/onboarding/days.tsx`)
     - Equipment selection (`mobile/app/onboarding/equipment.tsx`)
     - Music preferences (`mobile/app/onboarding/music.tsx`)
     - Spotify connection (`mobile/app/onboarding/spotify.tsx`)

2. Implement Onboarding Navigation
   - Create `mobile/app/onboarding/_layout.tsx`
   - Implement progress indicator
   - Add navigation between onboarding steps

3. Create Onboarding Context
   - Create `mobile/contexts/OnboardingContext.tsx`
   - Store onboarding progress and data
   - Submit data to backend on completion

#### 2.3 Dashboard/Home Screen

1. Enhance Home Screen
   - Update `mobile/app/(tabs)/index.tsx`
   - Connect to backend API to fetch:
     - Today's workout
     - Upcoming workouts
     - User stats
   - Implement pull-to-refresh
   - Add loading states and error handling

2. Create Workout Card Component
   - Create `mobile/components/WorkoutCard.tsx`
   - Display workout focus, duration, and exercises
   - Add start button with navigation to workout screen

3. Create Stats Component
   - Create `mobile/components/StatsDisplay.tsx`
   - Display workout stats (completed workouts, total minutes, streak)

#### 2.4 Exercise Detail View

1. Create Exercise Detail Screen
   - Create `mobile/app/exercise/[id].tsx`
   - Display exercise details:
     - Name and description
     - GIF/image demonstration
     - Muscle groups worked
     - Equipment needed
     - Instructions

2. Create Exercise Card Component
   - Create `mobile/components/ExerciseCard.tsx`
   - Display exercise name, sets/reps, and thumbnail
   - Add tap interaction to view details

#### 2.5 Spotify Integration

1. Implement Spotify Authentication
   - Create `mobile/services/spotify.ts`
   - Implement methods for:
     - Initiating Spotify OAuth flow
     - Handling OAuth callback
     - Checking connection status

2. Create Playlist Component
   - Create `mobile/components/PlaylistCard.tsx`
   - Display playlist cover, name, and details
   - Add play button with deep linking to Spotify app

3. Implement Playlist Refresh
   - Add refresh button to playlist component
   - Connect to backend API to get a new playlist

#### 2.6 Workout View

1. Enhance Workout Screen
   - Update `mobile/app/(tabs)/workout.tsx`
   - Connect to backend API to fetch:
     - Current workout details
     - Workout history
   - Implement tab navigation between upcoming and completed workouts

2. Create Active Workout Screen
   - Create `mobile/app/workout/active/[id].tsx`
   - Display current workout exercises
   - Implement exercise completion tracking
   - Add rest timer
   - Display selected playlist
   - Add workout completion button

#### 2.7 Settings Screen

1. Create Settings Screen
   - Create `mobile/app/(tabs)/settings.tsx`
   - Implement the following settings:
     - Profile information
     - Workout preferences
     - Spotify connection status
     - Logout button

2. Create Profile Edit Screen
   - Create `mobile/app/settings/profile.tsx`
   - Allow editing of user profile information
   - Connect to backend API to update profile

3. Create Preferences Edit Screen
   - Create `mobile/app/settings/preferences.tsx`
   - Allow editing of workout and music preferences
   - Connect to backend API to update preferences

### 3. Integration and Testing

#### 3.1 API Integration

1. Create API Service
   - Create `mobile/services/api.ts`
   - Implement base API client with authentication
   - Add methods for all required API endpoints

2. Implement Error Handling
   - Create `mobile/services/error.ts`
   - Implement error handling and formatting
   - Add retry logic for network failures

#### 3.2 Testing

1. Backend Tests
   - Write unit tests for all new services
   - Write API tests for all new endpoints
   - Ensure test coverage for critical paths

2. Frontend Tests
   - Write component tests for new components
   - Write screen tests for new screens
   - Test authentication flow

#### 3.3 Documentation

1. Update API Documentation
   - Ensure all endpoints are documented with Swagger/OpenAPI
   - Add examples and response schemas

2. Update README
   - Add information about new features
   - Update setup instructions if needed

### 4. Deployment

1. Prepare for Deployment
   - Update environment configuration
   - Ensure all secrets are properly managed
   - Verify database migrations

2. Deploy Backend
   - Deploy backend API to development environment
   - Verify all endpoints are working

3. Build Mobile App
   - Configure app for development environment
   - Build development version of the app

*Previous Task: Unit Tests Setup*

### Frontend Unit Tests Setup

1. Configure Jest testing environment for Expo
   - Verify Jest is already installed in the project
   - Create or update Jest configuration in `jest.config.js`:
     ```javascript
     module.exports = {
       preset: 'jest-expo',
       transformIgnorePatterns: [
         'node_modules/(?!((jest-)?react-native|@react-native(-community)?)|expo(nent)?|@expo(nent)?/.*|@expo-google-fonts/.*|react-navigation|@react-navigation/.*|@unimodules/.*|unimodules|sentry-expo|native-base|react-native-svg)'
       ],
       setupFilesAfterEnv: ['@testing-library/jest-native/extend-expect'],
       moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx'],
       collectCoverage: true,
       collectCoverageFrom: [
         '**/*.{js,jsx,ts,tsx}',
         '!**/coverage/**',
         '!**/node_modules/**',
         '!**/babel.config.js',
         '!**/jest.setup.js'
       ]
     };
     ```
   - Create a setup file for Jest in `__tests__/setup.js`:
     ```javascript
     import 'react-native-gesture-handler/jestSetup';

     jest.mock('react-native-reanimated', () => {
       const Reanimated = require('react-native-reanimated/mock');
       Reanimated.default.call = () => {};
       return Reanimated;
     });

     jest.mock('expo-router', () => ({
       useRouter: () => ({
         replace: jest.fn(),
         push: jest.fn(),
         back: jest.fn(),
       }),
       useLocalSearchParams: () => ({}),
       Link: 'Link',
       router: {
         replace: jest.fn(),
         push: jest.fn(),
         back: jest.fn(),
       },
     }));

     jest.mock('@react-native-async-storage/async-storage', () =>
       require('@react-native-async-storage/async-storage/jest/async-storage-mock')
     );
     ```

2. Create test directory structure
   - Create `__tests__` directory in the root of the SyncSweatApp directory if it doesn't exist
   - Create subdirectories for different test categories:
     - `__tests__/components` - For component tests
     - `__tests__/screens` - For screen tests
     - `__tests__/hooks` - For custom hook tests
     - `__tests__/utils` - For utility function tests

3. Install additional testing dependencies
   - Install React Testing Library: `npm install --save-dev @testing-library/react-native @testing-library/jest-native`
   - Install Mock dependencies: `npm install --save-dev jest-fetch-mock react-native-gesture-handler/jestSetup @react-native-async-storage/async-storage/jest/async-storage-mock`

4. Create basic component tests
   - Create a test for the main App component in `__tests__/App-test.tsx`:
     ```typescript
     import React from 'react';
     import { render } from '@testing-library/react-native';
     import App from '../app/_layout';

     jest.mock('expo-router');
     jest.mock('expo-linking');
     jest.mock('expo-constants', () => ({
       expoConfig: {
         extra: {
           apiUrl: 'https://test-api.example.com',
         },
       },
     }));

     describe('<App />', () => {
       it('renders correctly', () => {
         const { toJSON } = render(<App />);
         expect(toJSON()).toBeTruthy();
       });
     });
     ```

5. Create tests for the login screen
   - Create a test for the login screen in `__tests__/screens/LoginScreen-test.tsx`:
     ```typescript
     import React from 'react';
     import { render, fireEvent, waitFor } from '@testing-library/react-native';
     import LoginScreen from '../../app/index';

     jest.mock('expo-router', () => ({
       useRouter: () => ({
         replace: jest.fn(),
         push: jest.fn(),
       }),
       router: {
         replace: jest.fn(),
         push: jest.fn(),
       },
     }));

     describe('<LoginScreen />', () => {
       it('renders correctly', () => {
         const { getByText, getByPlaceholderText } = render(<LoginScreen />);

         expect(getByText('Sync & Sweat')).toBeTruthy();
         expect(getByText('Login to your account')).toBeTruthy();
         expect(getByPlaceholderText('Email')).toBeTruthy();
         expect(getByPlaceholderText('Password')).toBeTruthy();
         expect(getByText('Login')).toBeTruthy();
       });

       it('shows error when submitting empty form', () => {
         const { getByText } = render(<LoginScreen />);

         fireEvent.press(getByText('Login'));

         expect(getByText('Please enter email and password')).toBeTruthy();
       });

       it('navigates to main screen on successful login', async () => {
         const { getByText, getByPlaceholderText } = render(<LoginScreen />);

         fireEvent.changeText(getByPlaceholderText('Email'), 'test@example.com');
         fireEvent.changeText(getByPlaceholderText('Password'), 'password123');
         fireEvent.press(getByText('Login'));

         await waitFor(() => {
           expect(require('expo-router').router.replace).toHaveBeenCalledWith('/(tabs)/index');
         });
       });
     });
     ```

6. Create a run script for frontend tests
   - Create a `run_tests.bat` file in the SyncSweatApp directory for Windows:
     ```batch
     @echo off
     cd /d "%~dp0"
     npm test
     ```
   - Create a `run_tests.sh` file in the SyncSweatApp directory for Unix/Mac:
     ```bash
     #!/bin/bash
     cd "$(dirname "$0")"
     npm test
     ```
   - Make the shell script executable: `chmod +x SyncSweatApp/run_tests.sh`

### Backend Unit Tests Setup

1. Configure pytest for the backend
   - Verify pytest is already installed in the virtual environment
   - Install additional testing dependencies: `pip install pytest-cov httpx`
   - Create a pytest configuration file in `backend/pytest.ini`:
     ```ini
     [pytest]
     testpaths = tests
     python_files = test_*.py
     python_functions = test_*
     python_classes = Test*
     addopts = --cov=app --cov-report=term-missing
     ```
   - Create a `.coveragerc` file in the backend directory:
     ```ini
     [run]
     source = app
     omit =
         */tests/*
         */migrations/*
         */alembic/*

     [report]
     exclude_lines =
         pragma: no cover
         def __repr__
         raise NotImplementedError
         if __name__ == .__main__.:
         pass
         raise ImportError
     ```

2. Create test directory structure
   - Verify the `backend/tests` directory exists
   - Create an `__init__.py` file in the tests directory if it doesn't exist
   - Create a `conftest.py` file for shared test fixtures:
     ```python
     import pytest
     from fastapi.testclient import TestClient
     from sqlalchemy import create_engine
     from sqlalchemy.orm import sessionmaker
     from sqlalchemy.pool import StaticPool

     from app.main import app
     from app.db.session import Base, get_db

     # Use in-memory SQLite for tests
     SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

     engine = create_engine(
         SQLALCHEMY_DATABASE_URL,
         connect_args={"check_same_thread": False},
         poolclass=StaticPool,
     )
     TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

     @pytest.fixture(scope="function")
     def test_db():
         Base.metadata.create_all(bind=engine)
         try:
             db = TestingSessionLocal()
             yield db
         finally:
             db.close()
             Base.metadata.drop_all(bind=engine)

     @pytest.fixture(scope="function")
     def client(test_db):
         def override_get_db():
             try:
                 yield test_db
             finally:
                 test_db.close()

         app.dependency_overrides[get_db] = override_get_db
         with TestClient(app) as c:
             yield c
         app.dependency_overrides = {}
     ```

3. Create API endpoint tests
   - Update the existing `test_api.py` file to use the fixtures:
     ```python
     import pytest
     from fastapi.testclient import TestClient

     def test_root_endpoint(client):
         """Test that the root endpoint returns a welcome message."""
         response = client.get("/")
         assert response.status_code == 200
         assert "Welcome to" in response.json()["message"]

     def test_api_docs(client):
         """Test that the API documentation is accessible."""
         response = client.get("/docs")
         assert response.status_code == 200
         assert "text/html" in response.headers["content-type"]
     ```

4. Create model tests
   - Create a test file for the User model in `backend/tests/test_models.py`:
     ```python
     import pytest
     from app.models.user import User

     def test_user_model(test_db):
         """Test creating a User model instance."""
         user = User(
             email="test@example.com",
             hashed_password="hashed_password",
             is_active=True
         )
         test_db.add(user)
         test_db.commit()

         db_user = test_db.query(User).filter(User.email == "test@example.com").first()
         assert db_user is not None
         assert db_user.email == "test@example.com"
         assert db_user.hashed_password == "hashed_password"
         assert db_user.is_active is True
     ```

5. Create service tests
   - Create a test file for the Spotify service in `backend/tests/test_spotify_service.py`:
     ```python
     import pytest
     from unittest.mock import patch, MagicMock
     from app.services.spotify import SpotifyService

     @pytest.fixture
     def spotify_service():
         return SpotifyService()

     def test_get_auth_url(spotify_service):
         """Test generating the Spotify authorization URL."""
         redirect_uri = "http://localhost:8000/callback"
         auth_url = spotify_service.get_auth_url(redirect_uri)

         assert "client_id=" in auth_url
         assert "response_type=code" in auth_url
         assert f"redirect_uri={redirect_uri}" in auth_url
         assert "scope=" in auth_url

     @patch('requests.post')
     def test_get_access_token(mock_post, spotify_service):
         """Test getting an access token from Spotify."""
         # Mock the response from the Spotify API
         mock_response = MagicMock()
         mock_response.json.return_value = {
             "access_token": "test_access_token",
             "token_type": "Bearer",
             "expires_in": 3600,
             "refresh_token": "test_refresh_token"
         }
         mock_post.return_value = mock_response

         # Call the method
         code = "test_code"
         redirect_uri = "http://localhost:8000/callback"
         result = spotify_service.get_access_token(code, redirect_uri)

         # Check the result
         assert result["access_token"] == "test_access_token"
         assert result["token_type"] == "Bearer"
         assert result["expires_in"] == 3600
         assert result["refresh_token"] == "test_refresh_token"
     ```

6. Create a run script for backend tests
   - Update the existing `run_tests.bat` file in the backend directory for Windows:
     ```batch
     @echo off
     REM Navigate to the backend directory
     cd /d "%~dp0"

     REM Activate the virtual environment
     call venv\Scripts\activate

     REM Install test dependencies if needed
     pip install httpx pytest pytest-cov

     REM Run the tests
     python -m pytest tests/ --cov=app

     REM Check the exit code
     if %ERRORLEVEL% EQU 0 (
       echo ✅ All tests passed!
     ) else (
       echo ❌ Some tests failed.
     )
     ```
   - Update the existing `run_tests.sh` file in the backend directory for Unix/Mac:
     ```bash
     #!/bin/bash

     # Navigate to the backend directory
     cd "$(dirname "$0")"

     # Activate the virtual environment
     source venv/bin/activate

     # Install test dependencies if needed
     pip install httpx pytest pytest-cov

     # Run the tests
     python -m pytest tests/ --cov=app

     # Check the exit code
     if [ $? -eq 0 ]; then
       echo "✅ All tests passed!"
     else
       echo "❌ Some tests failed."
     fi
     ```
   - Make the shell script executable: `chmod +x backend/run_tests.sh`

### Documentation Update

1. Update the TESTING.md file
   - Update the existing TESTING.md file with comprehensive instructions:
     ```markdown
     # Testing Guide for Sync & Sweat

     This document provides instructions on how to run tests for both the frontend and backend components of the Sync & Sweat application.

     ## Frontend Tests

     The frontend tests verify that the React Native components render correctly and that the navigation works as expected.

     ### Running Frontend Tests

     1. Navigate to the SyncSweatApp directory:
        ```
        cd SyncSweatApp
        ```

     2. Install dependencies (if not already installed):
        ```
        npm install
        ```

     3. Run the tests:
        ```
        npm test
        ```

        Or use the provided scripts:
        - On Windows: `run_tests.bat`
        - On Unix/Mac: `./run_tests.sh` (make sure it's executable with `chmod +x run_tests.sh`)

     ### What's Being Tested

     - **App.test.tsx**: Verifies that the main App component renders without crashing
     - **LoginScreen.test.tsx**: Tests the login screen rendering and navigation
     - **Components**: Tests for individual UI components

     ## Backend Tests

     The backend tests verify that the FastAPI endpoints are working correctly and that the database models function as expected.

     ### Running Backend Tests

     1. Navigate to the backend directory:
        ```
        cd backend
        ```

     2. Activate the virtual environment:
        ```
        # On Windows
        venv\Scripts\activate

        # On Unix
        source venv/bin/activate
        ```

     3. Install test dependencies:
        ```
        pip install httpx pytest pytest-cov
        ```

     4. Run the tests:
        ```
        python -m pytest tests/ --cov=app
        ```

        Or use the provided scripts:
        - On Windows: `run_tests.bat`
        - On Unix/Mac: `./run_tests.sh` (make sure it's executable with `chmod +x run_tests.sh`)

     ### What's Being Tested

     - **test_api.py**: Tests the API endpoints
     - **test_models.py**: Tests the database models
     - **test_spotify_service.py**: Tests the Spotify integration
     - **test_exercise_service.py**: Tests the Exercise API integration

     ## Continuous Integration

     The project uses GitHub Actions for continuous integration. The workflows are defined in:

     - `.github/workflows/frontend.yml` for the frontend
     - `.github/workflows/backend.yml` for the backend

     These workflows run automatically on pushes to the main branch and pull requests.

     ## Troubleshooting

     ### Frontend Issues

     - If you encounter dependency issues, try reinstalling the dependencies:
       ```
       npm install --legacy-peer-deps
       ```

     - For React Navigation issues, ensure you have the correct versions:
       ```
       npm install @react-navigation/native@6.1.14 @react-navigation/native-stack@6.9.22 @react-navigation/bottom-tabs@6.5.16
       ```

     - For safe area context issues, install the specific version:
       ```
       npm install react-native-safe-area-context@4.8.2
       ```

     ### Backend Issues

     - If you encounter database connection issues, ensure PostgreSQL is running and the connection string in `.env` is correct.

     - If you encounter module import errors, ensure you're running the commands from the correct directory and that the virtual environment is activated.

     - For test database issues, the tests use an in-memory SQLite database by default. If you need to use PostgreSQL for testing, update the `conftest.py` file.
     ```

*Task: Phase 0 - Foundation & Setup*

### Environment Setup
1. Install Node.js and npm/yarn for React Native development
   - Download and install Node.js LTS version (v20.x or later) from nodejs.org
   - Verify installation with `node -v` and `npm -v`
   - Install Yarn globally with `npm install -g yarn` (optional but recommended)
   - Verify Yarn installation with `yarn -v`

2. Install Python and pip/conda for FastAPI backend
   - Verify installation with `python --version`
   - If not installed, Download and install Python 3.11+ from python.org
   - Ensure pip is installed and updated with `python -m pip install --upgrade pip`
   - Create a virtual environment with `python -m venv venv`
   - Activate virtual environment (Windows: `venv\Scripts\activate`, Unix: `source venv/bin/activate`)

3. Install PostgreSQL for database
   - Download and install PostgreSQL 13+ from postgresql.org
   - Set a secure password for the postgres user during installation
   - Verify installation with `psql --version`
   - Create a new database for the project with `createdb syncnsweat`

4. Set up VS Code with relevant extensions for React Native and Python development
   - Install VS Code from code.visualstudio.com
   - Install Python extension for VS Code
   - Install ESLint and Prettier extensions for JavaScript/TypeScript
   - Install React Native Tools extension
   - Install SQLTools extension for PostgreSQL integration
   - Configure workspace settings for consistent formatting

### Project Initialization
1. Create React Native project using Expo with TypeScript
   - Navigate to desired directory: `cd c:\Dev\kien.mac\syncnsweat`
   - Create Expo project with TypeScript: `npx create-expo-app SyncSweatApp --template expo-template-blank-typescript`
   - Verify project creation by navigating to the directory: `cd SyncSweatApp`
   - Install Expo SDK: `npx expo install expo-dev-client`
   - Test the app with: `npx expo start`

2. Set up Python backend project structure with FastAPI
   - Create a backend directory: `mkdir backend && cd backend`
   - Activate virtual environment if not already active
   - Install FastAPI and dependencies: `pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary python-dotenv`
   - Create basic directory structure:
     ```
     backend/
     ├── app/
     │   ├── __init__.py
     │   ├── main.py
     │   ├── api/
     │   │   ├── __init__.py
     │   │   └── endpoints/
     │   ├── core/
     │   │   ├── __init__.py
     │   │   └── config.py
     │   ├── db/
     │   │   ├── __init__.py
     │   │   └── session.py
     │   └── models/
     │       └── __init__.py
     ├── requirements.txt
     └── .env
     ```
   - Create a basic FastAPI app in `app/main.py`
   - Create a requirements.txt file with all dependencies

3. Initialize Git repository
   - Navigate to project root: `cd c:\Dev\kien.mac\syncnsweat`
   - Initialize Git repository: `git init`
   - Create .gitignore file with appropriate entries for React Native and Python
   - Make initial commit: `git add . && git commit -m "Initial project setup"`

4. Create initial README.md with project overview
   - Create README.md file with project name, description, and setup instructions
   - Include sections for frontend and backend setup
   - Add information about required environment variables
   - Include basic usage instructions

### Database Setup
1. Create initial PostgreSQL database
   - Connect to PostgreSQL: `psql -U postgres`
   - Create database: `CREATE DATABASE syncnsweat;`
   - Create a dedicated user: `CREATE USER syncnsweat_user WITH PASSWORD 'secure_password';`
   - Grant privileges: `GRANT ALL PRIVILEGES ON DATABASE syncnsweat TO syncnsweat_user;`
   - Verify connection with new user: `psql -U syncnsweat_user -d syncnsweat`

2. Choose and set up ORM (SQLAlchemy)
   - Ensure SQLAlchemy is installed: `pip install sqlalchemy`
   - Create database connection module in `app/db/session.py`:
     ```python
     from sqlalchemy import create_engine
     from sqlalchemy.ext.declarative import declarative_base
     from sqlalchemy.orm import sessionmaker
     from app.core.config import settings

     engine = create_engine(settings.DATABASE_URI)
     SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
     Base = declarative_base()

     def get_db():
         db = SessionLocal()
         try:
             yield db
         finally:
             db.close()
     ```
   - Create configuration module in `app/core/config.py` for database URI

3. Set up migration tool (Alembic)
   - Install Alembic: `pip install alembic`
   - Initialize Alembic: `alembic init migrations`
   - Configure Alembic to use SQLAlchemy models
   - Update `alembic.ini` with database connection string
   - Create initial migration script: `alembic revision --autogenerate -m "Initial tables"`

4. Design initial core schema (Users, Profiles, Basic Preferences)
   - Create User model in `app/models/user.py`:
     ```python
     from sqlalchemy import Boolean, Column, Integer, String, DateTime
     from sqlalchemy.sql import func
     from app.db.session import Base

     class User(Base):
         __tablename__ = "users"

         id = Column(Integer, primary_key=True, index=True)
         email = Column(String, unique=True, index=True)
         hashed_password = Column(String)
         is_active = Column(Boolean, default=True)
         created_at = Column(DateTime(timezone=True), server_default=func.now())
         updated_at = Column(DateTime(timezone=True), onupdate=func.now())
     ```
   - Create Profile model in `app/models/profile.py`
   - Create Preferences model in `app/models/preferences.py`
   - Define relationships between models
   - Run migration: `alembic upgrade head`

### API Setup
1. Set up basic FastAPI app structure
   - Create main FastAPI application in `app/main.py`:
     ```python
     from fastapi import FastAPI
     from app.api.endpoints import router as api_router
     from app.core.config import settings

     app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

     app.include_router(api_router, prefix=settings.API_V1_STR)

     @app.get("/")
     def root():
         return {"message": "Welcome to Sync & Sweat API"}

     if __name__ == "__main__":
         import uvicorn
         uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
     ```
   - Create configuration in `app/core/config.py`:
     ```python
     from pydantic import BaseSettings
     from typing import Optional
     import os
     from dotenv import load_dotenv

     load_dotenv()

     class Settings(BaseSettings):
         PROJECT_NAME: str = "Sync & Sweat"
         VERSION: str = "0.1.0"
         API_V1_STR: str = "/api/v1"
         SECRET_KEY: str = os.getenv("SECRET_KEY", "development_secret_key")
         DATABASE_URI: str = os.getenv("DATABASE_URI", "postgresql://syncnsweat_user:secure_password@localhost/syncnsweat")
         ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days

     settings = Settings()
     ```

2. Implement REST API design principles
   - Create API router in `app/api/endpoints/__init__.py`:
     ```python
     from fastapi import APIRouter
     from app.api.endpoints import users, auth, profiles, workouts, playlists

     router = APIRouter()

     router.include_router(auth.router, prefix="/auth", tags=["auth"])
     router.include_router(users.router, prefix="/users", tags=["users"])
     router.include_router(profiles.router, prefix="/profiles", tags=["profiles"])
     router.include_router(workouts.router, prefix="/workouts", tags=["workouts"])
     router.include_router(playlists.router, prefix="/playlists", tags=["playlists"])
     ```
   - Create placeholder endpoint modules (e.g., `users.py`, `auth.py`, etc.)
   - Implement consistent response models and error handling

3. Set up basic API routing
   - Create a basic users endpoint in `app/api/endpoints/users.py`:
     ```python
     from fastapi import APIRouter, Depends, HTTPException
     from sqlalchemy.orm import Session
     from app.db.session import get_db

     router = APIRouter()

     @router.get("/")
     def get_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
         return {"message": "List of users will be returned here"}

     @router.get("/{user_id}")
     def get_user(user_id: int, db: Session = Depends(get_db)):
         return {"message": f"User with ID {user_id} will be returned here"}
     ```
   - Create similar placeholder endpoints for other resources

4. Create initial API documentation
   - FastAPI automatically generates OpenAPI documentation
   - Add detailed docstrings to all endpoints
   - Create a `docs/api.md` file with API overview and usage examples
   - Document authentication flow and required headers
   - Include example requests and responses

### External Services Integration
1. Register app on Spotify Developer Dashboard
   - Visit [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/)
   - Create a new account if needed
   - Click "Create an App" and fill in the required information:
     - App name: "Sync & Sweat"
     - App description: "A fitness app that generates personalized workout schedules and music playlists"
     - Website: Can be left blank for development
     - Redirect URI: Set to `http://localhost:8000/api/v1/auth/spotify/callback` for local development
   - Accept the terms and conditions

2. Obtain Spotify Client ID & Client Secret
   - After creating the app, note down the Client ID displayed on the dashboard
   - Click "Show Client Secret" to reveal and note down the Client Secret
   - Store these securely in the `.env` file:
     ```
     SPOTIFY_CLIENT_ID=your_client_id_here
     SPOTIFY_CLIENT_SECRET=your_client_secret_here
     ```

3. Test basic OAuth connection locally
   - Create a Spotify service module in `app/services/spotify.py`:
     ```python
     import base64
     import requests
     from app.core.config import settings

     class SpotifyService:
         def __init__(self):
             self.client_id = settings.SPOTIFY_CLIENT_ID
             self.client_secret = settings.SPOTIFY_CLIENT_SECRET
             self.auth_url = "https://accounts.spotify.com/authorize"
             self.token_url = "https://accounts.spotify.com/api/token"
             self.api_base_url = "https://api.spotify.com/v1"

         def get_auth_url(self, redirect_uri, state=None):
             params = {
                 "client_id": self.client_id,
                 "response_type": "code",
                 "redirect_uri": redirect_uri,
                 "scope": "user-read-private user-read-email playlist-read-private playlist-read-collaborative"
             }
             if state:
                 params["state"] = state

             auth_url = f"{self.auth_url}?" + "&".join([f"{k}={v}" for k, v in params.items()])
             return auth_url

         def get_access_token(self, code, redirect_uri):
             auth_header = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
             headers = {
                 "Authorization": f"Basic {auth_header}",
                 "Content-Type": "application/x-www-form-urlencoded"
             }
             data = {
                 "grant_type": "authorization_code",
                 "code": code,
                 "redirect_uri": redirect_uri
             }

             response = requests.post(self.token_url, headers=headers, data=data)
             return response.json()
     ```
   - Create a simple test endpoint in `app/api/endpoints/auth.py` to test the OAuth flow

3. Obtain API keys for chosen Exercise API
   - Sign up for the selected Exercise API service
   - Generate API keys as required by the service
   - Store the API key securely in the `.env` file:
     ```
     EXERCISE_API_KEY=your_api_key_here
     EXERCISE_API_HOST=api_host_if_required
     ```

4. Test basic API calls to understand data structure
   - Create an Exercise service module in `app/services/exercise.py`:
     ```python
     import requests
     from app.core.config import settings

     class ExerciseService:
         def __init__(self):
             self.api_key = settings.EXERCISE_API_KEY
             self.api_host = settings.EXERCISE_API_HOST
             self.api_url = "https://exercisedb.p.rapidapi.com"  # Example for ExerciseDB

         def get_exercises_from_external_source(self, params=None):
             headers = {
                 "X-RapidAPI-Key": self.api_key,
                 "X-RapidAPI-Host": self.api_host
             }

             response = requests.get(f"{self.api_url}/exercises", headers=headers, params=params)
             return response.json()

         def get_exercise_by_id_from_external_source((self, exercise_id):
             headers = {
                 "X-RapidAPI-Key": self.api_key,
                 "X-RapidAPI-Host": self.api_host
             }

             response = requests.get(f"{self.api_url}/exercises/exercise/{exercise_id}", headers=headers)
             return response.json()

         def get_exercises_by_muscle_from_external_source(self, muscle):
             headers = {
                 "X-RapidAPI-Key": self.api_key,
                 "X-RapidAPI-Host": self.api_host
             }

             response = requests.get(f"{self.api_url}/exercises/target/{muscle}", headers=headers)
             return response.json()
     ```
   - Create a simple test script to verify API functionality
   - Document the data structure and available endpoints

### Basic CI/CD
1. Set up GitHub Actions for linting/testing on pushes
   - Create a `.github/workflows` directory in the project root
   - Create a workflow file for the frontend in `.github/workflows/frontend.yml`:
     ```yaml
     name: Frontend CI

     on:
       push:
         branches: [ main ]
         paths:
           - 'SyncSweatApp/**'
       pull_request:
         branches: [ main ]
         paths:
           - 'SyncSweatApp/**'

     jobs:
       build:
         runs-on: ubuntu-latest

         steps:
         - uses: actions/checkout@v2
         - name: Use Node.js
           uses: actions/setup-node@v4
           with:
             node-version: '20.x'
             cache: 'npm'
             cache-dependency-path: SyncSweatApp/package-lock.json

         - name: Install dependencies
           run: cd SyncSweatApp && npm install

         - name: Install Expo CLI
           run: npm install -g expo-cli

         - name: Lint
           run: cd SyncSweatApp && npm run lint

         - name: TypeScript check
           run: cd SyncSweatApp && npx tsc --noEmit

         - name: Run tests
           run: cd SyncSweatApp && npm test
     ```
   - Create a workflow file for the backend in `.github/workflows/backend.yml`:
     ```yaml
     name: Backend CI

     on:
       push:
         branches: [ main ]
         paths:
           - 'backend/**'
       pull_request:
         branches: [ main ]
         paths:
           - 'backend/**'

     jobs:
       build:
         runs-on: ubuntu-latest

         services:
           postgres:
             image: postgres:13
             env:
               POSTGRES_USER: postgres
               POSTGRES_PASSWORD: postgres
               POSTGRES_DB: test_db
             ports:
               - 5432:5432
             options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5

         steps:
         - uses: actions/checkout@v2
         - name: Set up Python
           uses: actions/setup-python@v5
           with:
             python-version: '3.9'
             cache: 'pip'
             cache-dependency-path: backend/requirements.txt

         - name: Install dependencies
           run: |
             cd backend
             python -m pip install --upgrade pip
             pip install -r requirements.txt
             pip install pytest pytest-cov flake8

         - name: Lint with flake8
           run: |
             cd backend
             flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

         - name: Test with pytest
           run: |
             cd backend
             pytest --cov=app
           env:
             DATABASE_URI: postgresql://postgres:postgres@localhost:5432/test_db
             SECRET_KEY: test_secret_key
     ```

2. Configure basic testing framework for both frontend and backend
   - Set up Jest for Expo frontend testing:
     - Install Jest and related dependencies: `cd SyncSweatApp && npx expo install jest-expo jest @testing-library/react-native @testing-library/jest-native`
     - Create a basic Jest configuration in `SyncSweatApp/jest.config.js` using the Expo preset
     - Add test script to `package.json`: `"test": "jest --watchAll"`
     - Create a sample test file in `SyncSweatApp/__tests__/App-test.tsx`
   - Set up pytest for Python backend testing:
     - Install pytest and related dependencies: `cd backend && pip install pytest pytest-cov`
     - Create a `backend/tests` directory with `__init__.py`
     - Create a `backend/tests/conftest.py` file with test fixtures
     - Create sample test files for API endpoints and services
     - Add a `.coveragerc` file to configure coverage reporting

### Technology Decisions
1. Select navigation library (React Navigation with Expo)
   - Install React Navigation: `cd SyncSweatApp && npx expo install @react-navigation/native`
   - Install dependencies: `npx expo install react-native-screens react-native-safe-area-context`
   - Install navigation stack: `npx expo install @react-navigation/native-stack @react-navigation/bottom-tabs`
   - Create a basic navigation structure in `SyncSweatApp/src/navigation/index.tsx`:
     ```tsx
     import React from 'react';
     import { NavigationContainer } from '@react-navigation/native';
     import { createNativeStackNavigator } from '@react-navigation/native-stack';
     import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';

     // Import screens
     import LoginScreen from '../screens/LoginScreen';
     import SignupScreen from '../screens/SignupScreen';
     import HomeScreen from '../screens/HomeScreen';
     import ProfileScreen from '../screens/ProfileScreen';
     import WorkoutScreen from '../screens/WorkoutScreen';

     const Stack = createNativeStackNavigator();
     const Tab = createBottomTabNavigator();

     const MainTabs = () => {
       return (
         <Tab.Navigator>
           <Tab.Screen name="Home" component={HomeScreen} />
           <Tab.Screen name="Workout" component={WorkoutScreen} />
           <Tab.Screen name="Profile" component={ProfileScreen} />
         </Tab.Navigator>
       );
     };

     const AppNavigator = () => {
       return (
         <NavigationContainer>
           <Stack.Navigator initialRouteName="Login">
             <Stack.Screen name="Login" component={LoginScreen} options={{ headerShown: false }} />
             <Stack.Screen name="Signup" component={SignupScreen} options={{ headerShown: false }} />
             <Stack.Screen name="Main" component={MainTabs} options={{ headerShown: false }} />
           </Stack.Navigator>
         </NavigationContainer>
       );
     };

     export default AppNavigator;
     ```

2. Choose state management approach (Context API, Redux Toolkit, or Zustand)
   - Evaluate options:
     - Context API: Built into React, simpler for smaller apps
     - Redux Toolkit: More structured, better for complex state
     - Zustand: Lightweight alternative to Redux
   - Decision: Use Context API for initial development with potential to migrate to Redux Toolkit if needed
   - Implement a basic auth context in `SyncSweatApp/src/contexts/AuthContext.tsx`:
     ```tsx
     import React, { createContext, useState, useContext, ReactNode } from 'react';

     type AuthContextType = {
       isAuthenticated: boolean;
       user: any | null;
       login: (email: string, password: string) => Promise<void>;
       logout: () => void;
       signup: (email: string, password: string, name: string) => Promise<void>;
     };

     const AuthContext = createContext<AuthContextType | undefined>(undefined);

     export const AuthProvider = ({ children }: { children: ReactNode }) => {
       const [isAuthenticated, setIsAuthenticated] = useState(false);
       const [user, setUser] = useState<any | null>(null);

       const login = async (email: string, password: string) => {
         // TODO: Implement actual API call
         setIsAuthenticated(true);
         setUser({ email });
       };

       const logout = () => {
         setIsAuthenticated(false);
         setUser(null);
       };

       const signup = async (email: string, password: string, name: string) => {
         // TODO: Implement actual API call
         setIsAuthenticated(true);
         setUser({ email, name });
       };

       return (
         <AuthContext.Provider value={{ isAuthenticated, user, login, logout, signup }}>
           {children}
         </AuthContext.Provider>
       );
     };

     export const useAuth = () => {
       const context = useContext(AuthContext);
       if (context === undefined) {
         throw new Error('useAuth must be used within an AuthProvider');
       }
       return context;
     };
     ```

3. Select styling approach (Styled Components or NativeWind)
   - Evaluate options:
     - Styled Components: Component-based styling with CSS-in-JS
     - NativeWind: Tailwind CSS for React Native
   - Decision: Use Styled Components for more flexibility
   - Install Styled Components: `cd SyncSweatApp && yarn add styled-components @types/styled-components @types/styled-components-react-native`
   - Create a theme file in `SyncSweatApp/src/theme/index.ts`:
     ```typescript
     export const theme = {
       colors: {
         primary: '#4361EE',
         secondary: '#3A0CA3',
         background: '#F8F9FA',
         text: '#212529',
         lightText: '#6C757D',
         error: '#E63946',
         success: '#2A9D8F',
         warning: '#F4A261',
         white: '#FFFFFF',
         black: '#000000',
       },
       spacing: {
         xs: 4,
         sm: 8,
         md: 16,
         lg: 24,
         xl: 32,
         xxl: 48,
       },
       fontSizes: {
         xs: 12,
         sm: 14,
         md: 16,
         lg: 18,
         xl: 20,
         xxl: 24,
       },
       borderRadius: {
         sm: 4,
         md: 8,
         lg: 16,
         full: 9999,
       },
     };

     export type Theme = typeof theme;
     ```

4. Finalize backend framework details and middleware
   - Confirm FastAPI as the backend framework
   - Select and install middleware components:
     - CORS: `pip install fastapi-cors`
     - Authentication: JWT with `pip install python-jose[cryptography] passlib[bcrypt]`
     - Request validation: Built into FastAPI with Pydantic
     - Database: SQLAlchemy ORM with PostgreSQL
   - Update the main FastAPI app in `app/main.py` to include middleware:
     ```python
     from fastapi import FastAPI
     from fastapi.middleware.cors import CORSMiddleware
     from app.api.endpoints import router as api_router
     from app.core.config import settings

     app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

     # Set up CORS
     origins = [
         "http://localhost",
         "http://localhost:3000",
         "http://localhost:8000",
         "http://localhost:19006",  # React Native Expo web
     ]

     app.add_middleware(
         CORSMiddleware,
         allow_origins=origins,
         allow_credentials=True,
         allow_methods=["*"],
         allow_headers=["*"],
     )

     app.include_router(api_router, prefix=settings.API_V1_STR)

     @app.get("/")
     def root():
         return {"message": "Welcome to Sync & Sweat API"}
     ```


---

## Rules

*Embedded rules governing the AI's autonomous operation.*

**# --- Core Workflow Rules ---**

RULE_WF_PHASE_ANALYZE:
  **Constraint:** Goal is understanding request/context. NO solutioning or implementation planning.

RULE_WF_PHASE_BLUEPRINT:
  **Constraint:** Goal is creating a detailed, unambiguous step-by-step plan. NO code implementation.

RULE_WF_PHASE_CONSTRUCT:
  **Constraint:** Goal is executing the `## Plan` exactly. NO deviation. If issues arise, trigger error handling or revert phase.

RULE_WF_PHASE_VALIDATE:
  **Constraint:** Goal is verifying implementation against `## Plan` and requirements using tools. NO new implementation.

RULE_WF_TRANSITION_01:
  **Trigger:** Explicit user command (`@analyze`, `@blueprint`, `@construct`, `@validate`).
  **Action:** Update `State.Phase` accordingly. Log phase change.

RULE_WF_TRANSITION_02:
  **Trigger:** AI determines current phase constraint prevents fulfilling user request OR error handling dictates phase change (e.g., RULE_ERR_HANDLE_TEST_01).
  **Action:** Log the reason. Update `State.Phase` (e.g., to `BLUEPRINT_REVISE`). Set `State.Status` appropriately (e.g., `NEEDS_PLAN_APPROVAL`). Report to user.

**# --- Initialization & Resumption Rules ---**

RULE_INIT_01:
  **Trigger:** AI session/task starts AND `workflow_state.md` is missing or empty.
  **Action:**
    1. Create `workflow_state.md` with default structure.
    2. Read `project_config.md` (prompt user if missing).
    3. Set `State.Phase = ANALYZE`, `State.Status = READY`.
    4. Log "Initialized new session."
    5. Prompt user for the first task.

RULE_INIT_02:
  **Trigger:** AI session/task starts AND `workflow_state.md` exists.
  **Action:**
    1. Read `project_config.md`.
    2. Read existing `workflow_state.md`.
    3. Log "Resumed session."
    4. Check `State.Status`: Handle READY, COMPLETED, BLOCKED_*, NEEDS_*, IN_PROGRESS appropriately (prompt user or report status).

RULE_INIT_03:
  **Trigger:** User confirms continuation via RULE_INIT_02 (for IN_PROGRESS state).
  **Action:** Proceed with the next action based on loaded state and rules.

**# --- Memory Management Rules ---**

RULE_MEM_READ_LTM_01:
  **Trigger:** Start of a new major task or phase.
  **Action:** Read `project_config.md`. Log action.

RULE_MEM_READ_STM_01:
  **Trigger:** Before *every* decision/action cycle.
  **Action:** Read `workflow_state.md`.

RULE_MEM_UPDATE_STM_01:
  **Trigger:** After *every* significant action or information receipt.
  **Action:** Immediately update relevant sections (`## State`, `## Plan`, `## Log`) in `workflow_state.md` and save.

RULE_MEM_UPDATE_LTM_01:
  **Trigger:** User command (`@config/update`) OR end of successful VALIDATE phase for significant change.
  **Action:** Propose concise updates to `project_config.md` based on `## Log`/diffs. Set `State.Status = NEEDS_LTM_APPROVAL`. Await user confirmation.

RULE_MEM_VALIDATE_01:
  **Trigger:** After updating `workflow_state.md` or `project_config.md`.
  **Action:** Perform internal consistency check. If issues found, log and set `State.Status = NEEDS_CLARIFICATION`.

**# --- Tool Integration Rules (Cursor Environment) ---**

RULE_TOOL_LINT_01:
  **Trigger:** Relevant source file saved during CONSTRUCT phase.
  **Action:** Instruct Cursor terminal to run lint command. Log attempt. On completion, parse output, log result, set `State.Status = BLOCKED_LINT` if errors.

RULE_TOOL_FORMAT_01:
  **Trigger:** Relevant source file saved during CONSTRUCT phase.
  **Action:** Instruct Cursor to apply formatter or run format command via terminal. Log attempt.

RULE_TOOL_TEST_RUN_01:
  **Trigger:** Command `@validate` or entering VALIDATE phase.
  **Action:** Instruct Cursor terminal to run test suite. Log attempt. On completion, parse output, log result, set `State.Status = BLOCKED_TEST` if failures, `TESTS_PASSED` if success.

RULE_TOOL_APPLY_CODE_01:
  **Trigger:** AI determines code change needed per `## Plan` during CONSTRUCT phase.
  **Action:** Generate modification. Instruct Cursor to apply it. Log action.

**# --- Error Handling & Recovery Rules ---**

RULE_ERR_HANDLE_LINT_01:
  **Trigger:** `State.Status` is `BLOCKED_LINT`.
  **Action:** Analyze error in `## Log`. Attempt auto-fix if simple/confident. Apply fix via RULE_TOOL_APPLY_CODE_01. Re-run lint via RULE_TOOL_LINT_01. If success, reset `State.Status`. If fail/complex, set `State.Status = BLOCKED_LINT_UNRESOLVED`, report to user.

RULE_ERR_HANDLE_TEST_01:
  **Trigger:** `State.Status` is `BLOCKED_TEST`.
  **Action:** Analyze failure in `## Log`. Attempt auto-fix if simple/localized/confident. Apply fix via RULE_TOOL_APPLY_CODE_01. Re-run failed test(s) or suite via RULE_TOOL_TEST_RUN_01. If success, reset `State.Status`. If fail/complex, set `State.Phase = BLUEPRINT_REVISE`, `State.Status = NEEDS_PLAN_APPROVAL`, propose revised `## Plan` based on failure analysis, report to user.

RULE_ERR_HANDLE_GENERAL_01:
  **Trigger:** Unexpected error or ambiguity.
  **Action:** Log error/situation to `## Log`. Set `State.Status = BLOCKED_UNKNOWN`. Report to user, request instructions.

---

## Log

*A chronological log of significant actions, events, tool outputs, and decisions.*
*(This section will be populated by the AI during operation)*

*Example:*
*   `[2025-03-26 17:55:00] Initialized new session.`
*   `[2025-03-26 17:55:15] User task: Implement login feature.`
*   `[2025-03-26 17:55:20] State.Phase changed to ANALYZE.`
*   `[2025-03-26 17:56:00] Read project_config.md.`
*   ...

*Actual Log:*

[2023-11-15 10:00:00] Initialized new session.
[2023-11-15 10:00:15] User task: Begin Phase 0 - Foundation & Setup.
[2023-11-15 10:00:20] State.Phase changed to ANALYZE.
[2023-11-15 10:00:30] Read project_overview.md.
[2023-11-15 10:01:00] Updated workflow_state.md with Phase 0 plan.
[2023-11-15 10:05:00] Completed analysis of Phase 0 requirements.
[2023-11-15 10:05:15] State.Phase changed to BLUEPRINT.
[2023-11-15 10:05:30] Created detailed implementation plan for Phase 0.
[2023-11-15 10:30:00] Completed detailed blueprint for all sections of Phase 0.
[2023-11-15 10:30:15] State.Phase changed to CONSTRUCT.
[2023-11-15 10:30:30] Ready to begin implementation of Phase 0 tasks.
[2025-04-26 12:24:35] Conducted comprehensive review of project overview and current workflow state.
[2025-04-26 12:24:35] Confirmed project is in CONSTRUCT phase with focus on FRONTEND_IMPLEMENTATION.
[2025-04-26 12:24:35] Prepared project overview summary with current status and next steps.
[2025-04-26 13:05:24] Started implementation of onboarding flow screens for the frontend.
[2025-04-26 13:17:00] Created onboarding layout with progress indicator and navigation structure.
[2025-04-26 13:17:00] Implemented welcome screen for onboarding flow.
[2025-04-26 13:17:00] Implemented goals selection screen with multiple fitness goal options.
[2025-04-26 13:17:00] Implemented fitness level selection screen with beginner, intermediate, and advanced options.
[2025-04-26 13:17:00] Implemented available days selection screen with weekday options.
[2025-04-26 13:17:00] Implemented equipment selection screen with various equipment options.
[2025-04-26 13:17:00] Implemented music preferences screen with genre selection.
[2025-04-26 13:17:00] Implemented Spotify connection screen with authentication flow.
[2025-04-26 13:17:00] Created OnboardingContext for state management across onboarding screens.
[2025-04-26 13:17:00] Updated app layout to include OnboardingProvider for state management.
[2025-04-26 13:17:00] Fixed navigation and linting issues in onboarding flow implementation.
[2023-11-15 11:10:00] Created project directory structure.
[2023-11-15 11:15:00] Installed Expo CLI and created Expo project with TypeScript template.
[2023-11-15 11:20:00] Created Python virtual environment and installed FastAPI dependencies.
[2023-11-15 11:25:00] Set up basic FastAPI application structure.
[2023-11-15 11:30:00] Created configuration files for backend.
[2023-11-15 11:35:00] Created project README.md and .gitignore files.
[2023-11-15 11:40:00] Initialized Git repository and made initial commit.
[2023-11-15 11:45:00] Completed Project Initialization (STEP_2).
[2023-11-15 11:45:15] Moving to Database Setup (STEP_3).
[2023-11-15 11:50:00] Created database models for User, Profile, Preferences, and Workout.
[2023-11-15 11:55:00] Set up Alembic for database migrations.
[2023-11-15 12:00:00] Configured Alembic to use SQLAlchemy models.
[2023-11-15 12:05:00] Generated initial migration script for database tables.
[2023-11-15 12:10:00] Completed Database Setup (STEP_3).
[2023-11-15 12:10:15] Moving to API Setup (STEP_4).
[2023-11-15 12:15:00] Created API schemas for User, Profile, Preferences, and Workout.
[2023-11-15 12:20:00] Implemented authentication endpoints and security utilities.
[2023-11-15 12:25:00] Implemented user and profile endpoints.
[2023-11-15 12:30:00] Implemented workout and exercise endpoints.
[2023-11-15 12:35:00] Implemented Spotify integration endpoints.
[2023-11-15 12:40:00] Created service classes for Spotify and Exercise APIs.
[2023-11-15 12:45:00] Completed API Setup (STEP_4).
[2023-11-15 12:45:15] Moving to External Services Integration (STEP_5).
[2023-11-15 12:50:00] Created unit tests for Spotify service.
[2023-11-15 12:55:00] Created unit tests for Exercise service.
[2023-11-15 13:00:00] Installed required dependencies for external services.
[2023-11-15 13:05:00] Verified external services integration with tests.
[2023-11-15 13:10:00] Completed External Services Integration (STEP_5).
[2023-11-15 13:10:15] Moving to Basic CI/CD (STEP_6).
[2023-11-15 13:15:00] Created GitHub Actions workflow for frontend.
[2023-11-15 13:20:00] Created GitHub Actions workflow for backend.
[2023-11-15 13:25:00] Set up Jest testing for frontend.
[2023-11-15 13:30:00] Created ESLint configuration for frontend.
[2023-11-15 13:35:00] Completed Basic CI/CD (STEP_6).
[2023-11-15 13:35:15] Moving to Technology Decisions (STEP_7).
[2023-11-15 13:40:00] Installed React Navigation and dependencies.
[2023-11-15 13:45:00] Created navigation structure with stack and tab navigators.
[2023-11-15 13:50:00] Created basic screen components (Login, Signup, Home, Profile, Workout).
[2023-11-15 13:55:00] Updated App.tsx to use navigation structure.
[2023-11-15 14:00:00] Completed Technology Decisions (STEP_7).
[2023-11-15 14:00:15] Completed CONSTRUCT phase for Phase 0.
[2023-11-15 14:00:30] State.Phase changed to VALIDATE.
[2023-11-15 14:00:45] Starting validation of Phase 0 implementation.
[2023-11-15 14:10:00] Verified frontend implementation with React Navigation and screens.
[2023-11-15 14:15:00] Verified backend API implementation with FastAPI.
[2023-11-15 14:20:00] Verified database models and migration scripts.
[2023-11-15 14:25:00] Verified external services integration with tests.
[2023-11-15 14:30:00] Verified CI/CD setup with GitHub Actions.
[2023-11-15 14:35:00] Completed validation of Phase 0 implementation.
[2023-11-15 14:40:00] State.Status changed to COMPLETED.
[2023-11-15 14:45:00] Phase 0 - Foundation & Setup completed successfully.
[2023-11-16 09:00:00] User task: Set up unit tests for the project.
[2023-11-16 09:00:15] State.Phase changed to ANALYZE.
[2023-11-16 09:00:30] State.Status changed to IN_PROGRESS.
[2023-11-16 09:00:45] CurrentTaskID changed to UNIT_TESTS_SETUP.
[2023-11-16 10:00:00] Created Jest setup file for mocking dependencies.
[2023-11-16 10:15:00] Created tests for ThemedView component.
[2023-11-16 10:30:00] Created tests for ExternalLink component.
[2023-11-16 10:45:00] Created tests for Collapsible component.
[2023-11-16 11:00:00] Created tests for HelloWave component.
[2023-11-16 11:15:00] Created tests for HapticTab component.
[2023-11-16 11:30:00] Created tests for IconSymbol component.
[2023-11-16 11:45:00] Created tests for useThemeColor hook.
[2023-11-16 12:00:00] Created tests for login screen.
[2023-11-16 12:15:00] Created tests for NotFound screen.
[2023-11-16 12:30:00] Created tests for app layout.
[2023-11-16 12:45:00] Updated README.md with testing instructions.
[2023-11-16 13:00:00] Created TESTING.md with comprehensive testing documentation.
[2023-11-16 13:15:00] Fixed Jest configuration issues.
[2023-11-16 13:30:00] Verified tests are running correctly.
[2023-11-16 13:45:00] State.Phase changed to VALIDATE.
[2023-11-16 14:00:00] State.Status changed to COMPLETED.
[2023-11-17 09:00:00] User task: Prepare for Phase 1 implementation.
[2023-11-17 09:00:15] State.Phase changed to ANALYZE.
[2023-11-17 09:00:30] State.Status changed to IN_PROGRESS.
[2023-11-17 09:00:45] CurrentTaskID changed to PHASE_1_IMPLEMENTATION.
[2023-11-17 09:01:00] CurrentStep changed to ANALYZE_REQUIREMENTS.
[2023-11-17 09:05:00] Analyzing Phase 1 requirements from project overview.
[2023-11-17 09:30:00] Completed analysis of Phase 1 requirements.
[2023-11-17 09:30:15] State.Phase changed to BLUEPRINT.
[2023-11-17 09:30:30] CurrentStep changed to CREATE_IMPLEMENTATION_PLAN.
[2023-11-17 09:35:00] Creating detailed implementation plan for Phase 1.
[2023-11-17 10:30:00] Completed detailed implementation plan for Phase 1.
[2023-11-17 10:35:00] Ready to begin implementation of Phase 1 tasks.
[2023-11-16 09:01:00] Reading project structure and existing test files.
[2023-11-16 09:05:00] Completed analysis of project structure and existing test files.
[2023-11-16 09:05:15] State.Phase changed to BLUEPRINT.
[2023-11-16 09:05:30] Creating detailed implementation plan for unit tests setup.
[2023-11-16 09:30:00] Completed detailed blueprint for unit tests setup.
[2023-11-16 09:30:15] State.Phase changed to CONSTRUCT.
[2023-11-16 09:30:30] Starting implementation of frontend unit tests.
[2023-11-17 10:15:00] BLUEPRINT phase completed. Moving to CONSTRUCT phase to begin implementation of the backend components as outlined in the implementation plan.
[2023-11-17 11:30:00] Implementing backend components. Completed the following:
- Enhanced auth endpoints with register, login, refresh-token, and me endpoints
- Implemented Spotify OAuth callback to store tokens in user preferences
- Created playlist selector service for music recommendations
- Added endpoints for workout scheduling and playlist selection
[2023-11-17 12:45:00] Continued backend implementation:
- Enhanced security.py with improved JWT token handling and timezone-aware datetime
- Created exercise selector service for exercise rotation and variety
- Added exercise swap endpoint to allow users to change exercises
- Fixed deprecated methods and improved code organization
[2023-11-17 14:30:00] Completed backend implementation phase:
- Fixed all deprecated dict() method calls with model_dump()
- Added constants for error messages to improve code quality
- Updated workflow state to move to frontend implementation
- Backend now has all core functionality implemented including auth, workout scheduling, exercise selection, and playlist recommendations
[2023-11-17 16:00:00] Started frontend implementation:
- Created AuthContext for authentication state management
- Enhanced login screen with loading state and error handling
- Enhanced signup screen with loading state and error handling
- Connected authentication screens to backend API
- Added token persistence with AsyncStorage
[2023-11-18 09:30:00] Continued frontend implementation - Onboarding Flow:
- Implemented complete onboarding flow with multiple screens (welcome, goals, fitness level, days, equipment, music, spotify)
- Created OnboardingContext for state management across onboarding screens
- Added progress indicator in onboarding layout
- Connected onboarding screens with proper navigation
[2023-11-18 11:15:00] Fixed linting issues in the codebase:
- Wrapped functions in useCallback in OnboardingContext to prevent unnecessary re-renders
- Fixed import path for useColorScheme in app/_layout.tsx
- Updated navigation paths in onboarding screens
- Improved code organization and readability
[2025-06-18 00:00:00] Onboarding flow implementation completed. State updated to DASHBOARD_HOME_SCREEN as next sub-step in frontend implementation.