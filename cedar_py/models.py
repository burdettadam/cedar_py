"""
Models for Cedar entity representation - Modernized with Pydantic v2
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .errors import EntityValidationError


class Entity(BaseModel):
    """
    Base class for Cedar entities, using Pydantic v2 for validation and serialization.

    Attributes:
        uid (str): The entity UID (e.g., 'User::"alice"').
        attributes (Dict[str, Any]): Optional entity attributes.
        parents (List['Entity']): Optional list of parent entities.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
        arbitrary_types_allowed=True,
    )

    uid: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
    parents: List["Entity"] = Field(default_factory=list)

    def __str__(self) -> str:
        return self.uid

    @field_validator("uid")
    @classmethod
    def validate_uid(cls, v: str) -> str:
        if not isinstance(v, str):
            raise EntityValidationError(v)

        # For backward compatibility, allow simple strings for actions
        # The engine will handle conversion as needed
        if "::" not in v:
            # Allow simple action names like "read", "write" for backward compatibility
            # These will be converted by the engine as needed
            return v

        # For full UIDs, ensure proper format
        return v

    def __init__(self, uid, attributes=None, parents=None, **kwargs):
        # Accept positional arguments for compatibility with tests
        if isinstance(uid, dict):
            # Allow dict input for from_dict
            super().__init__(**uid)
            return
        if attributes is None:
            attributes = {}
        if parents is None:
            parents = []
        super().__init__(uid=uid, attributes=attributes, parents=parents, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        if "::" in self.uid:
            type_str, id_str = self.uid.split("::", 1)
            id_str = id_str.strip('"')
            return {
                "uid": {"type": type_str, "id": id_str},
                "attrs": self.attributes,
                "parents": [p.uid_dict() for p in self.parents],
            }
        else:
            # For backward compatibility with simple strings
            return {
                "uid": {
                    "type": "Action",
                    "id": self.uid,
                },  # Default to Action for simple strings
                "attrs": self.attributes,
                "parents": [p.uid_dict() for p in self.parents],
            }

    def uid_dict(self) -> Dict[str, str]:
        if "::" in self.uid:
            type_str, id_str = self.uid.split("::", 1)
            id_str = id_str.strip('"')
            return {"type": type_str, "id": id_str}
        else:
            # For backward compatibility with simple strings
            return {
                "type": "Action",
                "id": self.uid,
            }  # Default to Action for simple strings

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        # Accepts both Cedar JSON and internal dict
        if "uid" in data and isinstance(data["uid"], dict):
            type_str = data["uid"].get("type")
            id_str = data["uid"].get("id")
            uid = f'{type_str}::"{id_str}"'
            attributes = data.get("attrs", {})
            parents = [cls.from_dict(p) for p in data.get("parents", [])]
            return cls(uid=uid, attributes=attributes, parents=parents)
        # fallback: handle dicts with type/id only
        if "type" in data and "id" in data:
            uid = f'{data["type"]}::"{data["id"]}"'
            attributes = data.get("attrs", {})
            parents = [cls.from_dict(p) for p in data.get("parents", [])]
            return cls(uid=uid, attributes=attributes, parents=parents)
        # fallback: treat as internal dict
        return cls(**data)


class Principal(Entity):
    """Represents a Cedar principal (the entity taking an action)."""

    pass


class Resource(Entity):
    """Represents a Cedar resource (the entity being acted upon)."""

    pass


class Action(Entity):
    """Represents a Cedar action (what is being performed)."""

    pass


class Context(BaseModel):
    """
    Represents additional context for an authorization decision, using Pydantic v2.

    Attributes:
        data (Dict[str, Any]): Context data for the authorization request.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )

    data: Dict[str, Any] = Field(default_factory=dict)

    def __init__(self, data=None, **kwargs):
        # Accept positional dict for compatibility with tests
        if data is None:
            data = {}
        super().__init__(data=data, **kwargs)

    def to_dict(self) -> Dict[str, Any]:
        return self.data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Context":
        # Accepts both direct dict and wrapped dict
        if isinstance(data, dict) and "data" in data:
            return cls(data=data["data"])
        return cls(data=data)
