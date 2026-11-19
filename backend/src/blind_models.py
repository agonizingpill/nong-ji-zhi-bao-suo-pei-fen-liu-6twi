from sqlalchemy import String,Float,ForeignKey,Text,CheckConstraint,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column
from .database import Base
class BlindReviewConfig(Base):
    __tablename__='blind_review_config'
    __table_args__=(CheckConstraint('low >= 0 AND high <= 1 AND low <= high'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    low:Mapped[float]=mapped_column(Float)
    high:Mapped[float]=mapped_column(Float)
    updated_by:Mapped[str]=mapped_column(String(120),default='')
    updated_at:Mapped[str]=mapped_column(String(40),default='')
class BlindReview(Base):
    __tablename__='blind_reviews'
    __table_args__=(CheckConstraint("state in ('collecting','revealed','signed')"),CheckConstraint('low <= risk AND risk <= high'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    claim_id:Mapped[int]=mapped_column(ForeignKey('claims.id'),unique=True)
    risk:Mapped[float]=mapped_column(Float)
    low:Mapped[float]=mapped_column(Float)
    high:Mapped[float]=mapped_column(Float)
    state:Mapped[str]=mapped_column(String(20),default='collecting')
    decision:Mapped[str|None]=mapped_column(String(10),nullable=True)
    reason:Mapped[str]=mapped_column(Text,default='')
    signed_by:Mapped[str|None]=mapped_column(String(120),nullable=True)
    created_at:Mapped[str]=mapped_column(String(40))
class BlindBallot(Base):
    __tablename__='blind_ballots'
    __table_args__=(UniqueConstraint('review_id','evaluator'),CheckConstraint("opinion in ('paid','denied')"),CheckConstraint('probability >= 0 AND probability <= 1'),)
    id:Mapped[int]=mapped_column(primary_key=True)
    review_id:Mapped[int]=mapped_column(ForeignKey('blind_reviews.id'))
    evaluator:Mapped[str]=mapped_column(String(120))
    opinion:Mapped[str]=mapped_column(String(10))
    probability:Mapped[float]=mapped_column(Float)
    note:Mapped[str]=mapped_column(Text,default='')
    created_at:Mapped[str]=mapped_column(String(40))
