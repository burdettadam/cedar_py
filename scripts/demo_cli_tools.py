#!/usr/bin/env python3
"""
Demo the Cedar-Py CLI functionality.
"""

from cedar_py import PolicyValidator, PolicyTester, PolicyMigrator, Policy
import tempfile
import json

def demo_cli_tools():
    """Demonstrate CLI functionality."""
    print("🔧 Cedar-Py CLI Tools Demo")
    print("=" * 30)
    print()
    
    # Demo 1: Policy validation from string
    print("1️⃣ Policy Validation")
    
    # Create a temporary valid policy file
    valid_policy = 'permit(principal == User::"alice", action == Action::"read", resource == Document::"doc1");'
    invalid_policy = 'invalid syntax here'
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cedar', delete=False) as f:
        f.write(valid_policy)
        valid_file = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cedar', delete=False) as f:
        f.write(invalid_policy)  
        invalid_file = f.name
    
    # Test validation
    result = PolicyValidator.validate_file(valid_file)
    print(f"Valid policy: {'✅ PASS' if result['valid'] else '❌ FAIL'}")
    
    result = PolicyValidator.validate_file(invalid_file)
    print(f"Invalid policy: {'✅ PASS' if not result['valid'] else '❌ FAIL'}")
    print()
    
    # Demo 2: Policy testing  
    print("2️⃣ Policy Testing")
    
    # Create test data
    test_data = {
        "tests": [
            {
                "name": "Alice can read doc1",
                "principal": "User::\"alice\"",
                "action": "Action::\"read\"",
                "resource": "Document::\"doc1\"",
                "expected": True
            },
            {
                "name": "Bob cannot read doc1", 
                "principal": "User::\"bob\"",
                "action": "Action::\"read\"",
                "resource": "Document::\"doc1\"",
                "expected": False
            }
        ]
    }
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(test_data, f)
        test_file = f.name
    
    try:
        tester = PolicyTester(valid_file)
        results = tester.run_test_file(test_file)
        print(f"Test execution: {'✅ PASS' if 'error' not in results else '❌ FAIL'}")
        if 'error' not in results:
            print(f"  - Total tests: {results['total_tests']}")
            print(f"  - Success rate: {results['success_rate']:.1%}")
        else:
            print(f"  - Error: {results['error']}")
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
    print()
    
    # Demo 3: Policy migration
    print("3️⃣ Policy Migration")
    
    result = PolicyMigrator.convert_to_json(valid_file)
    print(f"JSON conversion: {'✅ PASS' if result['success'] else '❌ FAIL'}")
    if result['success']:
        print(f"  - Policy ID: {result['json_policy']['id']}")
        print(f"  - Type: {result['json_policy']['type']}")
    
    result = PolicyMigrator.extract_entities(valid_file)
    print(f"Entity extraction: {'✅ PASS' if result['success'] else '❌ FAIL'}")
    if result['success']:
        print(f"  - Entities found: {result['entities_info']['entity_patterns_found']}")
    print()
    
    print("🎉 CLI tools demo completed!")
    
    # Cleanup
    import os
    os.unlink(valid_file)
    os.unlink(invalid_file)
    os.unlink(test_file)

if __name__ == '__main__':
    demo_cli_tools()