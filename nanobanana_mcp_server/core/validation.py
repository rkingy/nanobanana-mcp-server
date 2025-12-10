"""Input validation utilities."""

import os
import re

from ..config.constants import SUPPORTED_IMAGE_TYPES
from .exceptions import ValidationError

# Global configuration for allowed directories (set during server initialization)
_allowed_input_directories: list[str] = []
_allowed_output_directory: str | None = None


def configure_allowed_directories(
    input_dirs: list[str] | None = None, output_dir: str | None = None
) -> None:
    """
    Configure allowed directories for file operations.

    This should be called during server initialization to set up sandboxing.

    Args:
        input_dirs: List of directories from which input files can be read.
                   If None or empty, input file access is restricted to current working directory.
        output_dir: Directory where output files can be written.
                   If None, output is restricted to current working directory.
    """
    global _allowed_input_directories, _allowed_output_directory

    if input_dirs:
        # Resolve all input directories to absolute paths
        _allowed_input_directories = [os.path.realpath(os.path.abspath(d)) for d in input_dirs]
    else:
        # Default to current working directory only
        _allowed_input_directories = [os.path.realpath(os.getcwd())]

    if output_dir:
        _allowed_output_directory = os.path.realpath(os.path.abspath(output_dir))
    else:
        _allowed_output_directory = os.path.realpath(os.getcwd())


def get_allowed_input_directories() -> list[str]:
    """Get the list of allowed input directories."""
    if not _allowed_input_directories:
        # Return default if not configured
        return [os.path.realpath(os.getcwd())]
    return _allowed_input_directories.copy()


def get_allowed_output_directory() -> str | None:
    """Get the allowed output directory."""
    return _allowed_output_directory


def validate_prompt(prompt: str) -> None:
    """Validate image generation prompt."""
    if not prompt or not prompt.strip():
        raise ValidationError("Prompt cannot be empty")

    if len(prompt) > 8192:
        raise ValidationError("Prompt too long (max 8192 characters)")

    # Check for potentially harmful content patterns
    harmful_patterns = [
        r"\b(?:nude|naked|nsfw)\b",
        r"\b(?:violence|gore|blood)\b",
        r"\b(?:hate|racist|offensive)\b",
    ]

    for pattern in harmful_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            raise ValidationError("Prompt contains potentially inappropriate content")


def validate_image_count(n: int) -> None:
    """Validate requested image count."""
    if not isinstance(n, int):
        raise ValidationError("Image count must be an integer")

    if n < 1 or n > 4:
        raise ValidationError("Image count must be between 1 and 4")


def validate_image_format(mime_type: str) -> None:
    """Validate image MIME type."""
    if not mime_type:
        raise ValidationError("MIME type cannot be empty")

    if mime_type.lower() not in SUPPORTED_IMAGE_TYPES:
        raise ValidationError(
            f"Unsupported image format: {mime_type}. "
            f"Supported types: {', '.join(SUPPORTED_IMAGE_TYPES)}"
        )


def validate_base64_image(image_b64: str) -> None:
    """Validate base64 encoded image."""
    if not image_b64:
        raise ValidationError("Base64 image data cannot be empty")

    try:
        import base64

        base64.b64decode(image_b64, validate=True)
    except Exception as e:
        raise ValidationError(f"Invalid base64 image data: {e}")


def validate_image_list_consistency(
    images_b64: list[str] | None, mime_types: list[str] | None
) -> None:
    """Validate that image lists are consistent."""
    if images_b64 is None and mime_types is None:
        return

    if images_b64 is None or mime_types is None:
        raise ValidationError("Both images_b64 and mime_types must be provided together")

    if len(images_b64) != len(mime_types):
        raise ValidationError(
            f"images_b64 ({len(images_b64)}) and mime_types ({len(mime_types)}) "
            "must have the same length"
        )

    if len(images_b64) > 4:
        raise ValidationError("Maximum 4 input images allowed")

    # Validate each image and MIME type
    for i, (img_b64, mime_type) in enumerate(zip(images_b64, mime_types)):
        try:
            validate_base64_image(img_b64)
            validate_image_format(mime_type)
        except ValidationError as e:
            raise ValidationError(f"Invalid image {i + 1}: {e}")


def validate_file_path(
    path: str, allowed_directories: list[str] | None = None, must_exist: bool = True
) -> str:
    """
    Validate and sanitize file path for safe file operations.

    This function provides security against:
    - Path traversal attacks (../)
    - Symlink attacks (symlinks pointing outside allowed directories)
    - Access to files outside allowed directories

    Args:
        path: The file path to validate
        allowed_directories: List of directories the file must be within.
                           If None, uses globally configured input directories.
        must_exist: If True, validates that the file exists

    Returns:
        The resolved absolute path if validation passes

    Raises:
        ValidationError: If the path is invalid or outside allowed directories
    """
    if not path or not path.strip():
        raise ValidationError("File path cannot be empty")

    # Use provided directories or fall back to global config
    if allowed_directories is None:
        allowed_directories = get_allowed_input_directories()

    # Ensure we have at least one allowed directory
    if not allowed_directories:
        raise ValidationError("No allowed directories configured for file access")

    try:
        # First, get the absolute path without following symlinks
        abs_path = os.path.abspath(path)

        # Then resolve the full path, following all symlinks
        # This is critical for preventing symlink-based attacks
        resolved_path = os.path.realpath(abs_path)

        # Normalize the path to handle any remaining edge cases
        resolved_path = os.path.normpath(resolved_path)

    except (OSError, ValueError) as e:
        raise ValidationError(f"Invalid file path: {e}") from e

    # Resolve allowed directories the same way for consistent comparison
    resolved_allowed = [
        os.path.normpath(os.path.realpath(os.path.abspath(d))) for d in allowed_directories
    ]

    # Check if the resolved path is within any allowed directory
    path_allowed = False
    for allowed_dir in resolved_allowed:
        # Use os.path.commonpath to safely check if path is under allowed_dir
        try:
            # The path must start with the allowed directory
            # We add os.sep to ensure we match directory boundaries
            # e.g., /allowed/dir should match /allowed/dir/file but not /allowed/dirty
            if resolved_path.startswith(allowed_dir + os.sep) or resolved_path == allowed_dir:
                path_allowed = True
                break
        except ValueError:
            # commonpath raises ValueError if paths are on different drives (Windows)
            continue

    if not path_allowed:
        # Don't reveal the allowed directories in error messages (information disclosure)
        raise ValidationError("File path is outside allowed directories")

    if must_exist:
        if not os.path.exists(resolved_path):
            # Use generic error message to avoid filesystem enumeration
            raise ValidationError("File not found or inaccessible")

        if not os.path.isfile(resolved_path):
            raise ValidationError("Path is not a regular file")

        # Additional check: ensure it's not a device file or other special file
        try:
            file_stat = os.stat(resolved_path)
            import stat

            if not stat.S_ISREG(file_stat.st_mode):
                raise ValidationError("Path is not a regular file")
        except OSError as e:
            raise ValidationError("Unable to access file") from e

    return resolved_path


def validate_input_image_path(path: str) -> str:
    """
    Validate an input image path for reading.

    This is a convenience wrapper around validate_file_path specifically
    for input images used in generation/editing operations.

    Args:
        path: The file path to validate

    Returns:
        The resolved absolute path if validation passes

    Raises:
        ValidationError: If the path is invalid or not an allowed input
    """
    return validate_file_path(
        path, allowed_directories=get_allowed_input_directories(), must_exist=True
    )


def validate_output_path(path: str) -> str:
    """
    Validate an output file path for writing.

    Ensures the output path is within the allowed output directory.

    Args:
        path: The file path to validate

    Returns:
        The resolved absolute path if validation passes

    Raises:
        ValidationError: If the path is outside the allowed output directory
    """
    output_dir = get_allowed_output_directory()
    if not output_dir:
        raise ValidationError("No output directory configured")

    return validate_file_path(
        path,
        allowed_directories=[output_dir],
        must_exist=False,  # Output files don't need to exist yet
    )


def validate_edit_instruction(instruction: str) -> None:
    """Validate image edit instruction."""
    if not instruction or not instruction.strip():
        raise ValidationError("Edit instruction cannot be empty")

    if len(instruction) > 2048:
        raise ValidationError("Edit instruction too long (max 2048 characters)")

    # Check for harmful edit instructions
    harmful_patterns = [
        r"\b(?:remove|delete)\s+(?:clothes|clothing)\b",
        r"\b(?:add|create)\s+(?:nude|naked|nsfw)\b",
    ]

    for pattern in harmful_patterns:
        if re.search(pattern, instruction, re.IGNORECASE):
            raise ValidationError("Edit instruction contains inappropriate content")
