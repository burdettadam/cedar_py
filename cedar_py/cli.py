#!/usr/bin/env python3
"""
Cedar-Py CLI: Command-line tools for Cedar policy management.
Provides policy validation, testing, and management utilities.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .engine import Engine
from .policy import Policy, PolicySet


class PolicyValidator:
    """Policy validation utilities."""

    @staticmethod
    def validate_file(file_path: str) -> Dict[str, Any]:
        """Validate a Cedar policy file."""
        try:
            policy = Policy.from_file(file_path)
            return {
                "valid": True,
                "policy_id": policy.id,
                "file": file_path,
                "message": "Policy is valid",
            }
        except Exception as e:
            return {
                "valid": False,
                "file": file_path,
                "error": str(e),
                "error_type": type(e).__name__,
            }

    @staticmethod
    def validate_directory(directory: str) -> Dict[str, Any]:
        """Validate all Cedar policy files in a directory."""
        policy_dir = Path(directory)
        if not policy_dir.exists():
            return {"error": f"Directory not found: {directory}"}

        policy_files = list(policy_dir.glob("*.cedar"))
        if not policy_files:
            return {"error": f"No .cedar files found in {directory}"}

        results = []
        valid_count = 0

        for file_path in policy_files:
            result = PolicyValidator.validate_file(str(file_path))
            results.append(result)
            if result["valid"]:
                valid_count += 1

        return {
            "total_files": len(policy_files),
            "valid_files": valid_count,
            "invalid_files": len(policy_files) - valid_count,
            "results": results,
        }


class PolicyTester:
    """Policy testing utilities."""

    def __init__(self, policies_path: str):
        """Initialize with policies from file or directory."""
        self.policies_path = policies_path
        self.policies = self._load_policies()

    def _load_policies(self) -> PolicySet:
        """Load policies from file or directory."""
        path = Path(self.policies_path)
        policy_set = PolicySet()

        if path.is_file():
            if path.suffix == ".cedar":
                policy = Policy.from_file(str(path))
                policy_set.add(policy)
            else:
                raise ValueError(f"Unsupported file type: {path.suffix}")
        elif path.is_dir():
            for policy_file in path.glob("*.cedar"):
                policy = Policy.from_file(str(policy_file))
                policy_set.add(policy)
        else:
            raise ValueError(f"Path not found: {self.policies_path}")

        return policy_set

    def run_test_file(self, test_file: str) -> Dict[str, Any]:
        """Run tests from a JSON test file."""
        test_path = Path(test_file)
        if not test_path.exists():
            return {"error": f"Test file not found: {test_file}"}

        try:
            with open(test_path) as f:
                test_data = json.load(f)
        except json.JSONDecodeError as e:
            return {"error": f"Invalid JSON in test file: {e}"}

        engine = Engine(self.policies)
        results = []
        passed = 0
        failed = 0

        for test_case in test_data.get("tests", []):
            try:
                result = engine.is_authorized(
                    test_case["principal"],
                    test_case["action"],
                    test_case["resource"],
                    test_case.get("context", {}),
                    test_case.get("entities", {}),
                )

                expected = test_case.get("expected", True)
                success = result == expected

                if success:
                    passed += 1
                else:
                    failed += 1

                results.append(
                    {
                        "name": test_case.get("name", f"Test {len(results) + 1}"),
                        "passed": success,
                        "expected": expected,
                        "actual": result,
                        "principal": test_case["principal"],
                        "action": test_case["action"],
                        "resource": test_case["resource"],
                    }
                )

            except Exception as e:
                failed += 1
                results.append(
                    {
                        "name": test_case.get("name", f"Test {len(results) + 1}"),
                        "passed": False,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    }
                )

        return {
            "total_tests": len(results),
            "passed": passed,
            "failed": failed,
            "success_rate": passed / len(results) if results else 0,
            "results": results,
        }


class PolicyMigrator:
    """Policy migration utilities."""

    @staticmethod
    def convert_to_json(
        policy_file: str, output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """Convert Cedar policy to JSON format."""
        try:
            policy = Policy.from_file(policy_file)
            # Simple JSON representation of policy metadata
            json_policy = {
                "id": policy.id,
                "source": str(policy),
                "type": "cedar_policy",
            }

            if output_file:
                with open(output_file, "w") as f:
                    json.dump(json_policy, f, indent=2)
                return {"success": True, "output_file": output_file}
            else:
                return {"success": True, "json_policy": json_policy}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def extract_entities(
        policy_file: str, output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """Extract entity types and attributes from policies."""
        try:
            Policy.from_file(policy_file)  # Validate the policy loads
            # Analyze the policy source for entity patterns
            with open(policy_file, "r") as f:
                policy_source = f.read()

            # Simple entity extraction from policy text
            entities_info = {
                "policy_file": policy_file,
                "entity_patterns_found": [],
                "note": "Basic entity analysis - extend for more sophisticated extraction",
            }

            # Look for common entity patterns
            if "User::" in policy_source:
                entities_info["entity_patterns_found"].append("User")
            if "Document::" in policy_source:
                entities_info["entity_patterns_found"].append("Document")
            if "Group::" in policy_source:
                entities_info["entity_patterns_found"].append("Group")

            if output_file:
                with open(output_file, "w") as f:
                    json.dump(entities_info, f, indent=2)
                return {"success": True, "output_file": output_file}
            else:
                return {"success": True, "entities_info": entities_info}
        except Exception as e:
            return {"success": False, "error": str(e)}


def cmd_validate(args):
    """Handle validate command."""
    if args.file:
        result = PolicyValidator.validate_file(args.file)
        if result["valid"]:
            print(f"✅ {result['file']}: Valid (ID: {result['policy_id']})")
            return 0
        else:
            print(f"❌ {result['file']}: {result['error']}")
            return 1

    elif args.directory:
        result = PolicyValidator.validate_directory(args.directory)
        if "error" in result:
            print(f"❌ Error: {result['error']}")
            return 1

        print(f"📊 Validation Results for {args.directory}")
        print(f"   Total files: {result['total_files']}")
        print(f"   Valid: {result['valid_files']}")
        print(f"   Invalid: {result['invalid_files']}")
        print()

        for file_result in result["results"]:
            if file_result["valid"]:
                print(
                    f"✅ {file_result['file']}: Valid (ID: {file_result['policy_id']})"
                )
            else:
                print(f"❌ {file_result['file']}: {file_result['error']}")

        return 0 if result["invalid_files"] == 0 else 1


def cmd_test(args):
    """Handle test command."""
    try:
        tester = PolicyTester(args.policies)
        result = tester.run_test_file(args.test_file)

        if "error" in result:
            print(f"❌ Error: {result['error']}")
            return 1

        print("🧪 Test Results")
        print(f"   Total tests: {result['total_tests']}")
        print(f"   Passed: {result['passed']}")
        print(f"   Failed: {result['failed']}")
        print(f"   Success rate: {result['success_rate']:.1%}")
        print()

        for test_result in result["results"]:
            if test_result["passed"]:
                print(f"✅ {test_result['name']}: PASS")
            else:
                if "error" in test_result:
                    print(f"❌ {test_result['name']}: ERROR - {test_result['error']}")
                else:
                    print(
                        f"❌ {test_result['name']}: FAIL (expected {test_result['expected']}, got {test_result['actual']})"
                    )

        return 0 if result["failed"] == 0 else 1

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


def cmd_migrate(args):
    """Handle migrate command."""
    if args.to_json:
        result = PolicyMigrator.convert_to_json(args.policy_file, args.output)
        if result["success"]:
            if args.output:
                print(
                    f"✅ Converted {args.policy_file} to JSON: {result['output_file']}"
                )
            else:
                print(json.dumps(result["json_policy"], indent=2))
            return 0
        else:
            print(f"❌ Error: {result['error']}")
            return 1

    elif args.extract_entities:
        result = PolicyMigrator.extract_entities(args.policy_file, args.output)
        if result["success"]:
            if args.output:
                print(
                    f"✅ Extracted entities from {args.policy_file}: {result['output_file']}"
                )
            else:
                print(json.dumps(result["entities_info"], indent=2))
            return 0
        else:
            print(f"❌ Error: {result['error']}")
            return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Cedar-Py CLI: Tools for Cedar policy management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cedar-py validate --file policy.cedar
  cedar-py validate --directory ./policies
  cedar-py test --policies ./policies --test-file tests.json
  cedar-py migrate --policy-file policy.cedar --to-json --output policy.json
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate Cedar policies")
    validate_group = validate_parser.add_mutually_exclusive_group(required=True)
    validate_group.add_argument("--file", "-f", help="Validate a single policy file")
    validate_group.add_argument(
        "--directory", "-d", help="Validate all policies in directory"
    )

    # Test command
    test_parser = subparsers.add_parser("test", help="Test Cedar policies")
    test_parser.add_argument(
        "--policies", "-p", required=True, help="Policy file or directory"
    )
    test_parser.add_argument("--test-file", "-t", required=True, help="JSON test file")

    # Migrate command
    migrate_parser = subparsers.add_parser(
        "migrate", help="Migrate and analyze policies"
    )
    migrate_parser.add_argument(
        "--policy-file", "-p", required=True, help="Policy file to process"
    )
    migrate_parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    migrate_group = migrate_parser.add_mutually_exclusive_group(required=True)
    migrate_group.add_argument(
        "--to-json", action="store_true", help="Convert policy to JSON"
    )
    migrate_group.add_argument(
        "--extract-entities", action="store_true", help="Extract entity information"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "validate":
            return cmd_validate(args)
        elif args.command == "test":
            return cmd_test(args)
        elif args.command == "migrate":
            return cmd_migrate(args)
        else:
            print(f"Unknown command: {args.command}")
            return 1
    except KeyboardInterrupt:
        print("\n⏸️  Operation cancelled by user")
        return 130
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
