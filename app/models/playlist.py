from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import object_session, relationship
from app.db.base_class import Base
from app.models.association_tables import playlist_songs


class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    privacy = Column(String(20), nullable=False, server_default="public", default="public")
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships (using lazy='select' to defer loading until needed)
    owner = relationship("User", back_populates="playlists", lazy="select")
    songs = relationship("Song", secondary=playlist_songs, back_populates="playlists", lazy="select")
    comments = relationship("Comment", back_populates="playlist", cascade="all, delete-orphan", lazy="select")
    likes = relationship("Like", back_populates="playlist", cascade="all, delete-orphan", lazy="select")

    @property
    def likes_count(self) -> int:
        if "likes" in self.__dict__:
            return len(self.likes)

        session = object_session(self)
        if session is None:
            return 0

        from app.models.like import Like  # Imported lazily to avoid circular imports

        return (
            session.query(func.count(Like.user_id))
            .filter(Like.playlist_id == self.id)
            .scalar()
            or 0
        )

    @property
    def comments_count(self) -> int:
        if "comments" in self.__dict__:
            return len(self.comments)

        session = object_session(self)
        if session is None:
            return 0

        from app.models.comment import Comment  # Imported lazily to avoid circular imports

        return (
            session.query(func.count(Comment.id))
            .filter(Comment.playlist_id == self.id)
            .scalar()
            or 0
        )
