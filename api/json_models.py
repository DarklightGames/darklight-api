from typing import List
from pydantic import BaseModel, Field


class TextMessage(BaseModel):
    type: str
    message: str
    sender: int
    sent_at: str
    team_index: int
    squad_index: int


class MapBounds(BaseModel):
    ne: tuple[float, float, float]
    sw: tuple[float, float, float]


class Map(BaseModel):
    name: str
    bounds: MapBounds
    offset: int # or float?


class Server(BaseModel):
    name: str


class Session(BaseModel):
    ip: str # ip type
    ended_at: str
    started_at: str


class Player(BaseModel):
    id: int
    names: List[str]
    sessions: List[Session]


class PlayerPawn(BaseModel):
    id: str
    pawn: str | None
    team: int
    location: tuple[float, float, float]
    vehicle: str | None


class VehiclePawn(BaseModel):
    vehicle: str
    team: int
    location: tuple[float, float, float]


class Frag(BaseModel):
    damage_type: str
    hit_index: int
    time: int
    killer: PlayerPawn
    victim: PlayerPawn


class VehicleFrag(BaseModel):
    damage_type: str
    destroyed_vehicle: str
    time: int
    killer: PlayerPawn
    destroyed_vehicle: VehiclePawn


class Capture(BaseModel):
    objective_id: int
    round_time: int
    player_ids: List[int]
    team: int


# class Events(BaseModel):
#     type: str
    

class RallyPoint(BaseModel):
    team_index: int
    squad_index: int
    player_id: int
    is_established: bool
    establisher_count: int
    location: tuple[float, float, float]
    created_at: str
    destroyed_at: str | None
    destroyed_reason: str | None
    spawn_count: int


class Construction(BaseModel):
    team: int
    round_time: int
    class_name: str = Field(validation_alias='class')
    location: tuple[float, float, float]
    player_id: int


class Round(BaseModel):
    started_at: str
    ended_at: str
    frags: List[Frag]
    vehicle_frags: List[VehicleFrag]
    captures: List[Capture]
    constructions: List[Construction]
    # events: List[Events]
    rally_points: List[RallyPoint]
    winner: int


class Log(BaseModel):
    players: List[Player]
    map: Map
    rounds: List[Round]
    text_messages: List[TextMessage]
    version: str
    server: Server

