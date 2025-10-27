from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base
import uuid


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(255), unique=True, index=True, nullable=False)
    avatar_url = Column(String(255), nullable=True)
    bio = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    playlists = relationship("Playlist", back_populates="owner")
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="user", cascade="all, delete-orphan")
    followers = relationship(
        "User",
        secondary="follows",
        primaryjoin="User.id==follows.c.following_id",
        secondaryjoin="User.id==follows.c.follower_id",
        back_populates="following"
    )
    following = relationship(
        "User",
        secondary="follows",
        primaryjoin="User.id==follows.c.follower_id",
        secondaryjoin="User.id==follows.c.following_id",
        back_populates="followers"
    )