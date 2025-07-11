"""
Models for Cedar entity representation
"""

from pydantic import BaseModel, Field, root_validator

class Entity(BaseModel):
    def __str__(self):
        return self.uid
    """
    Base class for Cedar entities, using Pydantic for validation and serialization.

    Attributes:
        uid (str): The entity UID (e.g., 'User::"alice"').
        attributes (dict): Optional entity attributes.
        parents (list): Optional list of parent entities.
    """
    uid: str
    attributes: dict = Field(default_factory=dict)
    parents: list = Field(default_factory=list)


    @root_validator(pre=True)
    def validate_uid(cls, values):
        uid = values.get('uid')
        if not isinstance(uid, str) or '::' not in uid:
            raise ValueError(f"Invalid entity UID format: '{uid}'. Expected 'namespace::\"id\"'.")
        return values

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

    def to_dict(self) -> dict:
        type_str, id_str = self.uid.split("::", 1)
        id_str = id_str.strip('"')
        return {
            "uid": {"type": type_str, "id": id_str},
            "attrs": self.attributes,
            "parents": [p.uid_dict() for p in self.parents],
        }

    def uid_dict(self) -> dict:
        type_str, id_str = self.uid.split("::", 1)
        id_str = id_str.strip('"')
        return {"type": type_str, "id": id_str}

    @classmethod
    def from_dict(cls, data: dict) -> "Entity":
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
    Represents additional context for an authorization decision, using Pydantic.

    Attributes:
        data (dict): Context data for the authorization request.
    """
    data: dict = Field(default_factory=dict)

    def __init__(self, data=None, **kwargs):
        # Accept positional dict for compatibility with tests
        if data is None:
            data = {}
        super().__init__(data=data, **kwargs)

    def to_dict(self) -> dict:
        return self.data

    @classmethod
    def from_dict(cls, data: dict) -> "Context":
        # Accepts both direct dict and wrapped dict
        if isinstance(data, dict) and "data" in data:
            return cls(data=data["data"])
        return cls(data=data)
