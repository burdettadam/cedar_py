"""
Engine module for handling Cedar authorization decisions
"""


import json
import logging
from typing import Optional, Dict, Any, Union, Tuple, List
from dataclasses import dataclass

from .models import Action, Context, Entity, Principal, Resource
from .policy import Policy, PolicySet
from ._rust_importer import RustCedarAuthorizer as CedarAuthorizer

LOGGER = logging.getLogger(__name__)



from dataclasses import dataclass

@dataclass
class AuthorizationResponse:
    """
    Represents a detailed authorization response.
    """
    allowed: bool
    decision: List[str]
    errors: List[str]


class Engine:
    """
    The main Cedar authorization engine.

    Args:
        policy_set (Optional[Union[Policy, PolicySet]]): A Policy or PolicySet containing the policies. If None, an empty PolicySet is used.
        schema (Optional[Dict[str, Any]]): A JSON object representing the schema.
        entities (Optional[Dict[str, Any]]): A dictionary of entities.
        validate (bool): Whether to validate the schema and policies.
    """

    def __init__(
        self,
        policy_set: Optional[Union[Policy, PolicySet]] = None,
        schema: Optional[Dict[str, Any]] = None,
        entities: Optional[Dict[str, Any]] = None,
        validate: bool = True,
    ):
        """
        Initialize the Engine.
        """
        # Convert a single Policy to a PolicySet if needed
        if policy_set is None:
            self._policy_set = PolicySet()
        elif isinstance(policy_set, Policy):
            self._policy_set = PolicySet()
            self._policy_set.add(policy_set)
        else:
            self._policy_set = policy_set

        self._schema = schema
        self._entities = entities or {}
        self._authorizer = CedarAuthorizer()

        if validate and schema:
            # TODO: Implement schema validation if required by the Rust bindings
            pass

    def is_authorized(
        self,
        principal: Union[Principal, str],
        action: Union[Action, str],
        resource: Union[Resource, str],
        context: Optional[Context] = None,
        entities: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Check if a request is authorized.

        Args:
            principal (Union[Principal, str]): The principal entity or string identifier.
            action (Union[Action, str]): The action entity or string identifier.
            resource (Union[Resource, str]): The resource entity or string identifier.
            context (Optional[Context]): The context of the request.
            entities (Optional[Dict[str, Any]]): Additional entities to consider for this authorization check.

        Returns:
            bool: True if the request is allowed, False otherwise.
        """
        # Convert string identifiers to model objects if needed
        if isinstance(principal, str):
            principal = Principal(uid=principal)
        if isinstance(action, str):
            action = Action(uid=action)
        if isinstance(resource, str):
            resource = Resource(uid=resource)

        # Prepare entities dict for serialization
        entities_dict = self._prepare_entities(principal, action, resource, entities)
        # Convert all entities to dicts for JSON serialization, handle dicts and model objects
        def entity_to_dict(e):
            return e.to_dict() if hasattr(e, 'to_dict') else e
        entities_json = json.dumps([entity_to_dict(e) for e in entities_dict.values()]) if entities_dict else None
        context_json = json.dumps(context.data) if context else None

        # Call the Rust authorizer
        return self._authorizer.is_authorized(
            policy_set=self._policy_set.rust_policy_set,
            principal=principal.uid,
            action=action.uid,
            resource=resource.uid,
            context_json=context_json,
            entities_json=entities_json,
        )

    def _prepare_entities(
        self,
        principal: Principal,
        action: Action,
        resource: Resource,
        extra_entities: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Prepare the entities dictionary for authorization."""
        entities_dict = {}

        # Add engine-level entities first
        if self._entities:
            entities_dict.update(self._entities)

        # Add request-specific entities, allowing override
        if extra_entities:
            entities_dict.update(extra_entities)

        # Add the main actors, ensuring they are in the dict
        for entity in [principal, action, resource]:
            self._add_entity_and_parents(entities_dict, entity)

        return entities_dict

    def _add_entity_and_parents(self, entities_dict: Dict[str, Any], entity: Entity) -> None:
        """Recursively add an entity and its parents to the entities dictionary."""
        # Use a simple UID-based key for the dictionary
        if entity.uid not in entities_dict:
            entities_dict[entity.uid] = entity.to_dict()
            for parent in entity.parents:
                self._add_entity_and_parents(entities_dict, parent)
        
    def is_authorized_detailed(
        self,
        principal: Union[Principal, str],
        action: Union[Action, str],
        resource: Union[Resource, str],
        context: Optional[Context] = None,
        entities: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Check if a request is authorized and get a detailed response.

        Args:
            principal (Union[Principal, str]): The principal entity or string identifier.
            action (Union[Action, str]): The action entity or string identifier.
            resource (Union[Resource, str]): The resource entity or string identifier.
            context (Optional[Context]): The context of the request.
            entities (Optional[Dict[str, Any]]): Additional entities to consider for this authorization check.

        Returns:
            Tuple[bool, List[str], List[str]]: (allowed, policy_ids, errors)
        """
        # Convert string identifiers to model objects if needed
        if isinstance(principal, str):
            principal = Principal(uid=principal)
        if isinstance(action, str):
            action = Action(uid=action)
        if isinstance(resource, str):
            resource = Resource(uid=resource)

        # Prepare entities dict for serialization
        entities_dict = self._prepare_entities(principal, action, resource, entities)
        def entity_to_dict(e):
            return e.to_dict() if hasattr(e, 'to_dict') else e
        entities_json = json.dumps([entity_to_dict(e) for e in entities_dict.values()]) if entities_dict else None
        context_json = json.dumps(context.data) if context else None

        # Call the Rust authorizer
        return self._authorizer.is_authorized_detailed(
            policy_set=self._policy_set.rust_policy_set,
            principal=principal.uid,
            action=action.uid,
            resource=resource.uid,
            context_json=context_json,
            entities_json=entities_json,
        )

    def authorize(
        self,
        principal: Principal,
        action: Action,
        resource: Resource,
        context: Optional[Context] = None,
        entities: Optional[Dict[str, Any]] = None,
    ) -> AuthorizationResponse:
        """
        Get a detailed authorization response.

        Args:
            principal (Principal): The principal entity.
            action (Action): The action entity.
            resource (Resource): The resource entity.
            context (Optional[Context]): The context of the request.
            entities (Optional[Dict[str, Any]]): Additional entities to consider for this authorization check.

        Returns:
            AuthorizationResponse: The detailed authorization response.
        """
        allowed, decision, errors = self.is_authorized_detailed(
            principal, action, resource, context, entities
        )
        return AuthorizationResponse(allowed, decision, errors)
    
    def add_policy(self, policy: Policy) -> None:
        """
        Add a policy to the engine's policy set.

        Args:
            policy (Policy): The policy to add.
        """
        self._policy_set.add(policy)
