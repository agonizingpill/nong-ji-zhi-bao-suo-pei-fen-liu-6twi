from fastapi import APIRouter,Depends
from sqlalchemy import select
from .database import Session
from .security import current,allow
from .blind_models import BlindReviewConfig,BlindReview
from .blind_schemas import IntervalIn,BallotIn,BlindSignIn
from . import blind_service as blind
router=APIRouter()
@router.get('/blind-review-config')
def get_config(u=Depends(current)):
    with Session() as s:return blind.config_view(s.scalar(select(BlindReviewConfig).order_by(BlindReviewConfig.id)))
@router.put('/blind-review-config')
def put_config(d:IntervalIn,u=Depends(current)):
    allow(u,'admin')
    with Session.begin() as s:return blind.set_interval(s,d,u)
@router.get('/blind-reviews')
def reviews(u=Depends(current)):
    with Session() as s:return [blind.view(s,x) for x in s.scalars(select(BlindReview).order_by(BlindReview.id.desc()))]
@router.post('/blind-reviews/{id}/ballots')
def ballot(id:int,d:BallotIn,u=Depends(current)):
    allow(u,'admin','assessor')
    with Session.begin() as s:return blind.submit_ballot(s,id,d,u)
@router.post('/blind-reviews/{id}/reveal')
def open_up(id:int,u=Depends(current)):
    allow(u,'admin','assessor')
    with Session.begin() as s:return blind.reveal(s,id,u)
@router.post('/blind-reviews/{id}/sign')
def sign_off(id:int,d:BlindSignIn,u=Depends(current)):
    allow(u,'admin')
    with Session.begin() as s:return blind.sign(s,id,d,u)
