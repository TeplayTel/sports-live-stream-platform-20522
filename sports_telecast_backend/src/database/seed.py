"""
Database seeding script for Sports Telecast Backend

This script populates the database with initial sample data for development and testing.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
import uuid
import random

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from passlib.context import CryptContext

from src.database.connection import get_db_session
from src.database.models import (
    UserDB, TeamDB, EventDB, MatchDB, EmojiAssetDB, HighlightDB,
    MatchEventDB, UserEmojiReactionDB,
    SportTypeEnum, MatchStatusEnum, UserRoleEnum, EmojiTypeEnum
)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# PUBLIC_INTERFACE
async def seed_database():
    """
    Seed the database with initial sample data
    
    This function creates sample users, teams, events, matches, emojis, highlights,
    match events, and user emoji reactions for development and testing purposes.
    """
    async with get_db_session() as session:
        print("🌱 Starting database seeding...")
        
        # Check if data already exists
        try:
            existing_users_result = await session.execute(text("SELECT COUNT(*) FROM users"))
            if existing_users_result.scalar() > 0:
                print("⚠️ Database already contains data. Skipping seeding.")
                return
        except Exception as e:
            print(f"⚠️ Could not check existing data: {e}")
            print("Proceeding with seeding...")
        
        # Seed emoji assets first
        emojis, emoji_uuids = await seed_emojis(session)
        
        # Seed teams
        teams, team_uuids = await seed_teams(session)
        
        # Seed events
        events, event_uuids = await seed_events(session)
        
        # Seed matches
        matches, match_uuids = await seed_matches(session, teams, events, team_uuids, event_uuids)
        
        # Seed users
        users = await seed_users(session)
        
        # Seed match events
        await seed_match_events(session, matches, teams, match_uuids, team_uuids)
        
        # Seed highlights
        await seed_highlights(session, match_uuids)
        
        # Seed user emoji reactions
        await seed_user_emoji_reactions(session, users, emojis, emoji_uuids)
        
        print("✅ Database seeding completed successfully!")

async def seed_emojis(session: AsyncSession):
    """Seed emoji assets"""
    print("📱 Seeding emoji assets...")
    
    # Generate proper UUIDs for emojis
    emoji_uuids = {
        "EMJ103": uuid.uuid4(),
        "EMJ104": uuid.uuid4(),
        "EMJ105": uuid.uuid4(),
        "EMJ106": uuid.uuid4(),
        "EMJ107": uuid.uuid4(),
        "EMJ108": uuid.uuid4(),
        "EMJ109": uuid.uuid4(),
        "EMJ110": uuid.uuid4()
    }
    
    emojis_data = [
        {
            "emoji_type": EmojiTypeEnum.CLAP,
            "image_url": "https://cdn.mydomain.com/emojis/clap.png",
            "name": "Clap",
            "description": "Show appreciation",
            "sort_order": 1
        },
        {
            "emoji_type": EmojiTypeEnum.FIRE,
            "image_url": "https://cdn.mydomain.com/emojis/fire.png",
            "name": "Fire",
            "description": "Amazing play!",
            "sort_order": 2
        },
        {
            "emoji_type": EmojiTypeEnum.HEART,
            "image_url": "https://cdn.mydomain.com/emojis/heart.png", 
            "name": "Love",
            "description": "Love this moment",
            "sort_order": 3
        },
        {
            "emoji_type": EmojiTypeEnum.THUMBS_UP,
            "image_url": "https://cdn.mydomain.com/emojis/thumbs_up.png",
            "name": "Thumbs Up", 
            "description": "Great job!",
            "sort_order": 4
        },
        {
            "emoji_type": EmojiTypeEnum.GOAL,
            "image_url": "https://cdn.mydomain.com/emojis/goal.png",
            "name": "Goal",
            "description": "GOAL!!!",
            "sort_order": 5
        },
        {
            "emoji_type": EmojiTypeEnum.CELEBRATION,
            "image_url": "https://cdn.mydomain.com/emojis/celebration.png",
            "name": "Celebration",
            "description": "Let's celebrate!",
            "sort_order": 6
        },
        {
            "emoji_type": EmojiTypeEnum.SHOCKED,
            "image_url": "https://cdn.mydomain.com/emojis/shocked.png",
            "name": "Shocked",
            "description": "What a surprise!",
            "sort_order": 7
        },
        {
            "emoji_type": EmojiTypeEnum.LAUGH,
            "image_url": "https://cdn.mydomain.com/emojis/laugh.png",
            "name": "Laugh",
            "description": "That was funny!",
            "sort_order": 8
        }
    ]
    
    emojis = {}
    emoji_keys = list(emoji_uuids.keys())
    for i, emoji_data in enumerate(emojis_data):
        emoji_key = emoji_keys[i]
        emoji = EmojiAssetDB(emoji_id=emoji_uuids[emoji_key], **emoji_data)
        session.add(emoji)
        emojis[emoji_key] = emoji
    
    await session.commit()
    print(f"   ✅ Added {len(emojis_data)} emoji assets")
    return emojis, emoji_uuids

async def seed_teams(session: AsyncSession):
    """Seed teams"""
    print("🏟️ Seeding teams...")
    
    # Generate proper UUIDs for teams
    team_uuids = {
        "TEAM001": uuid.uuid4(),
        "TEAM002": uuid.uuid4(),
        "TEAM003": uuid.uuid4(),
        "TEAM004": uuid.uuid4(),
        "TEAM005": uuid.uuid4(),
        "TEAM006": uuid.uuid4(),
        "TEAM007": uuid.uuid4(),
        "TEAM008": uuid.uuid4()
    }
    
    teams_data = [
        {
            "name": "Arsenal FC",
            "short_name": "ARS",
            "logo_url": "https://cdn.example.com/logos/arsenal.png",
            "colors": {"primary": "#DC143C", "secondary": "#FFFFFF"}
        },
        {
            "name": "Chelsea FC",
            "short_name": "CHE",
            "logo_url": "https://cdn.example.com/logos/chelsea.png",
            "colors": {"primary": "#034694", "secondary": "#FFFFFF"}
        },
        {
            "name": "Manchester United",
            "short_name": "MUN",
            "logo_url": "https://cdn.example.com/logos/manchester_united.png",
            "colors": {"primary": "#FF0000", "secondary": "#FFFFFF"}
        },
        {
            "name": "Liverpool FC",
            "short_name": "LIV",
            "logo_url": "https://cdn.example.com/logos/liverpool.png",
            "colors": {"primary": "#C8102E", "secondary": "#FFFFFF"}
        },
        {
            "name": "Manchester City",
            "short_name": "MCI",
            "logo_url": "https://cdn.example.com/logos/manchester_city.png",
            "colors": {"primary": "#6CABDD", "secondary": "#FFFFFF"}
        },
        {
            "name": "Tottenham Hotspur",
            "short_name": "TOT",
            "logo_url": "https://cdn.example.com/logos/tottenham.png",
            "colors": {"primary": "#132257", "secondary": "#FFFFFF"}
        },
        {
            "name": "Newcastle United",
            "short_name": "NEW",
            "logo_url": "https://cdn.example.com/logos/newcastle.png",
            "colors": {"primary": "#000000", "secondary": "#FFFFFF"}
        },
        {
            "name": "Brighton & Hove Albion",
            "short_name": "BHA",
            "logo_url": "https://cdn.example.com/logos/brighton.png",
            "colors": {"primary": "#0057B8", "secondary": "#FFCD00"}
        }
    ]
    
    teams = {}
    team_keys = list(team_uuids.keys())
    for i, team_data in enumerate(teams_data):
        team_key = team_keys[i]
        team = TeamDB(team_id=team_uuids[team_key], **team_data)
        session.add(team)
        teams[team_key] = team
    
    await session.commit()
    print(f"   ✅ Added {len(teams_data)} teams")
    return teams, team_uuids

async def seed_events(session: AsyncSession):
    """Seed events"""
    print("🏆 Seeding events...")
    
    # Generate proper UUIDs for events
    event_uuids = {
        "EVT123": uuid.uuid4(),
        "EVT124": uuid.uuid4(),
        "EVT125": uuid.uuid4()
    }
    
    events_data = [
        {
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
        },
        {
            "name": "FA Cup 2024-25",
            "description": "The Football Association Challenge Cup",
            "sport_type": SportTypeEnum.FOOTBALL,
            "start_date": datetime.utcnow() - timedelta(days=45),
            "end_date": datetime.utcnow() + timedelta(days=120),
            "location": "England",
            "organizer": "The FA",
            "logo_url": "https://cdn.example.com/logos/fa_cup.png",
            "banner_url": "https://cdn.example.com/banners/fa_cup.jpg",
            "is_featured": False
        }
    ]
    
    events = {}
    event_keys = list(event_uuids.keys())
    for i, event_data in enumerate(events_data):
        event_key = event_keys[i]
        event = EventDB(event_id=event_uuids[event_key], **event_data)
        session.add(event)
        events[event_key] = event
    
    await session.commit()
    print(f"   ✅ Added {len(events_data)} events")
    return events, event_uuids

async def seed_matches(session: AsyncSession, teams: dict, events: dict, team_uuids: dict, event_uuids: dict):
    """Seed matches"""
    print("⚽ Seeding matches...")
    
    # Generate proper UUIDs for matches
    match_uuids = {
        "MATCH001": uuid.uuid4(),
        "MATCH002": uuid.uuid4(),
        "MATCH003": uuid.uuid4(),
        "MATCH004": uuid.uuid4(),
        "MATCH005": uuid.uuid4(),
        "MATCH006": uuid.uuid4(),
        "MATCH007": uuid.uuid4(),
        "MATCH008": uuid.uuid4(),
        "MATCH009": uuid.uuid4(),
        "MATCH010": uuid.uuid4(),
        "MATCH011": uuid.uuid4(),
        "MATCH012": uuid.uuid4()
    }
    
    matches_data = [
        {
            "event_id": event_uuids["EVT123"],
            "home_team_id": team_uuids["TEAM001"],
            "away_team_id": team_uuids["TEAM002"],
            "sport_type": SportTypeEnum.FOOTBALL,
            "status": MatchStatusEnum.LIVE,
            "home_score": 2,
            "away_score": 1,
            "start_time": datetime.utcnow() - timedelta(minutes=45),
            "venue": "Emirates Stadium",
            "competition": "Premier League",
            "round": "Matchday 15",
            "stream_url": "https://stream.example.com/match001",
            "statistics": {
                "possession": {"home": 58, "away": 42},
                "shots": {"home": 12, "away": 8},
                "corners": {"home": 6, "away": 3}
            }
        },
        {
            "event_id": event_uuids["EVT123"],
            "home_team_id": team_uuids["TEAM003"],
            "away_team_id": team_uuids["TEAM004"],
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
            "event_id": event_uuids["EVT123"],
            "home_team_id": team_uuids["TEAM001"],
            "away_team_id": team_uuids["TEAM004"],
            "sport_type": SportTypeEnum.FOOTBALL,
            "status": MatchStatusEnum.FINISHED,
            "home_score": 3,
            "away_score": 2,
            "start_time": datetime.utcnow() - timedelta(days=7),
            "end_time": datetime.utcnow() - timedelta(days=7, hours=-2),
            "venue": "Emirates Stadium",
            "competition": "Premier League",
            "round": "Matchday 14",
            "period_scores": {"first_half": {"home": 2, "away": 1}, "second_half": {"home": 1, "away": 1}},
            "statistics": {
                "possession": {"home": 65, "away": 35},
                "shots": {"home": 15, "away": 11},
                "corners": {"home": 8, "away": 5},
                "fouls": {"home": 12, "away": 16}
            }
        },
        {
            "event_id": event_uuids["EVT123"],
            "home_team_id": team_uuids["TEAM005"],
            "away_team_id": team_uuids["TEAM006"],
            "sport_type": SportTypeEnum.FOOTBALL,
            "status": MatchStatusEnum.SCHEDULED,
            "home_score": 0,
            "away_score": 0,
            "start_time": datetime.utcnow() + timedelta(days=1),
            "venue": "Etihad Stadium",
            "competition": "Premier League",
            "round": "Matchday 16"
        },
        {
            "event_id": event_uuids["EVT124"],
            "home_team_id": team_uuids["TEAM002"],
            "away_team_id": team_uuids["TEAM005"],
            "sport_type": SportTypeEnum.FOOTBALL,
            "status": MatchStatusEnum.FINISHED,
            "home_score": 1,
            "away_score": 0,
            "start_time": datetime.utcnow() - timedelta(days=3),
            "end_time": datetime.utcnow() - timedelta(days=3, hours=-2),
            "venue": "Stamford Bridge",
            "competition": "Champions League",
            "round": "Group Stage"
        },
        {
            "event_id": event_uuids["EVT123"],
            "home_team_id": team_uuids["TEAM007"],
            "away_team_id": team_uuids["TEAM008"],
            "sport_type": SportTypeEnum.FOOTBALL,
            "status": MatchStatusEnum.FINISHED,
            "home_score": 2,
            "away_score": 2,
            "start_time": datetime.utcnow() - timedelta(days=2),
            "end_time": datetime.utcnow() - timedelta(days=2, hours=-2),
            "venue": "St. James' Park",
            "competition": "Premier League",
            "round": "Matchday 14"
        },
        # Additional matches for "more matches" feature
        {
            "event_id": event_uuids["EVT123"],
            "home_team_id": team_uuids["TEAM004"],
            "away_team_id": team_uuids["TEAM005"],
            "sport_type": SportTypeEnum.FOOTBALL,
            "status": MatchStatusEnum.LIVE,
            "home_score": 1,
            "away_score": 1,
            "start_time": datetime.utcnow() - timedelta(minutes=73),
            "venue": "Anfield",
            "competition": "Premier League",
            "round": "Matchday 15",
            "stream_url": "https://stream.example.com/match007",
            "statistics": {
                "possession": {"home": 42, "away": 58},
                "shots": {"home": 8, "away": 12},
                "corners": {"home": 3, "away": 7}
            }
        },
        {
            "event_id": event_uuids["EVT125"],
            "home_team_id": team_uuids["TEAM001"],
            "away_team_id": team_uuids["TEAM006"],
            "sport_type": SportTypeEnum.FOOTBALL,
            "status": MatchStatusEnum.FINISHED,
            "home_score": 3,
            "away_score": 0,
            "start_time": datetime.utcnow() - timedelta(days=5),
            "end_time": datetime.utcnow() - timedelta(days=5, hours=-2),
            "venue": "Emirates Stadium",
            "competition": "FA Cup",
            "round": "4th Round",
            "statistics": {
                "possession": {"home": 70, "away": 30},
                "shots": {"home": 18, "away": 4},
                "corners": {"home": 9, "away": 2}
            }
        },
        {
            "event_id": event_uuids["EVT123"],
            "home_team_id": team_uuids["TEAM002"],
            "away_team_id": team_uuids["TEAM007"],
            "sport_type": SportTypeEnum.FOOTBALL,
            "status": MatchStatusEnum.SCHEDULED,
            "home_score": 0,
            "away_score": 0,
            "start_time": datetime.utcnow() + timedelta(hours=6),
            "venue": "Stamford Bridge",
            "competition": "Premier League",
            "round": "Matchday 16"
        },
        {
            "event_id": event_uuids["EVT124"],
            "home_team_id": team_uuids["TEAM003"],
            "away_team_id": team_uuids["TEAM001"],
            "sport_type": SportTypeEnum.FOOTBALL,
            "status": MatchStatusEnum.SCHEDULED,
            "home_score": 0,
            "away_score": 0,
            "start_time": datetime.utcnow() + timedelta(days=3),
            "venue": "Old Trafford",
            "competition": "Champions League",
            "round": "Round of 16"
        },
        {
            "event_id": event_uuids["EVT123"],
            "home_team_id": team_uuids["TEAM008"],
            "away_team_id": team_uuids["TEAM003"],
            "sport_type": SportTypeEnum.FOOTBALL,
            "status": MatchStatusEnum.FINISHED,
            "home_score": 1,
            "away_score": 4,
            "start_time": datetime.utcnow() - timedelta(days=4),
            "end_time": datetime.utcnow() - timedelta(days=4, hours=-2),
            "venue": "Falmer Stadium",
            "competition": "Premier League",
            "round": "Matchday 14",
            "statistics": {
                "possession": {"home": 35, "away": 65},
                "shots": {"home": 6, "away": 16},
                "corners": {"home": 2, "away": 8}
            }
        },
        {
            "event_id": event_uuids["EVT123"],
            "home_team_id": team_uuids["TEAM006"],
            "away_team_id": team_uuids["TEAM004"],
            "sport_type": SportTypeEnum.FOOTBALL,
            "status": MatchStatusEnum.SCHEDULED,
            "home_score": 0,
            "away_score": 0,
            "start_time": datetime.utcnow() + timedelta(days=2, hours=4),
            "venue": "Tottenham Hotspur Stadium",
            "competition": "Premier League",
            "round": "Matchday 16"
        }
    ]
    
    matches = {}
    match_keys = list(match_uuids.keys())
    for i, match_data in enumerate(matches_data):
        match_key = match_keys[i]
        match = MatchDB(match_id=match_uuids[match_key], **match_data)
        session.add(match)
        matches[match_key] = match
    
    await session.commit()
    print(f"   ✅ Added {len(matches_data)} matches")
    return matches, match_uuids

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
            "avatar_url": "https://cdn.example.com/avatars/admin.jpg",
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
            "avatar_url": "https://cdn.example.com/avatars/john.jpg",
            "preferences": {
                "favorite_teams": ["TEAM002", "TEAM004"],
                "favorite_sports": ["football"],
                "notification_settings": {"match_start": True, "goals": False},
                "preferred_language": "en",
                "timezone": "UTC"
            }
        },
        {
            "user_id": str(uuid.uuid4()),
            "email": "sarah.wilson@example.com",
            "username": "sarahw",
            "password_hash": pwd_context.hash("sarah123"),
            "full_name": "Sarah Wilson",
            "role": UserRoleEnum.USER,
            "is_active": True,
            "avatar_url": "https://cdn.example.com/avatars/sarah.jpg",
            "preferences": {
                "favorite_teams": ["TEAM001", "TEAM005"],
                "favorite_sports": ["football"],
                "notification_settings": {"match_start": True, "goals": True},
                "preferred_language": "en",
                "timezone": "America/New_York"
            }
        },
        {
            "user_id": str(uuid.uuid4()),
            "email": "mike.brown@example.com",
            "username": "mikeb",
            "password_hash": pwd_context.hash("mike123"),
            "full_name": "Mike Brown",
            "role": UserRoleEnum.MODERATOR,
            "is_active": True,
            "avatar_url": "https://cdn.example.com/avatars/mike.jpg",
            "preferences": {
                "favorite_teams": ["TEAM006", "TEAM002"],
                "favorite_sports": ["football"],
                "notification_settings": {"match_start": True, "goals": True},
                "preferred_language": "en",
                "timezone": "Europe/London"
            }
        },
        {
            "user_id": str(uuid.uuid4()),
            "email": "emma.garcia@example.com",
            "username": "emmag",
            "password_hash": pwd_context.hash("emma123"),
            "full_name": "Emma Garcia",
            "role": UserRoleEnum.USER,
            "is_active": True,
            "avatar_url": "https://cdn.example.com/avatars/emma.jpg",
            "preferences": {
                "favorite_teams": ["TEAM007", "TEAM008"],
                "favorite_sports": ["football"],
                "notification_settings": {"match_start": False, "goals": True},
                "preferred_language": "es",
                "timezone": "Europe/Madrid"
            }
        }
    ]
    
    users = {}
    for user_data in users_data:
        user = UserDB(**user_data)
        session.add(user)
        users[user_data["username"]] = user
    
    await session.commit()
    print(f"   ✅ Added {len(users_data)} users")
    return users

async def seed_match_events(session: AsyncSession, matches: dict, teams: dict, match_uuids: dict, team_uuids: dict):
    """Seed match events (goals, cards, substitutions, etc.)"""
    print("📊 Seeding match events...")
    
    match_events_data = [
        # Events for MATCH001 (Arsenal vs Chelsea - Live)
        {
            "match_id": match_uuids["MATCH001"],
            "event_type": "goal",
            "minute": 15,
            "team_id": team_uuids["TEAM001"],
            "player_name": "Gabriel Jesus",
            "description": "Goal! Arsenal takes the lead with a brilliant strike from Gabriel Jesus"
        },
        {
            "match_id": match_uuids["MATCH001"],
            "event_type": "yellow_card",
            "minute": 23,
            "team_id": team_uuids["TEAM002"],
            "player_name": "Enzo Fernandez",
            "description": "Yellow card for Enzo Fernandez for a tactical foul"
        },
        {
            "match_id": match_uuids["MATCH001"],
            "event_type": "goal",
            "minute": 34,
            "team_id": team_uuids["TEAM002"],
            "player_name": "Nicolas Jackson",
            "description": "Goal! Chelsea equalizes through Nicolas Jackson"
        },
        {
            "match_id": match_uuids["MATCH001"],
            "event_type": "goal",
            "minute": 67,
            "team_id": team_uuids["TEAM001"],
            "player_name": "Martin Odegaard",
            "description": "Goal! Arsenal retakes the lead with a penalty by Martin Odegaard"
        },
        
        # Events for MATCH003 (Arsenal vs Liverpool - Finished)
        {
            "match_id": match_uuids["MATCH003"],
            "event_type": "goal",
            "minute": 12,
            "team_id": team_uuids["TEAM001"],
            "player_name": "Bukayo Saka",
            "description": "Goal! Early opener from Bukayo Saka"
        },
        {
            "match_id": match_uuids["MATCH003"],
            "event_type": "goal",
            "minute": 28,
            "team_id": team_uuids["TEAM004"],
            "player_name": "Mohamed Salah",
            "description": "Goal! Liverpool responds with Mohamed Salah"
        },
        {
            "match_id": match_uuids["MATCH003"],
            "event_type": "goal", 
            "minute": 45,
            "team_id": team_uuids["TEAM001"],
            "player_name": "Gabriel Jesus",
            "description": "Goal! Arsenal leads 2-1 at halftime"
        },
        {
            "match_id": match_uuids["MATCH003"],
            "event_type": "substitution",
            "minute": 56,
            "team_id": team_uuids["TEAM004"],
            "player_name": "Darwin Nunez (in) / Diogo Jota (out)",
            "description": "Substitution: Darwin Nunez replaces Diogo Jota"
        },
        {
            "match_id": match_uuids["MATCH003"],
            "event_type": "goal",
            "minute": 73,
            "team_id": team_uuids["TEAM004"],
            "player_name": "Darwin Nunez",
            "description": "Goal! Darwin Nunez equalizes for Liverpool"
        },
        {
            "match_id": match_uuids["MATCH003"],
            "event_type": "goal",
            "minute": 89,
            "team_id": team_uuids["TEAM001"],
            "player_name": "Martin Odegaard",
            "description": "Goal! Late winner from Martin Odegaard seals the victory"
        },
        
        # Events for MATCH005 (Chelsea vs Man City - Finished)
        {
            "match_id": match_uuids["MATCH005"],
            "event_type": "goal",
            "minute": 31,
            "team_id": team_uuids["TEAM002"],
            "player_name": "Raheem Sterling",
            "description": "Goal! Raheem Sterling scores the only goal of the match"
        },
        {
            "match_id": match_uuids["MATCH005"],
            "event_type": "red_card",
            "minute": 78,
            "team_id": team_uuids["TEAM005"],
            "player_name": "Rodri",
            "description": "Red card! Rodri is sent off for a second yellow card"
        },
        
        # Events for MATCH006 (Newcastle vs Brighton - Finished)
        {
            "match_id": match_uuids["MATCH006"],
            "event_type": "goal",
            "minute": 22,
            "team_id": team_uuids["TEAM007"],
            "player_name": "Alexander Isak",
            "description": "Goal! Newcastle takes the lead through Alexander Isak"
        },
        {
            "match_id": match_uuids["MATCH006"],
            "event_type": "goal",
            "minute": 38,
            "team_id": team_uuids["TEAM008"],
            "player_name": "Evan Ferguson",
            "description": "Goal! Brighton equalizes with Evan Ferguson"
        },
        {
            "match_id": match_uuids["MATCH006"],
            "event_type": "goal",
            "minute": 55,
            "team_id": team_uuids["TEAM007"],
            "player_name": "Callum Wilson",
            "description": "Goal! Newcastle retakes the lead"
        },
        {
            "match_id": match_uuids["MATCH006"],
            "event_type": "goal",
            "minute": 82,
            "team_id": team_uuids["TEAM008"],
            "player_name": "Danny Welbeck",
            "description": "Goal! Late equalizer from Danny Welbeck"
        }
    ]
    
    for event_data in match_events_data:
        match_event = MatchEventDB(**event_data)
        session.add(match_event)
    
    await session.commit()
    print(f"   ✅ Added {len(match_events_data)} match events")

async def seed_highlights(session: AsyncSession, match_uuids: dict):
    """Seed highlights"""
    print("🎬 Seeding highlights...")
    
    highlights_data = [
        {
            "match_id": match_uuids["MATCH003"],
            "title": "Arsenal vs Liverpool - All Goals & Highlights",
            "description": "Watch all the goals and best moments from this thrilling 3-2 victory",
            "video_url": "https://cdn.example.com/highlights/match003.mp4",
            "thumbnail_url": "https://cdn.example.com/thumbnails/match003.jpg",
            "duration": 300,
            "tags": ["goals", "highlights", "premier-league", "arsenal", "liverpool"],
            "view_count": 15420
        },
        {
            "match_id": match_uuids["MATCH001"],
            "title": "Arsenal vs Chelsea - Live Match Highlights",
            "description": "Best moments from the ongoing match",
            "video_url": "https://cdn.example.com/highlights/match001.mp4", 
            "thumbnail_url": "https://cdn.example.com/thumbnails/match001.jpg",
            "duration": 180,
            "tags": ["live", "highlights", "arsenal", "chelsea", "premier-league"],
            "view_count": 8934
        },
        {
            "match_id": match_uuids["MATCH003"],
            "title": "Martin Odegaard's Winning Goal - Arsenal vs Liverpool",
            "description": "The decisive goal that sealed Arsenal's victory in the 89th minute",
            "video_url": "https://cdn.example.com/highlights/goal_match003.mp4",
            "thumbnail_url": "https://cdn.example.com/thumbnails/goal_match003.jpg",
            "duration": 45,
            "tags": ["goal", "winner", "arsenal", "odegaard"],
            "view_count": 25000
        },
        {
            "match_id": match_uuids["MATCH005"],
            "title": "Chelsea vs Man City - Champions League Highlights",
            "description": "Sterling's goal secures victory for Chelsea in the Champions League",
            "video_url": "https://cdn.example.com/highlights/match005.mp4",
            "thumbnail_url": "https://cdn.example.com/thumbnails/match005.jpg",
            "duration": 240,
            "tags": ["champions-league", "chelsea", "manchester-city", "sterling"],
            "view_count": 12750
        },
        {
            "match_id": match_uuids["MATCH006"],
            "title": "Newcastle vs Brighton - Thrilling 2-2 Draw",
            "description": "Four goals in an entertaining draw at St. James' Park",
            "video_url": "https://cdn.example.com/highlights/match006.mp4",
            "thumbnail_url": "https://cdn.example.com/thumbnails/match006.jpg",
            "duration": 280,
            "tags": ["draw", "goals", "newcastle", "brighton", "premier-league"],
            "view_count": 9200
        },
        {
            "match_id": match_uuids["MATCH001"],
            "title": "Gabriel Jesus Goal - Arsenal vs Chelsea",
            "description": "Arsenal's opening goal in the live match",
            "video_url": "https://cdn.example.com/highlights/jesus_goal.mp4",
            "thumbnail_url": "https://cdn.example.com/thumbnails/jesus_goal.jpg",
            "duration": 30,
            "tags": ["goal", "arsenal", "gabriel-jesus", "live"],
            "view_count": 18500
        }
    ]
    
    for highlight_data in highlights_data:
        highlight = HighlightDB(**highlight_data)
        session.add(highlight)
    
    await session.commit()
    print(f"   ✅ Added {len(highlights_data)} highlights")

async def seed_user_emoji_reactions(session: AsyncSession, users: dict, emojis: dict, emoji_uuids: dict):
    """Seed user emoji reactions to match events"""
    print("😍 Seeding user emoji reactions...")
    
    # Create realistic emoji reactions for various match events
    reactions_data = []
    
    # Get emoji UUID mappings for easier reference
    emoji_uuid_mapping = {}
    emoji_keys = list(emoji_uuids.keys())
    for i, emoji_key in enumerate(emoji_keys):
        emoji_uuid_mapping[emoji_key] = emoji_uuids[emoji_key]
    
    # Reactions to Arsenal vs Chelsea live match goals
    match_events = [
        {"event": "MATCH001_GOAL_15", "popular_emojis": ["EMJ107", "EMJ104", "EMJ108"]},
        {"event": "MATCH001_GOAL_34", "popular_emojis": ["EMJ107", "EMJ105", "EMJ103"]},
        {"event": "MATCH001_GOAL_67", "popular_emojis": ["EMJ107", "EMJ108", "EMJ104"]},
    ]
    
    # Reactions to finished Arsenal vs Liverpool match
    match_events.extend([
        {"event": "MATCH003_GOAL_12", "popular_emojis": ["EMJ107", "EMJ104"]},
        {"event": "MATCH003_GOAL_28", "popular_emojis": ["EMJ107", "EMJ103"]},
        {"event": "MATCH003_GOAL_45", "popular_emojis": ["EMJ107", "EMJ108"]},
        {"event": "MATCH003_GOAL_73", "popular_emojis": ["EMJ107", "EMJ109"]},
        {"event": "MATCH003_GOAL_89", "popular_emojis": ["EMJ107", "EMJ108", "EMJ104"]},
    ])
    
    # Reactions to Chelsea vs Man City match
    match_events.extend([
        {"event": "MATCH005_GOAL_31", "popular_emojis": ["EMJ107", "EMJ104", "EMJ108"]},
        {"event": "MATCH005_RED_CARD_78", "popular_emojis": ["EMJ109", "EMJ110"]},
    ])
    
    # Reactions to Newcastle vs Brighton match
    match_events.extend([
        {"event": "MATCH006_GOAL_22", "popular_emojis": ["EMJ107", "EMJ103"]},
        {"event": "MATCH006_GOAL_38", "popular_emojis": ["EMJ107", "EMJ105"]},
        {"event": "MATCH006_GOAL_55", "popular_emojis": ["EMJ107", "EMJ104"]},
        {"event": "MATCH006_GOAL_82", "popular_emojis": ["EMJ107", "EMJ109", "EMJ108"]},
    ])
    
    user_list = list(users.keys())
    
    for match_event in match_events:
        # Each event gets reactions from multiple users
        num_reactions = random.randint(8, 20)
        for _ in range(num_reactions):
            user_key = random.choice(user_list)
            emoji_key = random.choice(match_event["popular_emojis"])
            
            reaction_data = {
                "user_id": users[user_key].user_id,
                "event_id": match_event["event"],
                "emoji_id": emoji_uuid_mapping[emoji_key]
            }
            reactions_data.append(reaction_data)
    
    # Add some additional random reactions to general events
    for _ in range(50):
        user_key = random.choice(user_list)
        emoji_key = random.choice(list(emoji_uuid_mapping.keys()))
        event_id = f"GENERAL_EVENT_{random.randint(1000, 9999)}"
        
        reaction_data = {
            "user_id": users[user_key].user_id,
            "event_id": event_id,
            "emoji_id": emoji_uuid_mapping[emoji_key]
        }
        reactions_data.append(reaction_data)
    
    for reaction_data in reactions_data:
        reaction = UserEmojiReactionDB(**reaction_data)
        session.add(reaction)
    
    await session.commit()
    print(f"   ✅ Added {len(reactions_data)} user emoji reactions")

# CLI script entry point
if __name__ == "__main__":
    asyncio.run(seed_database())
