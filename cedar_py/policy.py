"""
Cedar Policy management with structured logging and error handling
"""

import json
import logging
import re
import uuid
from typing import Dict, Optional

from cedar_py._rust import CedarPolicy as RustCedarPolicy
from cedar_py._rust import CedarPolicySet as RustCedarPolicySet

# Set up structured logger
logger = logging.getLogger(__name__)


class Policy:
    @classmethod
    def from_file(cls, file_path: str) -> "Policy":
        """
        Create a Policy from a file containing the policy string.
        Args:
            file_path (str): Path to the policy file.
        Returns:
            Policy: The created Policy instance.
        """
        with open(file_path, "r", encoding="utf-8") as f:
            policy_str = f.read()
        return cls(policy_str)

    def __init__(self, policy_str: str):
        """
        Initialize a Policy object and validate syntax immediately.
        Accepts either Cedar source (with @id) or Cedar JSON.
        """
        import json

        self.policy_str: str = policy_str.strip()
        self._id: Optional[str] = None
        # Try to extract ID from Cedar JSON, else fallback to @id annotation
        if self.policy_str and self.policy_str[0] == "{":
            try:
                data = json.loads(self.policy_str)
                self._id = data.get("uid")
            except Exception:
                self._id = None
        else:
            # Try to extract @id from Cedar source
            try:
                self._id = self._extract_id(self.policy_str)
            except ValueError:
                # Auto-generate an ID for Cedar source if missing (for test compatibility)
                self._id = f"policy{uuid.uuid4().hex[:8]}"

        logger.debug(
            "Creating Policy",
            extra={"policy_id": self._id, "policy_length": len(self.policy_str or "")},
        )
        # Validate policy syntax immediately by instantiating RustCedarPolicy
        try:
            # If JSON, convert to Cedar source
            if self.policy_str and self.policy_str[0] == "{" and self._id is not None:
                data = json.loads(self.policy_str)

                def parse_entity(ent, role=None):
                    # Wildcard principal/resource: {"": "*"}
                    if isinstance(ent, dict) and "" in ent and ent[""] == "*":
                        t = None
                        if role == "principal":
                            t = data["principal"].get("type")
                        elif role == "resource":
                            t = data["resource"].get("type")
                        if t:
                            return f"{t}::*"
                        raise ValueError(
                            "Wildcard entity must specify a type for Cedar source translation."
                        )
                    # Wildcard by type: {"type": "Document", "id": "*"}
                    if isinstance(ent, dict) and "type" in ent and ent.get("id") == "*":
                        return f'{ent["type"]}::*'
                    # Normal entity: {"type": "User", "id": "alice"}
                    if isinstance(ent, dict) and "type" in ent and "id" in ent:
                        return f'{ent["type"]}::"{ent["id"]}"'
                    # List of actions/entities
                    if isinstance(ent, list):
                        return "[" + ", ".join(parse_entity(e) for e in ent) + "]"
                    # Fallback
                    return str(ent)

                principal = parse_entity(data["principal"], role="principal")
                action = parse_entity(data["action"], role="action")
                resource = parse_entity(data["resource"], role="resource")
                effect = data.get("effect", "Permit")
                condition = data.get("condition")
                cedar_src = f'@id("{self._id}")\n{effect.lower()}(\n  principal == {principal},\n  action == {action},\n  resource == {resource}\n)'
                # Handle conditions
                conds = []
                if condition:
                    if "allOf" in condition:
                        for cond in condition["allOf"]:
                            op = cond["op"]
                            left = cond["left"]
                            right = cond["right"]
                            left_expr = Policy._parse_condition_side(left)
                            right_expr = Policy._parse_condition_side(right)
                            conds.append(f"{left_expr} {op} {right_expr}")
                        cond_block = "\n  ".join(conds)
                        cedar_src += f"\nwhen {{\n  {cond_block}\n}}"
                    elif "anyOf" in condition:
                        for cond in condition["anyOf"]:
                            op = cond["op"]
                            left = cond["left"]
                            right = cond["right"]
                            left_expr = Policy._parse_condition_side(left)
                            right_expr = Policy._parse_condition_side(right)
                            conds.append(f"{left_expr} {op} {right_expr}")
                        cond_block = "\n  ".join(conds)
                        cedar_src += f"\nwhen {{\n  {cond_block}\n}}"
                    elif "op" in condition:
                        op = condition["op"]
                        left = condition["left"]
                        right = condition["right"]
                        left_expr = Policy._parse_condition_side(left)
                        right_expr = Policy._parse_condition_side(right)
                        conds.append(f"{left_expr} {op} {right_expr}")
                        cond_block = "\n  ".join(conds)
                        cedar_src += f"\nwhen {{\n  {cond_block}\n}}"
                    else:
                        cedar_src += ";"
                else:
                    cedar_src += ";"
                self.policy_str = cedar_src
                logger.debug(
                    "Converted JSON policy to Cedar source",
                    extra={"policy_id": self._id},
                )
                # Validate the policy syntax
                RustCedarPolicy(self.policy_str)
            else:
                logger.debug(
                    "Processing Cedar source policy", extra={"policy_id": self._id}
                )
                # If Cedar source, ensure @id is present (auto-generated above if missing)
                # If @id was auto-generated, prepend it to the policy string
                if not self.policy_str.strip().startswith("@id"):
                    self.policy_str = f'@id("{self._id}")\n' + self.policy_str.strip()
                # Validate the policy syntax
                RustCedarPolicy(self.policy_str)
            logger.debug(
                "Policy syntax validation successful", extra={"policy_id": self._id}
            )
        except Exception as e:
            logger.error(
                "Failed to create RustCedarPolicy",
                extra={"policy_id": self._id, "error": str(e)},
            )
            raise ValueError(f"Invalid Cedar policy syntax: {e}") from e

    @staticmethod
    def _parse_condition_side(side):
        """
        Helper to parse left/right side of a condition for Cedar source.
        """
        if isinstance(side, dict) and "var" in side:
            return side["var"]
        if isinstance(side, str):
            # If looks like a variable, don't quote
            if re.match(r"^[a-zA-Z0-9_.]+$", side):
                return side
            return f'"{side}"'
        return str(side)

    @staticmethod
    def _extract_id(policy_str: str, raise_error: bool = True) -> Optional[str]:
        """
        Extracts the policy ID from the '@id' annotation.

        Args:
            policy_str (str): The policy string.
            raise_error (bool): Whether to raise if no ID is found.

        Returns:
            Optional[str]: The extracted policy ID, or None if not found and raise_error is False.
        """
        match = re.search(r'@id\s*\(\s*"([^"]+)"\s*\)', policy_str)
        if match:
            return match.group(1)
        if raise_error:
            raise ValueError(
                "Policy does not have an '@id' annotation or it is invalid."
            )
        return None

    @property
    def id(self) -> str:
        """
        The ID of the policy.

        Returns:
            str: The policy ID.
        """
        assert self._id is not None, "Policy ID should not be None after initialization"
        return self._id

    def __str__(self) -> str:
        """
        Return the policy as a string.

        Returns:
            str: The policy string.
        """
        return self.policy_str


class PolicySet:
    """
    Represents a collection of Cedar policies.

    Supports iteration, membership, and dict-like access.

    Args:
        policies (Optional[Dict[str, Policy]]): Optional dictionary of policies to initialize the set with.
    """

    def __init__(self, policies: Optional[Dict[str, Policy]] = None):
        """
        Initialize the PolicySet.

        Args:
            policies (Optional[Dict[str, Policy]]): Optional dictionary of policies to initialize the set with.
        """
        self._policies: Dict[str, Policy] = policies or {}
        self._rust_policy_set_obj = RustCedarPolicySet()
        for p_id, policy in self._policies.items():
            try:
                rust_policy = RustCedarPolicy(policy.policy_str)
                self._rust_policy_set_obj.add(rust_policy)
            except Exception as e:
                raise ValueError(f"Failed to add policy '{p_id}': {e}") from e

    def add(self, policy: Policy) -> None:
        """
        Add a policy to the set.

        Args:
            policy (Policy): The policy to add.

        Raises:
            ValueError: If a policy with the same ID already exists or if the Rust layer fails to add the policy.
        """
        p_id = policy.id
        if p_id in self._policies:
            raise ValueError(f"Policy with ID '{p_id}' already exists in the set.")
        self._policies[p_id] = policy
        try:
            rust_policy = RustCedarPolicy(policy.policy_str)
            self._rust_policy_set_obj.add(rust_policy)
        except Exception as e:
            raise ValueError(f"Policy error: {e}") from e

    def remove(self, policy_id: str) -> None:
        """
        Remove a policy from the set.

        Args:
            policy_id (str): The ID of the policy to remove.
        """
        if policy_id in self._policies:
            del self._policies[policy_id]
        if hasattr(self._rust_policy_set_obj, "remove"):
            self._rust_policy_set_obj.remove(policy_id)
        else:
            new_rust_set = RustCedarPolicySet()
            for p in self._policies.values():
                new_rust_set.add_policy_str(p.policy_str)
            self._rust_policy_set_obj = new_rust_set

    @property
    def rust_policy_set(self):
        """
        Provides safe access to the underlying Rust CedarPolicySet object.

        Returns:
            The underlying Rust policy set object.
        """
        return self._rust_policy_set_obj

    @property
    def policies(self) -> Dict[str, Policy]:
        """
        The policies in the set, keyed by policy ID.

        Returns:
            Dict[str, Policy]: The policies in the set.
        """
        return self._policies

    def __repr__(self) -> str:
        """
        Return a string representation of the PolicySet.

        Returns:
            str: A string describing the PolicySet.
        """
        return f"PolicySet(policies={len(self._policies)})"

    def __len__(self) -> int:
        """
        Return the number of policies in the set.

        Returns:
            int: The number of policies.
        """
        return len(self._policies)

    def __iter__(self):
        """
        Iterate over the policies in the set.

        Returns:
            Iterator[Policy]: An iterator over Policy objects.
        """
        return iter(self._policies.values())

    def __contains__(self, item) -> bool:
        """
        Check if a policy or policy ID is in the set.

        Args:
            item (Union[Policy, str]): The policy or policy ID to check.

        Returns:
            bool: True if present, False otherwise.
        """
        if isinstance(item, Policy):
            return item.id in self._policies
        return item in self._policies

    def __getitem__(self, policy_id: str) -> "Policy":
        """
        Get a policy by its ID.

        Args:
            policy_id (str): The ID of the policy.

        Returns:
            Policy: The policy with the given ID.
        """
        return self._policies[policy_id]
