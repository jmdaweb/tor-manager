"""Estructuras de datos planas que viajan entre el backend y la interfaz."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

ONION_EPHEMERAL = 'ephemeral'
ONION_PERSISTENT = 'persistent'


@dataclass
class CircuitInfo:
    id: str
    status: str
    purpose: str
    path: list = field(default_factory=list)
    build_flags: list = field(default_factory=list)
    created: Optional[datetime] = None
    reason: Optional[str] = None
    remote_reason: Optional[str] = None
    hs_state: Optional[str] = None
    rend_query: Optional[str] = None
    socks_username: Optional[str] = None


@dataclass
class StreamInfo:
    id: str
    status: str
    circ_id: Optional[str]
    target: str
    target_address: Optional[str] = None
    target_port: Optional[int] = None
    purpose: Optional[str] = None
    source_addr: Optional[str] = None
    reason: Optional[str] = None
    remote_reason: Optional[str] = None


@dataclass
class RelayInfo:
    fingerprint: str
    nickname: str
    address: Optional[str] = None
    or_port: Optional[int] = None
    flags: list = field(default_factory=list)
    bandwidth: Optional[int] = None
    version: Optional[str] = None
    published: Optional[datetime] = None


@dataclass
class RelayDetails:
    relay: RelayInfo
    network_status_text: str
    microdescriptor_text: Optional[str] = None
    exit_policy: Optional[str] = None


@dataclass
class OnionServiceInfo:
    kind: str
    address: Optional[str]
    service_id: Optional[str] = None
    ports: list = field(default_factory=list)
    directory: Optional[str] = None
    detached: bool = False
    created_here: bool = False
    key_type: Optional[str] = None
    options: dict = field(default_factory=dict)


@dataclass
class OnionServiceCreated:
    kind: str
    address: Optional[str]
    ports: list
    service_id: Optional[str] = None
    private_key_type: Optional[str] = None
    private_key: Optional[str] = None
    client_auth: dict = field(default_factory=dict)
    detached: bool = False
    directory: Optional[str] = None
    publication: Optional[tuple] = None
    saved: object = None


@dataclass
class ConfigOption:
    name: str
    type: str
    values: Optional[list]
    defaults: list
    modified: bool
    description: str = ''


@dataclass
class AuthInfo:
    methods: list
    cookie_path: Optional[str]
    tor_version: Optional[str]


@dataclass
class FactoryResetResult:
    reset: list
    failed: list
    saved: bool
    save_error: Optional[str] = None


_BOOTSTRAP_FIELD_RE = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|\S+)')


@dataclass
class BootstrapStatus:
    progress: int
    tag: str = ''
    summary: str = ''
    warning: Optional[str] = None

    @classmethod
    def from_arguments(cls, arguments):
        try:
            progress = int(arguments.get('PROGRESS', 0))
        except (TypeError, ValueError):
            progress = 0
        return cls(progress, arguments.get('TAG', ''), arguments.get('SUMMARY', ''), arguments.get('WARNING'))

    @classmethod
    def parse(cls, text):
        fields = {key: value.strip('"') for key, value in _BOOTSTRAP_FIELD_RE.findall(text or '')}
        return cls.from_arguments(fields)
