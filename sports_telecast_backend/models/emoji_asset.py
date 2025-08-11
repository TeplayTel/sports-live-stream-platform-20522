from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

# PUBLIC_INTERFACE
class EmojiAsset(Base):
    """SQLAlchemy DB model for uploaded emoji assets."""
    __tablename__ = "emoji_assets"
    emoji_id = Column(String(36), primary_key=True, index=True)  # UUID hex
    emoji_type = Column(String(32), nullable=False)
    file_location = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
