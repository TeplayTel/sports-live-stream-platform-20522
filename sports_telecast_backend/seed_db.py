#!/usr/bin/env python3
"""
Database seeding script for Sports Telecast Backend

This script populates the database with initial sample data for development and testing.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
import uuid
import random

# Add the src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from passlib.context import CryptContext
from dotenv import load_dotenv
import logging

from database.connection import get_db_session, check_database_connection
from database.models import (
    UserDB, TeamDB, EventDB, MatchDB, EmojiAssetDB, HighlightDB,
    MatchEventDB, UserEmojiReactionDB,
    SportTypeEnum, MatchStatusEnum, UserRoleEnum, EmojiTypeEnum
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# PUBLIC_INTERFACE
def generate_uuid_mappings():
    """
    Generate UUID mappings for all entities to ensure consistent UUID usage across seeding functions
    
    Returns:
        dict: Dictionary containing UUID mappings for all entities
    """
    return {
        'emojis': {
            'EMJ103': uuid.uuid4(),
            'EMJ104': uuid.uuid4(), 
            'EMJ105': uuid.uuid4(),
            'EMJ106': uuid.uuid4(),
            'EMJ107': uuid.uuid4(),
            'EMJ108': uuid.uuid4(),
            'EMJ109': uuid.uuid4(),
            'EMJ110': uuid.uuid4(),
        },
        'teams': {
            'TEAM001': uuid.uuid4(),
            'TEAM002': uuid.uuid4(), 
            'TEAM003': uuid.uuid4(),
            'TEAM004': uuid.uuid4(),
            'TEAM005': uuid.uuid4(),
            'TEAM006': uuid.uuid4(),
            'TEAM007': uuid.uuid4(),
            'TEAM008': uuid.uuid4(),
        },
        'events': {
            'EVT123': uuid.uuid4(),
            'EVT124': uuid.uuid4(),
            'EVT125': uuid.uuid4(),
        },
        'matches': {
            'MATCH001': uuid.uuid4(),
            'MATCH002': uuid.uuid4(), 
            'MATCH003': uuid.uuid4(),
            'MATCH004': uuid.uuid4(),
            'MATCH005': uuid.uuid4(),
            'MATCH006': uuid.uuid4(),
        },
        'highlights': {
            'HIGH001': uuid.uuid4(),
            'HIGH002': uuid.uuid4(),
            'HIGH003': uuid.uuid4(),
            'HIGH004': uuid.uuid4(),
            'HIGH005': uuid.uuid4(),
            'HIGH006': uuid.uuid4(),
        },
        'users': {
            'admin': uuid.uuid4(),
            'johndoe': uuid.uuid4(),
            'sarahw': uuid.uuid4(),
            'mikeb': uuid.uuid4(),
            'emmag': uuid.uuid4(),
        }
    }

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
                return True
        except Exception as e:
            print(f"⚠️ Could not check existing data: {e}")
            print("Proceeding with seeding...")
        
        try:
            # Generate UUID mappings for all entities
            uuid_mappings = generate_uuid_mappings()
            
            # Seed emoji assets first
            await seed_emojis(session, uuid_mappings)
            
            # Seed teams
            await seed_teams(session, uuid_mappings)
            
            # Seed events
            await seed_events(session, uuid_mappings)
            
            # Seed matches
            await seed_matches(session, uuid_mappings)
            
            # Seed users
            await seed_users(session, uuid_mappings)
            
            # Seed match events
            await seed_match_events(session, uuid_mappings)
            
            # Seed highlights
            await seed_highlights(session, uuid_mappings)
            
            # Seed user emoji reactions
            await seed_user_emoji_reactions(session, uuid_mappings)
            
            print("✅ Database seeding completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Database seeding failed: {e}")
            print(f"❌ Error: {e}")
            return False

async def seed_emojis(session: AsyncSession, uuid_mappings: dict):
    """Seed emoji assets using UUID mappings"""
    print("📱 Seeding emoji assets...")
    
    emojis_data = [
        {
            "emoji_id": uuid_mappings['emojis']['EMJ103'],
            "emoji_type": EmojiTypeEnum.CLAP,
            "image_url": "https://cdn.sportstelecast.com/emojis/clap.png",
            "name": "Clap",
            "description": "Show appreciation",
            "sort_order": 1
        },
        {
            "emoji_id": uuid_mappings['emojis']['EMJ104'], 
            "emoji_type": EmojiTypeEnum.FIRE,
            "image_url": "https://cdn.sportstelecast.com/emojis/fire.png",
            "name": "Fire",
            "description": "Amazing play!",
            "sort_order": 2
        },
        {
            "emoji_id": uuid_mappings['emojis']['EMJ105'],
            "emoji_type": EmojiTypeEnum.HEART,
            "image_url": "https://cdn.sportstelecast.com/emojis/heart.png", 
            "name": "Love",
            "description": "Love this moment",
            "sort_order": 3
        },
        {
            "emoji_id": uuid_mappings['emojis']['EMJ106'],
            "emoji_type": EmojiTypeEnum.THUMBS_UP,
            "image_url": "https://cdn.sportstelecast.com/emojis/thumbs_up.png",
            "name": "Thumbs Up", 
            "description": "Great job!",
            "sort_order": 4
        },
        {
            "emoji_id": uuid_mappings['emojis']['EMJ107'],
            "emoji_type": EmojiTypeEnum.GOAL,
            "image_url": "https://cdn.sportstelecast.com/emojis/goal.png",
            "name": "Goal",
            "description": "GOAL!!!",
            "sort_order": 5
        },
        {
            "emoji_id": uuid_mappings['emojis']['EMJ108'],
            "emoji_type": EmojiTypeEnum.CELEBRATION,
            "image_url": "https://cdn.sportstelecast.com/emojis/celebration.png",
            "name": "Celebration",
            "description": "Let's celebrate!",
            "sort_order": 6
        },
        {
            "emoji_id": uuid_mappings['emojis']['EMJ109'],
            "emoji_type": EmojiTypeEnum.SHOCKED,
            "image_url": "https://cdn.sportstelecast.com/emojis/shocked.png",
            "name": "Shocked",
            "description": "What a surprise!",
            "sort_order": 7
        },
        {
            "emoji_id": uuid_mappings['emojis']['EMJ110'],
            "emoji_type": EmojiTypeEnum.LAUGH,
            "image_url": "https://cdn.sportstelecast.com/emojis/laugh.png",
            "name": "Laugh",
            "description": "That was funny!",
            "sort_order": 8
        }
    ]
    
    emojis = {}
    for emoji_data in emojis_data:
        emoji = EmojiAssetDB(**emoji_data)
        session.add(emoji)
        # Map using original string keys for backward compatibility
        reverse_key = next(k for k, v in uuid_mappings['emojis'].items() if v == emoji_data["emoji_id"])
        emojis[reverse_key] = emoji
    
    await session.commit()
    print(f"   ✅ Added {len(emojis_data)} emoji assets")
    return emojis

async def seed_teams(session: AsyncSession, uuid_mappings: dict):
    """Seed teams using UUID mappings"""
    print("🏟️ Seeding teams...")
    
    teams_data = [
        {
            "team_id": uuid_mappings['teams']['TEAM001'],
            "name": "Arsenal FC",
            "short_name": "ARS",
            "logo_url": "https://cdn.sportstelecast.com/logos/arsenal.png",
            "colors": {"primary": "#DC143C", "secondary": "#FFFFFF"}
        },
        {
            "team_id": uuid_mappings['teams']['TEAM002'], 
            "name": "Chelsea FC",
            "short_name": "CHE",
            "logo_url": "https://cdn.sportstelecast.com/logos/chelsea.png",
            "colors": {"primary": "#034694", "secondary": "#FFFFFF"}
        },
        {
            "team_id": uuid_mappings['teams']['TEAM003'],
            "name": "Manchester United",
            "short_name": "MUN",
            "logo_url": "https://cdn.sportstelecast.com/logos/manchester_united.png",
            "colors": {"primary": "#FF0000", "secondary": "#FFFFFF"}
        },
        {
            "team_id": uuid_mappings['teams']['TEAM004'],
            "name": "Liverpool FC",
            "short_name": "LIV",
            "logo_url": "https://cdn.sportstelecast.com/logos/liverpool.png",
            "colors": {"primary": "#C8102E", "secondary": "#FFFFFF"}
        },
        {
            "team_id": uuid_mappings['teams']['TEAM005'],
            "name": "Manchester City",
            "short_name": "MCI",
            "logo_url": "https://cdn.sportstelecast.com/logos/manchester_city.png",
            "colors": {"primary": "#6CABDD", "secondary": "#FFFFFF"}
        },
        {
            "team_id": uuid_mappings['teams']['TEAM006'],
            "name": "Tottenham Hotspur",
            "short_name": "TOT",
            "logo_url": "https://cdn.sportstelecast.com/logos/tottenham.png",
            "colors": {"primary": "#132257", "secondary": "#FFFFFF"}
        },
        {
            "team_id": uuid_mappings['teams']['TEAM007'],
            "name": "Newcastle United",
            "short_name": "NEW",
            "logo_url": "https://cdn.sportstelecast.com/logos/newcastle.png",
            "colors": {"primary": "#000000", "secondary": "#FFFFFF"}
        },
        {
            "team_id": uuid_mappings['teams']['TEAM008'],
            "name": "Brighton & Hove Albion",
            "short_name": "BHA",
            "logo_url": "https://cdn.sportstelecast.com/logos/brighton.png",
            "colors": {"primary": "#0057B8", "secondary": "#FFCD00"}
        }
    ]
    
    teams = {}
    for team_data in teams_data:
        team = TeamDB(**team_data)
        session.add(team)
        # Map using original string keys for backward compatibility
        reverse_key = next(k for k, v in uuid_mappings['teams'].items() if v == team_data["team_id"])
        teams[reverse_key] = team
    
    await session.commit()
    print(f"   ✅ Added {len(teams_data)} teams")
    return teams

async def seed_events(session: AsyncSession, uuid_mappings: dict):
    """Seed events using UUID mappings"""
    print("🏆 Seeding events...")
    
    events_data = [
        {
            "event_id": uuid_mappings['events']['EVT123'],
            "name": "Premier League 2024-25",
            "description": "English Premier League Season 2024-25",
            "sport_type": SportTypeEnum.FOOTBALL,
            "start_date": datetime.utcnow() - timedelta(days=30),
            "end_date": datetime.utcnow() + timedelta(days=200),
            "location": "England",
            "organizer": "Premier League",
            "logo_url": "https://cdn.sportstelecast.com/logos/premier_league.png",
            "banner_url": "https://cdn.sportstelecast.com/banners/premier_league.jpg",
            "is_featured": True
        },
        {
            "event_id": uuid_mappings['events']['EVT124'],
            "name": "Champions League 2024-25",
            "description": "UEFA Champions League Season 2024-25",
            "sport_type": SportTypeEnum.FOOTBALL,
            "start_date": datetime.utcnow() - timedelta(days=60),
            "end_date": datetime.utcnow() + timedelta(days=180),
            "location": "Europe",
            "organizer": "UEFA",
            "logo_url": "https://cdn.sportstelecast.com/logos/champions_league.png",
            "banner_url": "https://cdn.sportstelecast.com/banners/champions_league.jpg",
            "is_featured": True
        },
        {
            "event_id": uuid_mappings['events']['EVT125'],
            "name": "FA Cup 2024-25",
            "description": "The Football Association Challenge Cup",
            "sport_type": SportTypeEnum.FOOTBALL,
            "start_date": datetime.utcnow() - timedelta(days=45),
            "end_date": datetime.utcnow() + timedelta(days=120),
            "location": "England",
            "organizer": "The FA",
            "logo_url": "https://cdn.sportstelecast.com/logos/fa_cup.png",
            "banner_url": "https://cdn.sportstelecast.com/banners/fa_cup.jpg",
            "is_featured": False
        }
    ]
    
    events = {}
    for event_data in events_data:
        event = EventDB(**event_data)
        session.add(event)
        # Map using original string keys for backward compatibility
        reverse_key = next(k for k, v in uuid_mappings['events'].items() if v == event_data["event_id"])
        events[reverse_key] = event
    
    await session.commit()
    print(f"   ✅ Added {len(events_data)} events")
    return events

async def seed_matches(session: AsyncSession, uuid_mappings: dict):
    """Seed matches using UUID mappings"""
    print("⚽ Seeding matches...")
    
    matches_data = [
        {
            "match_id": uuid_mappings['matches']['MATCH001'],
            "event_id": uuid_mappings['events']['EVT123'],
            "home_team_id": uuid_mappings['teams']['TEAM001'],
            "away_team_id": uuid_mappings['teams']['TEAM002'],
            "sport_type": SportTypeEnum.FOOTBALL,
            "status": MatchStatusEnum.LIVE,
            "home_score": 2,
            "away_score": 1,
            "start_time": datetime.utcnow() - timedelta(minutes=45),
            "venue": "Emirates Stadium",
            "competition": "Premier League",
            "round": "Matchday 15",
            "stream_url": "https://stream.sportstelecast.com/match001",
            "statistics": {
                "possession": {"home": 58, "away": 42},
                "shots": {"home": 12, "away": 8},
                "corners": {"home": 6, "away": 3}
            }
        },
        {
            "match_id": uuid_mappings['matches']['MATCH002'], 
            "event_id": uuid_mappings['events']['EVT123'],
            "home_team_id": uuid_mappings['teams']['TEAM003'],
            "away_team_id": uuid_mappings['teams']['TEAM004'],
            "sport_type": SportTypeEnum.FOOTBALL,
            "status": MatchStatusEnum.SCHEDULED,
            "home_score": 0,
            "away_score": 0,
            "start_time": datetime.utcnow() + timedelta(hours=2),
            "venue": "Old Trafford",
            "competition": "Premier League",
            "round": "Matchday 15",
            "stream_url": "https://stream.sportstelecast.com/match002"
        },
        {
            "match_id": uuid_mappings['matches']['MATCH003'],
            "event_id": uuid_mappings['events']['EVT123'], 
            "home_team_id": uuid_mappings['teams']['TEAM001'],
            "away_team_id": uuid_mappings['teams']['TEAM004'],
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
            "match_id": uuid_mappings['matches']['MATCH004'],
            "event_id": uuid_mappings['events']['EVT123'],
            "home_team_id": uuid_mappings['teams']['TEAM005'],
            "away_team_id": uuid_mappings['teams']['TEAM006'],
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
            "match_id": uuid_mappings['matches']['MATCH005'],
            "event_id": uuid_mappings['events']['EVT124'],
            "home_team_id": uuid_mappings['teams']['TEAM002'],
            "away_team_id": uuid_mappings['teams']['TEAM005'],
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
            "match_id": uuid_mappings['matches']['MATCH006'],
            "event_id": uuid_mappings['events']['EVT123'],
            "home_team_id": uuid_mappings['teams']['TEAM007'],
            "away_team_id": uuid_mappings['teams']['TEAM008'],
            "sport_type": SportTypeEnum.FOOTBALL,
            "status": MatchStatusEnum.FINISHED,
            "home_score": 2,
            "away_score": 2,
            "start_time": datetime.utcnow() - timedelta(days=2),
            "end_time": datetime.utcnow() - timedelta(days=2, hours=-2),
            "venue": "St. James' Park",
            "competition": "Premier League",
            "round": "Matchday 14"
        }
    ]
    
    matches = {}
    for match_data in matches_data:
        match = MatchDB(**match_data)
        session.add(match)
        # Map using original string keys for backward compatibility
        reverse_key = next(k for k, v in uuid_mappings['matches'].items() if v == match_data["match_id"])
        matches[reverse_key] = match
    
    await session.commit()
    print(f"   ✅ Added {len(matches_data)} matches")
    return matches

async def seed_users(session: AsyncSession, uuid_mappings: dict):
    """Seed sample users using UUID mappings"""
    print("👤 Seeding users...")
    
    users_data = [
        {
            "user_id": uuid_mappings['users']['admin'],
            "email": "admin@sportstelecast.com",
            "username": "admin",
            "password_hash": pwd_context.hash("admin123"),
            "full_name": "System Administrator",
            "role": UserRoleEnum.ADMIN,
            "is_active": True,
            "avatar_url": "https://cdn.sportstelecast.com/avatars/admin.jpg",
            "preferences": {
                "favorite_teams": ["TEAM001", "TEAM003"],
                "favorite_sports": ["football"],
                "notification_settings": {"match_start": True, "goals": True},
                "preferred_language": "en",
                "timezone": "UTC"
            }
        },
        {
            "user_id": uuid_mappings['users']['johndoe'],
            "email": "john.doe@example.com",
            "username": "johndoe",
            "password_hash": pwd_context.hash("password123"),
            "full_name": "John Doe",
            "role": UserRoleEnum.USER,
            "is_active": True,
            "avatar_url": "https://cdn.sportstelecast.com/avatars/john.jpg",
            "preferences": {
                "favorite_teams": ["TEAM002", "TEAM004"],
                "favorite_sports": ["football"],
                "notification_settings": {"match_start": True, "goals": False},
                "preferred_language": "en",
                "timezone": "UTC"
            }
        },
        {
            "user_id": uuid_mappings['users']['sarahw'],
            "email": "sarah.wilson@example.com",
            "username": "sarahw",
            "password_hash": pwd_context.hash("sarah123"),
            "full_name": "Sarah Wilson",
            "role": UserRoleEnum.USER,
            "is_active": True,
            "avatar_url": "https://cdn.sportstelecast.com/avatars/sarah.jpg",
            "preferences": {
                "favorite_teams": ["TEAM001", "TEAM005"],
                "favorite_sports": ["football"],
                "notification_settings": {"match_start": True, "goals": True},
                "preferred_language": "en",
                "timezone": "America/New_York"
            }
        },
        {
            "user_id": uuid_mappings['users']['mikeb'],
            "email": "mike.brown@example.com",
            "username": "mikeb",
            "password_hash": pwd_context.hash("mike123"),
            "full_name": "Mike Brown",
            "role": UserRoleEnum.MODERATOR,
            "is_active": True,
            "avatar_url": "https://cdn.sportstelecast.com/avatars/mike.jpg",
            "preferences": {
                "favorite_teams": ["TEAM006", "TEAM002"],
                "favorite_sports": ["football"],
                "notification_settings": {"match_start": True, "goals": True},
                "preferred_language": "en",
                "timezone": "Europe/London"
            }
        },
        {
            "user_id": uuid_mappings['users']['emmag'],
            "email": "emma.garcia@example.com",
            "username": "emmag",
            "password_hash": pwd_context.hash("emma123"),
            "full_name": "Emma Garcia",
            "role": UserRoleEnum.USER,
            "is_active": True,
            "avatar_url": "https://cdn.sportstelecast.com/avatars/emma.jpg",
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

async def seed_match_events(session: AsyncSession, uuid_mappings: dict):
    """Seed match events (goals, cards, substitutions, etc.) using UUID mappings"""
    print("📊 Seeding match events...")
    
    match_events_data = [
        # Events for MATCH001 (Arsenal vs Chelsea - Live)
        {
            "event_id": uuid.uuid4(),
            "match_id": uuid_mappings['matches']['MATCH001'],
            "event_type": "goal",
            "minute": 15,
            "team_id": uuid_mappings['teams']['TEAM001'],
            "player_name": "Gabriel Jesus",
            "description": "Goal! Arsenal takes the lead with a brilliant strike from Gabriel Jesus"
        },
        {
            "event_id": uuid.uuid4(),
            "match_id": uuid_mappings['matches']['MATCH001'],
            "event_type": "yellow_card",
            "minute": 23,
            "team_id": uuid_mappings['teams']['TEAM002'],
            "player_name": "Enzo Fernandez",
            "description": "Yellow card for Enzo Fernandez for a tactical foul"
        },
        {
            "event_id": uuid.uuid4(),
            "match_id": uuid_mappings['matches']['MATCH001'],
            "event_type": "goal",
            "minute": 34,
            "team_id": uuid_mappings['teams']['TEAM002'],
            "player_name": "Nicolas Jackson",
            "description": "Goal! Chelsea equalizes through Nicolas Jackson"
        },
        {
            "event_id": uuid.uuid4(),
            "match_id": uuid_mappings['matches']['MATCH001'],
            "event_type": "goal",
            "minute": 67,
            "team_id": uuid_mappings['teams']['TEAM001'],
            "player_name": "Martin Odegaard",
            "description": "Goal! Arsenal retakes the lead with a penalty by Martin Odegaard"
        },
        
        # Events for MATCH003 (Arsenal vs Liverpool - Finished)
        {
            "event_id": uuid.uuid4(),
            "match_id": uuid_mappings['matches']['MATCH003'],
            "event_type": "goal",
            "minute": 12,
            "team_id": uuid_mappings['teams']['TEAM001'],
            "player_name": "Bukayo Saka",
            "description": "Goal! Early opener from Bukayo Saka"
        },
        {
            "event_id": uuid.uuid4(),
            "match_id": uuid_mappings['matches']['MATCH003'],
            "event_type": "goal",
            "minute": 28,
            "team_id": uuid_mappings['teams']['TEAM004'],
            "player_name": "Mohamed Salah",
            "description": "Goal! Liverpool responds with Mohamed Salah"
        },
        {
            "event_id": uuid.uuid4(),
            "match_id": uuid_mappings['matches']['MATCH003'],
            "event_type": "goal", 
            "minute": 45,
            "team_id": uuid_mappings['teams']['TEAM001'],
            "player_name": "Gabriel Jesus",
            "description": "Goal! Arsenal leads 2-1 at halftime"
        },
        {
            "event_id": uuid.uuid4(),
            "match_id": uuid_mappings['matches']['MATCH003'],
            "event_type": "substitution",
            "minute": 56,
            "team_id": uuid_mappings['teams']['TEAM004'],
            "player_name": "Darwin Nunez (in) / Diogo Jota (out)",
            "description": "Substitution: Darwin Nunez replaces Diogo Jota"
        },
        {
            "event_id": uuid.uuid4(),
            "match_id": uuid_mappings['matches']['MATCH003'],
            "event_type": "goal",
            "minute": 73,
            "team_id": uuid_mappings['teams']['TEAM004'],
            "player_name": "Darwin Nunez",
            "description": "Goal! Darwin Nunez equalizes for Liverpool"
        },
        {
            "event_id": uuid.uuid4(),
            "match_id": uuid_mappings['matches']['MATCH003'],
            "event_type": "goal",
            "minute": 89,
            "team_id": uuid_mappings['teams']['TEAM001'],
            "player_name": "Martin Odegaard",
            "description": "Goal! Late winner from Martin Odegaard seals the victory"
        },
        
        # Events for MATCH005 (Chelsea vs Man City - Finished)
        {
            "event_id": uuid.uuid4(),
            "match_id": uuid_mappings['matches']['MATCH005'],
            "event_type": "goal",
            "minute": 31,
            "team_id": uuid_mappings['teams']['TEAM002'],
            "player_name": "Raheem Sterling",
            "description": "Goal! Raheem Sterling scores the only goal of the match"
        },
        {
            "event_id": uuid.uuid4(),
            "match_id": uuid_mappings['matches']['MATCH005'],
            "event_type": "red_card",
            "minute": 78,
            "team_id": uuid_mappings['teams']['TEAM005'],
            "player_name": "Rodri",
            "description": "Red card! Rodri is sent off for a second yellow card"
        },
        
        # Events for MATCH006 (Newcastle vs Brighton - Finished)
        {
            "event_id": uuid.uuid4(),
            "match_id": uuid_mappings['matches']['MATCH006'],
            "event_type": "goal",
            "minute": 22,
            "team_id": uuid_mappings['teams']['TEAM007'],
            "player_name": "Alexander Isak",
            "description": "Goal! Newcastle takes the lead through Alexander Isak"
        },
        {
            "event_id": uuid.uuid4(),
            "match_id": uuid_mappings['matches']['MATCH006'],
            "event_type": "goal",
            "minute": 38,
            "team_id": uuid_mappings['teams']['TEAM008'],
            "player_name": "Evan Ferguson",
            "description": "Goal! Brighton equalizes with Evan Ferguson"
        },
        {
            "event_id": uuid.uuid4(),
            "match_id": uuid_mappings['matches']['MATCH006'],
            "event_type": "goal",
            "minute": 55,
            "team_id": uuid_mappings['teams']['TEAM007'],
            "player_name": "Callum Wilson",
            "description": "Goal! Newcastle retakes the lead"
        },
        {
            "event_id": uuid.uuid4(),
            "match_id": uuid_mappings['matches']['MATCH006'],
            "event_type": "goal",
            "minute": 82,
            "team_id": uuid_mappings['teams']['TEAM008'],
            "player_name": "Danny Welbeck",
            "description": "Goal! Late equalizer from Danny Welbeck"
        }
    ]
    
    for event_data in match_events_data:
        match_event = MatchEventDB(**event_data)
        session.add(match_event)
    
    await session.commit()
    print(f"   ✅ Added {len(match_events_data)} match events")

async def seed_highlights(session: AsyncSession, uuid_mappings: dict):
    """Seed highlights using UUID mappings"""
    print("🎬 Seeding highlights...")
    
    highlights_data = [
        {
            "highlight_id": uuid_mappings['highlights']['HIGH001'],
            "match_id": uuid_mappings['matches']['MATCH003'],
            "title": "Arsenal vs Liverpool - All Goals & Highlights",
            "description": "Watch all the goals and best moments from this thrilling 3-2 victory",
            "video_url": "https://cdn.sportstelecast.com/highlights/match003.mp4",
            "thumbnail_url": "https://cdn.sportstelecast.com/thumbnails/match003.jpg",
            "duration": 300,
            "tags": ["goals", "highlights", "premier-league", "arsenal", "liverpool"],
            "view_count": 15420
        },
        {
            "highlight_id": uuid_mappings['highlights']['HIGH002'],
            "match_id": uuid_mappings['matches']['MATCH001'],
            "title": "Arsenal vs Chelsea - Live Match Highlights",
            "description": "Best moments from the ongoing match",
            "video_url": "https://cdn.sportstelecast.com/highlights/match001.mp4", 
            "thumbnail_url": "https://cdn.sportstelecast.com/thumbnails/match001.jpg",
            "duration": 180,
            "tags": ["live", "highlights", "arsenal", "chelsea", "premier-league"],
            "view_count": 8934
        },
        {
            "highlight_id": uuid_mappings['highlights']['HIGH003'],
            "match_id": uuid_mappings['matches']['MATCH003'],
            "title": "Martin Odegaard's Winning Goal - Arsenal vs Liverpool",
            "description": "The decisive goal that sealed Arsenal's victory in the 89th minute",
            "video_url": "https://cdn.sportstelecast.com/highlights/goal_match003.mp4",
            "thumbnail_url": "https://cdn.sportstelecast.com/thumbnails/goal_match003.jpg",
            "duration": 45,
            "tags": ["goal", "winner", "arsenal", "odegaard"],
            "view_count": 25000
        },
        {
            "highlight_id": uuid_mappings['highlights']['HIGH004'],
            "match_id": uuid_mappings['matches']['MATCH005'],
            "title": "Chelsea vs Man City - Champions League Highlights",
            "description": "Sterling's goal secures victory for Chelsea in the Champions League",
            "video_url": "https://cdn.sportstelecast.com/highlights/match005.mp4",
            "thumbnail_url": "https://cdn.sportstelecast.com/thumbnails/match005.jpg",
            "duration": 240,
            "tags": ["champions-league", "chelsea", "manchester-city", "sterling"],
            "view_count": 12750
        },
        {
            "highlight_id": uuid_mappings['highlights']['HIGH005'],
            "match_id": uuid_mappings['matches']['MATCH006'],
            "title": "Newcastle vs Brighton - Thrilling 2-2 Draw",
            "description": "Four goals in an entertaining draw at St. James' Park",
            "video_url": "https://cdn.sportstelecast.com/highlights/match006.mp4",
            "thumbnail_url": "https://cdn.sportstelecast.com/thumbnails/match006.jpg",
            "duration": 280,
            "tags": ["draw", "goals", "newcastle", "brighton", "premier-league"],
            "view_count": 9200
        },
        {
            "highlight_id": uuid_mappings['highlights']['HIGH006'],
            "match_id": uuid_mappings['matches']['MATCH001'],
            "title": "Gabriel Jesus Goal - Arsenal vs Chelsea",
            "description": "Arsenal's opening goal in the live match",
            "video_url": "https://cdn.sportstelecast.com/highlights/jesus_goal.mp4",
            "thumbnail_url": "https://cdn.sportstelecast.com/thumbnails/jesus_goal.jpg",
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

async def seed_user_emoji_reactions(session: AsyncSession, uuid_mappings: dict):
    """Seed user emoji reactions to match events using UUID mappings"""
    print("😍 Seeding user emoji reactions...")
    
    # Create realistic emoji reactions for various match events
    reactions_data = []
    
    # Generate proper UUID event IDs for match events instead of using string identifiers
    match_events = [
        {"event": str(uuid.uuid4()), "popular_emojis": ["EMJ107", "EMJ104", "EMJ108"]},
        {"event": str(uuid.uuid4()), "popular_emojis": ["EMJ107", "EMJ105", "EMJ103"]},
        {"event": str(uuid.uuid4()), "popular_emojis": ["EMJ107", "EMJ108", "EMJ104"]},
    ]
    
    # Reactions to finished Arsenal vs Liverpool match
    match_events.extend([
        {"event": str(uuid.uuid4()), "popular_emojis": ["EMJ107", "EMJ104"]},
        {"event": str(uuid.uuid4()), "popular_emojis": ["EMJ107", "EMJ103"]},
        {"event": str(uuid.uuid4()), "popular_emojis": ["EMJ107", "EMJ108"]},
        {"event": str(uuid.uuid4()), "popular_emojis": ["EMJ107", "EMJ109"]},
        {"event": str(uuid.uuid4()), "popular_emojis": ["EMJ107", "EMJ108", "EMJ104"]},
    ])
    
    # Reactions to Chelsea vs Man City match
    match_events.extend([
        {"event": str(uuid.uuid4()), "popular_emojis": ["EMJ107", "EMJ104", "EMJ108"]},
        {"event": str(uuid.uuid4()), "popular_emojis": ["EMJ109", "EMJ110"]},
    ])
    
    # Reactions to Newcastle vs Brighton match
    match_events.extend([
        {"event": str(uuid.uuid4()), "popular_emojis": ["EMJ107", "EMJ103"]},
        {"event": str(uuid.uuid4()), "popular_emojis": ["EMJ107", "EMJ105"]},
        {"event": str(uuid.uuid4()), "popular_emojis": ["EMJ107", "EMJ104"]},
        {"event": str(uuid.uuid4()), "popular_emojis": ["EMJ107", "EMJ109", "EMJ108"]},
    ])
    
    user_list = list(uuid_mappings['users'].keys())
    
    for match_event in match_events:
        # Each event gets reactions from multiple users
        num_reactions = random.randint(8, 20)
        for _ in range(num_reactions):
            user_key = random.choice(user_list)
            emoji_key = random.choice(match_event["popular_emojis"])
            
            reaction_data = {
                "reaction_id": uuid.uuid4(),
                "user_id": uuid_mappings['users'][user_key],
                "event_id": match_event["event"],
                "emoji_id": uuid_mappings['emojis'][emoji_key]
            }
            reactions_data.append(reaction_data)
    
    # Add some additional random reactions to general events with proper UUIDs
    for _ in range(50):
        user_key = random.choice(user_list)
        emoji_key = random.choice(list(uuid_mappings['emojis'].keys()))
        event_id = str(uuid.uuid4())  # Use proper UUID instead of string
        
        reaction_data = {
            "reaction_id": uuid.uuid4(),
            "user_id": uuid_mappings['users'][user_key],
            "event_id": event_id,
            "emoji_id": uuid_mappings['emojis'][emoji_key]
        }
        reactions_data.append(reaction_data)
    
    for reaction_data in reactions_data:
        reaction = UserEmojiReactionDB(**reaction_data)
        session.add(reaction)
    
    await session.commit()
    print(f"   ✅ Added {len(reactions_data)} user emoji reactions")

async def main():
    """Main function to run database seeding"""
    print("🚀 Sports Telecast Database Seeding")
    print("=" * 50)
    
    try:
        # Check database connection first
        print("🔗 Checking database connection...")
        if await check_database_connection():
            print("✅ Database connection successful")
        else:
            print("❌ Database connection failed")
            return False
            
        # Run seeding
        success = await seed_database()
        
        if success:
            print("\n🎉 Database seeding completed!")
            print("\nSeeded tables:")
            print("  • users - 5 sample users (admin, johndoe, sarahw, mikeb, emmag)")
            print("  • teams - 8 Premier League teams")
            print("  • events - 3 sports events (Premier League, Champions League, FA Cup)")
            print("  • matches - 6 matches with various statuses")
            print("  • match_events - 16 match events (goals, cards, substitutions)")
            print("  • emoji_assets - 8 emoji reaction types")
            print("  • user_emoji_reactions - 100+ user reactions to match events")
            print("  • highlights - 6 match highlight videos")
            print("\nLogin credentials:")
            print("  Admin: admin@sportstelecast.com / admin123")
            print("  User: john.doe@example.com / password123")
        
        return success
        
    except Exception as e:
        logger.error(f"Database seeding failed: {e}")
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
