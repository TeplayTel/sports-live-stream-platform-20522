import uuid
import random
from sqlalchemy.ext.asyncio import AsyncSession
from .models import UserEmojiReactionDB

async def seed_user_emoji_reactions(session: AsyncSession, uuid_mappings: dict):
    """
    Seed user emoji reactions to match events using UUID mappings.
    All emoji UUIDs are taken from the uuid_mappings parameter.
    """
    print("😍 Seeding user emoji reactions...")
    
    # Create realistic emoji reactions for various match events
    reactions_data = []
    
    # Define match events and their popular emojis
    match_events = [
        {"event": "MATCH001_GOAL_15", "popular_emojis": ["EMJ107", "EMJ104", "EMJ108"]},
        {"event": "MATCH001_GOAL_34", "popular_emojis": ["EMJ107", "EMJ105", "EMJ103"]},
        {"event": "MATCH001_GOAL_67", "popular_emojis": ["EMJ107", "EMJ108", "EMJ104"]},
        {"event": "MATCH003_GOAL_12", "popular_emojis": ["EMJ107", "EMJ104"]},
        {"event": "MATCH003_GOAL_28", "popular_emojis": ["EMJ107", "EMJ103"]},
        {"event": "MATCH003_GOAL_45", "popular_emojis": ["EMJ107", "EMJ108"]},
        {"event": "MATCH003_GOAL_73", "popular_emojis": ["EMJ107", "EMJ109"]},
        {"event": "MATCH003_GOAL_89", "popular_emojis": ["EMJ107", "EMJ108", "EMJ104"]},
        {"event": "MATCH005_GOAL_31", "popular_emojis": ["EMJ107", "EMJ104", "EMJ108"]},
        {"event": "MATCH005_RED_CARD_78", "popular_emojis": ["EMJ109", "EMJ110"]},
        {"event": "MATCH006_GOAL_22", "popular_emojis": ["EMJ107", "EMJ103"]},
        {"event": "MATCH006_GOAL_38", "popular_emojis": ["EMJ107", "EMJ105"]},
        {"event": "MATCH006_GOAL_55", "popular_emojis": ["EMJ107", "EMJ104"]},
        {"event": "MATCH006_GOAL_82", "popular_emojis": ["EMJ107", "EMJ109", "EMJ108"]}
    ]
    
    user_list = list(uuid_mappings['users'].keys())
    emoji_keys = list(uuid_mappings['emojis'].keys())
    
    # Generate reactions for match events
    for match_event in match_events:
        num_reactions = random.randint(8, 20)
        for _ in range(num_reactions):
            user_key = random.choice(user_list)
            emoji_key = random.choice(match_event["popular_emojis"])
            
            reaction_data = {
                "reaction_id": str(uuid.uuid4()),  # Convert UUID to string for SQLite
                "user_id": uuid_mappings['users'][user_key],
                "event_id": match_event["event"],
                "emoji_id": uuid_mappings['emojis'][emoji_key]
            }
            reactions_data.append(reaction_data)
    
    # Add some random reactions to general events
    for _ in range(50):
        user_key = random.choice(user_list)
        emoji_key = random.choice(emoji_keys)
        event_id = f"GENERAL_EVENT_{random.randint(1000, 9999)}"
        
        reaction_data = {
            "reaction_id": str(uuid.uuid4()),  # Convert UUID to string for SQLite
            "user_id": uuid_mappings['users'][user_key],
            "event_id": event_id,
            "emoji_id": uuid_mappings['emojis'][emoji_key]
        }
        reactions_data.append(reaction_data)
    
    # Add all reactions to the database
    for reaction_data in reactions_data:
        reaction = UserEmojiReactionDB(**reaction_data)
        session.add(reaction)
    
    await session.commit()
    print(f"   ✅ Added {len(reactions_data)} user emoji reactions")
