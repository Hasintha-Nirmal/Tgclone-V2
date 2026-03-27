"""
Verification script for graceful shutdown implementation.
This script checks that all required changes are in place.
"""

import re

def check_file_contains(filepath, patterns, description):
    """Check if file contains all required patterns"""
    print(f"\nChecking {description}...")
    print(f"  File: {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        all_found = True
        for pattern_desc, pattern in patterns:
            if re.search(pattern, content, re.MULTILINE | re.DOTALL):
                print(f"  ✓ {pattern_desc}")
            else:
                print(f"  ✗ {pattern_desc} - NOT FOUND")
                all_found = False
        
        return all_found
    except Exception as e:
        print(f"  ✗ Error reading file: {e}")
        return False

def main():
    print("=" * 70)
    print("Graceful Worker Shutdown Implementation Verification")
    print("=" * 70)
    
    all_checks_passed = True
    
    # Check 1: SyncWorker has shutdown_timeout attribute
    check1 = check_file_contains(
        "app/worker/sync_worker.py",
        [
            ("shutdown_timeout attribute in __init__", 
             r"self\.shutdown_timeout\s*=\s*settings\.worker_shutdown_timeout"),
        ],
        "Sub-task 7.1: Shutdown infrastructure"
    )
    all_checks_passed = all_checks_passed and check1
    
    # Check 2: Graceful stop implementation
    check2 = check_file_contains(
        "app/worker/sync_worker.py",
        [
            ("Graceful shutdown logging", 
             r"logger\.info\(['\"]Initiating graceful shutdown"),
            ("Task cancellation loop", 
             r"for job_id, task in self\.tasks\.items\(\):.*task\.cancel\(\)"),
            ("asyncio.wait_for with timeout", 
             r"await asyncio\.wait_for\(.*timeout=self\.shutdown_timeout"),
            ("asyncio.gather with return_exceptions", 
             r"asyncio\.gather\(\*self\.tasks\.values\(\), return_exceptions=True\)"),
            ("Timeout exception handling", 
             r"except asyncio\.TimeoutError:"),
            ("Timeout warning log", 
             r"logger\.warning\(.*Shutdown timeout"),
        ],
        "Sub-task 7.2: Graceful stop implementation"
    )
    all_checks_passed = all_checks_passed and check2
    
    # Check 3: CancelledError handling
    check3 = check_file_contains(
        "app/worker/sync_worker.py",
        [
            ("CancelledError exception handler", 
             r"except asyncio\.CancelledError:"),
            ("Cleanup logging on cancellation", 
             r"logger\.info\(.*cancelled - cleaning up"),
            ("Database commit on cancellation", 
             r"await db\.commit\(\).*during shutdown"),
            ("Database rollback on error", 
             r"await db\.rollback\(\)"),
            ("Database close in finally", 
             r"await db\.close\(\)"),
            ("Re-raise CancelledError", 
             r"# Re-raise.*\n\s*raise"),
        ],
        "Sub-task 7.3: CancelledError handling"
    )
    all_checks_passed = all_checks_passed and check3
    
    # Check 4: Shutdown sequence in main.py
    check4 = check_file_contains(
        "app/web/main.py",
        [
            ("Worker stop logging", 
             r"logger\.info\(['\"]Stopping sync worker"),
            ("Await worker.stop()", 
             r"await sync_worker\.stop\(\)"),
            ("Worker stopped confirmation", 
             r"logger\.info\(['\"]Sync worker stopped successfully"),
            ("Job status update logging", 
             r"logger\.info\(['\"]Updating job statuses"),
            ("Client disconnect logging", 
             r"logger\.info\(['\"]Disconnecting Telegram clients"),
        ],
        "Sub-task 7.4: Shutdown sequence"
    )
    all_checks_passed = all_checks_passed and check4
    
    # Check 5: Configuration setting exists
    check5 = check_file_contains(
        "config/settings.py",
        [
            ("worker_shutdown_timeout setting", 
             r"worker_shutdown_timeout:\s*int\s*=\s*30"),
        ],
        "Configuration: worker_shutdown_timeout"
    )
    all_checks_passed = all_checks_passed and check5
    
    # Summary
    print("\n" + "=" * 70)
    if all_checks_passed:
        print("✓ ALL CHECKS PASSED")
        print("\nGraceful worker shutdown implementation is complete:")
        print("  • Shutdown timeout infrastructure added")
        print("  • Graceful stop with timeout implemented")
        print("  • CancelledError handling with cleanup added")
        print("  • Shutdown sequence properly logged")
        print("  • Configuration setting in place")
    else:
        print("✗ SOME CHECKS FAILED")
        print("\nPlease review the failed checks above.")
    print("=" * 70)
    
    return 0 if all_checks_passed else 1

if __name__ == "__main__":
    exit(main())
