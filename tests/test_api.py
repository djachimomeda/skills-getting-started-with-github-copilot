"""
Tests for the Mergington High School Activities API
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test"""
    activities.clear()
    activities.update({
        "Basketball Team": {
            "description": "Join the school basketball team and compete in inter-school tournaments",
            "schedule": "Mondays and Wednesdays, 4:00 PM - 6:00 PM",
            "max_participants": 15,
            "participants": ["james@mergington.edu", "william@mergington.edu"]
        },
        "Swimming Club": {
            "description": "Improve swimming techniques and participate in swimming competitions",
            "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
            "max_participants": 20,
            "participants": ["ava@mergington.edu", "noah@mergington.edu"]
        },
        "Drama Club": {
            "description": "Perform in school plays and develop acting skills",
            "schedule": "Wednesdays, 3:30 PM - 5:30 PM",
            "max_participants": 25,
            "participants": ["isabella@mergington.edu", "liam@mergington.edu"]
        }
    })


class TestRootEndpoint:
    """Tests for the root endpoint"""

    def test_root_redirects_to_index(self, client):
        """Test that root path redirects to index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""

    def test_get_all_activities(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Basketball Team" in data
        assert "Swimming Club" in data
        assert "Drama Club" in data

    def test_activities_structure(self, client):
        """Test that activities have the correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        basketball = data["Basketball Team"]
        assert "description" in basketball
        assert "schedule" in basketball
        assert "max_participants" in basketball
        assert "participants" in basketball
        assert isinstance(basketball["participants"], list)

    def test_activities_participants(self, client):
        """Test that activities return correct participants"""
        response = client.get("/activities")
        data = response.json()
        
        basketball = data["Basketball Team"]
        assert "james@mergington.edu" in basketball["participants"]
        assert "william@mergington.edu" in basketball["participants"]


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""

    def test_signup_new_participant(self, client):
        """Test signing up a new participant"""
        response = client.post(
            "/activities/Basketball Team/signup?email=new.student@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up new.student@mergington.edu for Basketball Team" in data["message"]

    def test_signup_adds_participant_to_list(self, client):
        """Test that signup actually adds participant to the activity"""
        email = "test.student@mergington.edu"
        client.post(f"/activities/Basketball Team/signup?email={email}")
        
        response = client.get("/activities")
        data = response.json()
        assert email in data["Basketball Team"]["participants"]

    def test_signup_duplicate_participant(self, client):
        """Test that signing up the same participant twice fails"""
        email = "james@mergington.edu"
        response = client.post(f"/activities/Basketball Team/signup?email={email}")
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"].lower()

    def test_signup_nonexistent_activity(self, client):
        """Test signing up for a non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_signup_multiple_participants(self, client):
        """Test signing up multiple new participants"""
        emails = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]
        
        for email in emails:
            response = client.post(f"/activities/Drama Club/signup?email={email}")
            assert response.status_code == 200
        
        response = client.get("/activities")
        data = response.json()
        drama_participants = data["Drama Club"]["participants"]
        
        for email in emails:
            assert email in drama_participants


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""

    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant"""
        email = "james@mergington.edu"
        response = client.delete(
            f"/activities/Basketball Team/unregister?email={email}"
        )
        assert response.status_code == 200
        data = response.json()
        assert f"Unregistered {email} from Basketball Team" in data["message"]

    def test_unregister_removes_participant_from_list(self, client):
        """Test that unregister actually removes participant from the activity"""
        email = "james@mergington.edu"
        client.delete(f"/activities/Basketball Team/unregister?email={email}")
        
        response = client.get("/activities")
        data = response.json()
        assert email not in data["Basketball Team"]["participants"]

    def test_unregister_nonexistent_participant(self, client):
        """Test unregistering a participant who is not registered"""
        email = "notregistered@mergington.edu"
        response = client.delete(
            f"/activities/Basketball Team/unregister?email={email}"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"].lower()

    def test_unregister_from_nonexistent_activity(self, client):
        """Test unregistering from a non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    def test_signup_and_unregister_workflow(self, client):
        """Test complete workflow: signup and then unregister"""
        email = "workflow.test@mergington.edu"
        activity = "Swimming Club"
        
        # Sign up
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        # Verify participant is in the list
        response = client.get("/activities")
        data = response.json()
        assert email in data[activity]["participants"]
        
        # Unregister
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 200
        
        # Verify participant is removed
        response = client.get("/activities")
        data = response.json()
        assert email not in data[activity]["participants"]


class TestActivityCapacity:
    """Tests for activity participant capacity"""

    def test_activity_has_max_participants(self, client):
        """Test that activities have max_participants defined"""
        response = client.get("/activities")
        data = response.json()
        
        for activity in data.values():
            assert "max_participants" in activity
            assert activity["max_participants"] > 0

    def test_participants_count_increases_on_signup(self, client):
        """Test that participant count increases when signing up"""
        response = client.get("/activities")
        initial_data = response.json()
        initial_count = len(initial_data["Basketball Team"]["participants"])
        
        client.post("/activities/Basketball Team/signup?email=new@mergington.edu")
        
        response = client.get("/activities")
        updated_data = response.json()
        new_count = len(updated_data["Basketball Team"]["participants"])
        
        assert new_count == initial_count + 1

    def test_participants_count_decreases_on_unregister(self, client):
        """Test that participant count decreases when unregistering"""
        response = client.get("/activities")
        initial_data = response.json()
        initial_count = len(initial_data["Basketball Team"]["participants"])
        
        client.delete("/activities/Basketball Team/unregister?email=james@mergington.edu")
        
        response = client.get("/activities")
        updated_data = response.json()
        new_count = len(updated_data["Basketball Team"]["participants"])
        
        assert new_count == initial_count - 1
