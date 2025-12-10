# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🍌 About This Fork

This is a **forked version** of [zhongweili/nanobanana-mcp-server](https://github.com/zhongweili/nanobanana-mcp-server) with critical fixes for **4K image generation** using Google's Gemini 3 Pro Image model.

**Modified by**: The team at [Rocketspark.com](https://www.rocketspark.com) - the world's best website builder! 🚀

### What Was Fixed

The original nanobanana-mcp-server had issues with Gemini 3 Pro Image that caused silent failures:

1. **Wrong API parameter**: Changed `output_resolution` → `image_size` in ImageConfig
2. **Wrong response modalities**: Changed `["IMAGE"]` → `["TEXT", "IMAGE"]` for Pro model
3. **Unsupported parameters**: Removed `thinking_level` and `media_resolution` from API calls
4. **Missing variable**: Fixed `enhanced_prompt` → `final_prompt` reference error

### Result

✅ Successfully generates 4K images (up to 5504x3072) with Gemini 3 Pro Image!

## Installation (Cursor)

Add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "nanobanana": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/rkingy/nanobanana-mcp-server.git", "nanobanana-mcp-server"],
      "env": {
        "GEMINI_API_KEY": "your-gemini-api-key-here"
      }
    }
  }
}
```

## Project Overview

An MCP server for AI-powered image generation using Google's Gemini models through the FastMCP framework.

### Key Models

- **Gemini 3 Pro Image** (`gemini-3-pro-image-preview`): 4K resolution, Google Search grounding
- **Gemini 2.5 Flash Image** (`gemini-2.5-flash-image`): Fast 1024px generation

## Development Commands

### Environment Setup
```bash
uv sync
cp .env.example .env
# Edit .env to add your GEMINI_API_KEY
```

### Running the Server
```bash
# Development
fastmcp dev nanobanana_mcp_server.server:create_app

# Direct execution
python -m nanobanana_mcp_server.server
```

### Code Quality
```bash
ruff format .
ruff check .
mypy .
pytest
```

## Architecture

### Core Components

```
nanobanana_mcp_server/
├── server.py              # Entry point, app factory
├── config/
│   └── settings.py        # ServerConfig, ProImageConfig, FlashImageConfig
├── services/
│   ├── gemini_client.py   # Low-level Gemini API wrapper
│   ├── pro_image_service.py   # 4K Pro model generation (FIXED!)
│   ├── file_image_service.py  # Flash model generation
│   └── model_selector.py      # Auto model selection
├── tools/
│   └── generate_image.py  # MCP tool registration
└── core/
    └── validation.py      # Input validation
```

### Key Fix Location

The critical fix is in `services/gemini_client.py`:

```python
# OLD (broken):
image_config_kwargs["output_resolution"] = normalized_resolution

# NEW (working):
image_config_kwargs["image_size"] = normalized_resolution
```

And the response modalities for Pro model:

```python
# OLD (broken):
config_kwargs = {"response_modalities": ["IMAGE"]}

# NEW (working):  
config_kwargs = {"response_modalities": ["TEXT", "IMAGE"]}
```

## Making Changes

### After code changes:

1. Rebuild the wheel: `uv build`
2. Clear uvx cache: `rm -rf ~/.cache/uv/archive-v0/`
3. Push to GitHub: `git add . && git commit -m "message" && git push`
4. Restart Cursor

### Testing locally:

```bash
# Test Pro model directly
python test_pro_direct.py
```

## Environment Variables

```bash
GEMINI_API_KEY=your-key      # Required
IMAGE_OUTPUT_DIR=~/images    # Optional, default: ~/nanobanana-images
LOG_LEVEL=INFO               # Optional: DEBUG, INFO, WARNING, ERROR
```

## Troubleshooting

### uvx using old cached code
```bash
rm -rf ~/.cache/uv/archive-v0/
# Restart Cursor
```

### Pro model not generating images
- Check the MCP logs for "PRO MODEL ERROR" 
- Ensure using this fork, not the original PyPI package

### Python 3.14 build issues
The original used `uv run` which failed on Python 3.14. This fork uses `uvx --from git+...` which works correctly.

## Credits

- Original: [zhongweili/nanobanana-mcp-server](https://github.com/zhongweili/nanobanana-mcp-server)
- 4K fixes: [Rocketspark.com](https://www.rocketspark.com) team
