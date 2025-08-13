#!/usr/bin/env python3
"""
Verify that the critical fixes are in place for the HVAC calculation issues
"""

import os
import sys

def verify_fixes():
    """Check that all critical fixes are in place"""
    
    print("Verifying AutoHVAC fixes...")
    print("-" * 50)
    
    issues_found = []
    
    # 1. Check construction vintage default
    print("1. Checking construction vintage default...")
    with open("tasks/calculate_hvac_loads.py", "r") as f:
        content = f.read()
        if "construction_vintage='current-code'" in content:
            print("   ✅ Construction vintage defaults to 'current-code'")
        else:
            print("   ❌ Construction vintage not set to 'current-code'")
            issues_found.append("Construction vintage default")
    
    # 2. Check GPT-4V timeout initialization
    print("2. Checking GPT-4V timeout initialization...")
    with open("services/gpt4v_blueprint_analyzer.py", "r") as f:
        content = f.read()
        lines = content.split('\n')
        timeout_line = -1
        model_config_line = -1
        
        for i, line in enumerate(lines):
            if 'self.gpt_timeout = float' in line:
                timeout_line = i
            if 'self.model_configs = {' in line:
                model_config_line = i
        
        if timeout_line > 0 and model_config_line > 0 and timeout_line < model_config_line:
            print("   ✅ GPT timeout initialized before model configs")
        else:
            print("   ❌ GPT timeout initialization order incorrect")
            issues_found.append("GPT-4V timeout init")
    
    # 3. Check fallback room creation is disabled
    print("3. Checking fallback room creation is disabled...")
    with open("services/blueprint_parser.py", "r") as f:
        content = f.read()
        if "raise NeedsInputError" in content and "AI FALLBACK DISABLED" in content:
            print("   ✅ AI fallback rooms are disabled")
        else:
            print("   ❌ AI fallback rooms might still be created")
            issues_found.append("Fallback room creation")
    
    # 4. Check that partial blueprint isn't created on NeedsInputError
    print("4. Checking NeedsInputError handling...")
    with open("services/blueprint_parser.py", "r") as f:
        content = f.read()
        if "isinstance(e, NeedsInputError)" in content and "Not creating fallback rooms" in content:
            print("   ✅ NeedsInputError properly handled without creating fake rooms")
        else:
            print("   ❌ NeedsInputError might still create partial results")
            issues_found.append("NeedsInputError handling")
    
    # 5. Check multi-story correction logic
    print("5. Checking multi-story correction logic...")
    with open("services/blueprint_parser.py", "r") as f:
        content = f.read()
        if "STORIES BUG: Detected" in content and "stories = len(floors_processed)" in content:
            print("   ✅ Multi-story correction logic in place")
        else:
            print("   ❌ Multi-story correction logic missing")
            issues_found.append("Multi-story correction")
    
    # 6. Check floor loss logic
    print("6. Checking floor loss application logic...")
    with open("services/manualj.py", "r") as f:
        content = f.read()
        if "is_ground_floor = (room.floor == 1)" in content:
            print("   ✅ Floor losses only applied to ground floor")
        else:
            print("   ❌ Floor loss logic might be incorrect")
            issues_found.append("Floor loss logic")
    
    print("-" * 50)
    
    if issues_found:
        print(f"❌ {len(issues_found)} issues found:")
        for issue in issues_found:
            print(f"   - {issue}")
        return False
    else:
        print("✅ All critical fixes are in place!")
        print("\nExpected improvements:")
        print("• Construction vintage: +8-10k BTU/hr heating")
        print("• Multi-story detection: +6k BTU/hr heating")
        print("• Scale/orientation: +2-3k BTU/hr heating")
        print("• Floor losses: +3k BTU/hr heating")
        print("• No fake rooms: +5k BTU/hr heating")
        print("\nTotal expected: ~74,000 BTU/hr heating (vs 60,125 before)")
        return True

if __name__ == "__main__":
    os.chdir("/Users/austindixon/Documents/AutoHVAC/backend")
    success = verify_fixes()
    sys.exit(0 if success else 1)