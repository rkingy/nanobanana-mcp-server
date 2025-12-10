# Nano Banana MCP Server 🍌 (Rocketspark Fork)

> **This is a forked version** of [zhongweili/nanobanana-mcp-server](https://github.com/zhongweili/nanobanana-mcp-server) with **fixes for 4K image generation** using Gemini 3 Pro Image.

Modified and maintained by the team at [Rocketspark.com](https://www.rocketspark.com) - the world's best website builder! 🚀

## 🔧 What's Fixed in This Fork

The original nanobanana-mcp-server had issues with the **Gemini 3 Pro Image** model that prevented 4K image generation from working. This fork includes:

- ✅ **Fixed Pro Model API calls** - Corrected `image_size` parameter in ImageConfig
- ✅ **Fixed response modalities** - Pro model now correctly uses `['TEXT', 'IMAGE']`
- ✅ **Simplified Pro service** - Removed unsupported parameters that caused silent failures
- ✅ **Working 4K generation** - Successfully generates images up to 5504x3072 resolution!

## 🚀 Quick Start - Cursor Installation

Add this to your Cursor MCP configuration (`~/.cursor/mcp.json`):

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

Then restart Cursor and you're ready to generate 4K images!

### Getting a Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a free API key
3. Add it to your MCP configuration

## ✨ Features

- 🏆 **4K Image Generation** - Up to 5504x3072 resolution with Gemini 3 Pro Image
- ⚡ **Fast Generation** - Gemini 2.5 Flash Image for quick iterations
- 🤖 **Smart Model Selection** - Automatically chooses the best model for your prompt
- 📐 **Aspect Ratio Control** - 1:1, 16:9, 9:16, 21:9, and more
- 🌐 **Google Search Grounding** - Real-world knowledge for accurate images
- 🧠 **Advanced Reasoning** - Thinking mode for complex compositions

## 📸 Usage Examples

Once configured, ask your AI assistant to generate images:

```
"Generate a 4K landscape of New Zealand mountains"
"Create a professional product photo"
"Make a 16:9 YouTube thumbnail"
```

### Model Selection

**Pro Model (4K, high quality)**:
- Use for: Professional photos, 4K resolution, text in images
- Triggers: "4K", "professional", "high-res", "production"

**Flash Model (fast)**:
- Use for: Quick drafts, iterations, sketches
- Triggers: "quick", "draft", "sketch", "rapid"

## 🔧 Other MCP Clients

### Claude Desktop

Add to `claude_desktop_config.json`:

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

### Claude Code (VS Code)

1. Install the Claude Code extension
2. Open Command Palette (`Cmd/Ctrl + Shift + P`)
3. Run "Claude Code: Add MCP Server"
4. Configure with the same settings as above

## ⚙️ Environment Variables

```bash
# Required
GEMINI_API_KEY=your-gemini-api-key-here

# Optional
IMAGE_OUTPUT_DIR=/path/to/images  # Default: ~/nanobanana-images
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
```

## 🐛 Troubleshooting

**Images not generating?**
- Make sure you're using this fork, not the original
- Clear uvx cache: `rm -rf ~/.cache/uv/archive-v0/`
- Restart your MCP client

**"GEMINI_API_KEY not set"**
- Add your API key to the MCP configuration
- Get a key at [Google AI Studio](https://makersuite.google.com/app/apikey)

## 🙏 Credits

- Original project: [zhongweili/nanobanana-mcp-server](https://github.com/zhongweili/nanobanana-mcp-server)
- 4K fixes by: [Rocketspark.com](https://www.rocketspark.com) team

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.
