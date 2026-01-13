import json
import hashlib
import sys
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def load_release_config(config_path):
    """
    Loads and validates the release config.
    Returns the config dict.
    """
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
        
    with open(path, "r") as f:
        content = f.read()
    
    # Compute SHA256 of raw config
    config_sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
    logger.info(f"Loaded Release Config: {path}")
    logger.info(f"Config SHA256: {config_sha}")
    
    config = json.loads(content)
    
    # Basic Validation
    req_keys = ["paths", "model", "sanitization", "inference", "reproducibility"]
    for k in req_keys:
        if k not in config:
            raise ValueError(f"Missing required config section: {k}")
            
    # Validate Paths Exist (Optional but good)
    for k, v in config["paths"].items():
        if not Path(v).exists():
            # Warn but don't fail immediately, runner might fail later
            logger.warning(f"Configured path does not exist: {k}={v}")
            
    return config

def print_config_summary(config):
    print("=== Release Config Summary ===")
    print(f"Version: {config.get('meta_version', 'unknown')}")
    print(f"Checkpoint: {config['paths']['checkpoint']}")
    print(f"Seeds: {config['reproducibility']}")
    print("==============================")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) > 1:
        c = load_release_config(sys.argv[1])
        print_config_summary(c)
