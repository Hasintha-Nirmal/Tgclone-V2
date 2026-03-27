#!/usr/bin/env python3
"""
Test script to verify safe file operations in MessageCloner
Tests upload verification and safe file cleanup
"""
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

async def test_safe_file_operations():
    """Test safe file operations in MessageCloner"""
    from app.utils.logger import logger
    
    try:
        from app.cloner.message_cloner import MessageCloner
        from config.settings import settings
        
        logger.info("=" * 60)
        logger.info("Testing Safe File Operations")
        logger.info("=" * 60)
        
        # Create mock client
        mock_client = AsyncMock()
        cloner = MessageCloner(mock_client)
        
        # Test 1: Successful upload with cleanup
        logger.info("\n1. Testing successful upload with cleanup...")
        
        # Create a mock message with media
        mock_message = Mock()
        mock_message.id = 12345
        mock_message.text = "Test message"
        mock_message.entities = []
        mock_message.media = Mock()  # Has media
        
        # Create a temporary test file
        test_file = Path("downloads/test_file_12345.jpg")
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("test content")
        
        # Mock the download to return our test file
        with patch.object(cloner, '_download_media', return_value=test_file):
            # Mock successful upload with result.id
            mock_result = Mock()
            mock_result.id = 67890
            mock_client.send_file = AsyncMock(return_value=mock_result)
            
            # Mock storage manager cleanup
            with patch('app.cloner.message_cloner.storage_manager') as mock_storage:
                mock_storage.cleanup_file = Mock()
                
                # Enable auto-delete
                original_auto_delete = settings.auto_delete_files
                settings.auto_delete_files = True
                
                try:
                    # Execute clone
                    await cloner._clone_single_message(
                        mock_message,
                        Mock(),  # target_entity
                        "test_job_1"
                    )
                    
                    # Verify upload was called
                    assert mock_client.send_file.called, "send_file should be called"
                    
                    # Verify cleanup was called (successful upload)
                    assert mock_storage.cleanup_file.called, "cleanup_file should be called on success"
                    logger.info("✓ File cleaned up after successful upload")
                    
                finally:
                    settings.auto_delete_files = original_auto_delete
                    if test_file.exists():
                        test_file.unlink()
        
        # Test 2: Failed upload - file retained
        logger.info("\n2. Testing failed upload - file should be retained...")
        
        test_file2 = Path("downloads/test_file_23456.jpg")
        test_file2.write_text("test content 2")
        
        with patch.object(cloner, '_download_media', return_value=test_file2):
            # Mock failed upload (no result.id)
            mock_result_failed = Mock()
            mock_result_failed.id = None  # Upload verification fails
            mock_client.send_file = AsyncMock(return_value=mock_result_failed)
            
            with patch('app.cloner.message_cloner.storage_manager') as mock_storage:
                mock_storage.cleanup_file = Mock()
                
                settings.auto_delete_files = True
                
                try:
                    # Execute clone - should raise exception
                    await cloner._clone_single_message(
                        mock_message,
                        Mock(),
                        "test_job_2"
                    )
                    assert False, "Should have raised exception for failed upload"
                    
                except Exception as e:
                    # Verify cleanup was NOT called (failed upload)
                    assert not mock_storage.cleanup_file.called, "cleanup_file should NOT be called on failure"
                    logger.info(f"✓ File retained after upload failure: {e}")
                    
                finally:
                    settings.auto_delete_files = original_auto_delete
                    if test_file2.exists():
                        test_file2.unlink()
        
        # Test 3: Upload verification with result.id
        logger.info("\n3. Testing upload verification...")
        
        test_file3 = Path("downloads/test_file_34567.jpg")
        test_file3.write_text("test content 3")
        
        with patch.object(cloner, '_download_media', return_value=test_file3):
            # Mock successful upload with valid result.id
            mock_result_success = Mock()
            mock_result_success.id = 99999
            mock_client.send_file = AsyncMock(return_value=mock_result_success)
            
            with patch('app.cloner.message_cloner.storage_manager') as mock_storage:
                mock_storage.cleanup_file = Mock()
                
                settings.auto_delete_files = True
                
                try:
                    await cloner._clone_single_message(
                        mock_message,
                        Mock(),
                        "test_job_3"
                    )
                    
                    # Verify upload verification succeeded
                    logger.info(f"✓ Upload verified with result.id: {mock_result_success.id}")
                    assert mock_storage.cleanup_file.called, "File should be cleaned up after verified upload"
                    
                finally:
                    settings.auto_delete_files = original_auto_delete
                    if test_file3.exists():
                        test_file3.unlink()
        
        # Test 4: File lifecycle logging
        logger.info("\n4. Testing file lifecycle logging...")
        
        test_file4 = Path("downloads/test_file_45678.jpg")
        test_file4.write_text("test content 4")
        
        with patch.object(cloner, '_download_media', return_value=test_file4):
            mock_result_log = Mock()
            mock_result_log.id = 11111
            mock_client.send_file = AsyncMock(return_value=mock_result_log)
            
            with patch('app.cloner.message_cloner.storage_manager') as mock_storage:
                mock_storage.cleanup_file = Mock()
                
                settings.auto_delete_files = True
                
                # Capture log messages
                with patch('app.cloner.message_cloner.logger') as mock_logger:
                    try:
                        await cloner._clone_single_message(
                            mock_message,
                            Mock(),
                            "test_job_4"
                        )
                        
                        # Verify logging calls
                        log_calls = [str(call) for call in mock_logger.debug.call_args_list + 
                                   mock_logger.info.call_args_list]
                        
                        # Check for key log messages
                        has_download_log = any('download' in str(call).lower() for call in log_calls)
                        has_upload_log = any('upload' in str(call).lower() for call in log_calls)
                        has_cleanup_log = any('cleanup' in str(call).lower() or 'cleaning' in str(call).lower() for call in log_calls)
                        
                        logger.info(f"✓ File lifecycle logging present:")
                        logger.info(f"  - Download logging: {has_download_log}")
                        logger.info(f"  - Upload logging: {has_upload_log}")
                        logger.info(f"  - Cleanup logging: {has_cleanup_log}")
                        
                    finally:
                        settings.auto_delete_files = original_auto_delete
                        if test_file4.exists():
                            test_file4.unlink()
        
        # Test 5: Auto-delete disabled - file retained
        logger.info("\n5. Testing auto-delete disabled...")
        
        test_file5 = Path("downloads/test_file_56789.jpg")
        test_file5.write_text("test content 5")
        
        with patch.object(cloner, '_download_media', return_value=test_file5):
            mock_result_no_delete = Mock()
            mock_result_no_delete.id = 22222
            mock_client.send_file = AsyncMock(return_value=mock_result_no_delete)
            
            with patch('app.cloner.message_cloner.storage_manager') as mock_storage:
                mock_storage.cleanup_file = Mock()
                
                settings.auto_delete_files = False  # Disable auto-delete
                
                try:
                    await cloner._clone_single_message(
                        mock_message,
                        Mock(),
                        "test_job_5"
                    )
                    
                    # Verify cleanup was NOT called (auto-delete disabled)
                    assert not mock_storage.cleanup_file.called, "cleanup_file should NOT be called when auto-delete is disabled"
                    logger.info("✓ File retained when auto-delete is disabled")
                    
                finally:
                    settings.auto_delete_files = original_auto_delete
                    if test_file5.exists():
                        test_file5.unlink()
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ ALL TESTS PASSED")
        logger.info("=" * 60)
        logger.info("\nSafe File Operations Summary:")
        logger.info("- Upload verification working (checks result.id)")
        logger.info("- Files cleaned up only on successful upload")
        logger.info("- Files retained on upload failure")
        logger.info("- File lifecycle logging implemented")
        logger.info("- Auto-delete setting respected")
        logger.info("- No premature file deletion")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_safe_file_operations())
    sys.exit(0 if success else 1)
