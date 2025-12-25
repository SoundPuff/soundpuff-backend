from sqlalchemy import Column, BigInteger, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base


class Comment(Base):
    __tablename__ = "comments"

    id = Column(BigInteger, primary_key=True, index=True, autoincrement=True)
    body = Column(Text, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    playlist_id = Column(BigInteger, ForeignKey("playlists.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_comment_id = Column(BigInteger, ForeignKey("comments.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="comments")
    playlist = relationship("Playlist", back_populates="comments")
    parent = relationship(
        "Comment",
        remote_side=[id],
        back_populates="replies",
        passive_deletes=True,
    )
    replies = relationship(
        "Comment",
        back_populates="parent",
        passive_deletes=True,
        cascade="all, delete-orphan",
        single_parent=True,
    )
    likes = relationship("CommentLike", back_populates="comment", cascade="all, delete-orphan")

    @property
    def likes_count(self) -> int:
        return len(self.likes)

    @property
    def is_liked(self) -> bool:
        return getattr(self, "_is_liked", False)
