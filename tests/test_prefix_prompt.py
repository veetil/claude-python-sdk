"""
Test prefix prompt functionality.
"""

import pytest
from pathlib import Path
from claude_sdk.core.config import ClaudeConfig


class TestPrefixPrompt:
    """Test the prefix prompt functionality."""
    
    def test_default_prefix_prompt_enabled(self):
        """Test that prefix prompt is enabled by default."""
        config = ClaudeConfig()
        assert config.enable_prefix_prompt is True
        assert config.prefix_prompt_file == "prefix-prompt.md"
    
    def test_disable_prefix_prompt(self):
        """Test disabling prefix prompt."""
        config = ClaudeConfig(enable_prefix_prompt=False)
        assert config.enable_prefix_prompt is False
        
        # Should return empty string when disabled
        prefix = config.get_prefix_prompt()
        assert prefix == ""
        
        # Should return unchanged prompt
        user_prompt = "test prompt"
        result = config.apply_prefix_prompt(user_prompt)
        assert result == user_prompt
    
    def test_custom_prefix_prompt_file(self):
        """Test custom prefix prompt file path."""
        custom_path = "/custom/path/to/prefix.md"
        config = ClaudeConfig(prefix_prompt_file=custom_path)
        assert config.prefix_prompt_file == custom_path
    
    def test_apply_prefix_prompt(self):
        """Test applying prefix prompt to user prompt."""
        # Create a temporary prefix file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("This is a test prefix prompt.")
            temp_file = f.name
        
        try:
            config = ClaudeConfig(prefix_prompt_file=temp_file)
            
            # Get prefix content
            prefix = config.get_prefix_prompt()
            assert prefix == "This is a test prefix prompt."
            
            # Apply to user prompt
            user_prompt = "User's question"
            result = config.apply_prefix_prompt(user_prompt)
            expected = "This is a test prefix prompt.\n\nUser's question"
            assert result == expected
            
        finally:
            # Clean up
            Path(temp_file).unlink(missing_ok=True)
    
    def test_missing_prefix_file(self):
        """Test behavior with missing prefix file."""
        config = ClaudeConfig(prefix_prompt_file="nonexistent.md")
        
        # Should return empty string
        prefix = config.get_prefix_prompt()
        assert prefix == ""
        
        # Should return unchanged prompt
        user_prompt = "test prompt"
        result = config.apply_prefix_prompt(user_prompt)
        assert result == user_prompt
    
    def test_prefix_prompt_from_env(self):
        """Test loading prefix prompt settings from environment."""
        import os
        
        # Save original values
        orig_enable = os.environ.get("CLAUDE_ENABLE_PREFIX_PROMPT")
        orig_file = os.environ.get("CLAUDE_PREFIX_PROMPT_FILE")
        
        try:
            os.environ["CLAUDE_ENABLE_PREFIX_PROMPT"] = "false"
            os.environ["CLAUDE_PREFIX_PROMPT_FILE"] = "custom-prefix.md"
            
            config = ClaudeConfig.from_env()
            assert config.enable_prefix_prompt is False
            assert config.prefix_prompt_file == "custom-prefix.md"
            
        finally:
            # Restore original values
            if orig_enable is None:
                os.environ.pop("CLAUDE_ENABLE_PREFIX_PROMPT", None)
            else:
                os.environ["CLAUDE_ENABLE_PREFIX_PROMPT"] = orig_enable
                
            if orig_file is None:
                os.environ.pop("CLAUDE_PREFIX_PROMPT_FILE", None)
            else:
                os.environ["CLAUDE_PREFIX_PROMPT_FILE"] = orig_file
    
    def test_empty_prefix_file(self):
        """Test behavior with empty prefix file."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("")  # Empty file
            temp_file = f.name
        
        try:
            config = ClaudeConfig(prefix_prompt_file=temp_file)
            
            # Should return empty string
            prefix = config.get_prefix_prompt()
            assert prefix == ""
            
            # Should return unchanged prompt
            user_prompt = "test prompt"
            result = config.apply_prefix_prompt(user_prompt)
            assert result == user_prompt
            
        finally:
            Path(temp_file).unlink(missing_ok=True)