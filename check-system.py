#!/usr/bin/env python3
"""
System Check Script
Verifies configuration and system status
"""
import os
import sys
from pathlib import Path

def check_env_file():
    """Check if .env file exists and has required variables"""
    print("Checking .env file...")
    
    if not Path(".env").exists():
        print("  ✗ .env file not found")
        print("  → Run: cp .env.example .env")
        return False
    
    print("  ✓ .env file exists")
    
    required_vars = [
        "TELEGRAM_API_ID",
        "TELEGRAM_API_HASH",
        "TELEGRAM_PHONE",
        "SECRET_KEY"
    ]
    
    missing = []
    with open(".env") as f:
        content = f.read()
        for var in required_vars:
            if f"{var}=" not in content or f"{var}=your_" in content or f"{var}=change" in content:
                missing.append(var)
    
    if missing:
        print(f"  ✗ Missing or invalid variables: {', '.join(missing)}")
        return False
    
    print("  ✓ All required variables set")
    return True

def check_directories():
    """Check if required directories exist"""
    print("\nChecking directories...")
    
    dirs = ["sessions", "logs", "downloads", "data"]
    all_exist = True
    
    for d in dirs:
        if Path(d).exists():
            print(f"  ✓ {d}/ exists")
        else:
            print(f"  ✗ {d}/ missing")
            all_exist = False
    
    return all_exist

def check_session():
    """Check if session file exists"""
    print("\nChecking Telegram session...")
    
    session_files = list(Path("sessions").glob("*.session"))
    
    if not session_files:
        print("  ✗ No session file found")
        print("  → Run: python authorize.py")
        return False
    
    print(f"  ✓ Session file found: {session_files[0].name}")
    return True

def check_dependencies():
    """Check if required packages are installed"""
    print("\nChecking dependencies...")
    
    required = ["telethon", "fastapi", "uvicorn", "sqlalchemy"]
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"  ✓ {package} installed")
        except ImportError:
            print(f"  ✗ {package} not installed")
            missing.append(package)
    
    if missing:
        print(f"\n  → Run: pip install -r requirements.txt")
        return False
    
    return True

def check_docker():
    """Check Docker status"""
    print("\nChecking Docker...")
    
    import subprocess
    
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=telegram-automation"],
            capture_output=True,
            text=True
        )
        
        if "telegram-automation" in result.stdout:
            print("  ✓ Docker container is running")
            return True
        else:
            print("  ✗ Docker container not running")
            print("  → Run: docker-compose up -d")
            return False
    except FileNotFoundError:
        print("  ℹ Docker not found (OK if running locally)")
        return None

def main():
    print("=" * 60)
    print("Telegram Automation System - System Check")
    print("=" * 60)
    print()
    
    checks = {
        "Environment": check_env_file(),
        "Directories": check_directories(),
        "Dependencies": check_dependencies(),
        "Session": check_session(),
    }
    
    docker_status = check_docker()
    if docker_status is not None:
        checks["Docker"] = docker_status
    
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)
    
    for name, status in checks.items():
        symbol = "✓" if status else "✗"
        print(f"{symbol} {name}")
    
    all_passed = all(checks.values())
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("✓ All checks passed!")
        print("\nYou can now run:")
        print("  python main.py")
        print("\nOr with Docker:")
        print("  docker-compose up -d")
        print("\nThen access: http://localhost:8000")
    else:
        print("✗ Some checks failed")
        print("\nPlease fix the issues above and run this script again.")
        sys.exit(1)
    
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCheck cancelled")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
