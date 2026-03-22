#!/usr/bin/env python3
"""
Management CLI for Telegram Automation System
"""
import sys
import subprocess
import argparse
from pathlib import Path

def run_command(cmd, check=True):
    """Run shell command"""
    try:
        result = subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True)
        return result.returncode == 0
    except subprocess.CalledProcessError:
        return False

def docker_status():
    """Check if Docker container is running"""
    result = subprocess.run(
        "docker ps --filter name=telegram-automation --format '{{.Status}}'",
        shell=True,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

def cmd_start(args):
    """Start the system"""
    if args.docker:
        print("Starting Docker containers...")
        run_command("docker-compose up -d")
        print("\n✓ Started!")
        print("Access dashboard: http://localhost:8000")
        print("\nNext step: Authorize your account")
        print("  Run: python manage.py authorize")
    else:
        print("Starting local server...")
        print("Access dashboard: http://localhost:8000")
        print("\nPress Ctrl+C to stop")
        run_command("python main.py", check=False)

def cmd_stop(args):
    """Stop the system"""
    if args.docker:
        print("Stopping Docker containers...")
        run_command("docker-compose down")
        print("✓ Stopped!")
    else:
        print("Stop the local server with Ctrl+C")

def cmd_restart(args):
    """Restart the system"""
    if args.docker:
        print("Restarting Docker containers...")
        run_command("docker-compose restart")
        print("✓ Restarted!")
    else:
        print("Restart the local server manually")

def cmd_logs(args):
    """View logs"""
    if args.docker:
        print("Viewing Docker logs (Ctrl+C to exit)...")
        run_command("docker-compose logs -f", check=False)
    else:
        log_file = Path("logs/app.log")
        if log_file.exists():
            run_command(f"tail -f {log_file}", check=False)
        else:
            print("No log file found")

def cmd_authorize(args):
    """Authorize Telegram account"""
    if args.docker:
        print("Authorizing in Docker container...")
        run_command("docker exec -it telegram-automation python authorize.py", check=False)
        print("\nRestarting container...")
        run_command("docker-compose restart")
    else:
        print("Running authorization...")
        run_command("python authorize.py", check=False)

def cmd_status(args):
    """Show system status"""
    print("=" * 60)
    print("System Status")
    print("=" * 60)
    
    # Check .env
    if Path(".env").exists():
        print("✓ Configuration file exists")
    else:
        print("✗ Configuration file missing")
        print("  Run: cp .env.example .env")
    
    # Check session
    sessions = list(Path("sessions").glob("*.session"))
    if sessions:
        print(f"✓ Session file exists: {sessions[0].name}")
    else:
        print("✗ No session file found")
        print("  Run: python manage.py authorize")
    
    # Check Docker
    status = docker_status()
    if status:
        print(f"✓ Docker container: {status}")
    else:
        print("✗ Docker container not running")
        print("  Run: python manage.py start --docker")
    
    # Check web
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:8000/health", timeout=2)
        print("✓ Web interface: http://localhost:8000")
    except:
        print("✗ Web interface not accessible")
    
    print("=" * 60)

def cmd_cleanup(args):
    """Cleanup old files"""
    print("Cleaning up old files...")
    
    if args.docker:
        run_command("docker exec telegram-automation python -c \"from app.utils.storage import storage_manager; storage_manager.cleanup_old_files()\"")
    else:
        from app.utils.storage import storage_manager
        storage_manager.cleanup_old_files()
    
    print("✓ Cleanup complete!")

def cmd_check(args):
    """Run system checks"""
    print("Running system checks...")
    run_command("python check-system.py", check=False)

def cmd_shell(args):
    """Open shell in Docker container"""
    if docker_status():
        print("Opening shell in container...")
        run_command("docker exec -it telegram-automation bash", check=False)
    else:
        print("✗ Container not running")
        print("  Run: python manage.py start --docker")

def main():
    parser = argparse.ArgumentParser(
        description="Telegram Automation System Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python manage.py start --docker    # Start with Docker
  python manage.py authorize         # Authorize Telegram account
  python manage.py logs --docker     # View logs
  python manage.py status            # Check system status
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start the system")
    start_parser.add_argument("--docker", action="store_true", help="Use Docker")
    start_parser.set_defaults(func=cmd_start)
    
    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop the system")
    stop_parser.add_argument("--docker", action="store_true", help="Use Docker")
    stop_parser.set_defaults(func=cmd_stop)
    
    # Restart command
    restart_parser = subparsers.add_parser("restart", help="Restart the system")
    restart_parser.add_argument("--docker", action="store_true", help="Use Docker")
    restart_parser.set_defaults(func=cmd_restart)
    
    # Logs command
    logs_parser = subparsers.add_parser("logs", help="View logs")
    logs_parser.add_argument("--docker", action="store_true", help="Use Docker")
    logs_parser.set_defaults(func=cmd_logs)
    
    # Authorize command
    auth_parser = subparsers.add_parser("authorize", help="Authorize Telegram account")
    auth_parser.add_argument("--docker", action="store_true", help="Use Docker")
    auth_parser.set_defaults(func=cmd_authorize)
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show system status")
    status_parser.set_defaults(func=cmd_status)
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Cleanup old files")
    cleanup_parser.add_argument("--docker", action="store_true", help="Use Docker")
    cleanup_parser.set_defaults(func=cmd_cleanup)
    
    # Check command
    check_parser = subparsers.add_parser("check", help="Run system checks")
    check_parser.set_defaults(func=cmd_check)
    
    # Shell command
    shell_parser = subparsers.add_parser("shell", help="Open shell in Docker container")
    shell_parser.set_defaults(func=cmd_shell)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    args.func(args)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
