import os
import yaml

# Path to the config file (assuming this script is run from the project root)
CONFIG_PATH = "config.yaml"

def load_config(path: str = CONFIG_PATH) -> dict:
    """Reads the YAML configuration file and returns it as a dictionary."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ Configuration file not found at {path}")
    
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# Load the config globally so it can be imported anywhere in the app
# Example: from src.core.config import config; print(config['thresholds']['vector_quality_threshold'])
config = load_config()