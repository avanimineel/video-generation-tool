"""The editable film format: layers on one canvas, a camera, transitions, sounds and music.

Both the Studio editor and the AI write this format, so every part of a film stays editable. validate()
cleans whatever arrives (from a person, Claude or Gemini) into a film the engine can always draw.
"""
import json
import re
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ENGINE = Path(__file__).with_name('engine.js')
LAYER_TYPES = ('text', 'image', 'shape', 'path', 'particles', 'counter', 'logo')
TEXT_IN = ('rise-words', 'mask-up', 'blur-in', 'scale-pop', 'type', 'letters-scatter', 'letters-rise', 'fade', 'none')
ANY_IN = ('fade', 'rise', 'scale', 'zoom-in', 'pop', 'blur', 'mask-circle', 'wipe-left', 'draw', 'none')
OUT = ('fade', 'rise', 'blur', 'scale', 'none')
TRANSITIONS = ('whip', 'zoom-through', 'flash', 'wipe', 'dip')
EASES = ('linear', 'out', 'in', 'inOut', 'expo', 'back', 'elastic')


class Loose(BaseModel):
    model_config = ConfigDict(extra='allow')


class Entrance(Loose):
    effect: str = 'fade'
    duration: float = Field(default=.55, ge=0, le=6)
    stagger: Optional[float] = Field(default=None, ge=0, le=1)
    ease: Optional[str] = None


class Exit(Loose):
    effect: str = 'fade'
    duration: float = Field(default=.4, ge=0, le=4)


class Key(Loose):
    t: float = Field(ge=0)
    ease: Optional[str] = None


class Layer(Loose):
    id: str
    type: str = 'text'
    block: Optional[str] = None
    name: Optional[str] = None
    start: float = Field(default=0, ge=0)
    end: float = Field(default=3, gt=0)
    x: Optional[float] = None
    y: Optional[float] = None
    width: Optional[float] = Field(default=None, gt=0)
    height: Optional[float] = Field(default=None, gt=0)
    depth: float = Field(default=1, ge=-1, le=3)
    z: Optional[int] = None
    opacity: float = Field(default=1, ge=0, le=1)
    scale: float = Field(default=1, gt=0, le=20)
    rotate: float = 0
    anchor: str = 'center'
    text: Optional[str] = None
    value: Optional[str] = None
    accent: list[int] = Field(default_factory=list)
    style: dict[str, Any] = Field(default_factory=dict)
    src: Optional[str] = None
    entrance: Optional[Entrance] = Field(default=None, alias='in')
    exit: Optional[Exit] = Field(default=None, alias='out')
    motion: list[Key] = Field(default_factory=list)
    sound: Optional[dict[str, Any]] = None
    model_config = ConfigDict(extra='allow', populate_by_name=True)

    @field_validator('type')
    @classmethod
    def known_type(cls, value):
        return value if value in LAYER_TYPES else 'text'

    @model_validator(mode='before')
    @classmethod
    def particle_flow(cls, data):
        # Particles move by a named flow ("drift", "rise", "orbit", "burst"); motion is for keyframes.
        if isinstance(data, dict) and isinstance(data.get('motion'), str):
            data = dict(data); data['flow'] = data.pop('motion')
        return data


class Block(Loose):
    id: str
    name: str
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    origin: dict[str, float] = Field(default_factory=lambda: {'x': 0, 'y': 0})  # The block's spot on the canvas.


class Transition(Loose):
    at: float = Field(ge=0)
    type: str = 'whip'
    duration: float = Field(default=.5, gt=0, le=3)

    @field_validator('type')
    @classmethod
    def known(cls, value):
        return value if value in TRANSITIONS else 'whip'


class Film(Loose):
    version: int = 1
    title: str = 'Untitled film'
    aspect: Literal['16:9', '9:16', '1:1'] = '16:9'
    duration: float = Field(default=20, gt=0, le=180)
    brand: dict[str, Any] = Field(default_factory=dict)
    background: dict[str, Any] = Field(default_factory=lambda: {'color': 'background', 'texture': 'none'})
    camera: list[Key] = Field(default_factory=list)
    blocks: list[Block] = Field(default_factory=list)
    layers: list[Layer] = Field(default_factory=list)
    transitions: list[Transition] = Field(default_factory=list)
    sounds: list[dict[str, Any]] = Field(default_factory=list)
    music: dict[str, Any] = Field(default_factory=lambda: {'mood': 'cinematic', 'volume': .55})


def validate(data, folder=None):
    """A clean film: known types and effects, times inside the film, unique ids, only local images that exist."""
    if isinstance(data, (str, bytes)): data = json.loads(data)
    film = Film.model_validate(data)
    seen = set()
    for index, layer in enumerate(film.layers):
        if not layer.id or layer.id in seen: layer.id = f'layer{index + 1}'
        seen.add(layer.id)
        layer.end = min(layer.end, film.duration); layer.start = min(layer.start, max(0, layer.end - .1))
        if layer.entrance:
            allowed = TEXT_IN + ANY_IN if layer.type in ('text', 'counter') else ANY_IN
            if layer.entrance.effect not in allowed: layer.entrance.effect = 'fade'
            if layer.entrance.ease and layer.entrance.ease not in EASES: layer.entrance.ease = None
        if layer.exit and layer.exit.effect not in OUT: layer.exit.effect = 'fade'
        if layer.src:
            # Only the film's own files: no remote URLs, no paths outside the film folder.
            clean = layer.src.lstrip('/')
            if re.match(r'^[a-z]+:', layer.src) or '..' in Path(clean).parts or (folder and not (Path(folder) / clean).is_file()):
                layer.src = None
            else:
                layer.src = clean
        if layer.type == 'image' and not layer.src: layer.type = 'shape'
    film.transitions = [t for t in film.transitions if t.at <= film.duration]
    film.camera = sorted(film.camera, key=lambda k: k.t)
    return film


def dump(film):
    return json.loads(film.model_dump_json(by_alias=True, exclude_none=True))


def player_html(film, fonts_css=''):
    """A page that draws the film with the shared engine; used for preview and for recording."""
    data = json.dumps(dump(film), ensure_ascii=False).replace('</', '<\\/')
    families = {f for f in (film.brand.get('fonts') or {}).values() if isinstance(f, str) and re.fullmatch(r'[A-Za-z0-9 ]{2,40}', f)}
    link = ''
    if families:
        query = '&'.join('family=' + f.replace(' ', '+') + ':ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400;1,700' for f in sorted(families))
        link = f'<link rel="stylesheet" href="https://fonts.googleapis.com/css2?{query}&display=block">'
    return (f'<!doctype html><html><head><meta charset="utf-8">{link}{fonts_css}</head><body>'
            f'<script>window.FILM = {data};</script><script>{ENGINE.read_text()}</script></body></html>')
