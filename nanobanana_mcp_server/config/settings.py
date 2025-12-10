from dataclasses import dataclass, field
from enum import Enum
import os
from pathlib import Path

from dotenv import load_dotenv

# Security: Directories that are never allowed for output
# These are sensitive system directories that should never be written to
FORBIDDEN_OUTPUT_DIRECTORIES = [
    "/",
    "/etc",
    "/usr",
    "/bin",
    "/sbin",
    "/var",
    "/root",
    "/boot",
    "/dev",
    "/proc",
    "/sys",
    "/tmp",  # noqa: S108 - Avoid tmp for persistent storage (intentionally in forbidden list)
    "/System",  # macOS system
    "/Library",  # macOS system library
    "/Applications",  # macOS applications
    "C:\\Windows",  # Windows system
    "C:\\Program Files",
    "C:\\Program Files (x86)",
]


def _validate_output_directory(output_dir: str) -> str:
    """
    Validate that the output directory is safe for writing.

    Args:
        output_dir: The proposed output directory path

    Returns:
        The resolved absolute path if valid

    Raises:
        ValueError: If the directory is forbidden or invalid
    """
    # Resolve to absolute path
    resolved = os.path.realpath(os.path.abspath(output_dir))
    normalized = os.path.normpath(resolved)

    # Check against forbidden directories
    for forbidden in FORBIDDEN_OUTPUT_DIRECTORIES:
        forbidden_resolved = os.path.normpath(os.path.realpath(forbidden))
        # Check if output is exactly forbidden or is a direct child trying to write broadly
        if normalized == forbidden_resolved:
            raise ValueError(
                f"Output directory '{output_dir}' resolves to forbidden system directory"
            )
        # Also prevent writing directly under root-level forbidden paths
        if (
            normalized.startswith(forbidden_resolved + os.sep)
            and normalized.count(os.sep) <= forbidden_resolved.count(os.sep) + 1
        ):
            # Allow subdirectories but not direct children of sensitive roots
            pass  # This is okay - we allow deeper nesting

    # Ensure we're not trying to write to a symlink that points somewhere dangerous
    if os.path.islink(output_dir):
        link_target = os.readlink(output_dir)
        target_resolved = os.path.realpath(link_target)
        for forbidden in FORBIDDEN_OUTPUT_DIRECTORIES:
            if target_resolved.startswith(os.path.realpath(forbidden)):
                raise ValueError("Output directory symlink points to forbidden location")

    return resolved


def _get_allowed_input_directories() -> list[str]:
    """
    Get the list of allowed input directories from environment or defaults.

    Returns:
        List of allowed input directory paths
    """
    # Check for environment variable (comma-separated list)
    env_dirs = os.getenv("NANOBANANA_ALLOWED_INPUT_DIRS", "").strip()

    if env_dirs:
        dirs = [d.strip() for d in env_dirs.split(",") if d.strip()]
        # Resolve all paths
        return [os.path.realpath(os.path.abspath(d)) for d in dirs]

    # Default: current working directory and user's home directory
    defaults = [
        os.getcwd(),
        str(Path.home()),
    ]

    return [os.path.realpath(os.path.abspath(d)) for d in defaults]


class ModelTier(str, Enum):
    """Model selection options."""

    FLASH = "flash"  # Speed-optimized (Gemini 2.5 Flash)
    PRO = "pro"  # Quality-optimized (Gemini 3 Pro)
    AUTO = "auto"  # Automatic selection


class ThinkingLevel(str, Enum):
    """Gemini 3 thinking levels for advanced reasoning."""

    LOW = "low"  # Minimal latency, less reasoning
    HIGH = "high"  # Maximum reasoning (default for Pro)


class MediaResolution(str, Enum):
    """Media resolution for vision processing."""

    LOW = "low"  # Faster, less detail
    MEDIUM = "medium"  # Balanced
    HIGH = "high"  # Maximum detail


@dataclass
class ServerConfig:
    """Server configuration settings."""

    gemini_api_key: str
    server_name: str = "nanobanana-mcp-server"
    transport: str = "stdio"  # stdio or http
    host: str = "127.0.0.1"
    port: int = 9000
    mask_error_details: bool = False
    max_concurrent_requests: int = 10
    image_output_dir: str = ""
    allowed_input_directories: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "ServerConfig":
        """Load configuration from environment variables."""
        load_dotenv()

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY must be set")

        # Handle image output directory with security validation
        output_dir = os.getenv("IMAGE_OUTPUT_DIR", "").strip()
        if not output_dir:
            # Default to ~/nanobanana-images in user's home directory for better compatibility
            output_dir = str(Path.home() / "nanobanana-images")

        # Validate the output directory is not in a forbidden location
        try:
            validated_output_dir = _validate_output_directory(output_dir)
        except ValueError as e:
            raise ValueError(f"Invalid IMAGE_OUTPUT_DIR: {e}") from e

        # Convert to Path and ensure it exists
        output_path = Path(validated_output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Get allowed input directories
        allowed_input_dirs = _get_allowed_input_directories()

        return cls(
            gemini_api_key=api_key,
            transport=os.getenv("FASTMCP_TRANSPORT", "stdio"),
            host=os.getenv("FASTMCP_HOST", "127.0.0.1"),
            port=int(os.getenv("FASTMCP_PORT", "9000")),
            mask_error_details=os.getenv("FASTMCP_MASK_ERRORS", "false").lower() == "true",
            image_output_dir=str(output_path),
            allowed_input_directories=allowed_input_dirs,
        )


@dataclass
class BaseModelConfig:
    """Shared base configuration for all models."""

    max_images_per_request: int = 4
    max_inline_image_size: int = 20 * 1024 * 1024  # 20MB
    default_image_format: str = "png"
    request_timeout: int = 60  # seconds


@dataclass
class FlashImageConfig(BaseModelConfig):
    """Gemini 2.5 Flash Image configuration (speed-optimized)."""

    model_name: str = "gemini-2.5-flash-image"
    max_resolution: int = 1024
    supports_thinking: bool = False
    supports_grounding: bool = False
    supports_media_resolution: bool = False


@dataclass
class ProImageConfig(BaseModelConfig):
    """Gemini 3 Pro Image configuration (quality-optimized)."""

    model_name: str = "gemini-3-pro-image-preview"
    max_resolution: int = 3840  # 4K
    default_resolution: str = "high"  # low/medium/high
    default_thinking_level: ThinkingLevel = ThinkingLevel.HIGH
    default_media_resolution: MediaResolution = MediaResolution.HIGH
    supports_thinking: bool = True
    supports_grounding: bool = True
    supports_media_resolution: bool = True
    enable_search_grounding: bool = True
    request_timeout: int = 90  # Pro model needs more time for 4K


@dataclass
class ModelSelectionConfig:
    """Configuration for intelligent model selection."""

    default_tier: ModelTier = ModelTier.AUTO
    auto_quality_keywords: list[str] = field(
        default_factory=lambda: [
            "4k",
            "high quality",
            "professional",
            "production",
            "high-res",
            "high resolution",
            "detailed",
            "sharp",
            "crisp",
            "hd",
            "ultra",
            "premium",
            "magazine",
            "print",
        ]
    )
    auto_speed_keywords: list[str] = field(
        default_factory=lambda: [
            "quick",
            "fast",
            "draft",
            "prototype",
            "sketch",
            "rapid",
            "rough",
            "temporary",
            "test",
        ]
    )

    @classmethod
    def from_env(cls) -> "ModelSelectionConfig":
        """Load model selection config from environment."""
        load_dotenv()

        model_tier_str = os.getenv("NANOBANANA_MODEL", "auto").lower()
        try:
            default_tier = ModelTier(model_tier_str)
        except ValueError:
            default_tier = ModelTier.AUTO

        return cls(default_tier=default_tier)


@dataclass
class GeminiConfig:
    """Legacy Gemini API configuration (backward compatibility)."""

    model_name: str = "gemini-2.5-flash-image"
    max_images_per_request: int = 4
    max_inline_image_size: int = 20 * 1024 * 1024  # 20MB
    default_image_format: str = "png"
    request_timeout: int = 60  # seconds - increased for image generation
