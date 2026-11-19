from datetime import datetime,timezone
from sqlalchemy import select
from fastapi import HTTPException
from .models import Claim
from .blind_models import BlindReviewConfig,BlindReview,BlindBallot
from .claim_service import get,audit,adjudicate

DEFAULT_LOW,DEFAULT_HIGH=.4,.6
def now():return datetime.now(timezone.utc).isoformat()
def interval(s):
    cfg=s.scalar(select(BlindReviewConfig).order_by(BlindReviewConfig.id))
    return (cfg.low,cfg.high) if cfg else (DEFAULT_LOW,DEFAULT_HIGH)
def config_view(cfg):return {'low':cfg.low,'high':cfg.high,'updated_by':cfg.updated_by,'updated_at':cfg.updated_at} if cfg else {'low':DEFAULT_LOW,'high':DEFAULT_HIGH,'updated_by':'','updated_at':''}
def set_interval(s,d,u):
    if d.low>d.high:raise HTTPException(409,'盲审区间下限不能高于上限')
    cfg=s.scalar(select(BlindReviewConfig).order_by(BlindReviewConfig.id).with_for_update())
    if not cfg:cfg=BlindReviewConfig(low=d.low,high=d.high);s.add(cfg)
    cfg.low,cfg.high=d.low,d.high;cfg.updated_by=u['email'];cfg.updated_at=now()
    s.flush();audit(s,u,'blind_interval_updated',f'[{d.low:.2f},{d.high:.2f}]，仅影响之后受理的分流');return config_view(cfg)
def locked(s,id):
    x=s.scalar(select(BlindReview).where(BlindReview.id==id).with_for_update().execution_options(populate_existing=True))
    if not x:raise HTTPException(404,'盲审记录不存在')
    return x
def ballots_of(s,review_id,lock=False):
    q=select(BlindBallot).where(BlindBallot.review_id==review_id).order_by(BlindBallot.id)
    if lock:q=q.with_for_update()
    return s.scalars(q).all()
def view(s,x):
    c=get(s,Claim,x.claim_id);shown=x.state in ('revealed','signed')
    return {k:getattr(x,k) for k in ['id','claim_id','risk','low','high','state','decision','reason','signed_by','created_at']}|{'claim_code':c.code,'claim_status':c.status,'ballots':[{'id':b.id,'evaluator':b.evaluator,'created_at':b.created_at,'opinion':b.opinion if shown else None,'probability':b.probability if shown else None,'note':b.note if shown else None} for b in ballots_of(s,x.id)]}
def submit_ballot(s,id,d,u):
    x=locked(s,id)
    if x.state!='collecting':raise HTTPException(409,'盲审已揭盲或签署，不能再交卷')
    ballots=ballots_of(s,x.id,lock=True)
    mine=[b for b in ballots if b.evaluator==u['email']]
    if mine:
        b=mine[0]
        if b.opinion==d.opinion and abs(b.probability-d.probability)<1e-9 and b.note==d.note.strip():return view(s,x)
        raise HTTPException(409,'已交卷，结论不可更改；重试不会重复记票')
    if len(ballots)>=2:raise HTTPException(409,'盲审只需两名评估员，交卷已满')
    s.add(BlindBallot(review_id=x.id,evaluator=u['email'],opinion=d.opinion,probability=d.probability,note=d.note.strip(),created_at=now()))
    s.flush();audit(s,u,'blind_ballot_submitted',f'{get(s,Claim,x.claim_id).code}:{len(ballots)+1}/2');return view(s,x)
def reveal(s,id,u):
    x=locked(s,id)
    if x.state=='collecting':
        if len(ballots_of(s,x.id,lock=True))<2:raise HTTPException(409,'须两名评估员交齐后才能揭盲')
        x.state='revealed';audit(s,u,'blind_revealed',get(s,Claim,x.claim_id).code)
    return view(s,x)
def sign(s,id,d,u):
    x=locked(s,id)
    if x.state=='signed':raise HTTPException(409,'盲审已签署结案，不能重复签署')
    if x.state!='revealed':raise HTTPException(409,'须先揭盲，再按结论签署')
    ballots=ballots_of(s,x.id,lock=True)
    if len(ballots)<2:raise HTTPException(409,'须两名评估员交齐并揭盲后才能签署')
    opinions={b.opinion for b in ballots}
    if len(opinions)==1:
        if d.decision!=ballots[0].opinion:raise HTTPException(409,'两名评估员意见一致，须按该结论签署')
    else:
        if u['email'] in {b.evaluator for b in ballots}:raise HTTPException(409,'意见分歧时须由未参评主管裁决')
        if len(d.reason.strip())<8:raise HTTPException(409,'分歧裁决须写明至少8字理由')
    x.state='signed';x.decision=d.decision;x.reason=d.reason.strip();x.signed_by=u['email'];s.flush()
    c=get(s,Claim,x.claim_id);adjudicate(s,c,d.decision,u)
    audit(s,u,'blind_signed',f'{c.code}:{d.decision}');return view(s,x)
