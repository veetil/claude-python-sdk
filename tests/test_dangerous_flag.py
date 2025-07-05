"""
Test --dangerously-skip-permissions flag handling.
"""

import pytest
from claude_sdk.core.subprocess_wrapper import CommandBuilder
from claude_sdk.core.config import ClaudeConfig


class TestDangerousFlag:
    """Test the --dangerously-skip-permissions flag handling."""
    
    def test_default_includes_dangerous_flag(self):
        """Test that the flag is included by default."""
        builder = CommandBuilder()
        cmd = builder.add_prompt("Hello").build()
        
        assert "--dangerously-skip-permissions" in cmd
        assert cmd == ["claude", "--dangerously-skip-permissions", "-p", "Hello"]
    
    def test_safe_mode_excludes_dangerous_flag(self):
        """Test that safe mode excludes the flag."""
        config = ClaudeConfig(safe_mode=True)
        builder = CommandBuilder(config=config)
        cmd = builder.add_prompt("Hello").build()
        
        assert "--dangerously-skip-permissions" not in cmd
        assert cmd == ["claude", "-p", "Hello"]
    
    def test_with_multiple_options(self):
        """Test flag placement with multiple options."""
        builder = CommandBuilder()
        cmd = (builder
               .add_prompt("Test")
               .set_session_id("123")
               .set_output_format("json")
               .build())
        
        # Flag should be right after 'claude'
        assert cmd[0] == "claude"
        assert cmd[1] == "--dangerously-skip-permissions"
        assert "-p" in cmd
        assert "Test" in cmd
        assert "--session-id" in cmd
        assert "123" in cmd
        assert "--output-format" in cmd
        assert "json" in cmd
    
    def test_with_files_and_workspace(self):
        """Test flag with files and workspace options."""
        builder = CommandBuilder()
        cmd = (builder
               .add_prompt("Analyze")
               .add_files(["file1.py", "file2.py"])
               .set_workspace_id("ws-123")
               .build())
        
        assert cmd[0] == "claude"
        assert cmd[1] == "--dangerously-skip-permissions"
        assert "--file" in cmd
        assert "file1.py" in cmd
        assert "file2.py" in cmd
        assert "--workspace-id" in cmd
        assert "ws-123" in cmd
    
    def test_raw_args(self):
        """Test flag with raw arguments."""
        builder = CommandBuilder()
        cmd = builder.add_raw_args(["--help"]).build()
        
        assert cmd == ["claude", "--dangerously-skip-permissions", "--help"]
    
    def test_safe_mode_from_env(self):
        """Test safe mode can be set from environment."""
        import os
        original = os.environ.get("CLAUDE_SAFE_MODE")
        
        try:
            os.environ["CLAUDE_SAFE_MODE"] = "true"
            config = ClaudeConfig.from_env()
            assert config.safe_mode is True
            
            builder = CommandBuilder(config=config)
            cmd = builder.add_prompt("Test").build()
            assert "--dangerously-skip-permissions" not in cmd
            
        finally:
            if original is None:
                os.environ.pop("CLAUDE_SAFE_MODE", None)
            else:
                os.environ["CLAUDE_SAFE_MODE"] = original