from pydantic import BaseModel,Field
from typing import Literal
class IntervalIn(BaseModel):
    low:float=Field(ge=0,le=1)
    high:float=Field(ge=0,le=1)
class BallotIn(BaseModel):
    opinion:Literal['paid','denied']
    probability:float=Field(ge=0,le=1)
    note:str=Field(default='',max_length=2000)
class BlindSignIn(BaseModel):
    decision:Literal['paid','denied']
    reason:str=Field(default='',max_length=2000)
