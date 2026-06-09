from __future__ import annotations

from functools import cached_property

from google.adk.models import Gemini
from google.genai import Client, types

from .runtime_config import get_api_key
from .runtime_config import get_vertex_location
from .runtime_config import get_vertex_project
from .runtime_config import use_vertex_ai


class ManagedGemini(Gemini):
    @cached_property
    def api_client(self) -> Client:
        base_url, api_version = self._base_url_and_api_version
        kwargs_for_http_options: dict[str, object] = {
            "headers": self._tracking_headers(),
            "retry_options": self.retry_options,
            "base_url": base_url,
        }
        if api_version:
            kwargs_for_http_options["api_version"] = api_version

        kwargs: dict[str, object] = {
            "http_options": types.HttpOptions(**kwargs_for_http_options),
        }

        if use_vertex_ai():
            kwargs["vertexai"] = True
            api_key = get_api_key()
            if api_key:
                kwargs["api_key"] = api_key
            project = get_vertex_project()
            if project:
                kwargs["project"] = project
            kwargs["location"] = get_vertex_location()
        else:
            api_key = get_api_key()
            if not api_key:
                raise RuntimeError(
                    "Set GEMINI_API_KEY in the root .env for Gemini API auth, "
                    "or set GOOGLE_GENAI_USE_VERTEXAI=true with Vertex AI "
                    "credentials."
                )
            kwargs["api_key"] = api_key

        return Client(**kwargs)
