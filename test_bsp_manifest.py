#!/usr/bin/env python3
"""
BSP Manifest Integration Test Script

This script demonstrates how to use the BSP manifest file (bsp-main-137.yaml)
with the ZCU102 test framework. It shows the integration between the manifest
format and the test execution system.
"""

import os
import sys
import logging
from pathlib import Path

# Add test_host to Python path
test_host_path = Path(__file__).parent / "test_host"
sys.path.insert(0, str(test_host_path))

from test_host.run_tests import TestOrchestrator
import yaml

def setup_logging():
    """Set up logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('bsp_manifest_test.log')
        ]
    )

def load_base_config():
    """Load base test configuration."""
    config_path = Path(__file__).parent / "test_host" / "config.yaml"
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Enable mock hardware for this demonstration
    config.setdefault('development', {})['mock_hardware'] = True
    
    return config

def demonstrate_bsp_manifest_parsing():
    """Demonstrate BSP manifest parsing and integration."""
    logger = logging.getLogger(__name__)
    
    # Path to the BSP manifest file
    manifest_path = Path(__file__).parent / "artifacts" / "bsp-main-137.yaml"
    
    logger.info("=== BSP Manifest Integration Demonstration ===")
    logger.info(f"Using BSP manifest: {manifest_path}")
    
    if not manifest_path.exists():
        logger.error(f"BSP manifest file not found: {manifest_path}")
        return False
    
    try:
        # Load base configuration
        config = load_base_config()
        
        # Initialize test orchestrator
        orchestrator = TestOrchestrator(config)
        
        # Parse the BSP manifest
        logger.info("Parsing BSP manifest...")
        manifest = orchestrator.parse_deployment_manifest(str(manifest_path))
        
        # Display parsed information
        logger.info("=== BSP Manifest Information ===")
        logger.info(f"Manifest Version: {manifest.get('manifest_version')}")
        logger.info(f"Target Board: {manifest.get('target_board')}")
        logger.info(f"Build ID: {manifest.get('build_info', {}).get('build_id')}")
        logger.info(f"Commit Hash: {manifest.get('build_info', {}).get('commit_hash')}")
        
        # Display artifacts
        artifacts = manifest.get('artifacts', {}).get('components', [])
        logger.info(f"Artifacts ({len(artifacts)} components):")
        for component in artifacts:
            logger.info(f"  - {component['name']}: {component['file']} (v{component['version']})")
        
        # Display test plan
        test_plan = manifest.get('test_plan', [])
        logger.info(f"Test Plan ({len(test_plan)} test suites):")
        for test in test_plan:
            logger.info(f"  - {test}")
        
        # Display deployment configuration
        deployment_config = manifest.get('deployment_config', {})
        logger.info("Deployment Configuration:")
        logger.info(f"  Method: {deployment_config.get('method')}")
        logger.info(f"  SD Card Device: {deployment_config.get('sd_card_device')}")
        
        # Display runtime configuration
        runtime_config = manifest.get('runtime_config', {})
        logger.info("Runtime Configuration:")
        console_config = runtime_config.get('console', {})
        logger.info(f"  Console Baud Rate: {console_config.get('baud_rate')}")
        
        network_config = runtime_config.get('network', {})
        logger.info(f"  Network Interface: {network_config.get('interface')}")
        logger.info(f"  IP Configuration: {network_config.get('config_method')}")
        if network_config.get('config_method') == 'static':
            logger.info(f"  Static IP: {network_config.get('ip_address')}")
            logger.info(f"  Netmask: {network_config.get('netmask')}")
            logger.info(f"  Gateway: {network_config.get('gateway')}")
        
        logger.info("=== Configuration Integration Check ===")
        # Check how the manifest information was integrated into the orchestrator config
        orch_config = orchestrator.config
        logger.info(f"Orchestrator Build Version: {orch_config.get('build_version')}")
        logger.info(f"Orchestrator Board Type: {orch_config.get('board_type')}")
        logger.info(f"Orchestrator Commit Hash: {orch_config.get('commit_hash')}")
        
        if 'artifacts' in orch_config:
            logger.info("Orchestrator Artifacts:")
            for name, artifact in orch_config['artifacts'].items():
                logger.info(f"  - {name}: {artifact['file']} (checksum: {artifact['checksum'][:8]}...)")
        
        logger.info("=== BSP Manifest Integration Successful ===")
        return True
        
    except Exception as e:
        logger.error(f"BSP manifest integration failed: {e}")
        return False

def demonstrate_test_execution():
    """Demonstrate test execution with BSP manifest."""
    logger = logging.getLogger(__name__)
    
    logger.info("=== Test Execution with BSP Manifest ===")
    logger.info("Command line example:")
    logger.info("python test_host/run_tests.py \\")
    logger.info("  --config test_host/config.yaml \\")
    logger.info("  --manifest artifacts/bsp-main-137.yaml \\")
    logger.info("  --test-suite smoke \\")
    logger.info("  --mock-hardware \\")
    logger.info("  --verbose")
    
    logger.info("\nThis would:")
    logger.info("1. Parse the BSP manifest to extract build and artifact information")
    logger.info("2. Configure the test framework with manifest parameters")
    logger.info("3. Provision hardware using the deployment configuration")
    logger.info("4. Execute the test plan specified in the manifest")
    logger.info("5. Report results with full traceability to the build")

if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Demonstrate manifest parsing
        if not demonstrate_bsp_manifest_parsing():
            sys.exit(1)
        
        # Show test execution example
        demonstrate_test_execution()
        
        logger.info("BSP manifest integration demonstration completed successfully!")
        
    except Exception as e:
        logger.error(f"Demonstration failed: {e}")
        sys.exit(1)
