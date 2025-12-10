import base64
import logging
from typing import Any

from google import genai
from google.genai import types as gx

from ..config.settings import (
    BaseModelConfig,
    FlashImageConfig,
    GeminiConfig,
    ProImageConfig,
    ServerConfig,
)


class GeminiClient:
    """Wrapper for Google Gemini API client with multi-model support."""

    def __init__(
        self,
        config: ServerConfig,
        gemini_config: GeminiConfig | BaseModelConfig | FlashImageConfig | ProImageConfig
    ):
        self.config = config
        self.gemini_config = gemini_config
        self.logger = logging.getLogger(__name__)
        self._client = None

    @property
    def client(self) -> genai.Client:
        """Lazy initialization of Gemini client."""
        if self._client is None:
            self._client = genai.Client(api_key=self.config.gemini_api_key)
        return self._client

    def create_image_parts(self, images_b64: list[str], mime_types: list[str]) -> list[gx.Part]:
        """Convert base64 images to Gemini Part objects."""
        if not images_b64 or not mime_types:
            return []

        if len(images_b64) != len(mime_types):
            raise ValueError(f"Images and MIME types count mismatch: {len(images_b64)} vs {len(mime_types)}")

        parts = []
        for i, (b64, mime_type) in enumerate(zip(images_b64, mime_types, strict=False)):
            if not b64 or not mime_type:
                self.logger.warning(f"Skipping empty image or MIME type at index {i}")
                continue

            try:
                raw_data = base64.b64decode(b64)
                if len(raw_data) == 0:
                    self.logger.warning(f"Skipping empty image data at index {i}")
                    continue

                part = gx.Part.from_bytes(data=raw_data, mime_type=mime_type)
                parts.append(part)
            except Exception as e:
                self.logger.error(f"Failed to process image at index {i}: {e}")
                raise ValueError(f"Invalid image data at index {i}: {e}") from e
        return parts

    def generate_content(
        self,
        contents: list,
        config: dict[str, Any] | None = None,
        aspect_ratio: str | None = None,
        output_resolution: str | None = None,
        **kwargs
    ) -> any:
        """
        Generate content using Gemini API with model-aware parameter handling.

        Args:
            contents: Content list (text, images, etc.)
            config: Generation configuration dict (model-specific parameters)
            aspect_ratio: Optional aspect ratio string (e.g., "16:9")
            output_resolution: Optional output resolution ("1K", "2K", "4K", "high")
                               Only supported by Pro model. Values normalized to uppercase.
            **kwargs: Additional parameters

        Returns:
            API response object
        """
        try:
            # Remove unsupported request_options parameter
            kwargs.pop("request_options", None)

            # Check for config conflict
            config_obj = kwargs.pop("config", None)
            if config_obj is not None:
                if aspect_ratio or config or output_resolution:
                    self.logger.warning(
                        "Custom 'config' kwarg provided; ignoring aspect_ratio, output_resolution and config parameters"
                    )
                kwargs["config"] = config_obj
            else:
                # Filter parameters based on model capabilities
                filtered_config = self._filter_parameters(config or {})

                # Build generation config - Pro model supports TEXT + IMAGE responses
                if isinstance(self.gemini_config, ProImageConfig):
                    config_kwargs = {
                        "response_modalities": ["TEXT", "IMAGE"],  # Pro can return both
                    }
                else:
                    config_kwargs = {
                        "response_modalities": ["IMAGE"],  # Flash: image-only responses
                    }

                # Build ImageConfig with aspect_ratio and/or image_size
                image_config_kwargs = {}
                if aspect_ratio:
                    image_config_kwargs["aspect_ratio"] = aspect_ratio

                # Handle image_size for Pro model (1K, 2K, 4K)
                if output_resolution and isinstance(self.gemini_config, ProImageConfig):
                    # Normalize resolution to uppercase (API requires "4K" not "4k")
                    normalized_resolution = self._normalize_resolution(output_resolution)
                    if normalized_resolution:
                        image_config_kwargs["image_size"] = normalized_resolution
                        self.logger.info(
                            f"Setting image_size={normalized_resolution} for Pro model"
                        )
                elif output_resolution and not isinstance(self.gemini_config, ProImageConfig):
                    self.logger.warning(
                        f"output_resolution='{output_resolution}' ignored for Flash model "
                        "(only Pro model supports resolutions above 1024px)"
                    )

                # Create ImageConfig if we have any parameters
                if image_config_kwargs:
                    config_kwargs["image_config"] = gx.ImageConfig(**image_config_kwargs)

                # Merge filtered config parameters
                config_kwargs.update(filtered_config)

                kwargs["config"] = gx.GenerateContentConfig(**config_kwargs)

            # Prepare kwargs
            api_kwargs = {
                "model": self.gemini_config.model_name,
                "contents": contents,
            }

            # Merge additional kwargs
            api_kwargs.update(kwargs)

            # Log detailed config for debugging
            config_obj = api_kwargs.get('config')
            if config_obj:
                self.logger.info(
                    f"Calling Gemini API: model={self.gemini_config.model_name}, "
                    f"response_modalities={getattr(config_obj, 'response_modalities', None)}, "
                    f"image_config={getattr(config_obj, 'image_config', None)}"
                )
            else:
                self.logger.info(f"Calling Gemini API: model={self.gemini_config.model_name}, config=None")

            response = self.client.models.generate_content(**api_kwargs)
            self.logger.info(f"Gemini API response received for {self.gemini_config.model_name}")
            return response

        except Exception as e:
            import traceback
            self.logger.error(f"Gemini API error for {self.gemini_config.model_name}: {e}")
            self.logger.error(f"Full traceback: {traceback.format_exc()}")
            raise

    def _filter_parameters(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Filter configuration parameters based on model capabilities.

        Ensures we only send parameters that the current model supports,
        preventing API errors from unsupported parameters.

        Args:
            config: Raw configuration dictionary

        Returns:
            Filtered configuration with only supported parameters
        """
        if not config:
            return {}

        filtered = {}

        # Common parameters (supported by all models)
        for param in ["temperature", "top_p", "top_k", "max_output_tokens"]:
            if param in config:
                filtered[param] = config[param]

        # Pro-specific parameters
        if isinstance(self.gemini_config, ProImageConfig):
            # Thinking level (Pro only)
            if "thinking_level" in config:
                filtered["thinking_level"] = config["thinking_level"]

            # Media resolution (Pro only)
            if "media_resolution" in config:
                filtered["media_resolution"] = config["media_resolution"]

            # Note: output_resolution is now handled via ImageConfig in generate_content()
            # Note: enable_grounding may be controlled via system instructions
            # rather than as a direct API parameter in some SDK versions

        else:
            # Flash model - warn if Pro parameters are used
            pro_params = ["thinking_level", "media_resolution"]
            used_pro_params = [p for p in pro_params if p in config]
            if used_pro_params:
                self.logger.warning(
                    f"Pro-only parameters ignored for Flash model: {used_pro_params}"
                )

        return filtered

    def _normalize_resolution(self, resolution: str) -> str | None:
        """
        Normalize resolution string to API-compatible format.

        The Gemini API requires uppercase resolution values ("4K", not "4k").
        Also maps "high" to appropriate value.

        Args:
            resolution: Raw resolution string (e.g., "4k", "high", "2K")

        Returns:
            Normalized resolution string or None if invalid
        """
        if not resolution:
            return None

        resolution_lower = resolution.lower().strip()

        # Map common values to API format
        resolution_map = {
            "4k": "4K",
            "2k": "2K",
            "1k": "1K",
            "high": "4K",  # "high" maps to max quality (4K) for Pro model
        }

        normalized = resolution_map.get(resolution_lower)

        if normalized:
            return normalized
        else:
            self.logger.warning(
                f"Unknown resolution '{resolution}', defaulting to None. "
                f"Valid values: 1K, 2K, 4K, high"
            )
            return None

    def extract_images(self, response) -> list[bytes]:
        """Extract image bytes from Gemini response.

        Handles both Flash model (inline_data) and Pro model (as_image()) formats.
        """
        images = []

        # Try using response.parts directly first (newer API style)
        parts = getattr(response, "parts", None)
        if parts:
            for part in parts:
                # Try as_image() method (Pro model style from docs)
                if hasattr(part, "as_image"):
                    try:
                        img = part.as_image()
                        if img:
                            # as_image() returns a PIL-like object, get bytes
                            import io
                            buf = io.BytesIO()
                            img.save(buf, format="PNG")
                            images.append(buf.getvalue())
                            continue
                    except Exception:
                        pass  # Fall through to other methods

                # Try inline_data (Flash model style)
                inline_data = getattr(part, "inline_data", None)
                if inline_data and hasattr(inline_data, "data") and inline_data.data:
                    images.append(inline_data.data)

            if images:
                return images

        # Fall back to candidates structure
        candidates = getattr(response, "candidates", None)
        if not candidates or len(candidates) == 0:
            return images

        first_candidate = candidates[0]
        if not hasattr(first_candidate, "content") or not first_candidate.content:
            return images

        content_parts = getattr(first_candidate.content, "parts", [])
        for part in content_parts:
            # Try as_image() method first
            if hasattr(part, "as_image"):
                try:
                    img = part.as_image()
                    if img:
                        import io
                        buf = io.BytesIO()
                        img.save(buf, format="PNG")
                        images.append(buf.getvalue())
                        continue
                except Exception:
                    pass

            # Try inline_data
            inline_data = getattr(part, "inline_data", None)
            if inline_data and hasattr(inline_data, "data") and inline_data.data:
                images.append(inline_data.data)

        return images

    def upload_file(self, file_path: str, _display_name: str | None = None):
        """Upload file to Gemini Files API.

        Note: display_name is kept for API compatibility but ignored as the
        Gemini Files API does not support display_name parameter in upload.
        """
        try:
            # Gemini Files API only accepts file parameter
            return self.client.files.upload(file=file_path)
        except Exception as e:
            self.logger.error(f"File upload error: {e}")
            raise

    def get_file_metadata(self, file_name: str):
        """Get file metadata from Gemini Files API."""
        try:
            return self.client.files.get(name=file_name)
        except Exception as e:
            self.logger.error(f"File metadata error: {e}")
            raise
