# Imports the NetPilot configuration module so the tests can inspect application settings.
from app import config


# Defines a CI smoke test that verifies the Ollama host is configured.
def test_netpilot_configuration_loads():

    # Confirms that NetPilot has a configured Ollama endpoint.
    assert config.OLLAMA_HOST

    # Confirms that NetPilot has a configured Ollama model.
    assert config.OLLAMA_MODEL

    # Confirms that the Ollama timeout is a positive number.
    assert config.OLLAMA_TIMEOUT > 0


# Defines a CI smoke test that verifies the Ollama endpoint uses HTTP or HTTPS.
def test_ollama_endpoint_uses_valid_protocol():

    # Confirms that the configured Ollama endpoint starts with an accepted HTTP protocol.
    assert config.OLLAMA_HOST.startswith(("http://", "https://"))
