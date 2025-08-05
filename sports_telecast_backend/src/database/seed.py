"""
Database seeding script for Sports Telecast Backend

This script populates the database with initial sample data for development and testing.
"""

import asyncio
from datetime import datetime, timedelta
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from .connection import get_db_session
from .models import (
    UserDB, TeamDB, EventDB, MatchDB, EmojiAssetDB, HighlightDB,
    SportTypeEnum, MatchStatusEnum, UserRoleEnum, EmojiTypeEnum
)
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# PUBLIC_INTERFACE
async def seed_database():
    """
    Seed the database with initial sample data
    
    This function creates sample users, teams, events, matches, emojis, and highlights
    for development and testing purposes.
    """
    async with get_db_session() as session:
        print("🌱 Starting database seeding...")
        
        # Check if data already exists
        existing_users = await session.execute("SELECT COUNT(*) FROM users")
        if existing_users.scalar() > 0:
            print("⚠️ Database already contains data. Skipping seeding.")
            return
        
        # Seed emoji assets
        await seed_emojis(session)
        
        # Seed teams
        teams = await seed_teams(session)
        
        # Seed events
        events = await seed_events(session)
        
        # Seed matches
        await seed_matches(session, teams, events)
        
        # Seed users
        await seed_users(session)
        
        # Seed highlights
        await seed_highlights(session)
        
        print("✅ Database seeding completed successfully!")

async def seed_emojis(session: AsyncSession):
    """Seed emoji assets"""
    print("📱 Seeding emoji assets...")
    
    emojis = [
        {
            "emoji_id": "EMJ103",
            "emoji_type": EmojiTypeEnum.CLAP,
            "image_url": "https://cdn.mydomain.com/emojis/clap.png",
            "name": "Clap",
            "description": "Show appreciation",
            "sort_order": 1
        },
        {
            "emoji_id": "EMJ104", 
            "emoji_type": EmojiTypeEnum.FIRE,
            "image_url": "https://cdn.mydomain.com/emojis/fire.png",
            "name": "Fire",
            "description": "Amazing play!",
            "sort_order": 2
        },
        {
            "emoji_id": "EMJ105",
            "emoji_type": EmojiTypeEnum.HEART,
            "image_url": "https://cdn.mydomain.com/emojis/heart.png", 
            "name": "Love",
            "description": "Love this moment",
            "sort_order": 3
        },
        {
            "emoji_id": "EMJ106",
            "emoji_type": EmojiTypeEnum.THUMBS_UP,
            "image_url": "https://cdn.mydomain.com/emojis/thumbs_up.png",
            "name": "Thumbs Up", 
            "description": "Great job!",
            "sort_order": 4
        },
        {
            "emoji_id": "EMJ107",
            "emoji_type": EmojiTypeEnum.GOAL,
            "image_url": "https://cdn.mydomain.com/emojis/goal.png",
            "name": "Goal",
            "description": "GOAL!!!",
            "sort_order": 5
        },
        {
            "emoji_id": "EMJ108",
            "emoji_type": EmojiTypeEnum.CELEBRATION,
            "image_url": "https://cdn.mydomain.com/emojis/celebration.png",
            "name": "Celebration",
            "description": "Let's celebrate!",
            "sort_order": 6
        }
    ]
    
    for emoji_data in emojis:
        emoji = EmojiAssetDB(**emoji_data)
        session.add(emoji)
    
    await session.commit()
    print(f"   ✅ Added {len(emojis)} emoji assets")

async def seed_teams(session: AsyncSession):
    """Seed teams"""
    print("🏟️ Seeding teams...")
    
    teams_data = [
        {
            "team_id": "TEAM001",
            "name": "Arsenal FC",
            "short_name": "ARS",
            "logo_url": "https://cdn.example.com/logos/arsenal.png",
            "colors": {"primary": "#DC143C", "secondary": "#FFFFFF"}
        },
        {
            "team_id": "TEAM002", 
            "name": "Chelsea FC",
            "short_name": "CHE",
            "logo_url": "https://cdn.example.com/logos/chelsea.png",
            "colors": {"primary": "#034694", "secondary": "#FFFFFF"}
        },
        {
            "team_id": "TEAM003",
            "name": "Manchester United",
            "short_name": "MUN",
            "logo_url": "https://cdn.example.com/logos/manchester_united.png",
            "colors": {"primary": "#FF0000", "secondary": "#FFFFFF"}
        },
        {
            "team_id": "TEAM004",
            "name": "Liverpool FC",
            "short_name": "LIV",
            "logo_url": "https://cdn.example.com/logos/liverpool.png",
            "colors": {"primary": "#C8102E", "secondary": "#FFFFFF"}
        },
        {
            "team_id": "TEAM005",
            "name": "Manchester City",
            "short_name": "MCI",
            "logo_url": "https://cdn.example.com/logos/manchester_city.png",
            "colors": {"primary": "#6CABDD", "secondary": "#FFFFFF"}
        },
        {
            "team_id": "TEAM006",
            "name": "Tottenham Hotspur",
            "short_name": "TOT",
            "logo_url": "https://cdn.example.com/logos/tottenham.png",
            "colors": {"primary": "#132257", "secondary": "#FFFFFF"}
        }
    ]
    
    teams = {}
    for team_data in teams_data:
        team = TeamDB(**team_data)
        session.add(team)
        teams[team_data["team_id"]] = team
    
    await session.commit()
    print(f"   ✅ Added {len(teams_data)} teams")
    return teams

async def seed_events(session: AsyncSession):
    """Seed events"""
    print("🏆 Seeding events...")
    
    events_data = [
        {
            "event_id": "EVT123",
            "name": "Premier League 2024-25",
            "description": "English Premier League Season 2024-25",
            "sport_type": SportTypeEnum.FOOTBALL,
            "start_date": datetime.utcnow() - timedelta(days=30),
            "end_date": datetime.utcnow() + timedelta(days=200),
            "location": "England",
            "organizer": "Premier League",
            "logo_url": "https://cdn.example.com/logos/premier_league.png",
            "banner_url": "https://cdn.example.com/banners/premier_league.jpg",
            "is_featured": True
        },
        {
            "event_id": "EVT124",
            "name": "Champions League 2024-25",
            "description": "UEFA Champions League Season 2024-25",
            "sport_type": SportTypeEnum.FOOTBALL,
            "start_date": datetime.utcnow() - timedelta(days=60),
            "end_date": datetime.utcnow() + timedelta(days=180),
            "location": "Europe",
            "organizer": "UEFA",
            "logo_url": "https://cdn.example.com/logos/champions_league.png",
            "banner_url": "https://cdn.example.com/banners/champions_league.jpg",
            "is_featured": True
        }
    ]
    
    events = {}
    for event_data in events_data:
        event = EventDB(**event_data)
        session.add(event)
        events[event_data["event_id"]] = event
    
    await session.commit()
    print(f"   ✅ Added {len(events_data)} events")
    return events

async def seed_matches(session: AsyncSession, teams: dict, events: dict):
    """Seed matches"""
    print("⚽ Seeding matches...")
    
    matches_data = [
        {
            "match_id": "MATCH001",
            "event_id": "EVT123",
            "home_team_id": "TEAM001",
            "away_team_id": "TEAM002",
            "sport_type": SportTypeEnum.FOOTBALL,
            "status": MatchStatusEnum.LIVE,
            "home_score": 2,
            "away_score": 1,
            "start_time": datetime.utcnow() - timedelta(minutes=45),
            "venue": "Emirates Stadium",
            "competition": "Premier League",
            "round": "Matchday 15",
            "stream_url": "https://stream.example.com/match001"
        },
        {
            "match_id": "MATCH002", 
            "event_id": "EVT123",
            "home_team_id": "TEAM003",
            "away_team_id": "TEAM004",
            "sport_type": SportTypeEnum.FOOTBALL,
            "status": MatchStatusEnum.SCHEDULED,
            "home_score": 0,
            "away_score": 0,
            "start_time": datetime.utcnow() + timedelta(hours=2),
            "venue": "Old Trafford",
            "competition": "Premier League",
            "round": "Matchday 15",
            "stream_url": "https://stream.example.com/match002"
        },
        {
            "match_id": "MATCH003",
            "event_id": "EVT123", 
            "home_team_id": "TEAM001",
            "away_team_id": "TEAM004",
            "sport_type": SportTypeEnum.FOOTBALL,
            "status": MatchStatusEnum.FINISHED,
            "home_score": 3,
            "away_score": 2,
            "start_time": datetime.utcnow() - timedelta(days=7),
            "end_time": datetime.utcnow() - timedelta(days=7, hours=-2),
            "venue": "Emirates Stadium",
            "competition": "Premier League",
            "round": "Matchday 14"
        },
        {
            "match_id": "MATCH004",
            "event_id": "EVT123",
            "home_team_id": "TEAM005",
            "away_team_id": "TEAM006",
            "sport_type": SportTypeEnum.FOOTBALL,
            "status": MatchStatusEnum.SCHEDULED,
            "home_score": 0,
            "away_score": 0,
            "start_time": datetime.utcnow() + timedelta(days=1),
            "venue": "Etihad Stadium",
            "competition": "Premier League",
            "round": "Matchday 16"
        }
    ]
    
    for match_data in matches_data:
        match = MatchDB(**match_data)
        session.add(match)
    
    await session.commit()
    print(f"   ✅ Added {len(matches_data)} matches")

async def seed_users(session: AsyncSession):
    """Seed sample users"""
    print("👤 Seeding users...")
    
    users_data = [
        {
            "user_id": str(uuid.uuid4()),
            "email": "admin@sportstelecast.com",
            "username": "admin",
            "password_hash": pwd_context.hash("admin123"),
            "full_name": "System Administrator",
            "role": UserRoleEnum.ADMIN,
            "is_active": True,
            "preferences": {
                "favorite_teams": ["TEAM001", "TEAM003"],
                "favorite_sports": ["football"],
                "notification_settings": {"match_start": True, "goals": True},
                "preferred_language": "en",
                "timezone": "UTC"
            }
        },
        {
            "user_id": str(uuid.uuid4()),
            "email": "john.doe@example.com",
            "username": "johndoe",
            "password_hash": pwd_context.hash("password123"),
            "full_name": "John Doe",
            "role": UserRoleEnum.USER,
            "is_active": True,
            "preferences": {
                "favorite_teams": ["TEAM002", "TEAM004"],
                "favorite_sports": ["football"],
                "notification_settings": {"match_start": True, "goals": False},
                "preferred_language": "en",
                "timezone": "UTC"
            }
        }
    ]
    
    for user_data in users_data:
        user = UserDB(**user_data)
        session.add(user)
    
    await session.commit()
    print(f"   ✅ Added {len(users_data)} users")

async def seed_highlights(session: AsyncSession):
    """Seed highlights"""
    print("🎬 Seeding highlights...")
    
    highlights_data = [
        {
            "highlight_id": "HIGH001",
            "match_id": "MATCH003",
            "title": "Arsenal vs Liverpool - All Goals & Highlights",
            "description": "Watch all the goals and best moments from this thrilling match",
            "video_url": "https://cdn.example.com/highlights/match003.mp4",
            "thumbnail_url": "https://cdn.example.com/thumbnails/match003.jpg",
            "duration": 300,
            "tags": ["goals", "highlights", "premier-league"],
            "view_count": 15420
        },
        {
            "highlight_id": "HIGH002",
            "match_id": "MATCH001",
            "title": "Arsenal vs Chelsea - Live Match Highlights",
            "description": "Best moments from the ongoing match",
            "video_url": "https://cdn.example.com/highlights/match001.mp4", 
            "thumbnail_url": "https://cdn.example.com/thumbnails/match001.jpg",
            "duration": 180,
            "tags": ["live", "highlights", "arsenal", "chelsea"],
            "view_count": 8934
        },
        {
            "highlight_id": "HIGH003",
            "match_id": "MATCH003",
            "title": "Best Goal of the Match - Arsenal vs Liverpool",
            "description": "An incredible goal that decided the match",
            "video_url": "https://cdn.example.com/highlights/goal_match003.mp4",
            "thumbnail_url": "https://cdn.example.com/thumbnails/goal_match003.jpg",
            "duration": 45,
            "tags": ["goal", "best-moment", "arsenal"],
            "view_count": 25000
        }
    ]
    
    for highlight_data in highlights_data:
        highlight = HighlightDB(**highlight_data)
        session.add(highlight)
    
    await session.commit()
    print(f"   ✅ Added {len(highlights_data)} highlights")

# CLI script entry point
if __name__ == "__main__":
    asyncio.run(seed_database())
