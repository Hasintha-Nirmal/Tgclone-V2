#!/usr/bin/env python3
"""
Authorization Helper Script
Run this to authorize your Telegram account
"""
import asyncio
from telethon import TelegramClient
from pathlib import Path
from config.settings import settings

async def authorize():
    print("=" * 60)
    print("Telegram Account Authorization")
    print("=" * 60)
    
    session_dir = Path("sessions")
    session_dir.mkdir(exist_ok=True)
    
    phone = settings.telegram_phone
    session_name = phone.replace("+", "")
    session_file = session_dir / f"{session_name}.session"
    
    print(f"\nPhone: {phone}")
    print(f"Session: {session_file}")
    print("-" * 60)
    
    client = TelegramClient(
        str(session_file),
        settings.telegram_api_id,
        settings.telegram_api_hash
    )
    
    await client.connect()
    
    if await client.is_user_authorized():
        print("\n✓ Already authorized!")
        me = await client.get_me()
        print(f"  Logged in as: {me.first_name} {me.last_name or ''}")
        print(f"  Username: @{me.username or 'N/A'}")
        print(f"  Phone: {me.phone}")
    else:
        print("\n⚠ Authorization required")
        print("\nSending code to your Telegram account...")
        
        await client.send_code_request(phone)
        
        print("\n📱 Check your Telegram app for the verification code")
        code = input("Enter the code: ").strip()
        
        try:
            await client.sign_in(phone, code)
            print("\n✓ Successfully authorized!")
            
            me = await client.get_me()
            print(f"  Logged in as: {me.first_name} {me.last_name or ''}")
            print(f"  Username: @{me.username or 'N/A'}")
            
        except Exception as e:
            if "Two-steps verification" in str(e) or "password" in str(e).lower():
                print("\n🔐 2FA enabled - password required")
                # Use getpass for secure password input
                import getpass
                password = getpass.getpass("Enter your 2FA password: ").strip()
                await client.sign_in(password=password)
                print("\n✓ Successfully authorized with 2FA!")
            else:
                print(f"\n✗ Authorization failed: {e}")
                await client.disconnect()
                return
    
    await client.disconnect()
    
    print("\n" + "=" * 60)
    print("✓ Authorization complete!")
    print("You can now restart the application:")
    print("  docker-compose restart")
    print("=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(authorize())
    except KeyboardInterrupt:
        print("\n\nAuthorization cancelled")
    except Exception as e:
        print(f"\n✗ Error: {e}")
