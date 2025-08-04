from typing import Dict, List, Optional
from datetime import datetime, timedelta
import uuid
from ..models.user import User, UserCreate, UserPreferences
from ..models.match import Match, Event, Team, Score, Highlight, SportType, MatchStatus
from ..models.emoji import EmojiAsset, UserEmojiReaction, EmojiReactionSummary, EmojiType

class MockDatabase:
    """
    Mock database implementation for development
    In production, this would be replaced with proper PostgreSQL connection
    """
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.matches: Dict[str, Match] = {}
        self.events: Dict[str, Event] = {}
        self.emojis: Dict[str, EmojiAsset] = {}
        self.reactions: List[UserEmojiReaction] = []
        self.highlights: Dict[str, Highlight] = {}
        
        # Initialize with sample data
        self._initialize_sample_data()
    
    def _initialize_sample_data(self):
        """Initialize database with sample data"""
        
        # Sample emojis
        sample_emojis = [
            {
                "emoji_id": "EMJ103",
                "emoji_type": EmojiType.CLAP,
                "image_url": "https://cdn.mydomain.com/emojis/clap.png",
                "name": "Clap",
                "description": "Show appreciation"
            },
            {
                "emoji_id": "EMJ104", 
                "emoji_type": EmojiType.FIRE,
                "image_url": "https://cdn.mydomain.com/emojis/fire.png",
                "name": "Fire",
                "description": "Amazing play!"
            },
            {
                "emoji_id": "EMJ105",
                "emoji_type": EmojiType.HEART,
                "image_url": "https://cdn.mydomain.com/emojis/heart.png", 
                "name": "Love",
                "description": "Love this moment"
            },
            {
                "emoji_id": "EMJ106",
                "emoji_type": EmojiType.THUMBS_UP,
                "image_url": "https://cdn.mydomain.com/emojis/thumbs_up.png",
                "name": "Thumbs Up", 
                "description": "Great job!"
            },
            {
                "emoji_id": "EMJ107",
                "emoji_type": EmojiType.GOAL,
                "image_url": "https://cdn.mydomain.com/emojis/goal.png",
                "name": "Goal",
                "description": "GOAL!!!"
            }
        ]
        
        for emoji_data in sample_emojis:
            emoji = EmojiAsset(**emoji_data)
            self.emojis[emoji.emoji_id] = emoji
        
        # Sample teams
        teams = {
            "TEAM001": Team(
                team_id="TEAM001",
                name="Arsenal FC",
                short_name="ARS",
                logo_url="https://cdn.example.com/logos/arsenal.png",
                colors={"primary": "#DC143C", "secondary": "#FFFFFF"}
            ),
            "TEAM002": Team(
                team_id="TEAM002", 
                name="Chelsea FC",
                short_name="CHE",
                logo_url="https://cdn.example.com/logos/chelsea.png",
                colors={"primary": "#034694", "secondary": "#FFFFFF"}
            ),
            "TEAM003": Team(
                team_id="TEAM003",
                name="Manchester United",
                short_name="MUN",
                logo_url="https://cdn.example.com/logos/manchester_united.png",
                colors={"primary": "#FF0000", "secondary": "#FFFFFF"}
            ),
            "TEAM004": Team(
                team_id="TEAM004",
                name="Liverpool FC",
                short_name="LIV",
                logo_url="https://cdn.example.com/logos/liverpool.png",
                colors={"primary": "#C8102E", "secondary": "#FFFFFF"}
            )
        }
        
        # Sample events
        event = Event(
            event_id="EVT123",
            name="Premier League 2024-25",
            description="English Premier League Season 2024-25",
            sport_type=SportType.FOOTBALL,
            start_date=datetime.utcnow() - timedelta(days=30),
            end_date=datetime.utcnow() + timedelta(days=200),
            location="England",
            organizer="Premier League",
            is_featured=True
        )
        self.events[event.event_id] = event
        
        # Sample matches
        matches = [
            {
                "match_id": "MATCH001",
                "event_id": "EVT123",
                "home_team": teams["TEAM001"],
                "away_team": teams["TEAM002"],
                "sport_type": SportType.FOOTBALL,
                "status": MatchStatus.LIVE,
                "score": Score(home_score=2, away_score=1),
                "start_time": datetime.utcnow() - timedelta(minutes=45),
                "venue": "Emirates Stadium",
                "competition": "Premier League",
                "round": "Matchday 15",
                "stream_url": "https://stream.example.com/match001"
            },
            {
                "match_id": "MATCH002", 
                "event_id": "EVT123",
                "home_team": teams["TEAM003"],
                "away_team": teams["TEAM004"],
                "sport_type": SportType.FOOTBALL,
                "status": MatchStatus.SCHEDULED,
                "score": Score(),
                "start_time": datetime.utcnow() + timedelta(hours=2),
                "venue": "Old Trafford",
                "competition": "Premier League",
                "round": "Matchday 15",
                "stream_url": "https://stream.example.com/match002"
            },
            {
                "match_id": "MATCH003",
                "event_id": "EVT123", 
                "home_team": teams["TEAM001"],
                "away_team": teams["TEAM004"],
                "sport_type": SportType.FOOTBALL,
                "status": MatchStatus.FINISHED,
                "score": Score(home_score=3, away_score=2),
                "start_time": datetime.utcnow() - timedelta(days=7),
                "end_time": datetime.utcnow() - timedelta(days=7, hours=-2),
                "venue": "Emirates Stadium",
                "competition": "Premier League",
                "round": "Matchday 14"
            }
        ]
        
        for match_data in matches:
            match = Match(**match_data)
            self.matches[match.match_id] = match
        
        # Sample highlights
        highlights = [
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
            }
        ]
        
        for highlight_data in highlights:
            highlight = Highlight(**highlight_data)
            self.highlights[highlight.highlight_id] = highlight
    
    # User operations
    def create_user(self, user_data: UserCreate) -> User:
        """Create a new user"""
        user_id = str(uuid.uuid4())
        user = User(
            user_id=user_id,
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            preferences=UserPreferences()
        )
        self.users[user_id] = user
        return user
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        return self.users.get(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        for user in self.users.values():
            if user.email == email:
                return user
        return None
    
    # Match operations
    def get_matches(self, limit: int = 20, offset: int = 0) -> List[Match]:
        """Get paginated list of matches"""
        matches = list(self.matches.values())
        return matches[offset:offset + limit]
    
    def get_match_by_id(self, match_id: str) -> Optional[Match]:
        """Get match by ID"""
        return self.matches.get(match_id)
    
    def get_live_matches(self) -> List[Match]:
        """Get all live matches"""
        return [match for match in self.matches.values() if match.status == MatchStatus.LIVE]
    
    # Event operations
    def get_events(self, limit: int = 20, offset: int = 0) -> List[Event]:
        """Get paginated list of events"""
        events = list(self.events.values())
        return events[offset:offset + limit]
    
    def get_event_by_id(self, event_id: str) -> Optional[Event]:
        """Get event by ID"""
        return self.events.get(event_id)
    
    # Emoji operations
    def get_emojis(self, limit: int = 10, offset: int = 0) -> List[EmojiAsset]:
        """Get paginated list of emojis"""
        emojis = [emoji for emoji in self.emojis.values() if emoji.is_active]
        emojis.sort(key=lambda x: x.sort_order)
        return emojis[offset:offset + limit]
    
    def get_emoji_by_id(self, emoji_id: str) -> Optional[EmojiAsset]:
        """Get emoji by ID"""
        return self.emojis.get(emoji_id)
    
    def add_reaction(self, reaction: UserEmojiReaction) -> str:
        """Add emoji reaction"""
        reaction_id = str(uuid.uuid4())
        self.reactions.append(reaction)
        return reaction_id
    
    def get_reaction_summary(self, event_id: str) -> EmojiReactionSummary:
        """Get emoji reaction summary for an event"""
        event_reactions = [r for r in self.reactions if r.event_id == event_id]
        
        emoji_counts = {}
        for reaction in event_reactions:
            emoji_counts[reaction.emoji_id] = emoji_counts.get(reaction.emoji_id, 0) + 1
        
        top_emojis = []
        for emoji_id, count in sorted(emoji_counts.items(), key=lambda x: x[1], reverse=True):
            emoji = self.get_emoji_by_id(emoji_id)
            if emoji:
                top_emojis.append({
                    "emoji_id": emoji_id,
                    "emoji_type": emoji.emoji_type.value,
                    "count": count,
                    "image_url": str(emoji.image_url)
                })
        
        return EmojiReactionSummary(
            event_id=event_id,
            emoji_counts=emoji_counts,
            total_reactions=len(event_reactions),
            top_emojis=top_emojis[:5]  # Top 5 emojis
        )
    
    # Highlight operations
    def get_highlights(self, limit: int = 20, offset: int = 0) -> List[Highlight]:
        """Get paginated list of highlights"""
        highlights = list(self.highlights.values())
        highlights.sort(key=lambda x: x.created_at, reverse=True)
        return highlights[offset:offset + limit]
    
    def get_highlight_by_id(self, highlight_id: str) -> Optional[Highlight]:
        """Get highlight by ID"""
        return self.highlights.get(highlight_id)
    
    def get_highlights_by_match(self, match_id: str) -> List[Highlight]:
        """Get highlights for a specific match"""
        return [h for h in self.highlights.values() if h.match_id == match_id]

# Database instance
db = MockDatabase()
