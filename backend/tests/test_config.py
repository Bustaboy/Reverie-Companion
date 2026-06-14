"""Configuration defaults that keep a clean checkout runnable."""

from app.core.config import Settings


def test_default_cors_origins_include_frontend_dev_ports() -> None:
    settings = Settings(_env_file=None)

    assert "http://localhost:1420" in settings.cors_origins
    assert "http://localhost:5173" in settings.cors_origins


def test_local_ai_hotswap_defaults_enabled_for_8gb_setup() -> None:
    settings = Settings(_env_file=None)

    assert settings.local_ai_hotswap_enabled is True
    assert settings.local_ai_unload_ollama_before_images is True
    assert settings.local_ai_unload_comfyui_before_chat is True
    assert settings.local_ai_hotswap_timeout_seconds == 3.0


def test_tts_defaults_match_orpheus_primary_with_piper_fallback() -> None:
    settings = Settings(_env_file=None)

    assert settings.tts_primary_backend == "orpheus"
    assert settings.tts_orpheus_runtime == "cpp"
    assert settings.tts_orpheus_cpp_model_id == "isaiahbjork/orpheus-3b-0.1-ft-Q4_K_M-GGUF"
    assert settings.tts_orpheus_default_voice_id == "tara"
    assert settings.tts_device == "cpu"
    assert settings.tts_orpheus_cpp_n_gpu_layers == 0
    assert settings.tts_orpheus_cpp_n_ctx == 4096
    assert settings.tts_piper_voice_dir == "./models/piper"
    assert settings.tts_piper_timeout_seconds == 20.0
    assert settings.tts_orpheus_model_id == "canopylabs/orpheus-3b-0.1-ft"
