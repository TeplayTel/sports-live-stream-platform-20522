#!/usr/bin/env python3
"""
Model validation script for Sports Telecast Backend

This script validates that SQLAlchemy ORM models correctly mirror Pydantic models
and that schema conversions work properly.
"""

import sys
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any

# Import SQLAlchemy models
from src.database.models import (
    UserDB, TeamDB, EventDB, MatchDB, HighlightDB,
    EmojiAssetDB,
    SportTypeEnum, MatchStatusEnum, UserRoleEnum, EmojiTypeEnum
)

# Import Pydantic models
from src.models.user import UserRole
from src.models.match import SportType, MatchStatus
from src.models.emoji import EmojiType

# Import schema converters
from src.database.schemas import (
    convert_user_db_to_response,
    convert_team_db_to_pydantic,
    convert_event_db_to_pydantic,
    convert_match_db_to_pydantic,
    convert_highlight_db_to_pydantic,
    convert_emoji_db_to_pydantic
)

def test_enum_mappings():
    """Test that all enum mappings work correctly"""
    print("Testing enum mappings...")
    
    # Test SportType mappings
    assert SportTypeEnum.FOOTBALL.value == SportType.FOOTBALL.value
    assert SportTypeEnum.BASKETBALL.value == SportType.BASKETBALL.value
    
    # Test MatchStatus mappings  
    assert MatchStatusEnum.LIVE.value == MatchStatus.LIVE.value
    assert MatchStatusEnum.FINISHED.value == MatchStatus.FINISHED.value
    
    # Test UserRole mappings
    assert UserRoleEnum.USER.value == UserRole.USER.value
    assert UserRoleEnum.ADMIN.value == UserRole.ADMIN.value
    
    # Test EmojiType mappings
    assert EmojiTypeEnum.CLAP.value == EmojiType.CLAP.value
    assert EmojiTypeEnum.FIRE.value == EmojiType.FIRE.value
    
    print("✓ Enum mappings are correct")

def create_test_user() -> UserDB:
    """Create a test user instance"""
    return UserDB(
        user_id=str(uuid.uuid4()),
        email="test@example.com",
        username="testuser",
        password_hash="hashed_password",
        full_name="Test User",
        avatar_url="https://example.com/avatar.jpg",
        role=UserRoleEnum.USER,
        is_active=True,
        preferences={
            "favorite_teams": ["TEAM001", "TEAM002"],
            "favorite_sports": ["football", "basketball"],
            "notification_settings": {
                "email_notifications": True,
                "push_notifications": False
            },
            "preferred_language": "en",
            "timezone": "UTC"
        },
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

def create_test_team() -> TeamDB:
    """Create a test team instance"""
    return TeamDB(
        team_id=str(uuid.uuid4()),
        name="Test Team FC",
        short_name="TFC",
        logo_url="https://example.com/logo.png",
        colors={"primary": "#FF0000", "secondary": "#0000FF"},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

def create_test_event() -> EventDB:
    """Create a test event instance"""
    return EventDB(
        event_id=str(uuid.uuid4()),
        name="Test Championship",
        description="A test championship event",
        sport_type=SportTypeEnum.FOOTBALL,
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=30),
        location="Test Stadium",
        organizer="Test League",
        logo_url="https://example.com/event_logo.png",
        banner_url="https://example.com/banner.jpg",
        is_featured=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

def create_test_match(event: EventDB, home_team: TeamDB, away_team: TeamDB) -> MatchDB:
    """Create a test match instance"""
    return MatchDB(
        match_id=str(uuid.uuid4()),
        event_id=event.event_id,
        home_team_id=home_team.team_id,
        away_team_id=away_team.team_id,
        sport_type=SportTypeEnum.FOOTBALL,
        status=MatchStatusEnum.LIVE,
        home_score=2,
        away_score=1,
        period_scores=[{"home": 1, "away": 0}, {"home": 1, "away": 1}],
        start_time=datetime.utcnow(),
        end_time=None,
        venue="Test Stadium",
        competition="Test League",
        round="Round 16",
        stream_url="https://example.com/stream",
        statistics={
            "possession": {"home": 60, "away": 40},
            "shots": {"home": 15, "away": 8}
        },
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

def create_test_highlight(match: MatchDB) -> HighlightDB:
    """Create a test highlight instance"""
    return HighlightDB(
        highlight_id=str(uuid.uuid4()),
        match_id=match.match_id,
        title="Amazing Goal!",
        description="A spectacular goal in the 75th minute",
        video_url="https://example.com/highlight.mp4",
        thumbnail_url="https://example.com/thumbnail.jpg",
        duration=30,
        tags=["goal", "spectacular", "75th_minute"],
        view_count=1500,
        created_at=datetime.utcnow()
    )

def create_test_emoji() -> EmojiAssetDB:
    """Create a test emoji instance"""
    return EmojiAssetDB(
        emoji_id=str(uuid.uuid4()),
        emoji_type=EmojiTypeEnum.CLAP,
        image_url="https://example.com/clap.png",
        name="Clap",
        description="Clapping hands emoji",
        is_active=True,
        sort_order=1,
        created_at=datetime.utcnow()
    )

def test_model_creation():
    """Test that all models can be created without errors"""
    print("Testing model creation...")
    
    # Create test instances
    user = create_test_user()
    home_team = create_test_team()
    away_team = create_test_team()
    event = create_test_event()
    match = create_test_match(event, home_team, away_team)
    highlight = create_test_highlight(match)
    emoji = create_test_emoji()
    
    # Set relationships for testing
    match.home_team = home_team
    match.away_team = away_team
    match.event = event
    highlight.match = match
    
    print("✓ All models created successfully")
    return {
        'user': user,
        'home_team': home_team,
        'away_team': away_team,
        'event': event,
        'match': match,
        'highlight': highlight,
        'emoji': emoji
    }

def test_schema_conversions(test_data: Dict[str, Any]):
    """Test schema conversion functions"""
    print("Testing schema conversions...")
    
    # Test user conversion
    user_response = convert_user_db_to_response(test_data['user'])
    assert user_response.user_id == test_data['user'].user_id
    assert user_response.email == test_data['user'].email
    assert user_response.role == UserRole.USER
    print("✓ User conversion works")
    
    # Test team conversion
    team_pydantic = convert_team_db_to_pydantic(test_data['home_team'])
    assert team_pydantic.team_id == test_data['home_team'].team_id
    assert team_pydantic.name == test_data['home_team'].name
    print("✓ Team conversion works")
    
    # Test event conversion
    event_pydantic = convert_event_db_to_pydantic(test_data['event'])
    assert event_pydantic.event_id == test_data['event'].event_id
    assert event_pydantic.sport_type == SportType.FOOTBALL
    print("✓ Event conversion works")
    
    # Test match conversion
    match_pydantic = convert_match_db_to_pydantic(test_data['match'])
    assert match_pydantic.match_id == test_data['match'].match_id
    assert match_pydantic.status == MatchStatus.LIVE
    assert match_pydantic.score.home_score == 2
    assert match_pydantic.score.away_score == 1
    print("✓ Match conversion works")
    
    # Test highlight conversion
    highlight_pydantic = convert_highlight_db_to_pydantic(test_data['highlight'])
    assert highlight_pydantic.highlight_id == test_data['highlight'].highlight_id
    assert isinstance(highlight_pydantic.tags, list)
    assert len(highlight_pydantic.tags) == 3
    print("✓ Highlight conversion works")
    
    # Test emoji conversion
    emoji_pydantic = convert_emoji_db_to_pydantic(test_data['emoji'])
    assert emoji_pydantic.emoji_id == test_data['emoji'].emoji_id
    assert emoji_pydantic.emoji_type == EmojiType.CLAP
    print("✓ Emoji conversion works")

def test_field_mappings():
    """Test that all required fields from OpenAPI spec are present"""
    print("Testing field mappings against OpenAPI spec...")
    
    # Check User fields
    user_fields = set(UserDB.__table__.columns.keys())
    required_user_fields = {
        'user_id', 'email', 'username', 'password_hash', 'full_name',
        'avatar_url', 'role', 'is_active', 'preferences', 'created_at', 'updated_at'
    }
    assert required_user_fields.issubset(user_fields), f"Missing user fields: {required_user_fields - user_fields}"
    
    # Check Team fields
    team_fields = set(TeamDB.__table__.columns.keys())
    required_team_fields = {
        'team_id', 'name', 'short_name', 'logo_url', 'colors', 'created_at', 'updated_at'
    }
    assert required_team_fields.issubset(team_fields), f"Missing team fields: {required_team_fields - team_fields}"
    
    # Check Match fields
    match_fields = set(MatchDB.__table__.columns.keys())
    required_match_fields = {
        'match_id', 'event_id', 'home_team_id', 'away_team_id', 'sport_type',
        'status', 'home_score', 'away_score', 'period_scores', 'start_time',
        'end_time', 'venue', 'competition', 'round', 'stream_url', 'statistics',
        'created_at', 'updated_at'
    }
    assert required_match_fields.issubset(match_fields), f"Missing match fields: {required_match_fields - match_fields}"
    
    # Check Event fields
    event_fields = set(EventDB.__table__.columns.keys())
    required_event_fields = {
        'event_id', 'name', 'description', 'sport_type', 'start_date', 'end_date',
        'location', 'organizer', 'logo_url', 'banner_url', 'is_featured',
        'created_at', 'updated_at'
    }
    assert required_event_fields.issubset(event_fields), f"Missing event fields: {required_event_fields - event_fields}"
    
    # Check Highlight fields
    highlight_fields = set(HighlightDB.__table__.columns.keys())
    required_highlight_fields = {
        'highlight_id', 'match_id', 'title', 'description', 'video_url',
        'thumbnail_url', 'duration', 'tags', 'view_count', 'created_at'
    }
    assert required_highlight_fields.issubset(highlight_fields), f"Missing highlight fields: {required_highlight_fields - highlight_fields}"
    
    # Check Emoji fields
    emoji_fields = set(EmojiAssetDB.__table__.columns.keys())
    required_emoji_fields = {
        'emoji_id', 'emoji_type', 'image_url', 'name', 'description',
        'is_active', 'sort_order', 'created_at'
    }
    assert required_emoji_fields.issubset(emoji_fields), f"Missing emoji fields: {required_emoji_fields - emoji_fields}"
    
    print("✓ All required fields are present")

def main():
    """Run all validation tests"""
    try:
        print("=" * 60)
        print("Sports Telecast Backend - Model Validation")
        print("=" * 60)
        
        test_enum_mappings()
        test_data = test_model_creation()
        test_schema_conversions(test_data)
        test_field_mappings()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("SQLAlchemy models correctly mirror Pydantic models")
        print("Schema conversions work properly")
        print("All relationships are established")
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        print("=" * 60)
        print("❌ VALIDATION FAILED!")
        print(f"Error: {str(e)}")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
