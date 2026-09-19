# Imports the NetPilot configuration module so we can verify it loads correctly.
from app import config


# Defines a simple CI smoke test that does not require network access.
def test_netpilot_configuration_loads():

    # Confirms that NetPilot has a configured Ollama endpoint.
    assert config.OLLAMA_HOST

    # Confirms that NetPilot has a configured Ollama model.
    assert config.OLLAMA_MODEL

    # Confirms that the Ollama timeout is a positive number.
    assert config.OLLAMA_TIMEOUT > 0

