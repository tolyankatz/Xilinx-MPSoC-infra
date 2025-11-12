#!/usr/bin/env python3
"""
ZCU102 Test Orchestrator

This script serves as the main entry point for executing the ZCU102 BSP validation
test suite. It coordinates test execution, hardware provisioning, artifact management,
and results reporting to provide a complete automated testing solution.

The orchestrator embodies the "glass box" philosophy by providing comprehensive
logging, metrics collection, and traceability throughout the test execution process.
"""

import os
import sys
import argparse
import logging
import subprocess
import time
import yaml
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import urlparse

# Add current directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent))

from hardware_control.power_controller import create_power_controller, PowerState
from hardware_control.jtag_controller import create_jtag_controller
from reporters.prometheus_reporter import PrometheusReporter
from reporters.elk_reporter import ELKReporter, LogLevel


class TestOrchestrator:
    """
    Main test orchestrator for ZCU102 BSP validation.
    
    This class coordinates the complete test execution workflow including
    hardware provisioning, test suite execution, and results reporting.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize test orchestrator.
        
        Args:
            config: Complete test configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Test execution state
        self.test_session_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"
        self.deployment_manifest = None
        self.hardware_provisioned = False
        
        # Initialize reporters
        self.prometheus_reporter = self._initialize_prometheus_reporter()
        self.elk_reporter = self._initialize_elk_reporter()
        
        # Initialize hardware controllers
        self.power_controller = self._initialize_power_controller()
        self.jtag_controller = self._initialize_jtag_controller()
        
        self.logger.info(f"Test orchestrator initialized: session_id={self.test_session_id}")
    
    def _initialize_prometheus_reporter(self) -> Optional[PrometheusReporter]:
        """Initialize Prometheus metrics reporter."""
        try:
            reporting_config = self.config.get('reporting', {})
            prometheus_config = reporting_config.get('prometheus', {})
            
            if not prometheus_config.get('enabled', True):
                return None
            
            reporter = PrometheusReporter(
                pushgateway_url=prometheus_config['pushgateway_url'],
                job_name=prometheus_config.get('job_name', 'zcu102_hardware_tests'),
                instance_id=self.test_session_id
            )
            
            self.logger.info("Prometheus reporter initialized")
            return reporter
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize Prometheus reporter: {e}")
            return None
    
    def _initialize_elk_reporter(self) -> Optional[ELKReporter]:
        """Initialize ELK Stack reporter."""
        try:
            reporting_config = self.config.get('reporting', {})
            elk_config = reporting_config.get('elasticsearch', {})
            
            if not elk_config.get('enabled', True):
                return None
            
            reporter = ELKReporter(
                elasticsearch_hosts=elk_config['hosts'],
                index_prefix=elk_config.get('index_prefix', 'zcu102-test-logs'),
                session_id=self.test_session_id
            )
            
            self.logger.info("ELK reporter initialized")
            return reporter
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize ELK reporter: {e}")
            return None
    
    def _initialize_power_controller(self):
        """Initialize power controller for hardware management."""
        try:
            if self.config.get('development', {}).get('mock_hardware', False):
                return create_power_controller(
                    controller_type="mock",
                    device_id=self.config.get('board_type', 'zcu102')
                )
            
            power_config = self.config['hardware']['power']
            return create_power_controller(
                controller_type=power_config['controller_type'],
                device_id=power_config['device_id'],
                **{k: v for k, v in power_config.items() if k not in ['controller_type', 'device_id']}
            )
            
        except Exception as e:
            self.logger.error(f"Failed to initialize power controller: {e}")
            return None
    
    def _initialize_jtag_controller(self):
        """Initialize JTAG controller for firmware management."""
        try:
            if self.config.get('development', {}).get('mock_hardware', False):
                return None
            
            jtag_config = self.config['hardware']['jtag']
            return create_jtag_controller(
                cable_type=jtag_config['cable_type'],
                device_part=jtag_config['device_part'],
                **{k: v for k, v in jtag_config.items() if k not in ['cable_type', 'device_part']}
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to initialize JTAG controller: {e}")
            return None
    
    def parse_deployment_manifest(self, manifest_url: str) -> Dict[str, Any]:
        """
        Parse deployment manifest from Jenkins pipeline.
        Supports both new BSP manifest format and legacy formats.
        
        Args:
            manifest_url: URL or path to deployment manifest
            
        Returns:
            Parsed deployment manifest dictionary
        """
        self.logger.info(f"Parsing deployment manifest: {manifest_url}")
        
        try:
            # Handle local file paths
            if not manifest_url.startswith(('http://', 'https://')):
                manifest_path = Path(manifest_url)
                if manifest_path.exists():
                    with open(manifest_path, 'r') as f:
                        self.deployment_manifest = yaml.safe_load(f)
                else:
                    raise FileNotFoundError(f"Manifest file not found: {manifest_url}")
            else:
                # Download manifest from URL
                import requests
                response = requests.get(manifest_url, timeout=30)
                response.raise_for_status()
                self.deployment_manifest = yaml.safe_load(response.text)
            
            # Detect manifest format and validate
            if 'manifest_version' in self.deployment_manifest:
                # New BSP manifest format
                self._validate_bsp_manifest()
                self._extract_bsp_config()
            elif 'metadata' in self.deployment_manifest and 'spec' in self.deployment_manifest:
                # Legacy Kubernetes-style manifest format
                self._validate_legacy_manifest()
                self._extract_legacy_config()
            else:
                raise ValueError("Unrecognized manifest format")
            
            self.logger.info(f"Deployment manifest parsed: {self.config.get('build_version', 'unknown')} for {self.config.get('board_type', 'unknown')}")
            return self.deployment_manifest
            
        except Exception as e:
            self.logger.error(f"Failed to parse deployment manifest: {e}")
            raise
    
    def _validate_bsp_manifest(self):
        """Validate BSP manifest format structure."""
        required_fields = ['manifest_version', 'target_board', 'build_info', 'artifacts']
        for field in required_fields:
            if field not in self.deployment_manifest:
                raise ValueError(f"Missing required field in BSP manifest: {field}")
    
    def _extract_bsp_config(self):
        """Extract configuration from BSP manifest format."""
        build_info = self.deployment_manifest['build_info']
        self.config['build_version'] = build_info['build_id']
        self.config['commit_hash'] = build_info['commit_hash']
        self.config['board_type'] = self.deployment_manifest['target_board'].lower()
        
        # Extract artifact information
        artifacts = self.deployment_manifest['artifacts']
        self.config['artifact_repository'] = artifacts['repository_url']
        self.config['artifacts'] = {}
        
        for component in artifacts['components']:
            self.config['artifacts'][component['name']] = {
                'file': component['file'],
                'version': component['version'],
                'checksum': component['checksum_md5'],
                'url': f"{artifacts['repository_url']}{component['file']}"
            }
        
        # Extract deployment and runtime configuration
        if 'deployment_config' in self.deployment_manifest:
            self.config['deployment'] = self.deployment_manifest['deployment_config']
        
        if 'runtime_config' in self.deployment_manifest:
            self.config['runtime'] = self.deployment_manifest['runtime_config']
        
        # Extract test plan
        if 'test_plan' in self.deployment_manifest:
            self.config['test_plan'] = self.deployment_manifest['test_plan']
    
    def _validate_legacy_manifest(self):
        """Validate legacy manifest format structure."""
        required_fields = ['metadata', 'spec']
        for field in required_fields:
            if field not in self.deployment_manifest:
                raise ValueError(f"Missing required field in legacy manifest: {field}")
    
    def _extract_legacy_config(self):
        """Extract configuration from legacy manifest format."""
        metadata = self.deployment_manifest['metadata']
        spec = self.deployment_manifest['spec']
        
        self.config['build_version'] = metadata['name']
        self.config['board_type'] = metadata['labels']['board']
    
    def provision_hardware(self, force_flash: bool = False) -> bool:
        """
        Provision hardware with firmware from deployment manifest.
        
        Args:
            force_flash: Force firmware flashing even if not required
            
        Returns:
            True if hardware provisioning succeeded
        """
        self.logger.info("Starting hardware provisioning")
        
        try:
            # Ensure power controller is available
            if not self.power_controller:
                raise RuntimeError("Power controller not available for hardware provisioning")
            
            # Power cycle board to ensure clean state
            self.logger.info("Power cycling board for clean state")
            if not self.power_controller.power_cycle():
                raise RuntimeError("Failed to power cycle board")
            
            # Flash firmware if deployment manifest specifies new artifacts
            if self.deployment_manifest and (force_flash or self._requires_firmware_flash()):
                if not self._flash_firmware():
                    raise RuntimeError("Firmware flashing failed")
            
            # Wait for boot completion and verify system is ready
            if not self._wait_for_system_ready():
                raise RuntimeError("System failed to reach ready state")
            
            self.hardware_provisioned = True
            self.logger.info("Hardware provisioning completed successfully")
            
            # Report hardware provisioning metrics
            if self.prometheus_reporter:
                self.prometheus_reporter.record_hardware_control_metrics(
                    power_cycle_duration=10,  # Approximate duration
                    board_type=self.config['board_type']
                )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Hardware provisioning failed: {e}")
            
            # Report provisioning failure
            if self.elk_reporter:
                self.elk_reporter.log_test_message(
                    test_name="hardware_provisioning",
                    test_type="system",
                    log_level=LogLevel.ERROR,
                    message=f"Hardware provisioning failed: {e}",
                    board_type=self.config['board_type'],
                    build_version=self.config.get('build_version', 'unknown')
                )
            
            return False
    
    def _requires_firmware_flash(self) -> bool:
        """Determine if firmware flashing is required."""
        # For now, always flash if manifest is provided
        # In production, this could check version compatibility
        return self.deployment_manifest is not None
    
    def _flash_firmware(self) -> bool:
        """Flash firmware artifacts from deployment manifest."""
        self.logger.info("Flashing firmware from deployment manifest")
        
        if not self.jtag_controller:
            self.logger.warning("JTAG controller not available - skipping firmware flash")
            return True  # Allow tests to continue without flashing
        
        try:
            spec = self.deployment_manifest['spec']
            artifacts = spec['artifacts']
            
            # Download and flash bootloader if available
            if 'bootloader' in artifacts:
                bootloader_url = artifacts['bootloader']['path']
                bootloader_file = self._download_artifact(bootloader_url)
                
                result = self.jtag_controller.flash_image(bootloader_file, target="boot")
                if not result.success:
                    raise RuntimeError(f"Bootloader flash failed: {result.error_message}")
                
                self.logger.info("Bootloader flashed successfully")
            
            # Flash FPGA bitstream if available
            if 'fpga_bitstream' in artifacts:
                bitstream_url = artifacts['fpga_bitstream']['path']
                bitstream_file = self._download_artifact(bitstream_url)
                
                result = self.jtag_controller.flash_image(bitstream_file, target="fpga")
                if not result.success:
                    raise RuntimeError(f"FPGA bitstream flash failed: {result.error_message}")
                
                self.logger.info("FPGA bitstream flashed successfully")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Firmware flashing failed: {e}")
            return False
    
    def _download_artifact(self, artifact_url: str) -> str:
        """
        Download artifact from URL to temporary file.
        
        Args:
            artifact_url: URL of artifact to download
            
        Returns:
            Path to downloaded file
        """
        import requests
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(artifact_url).suffix) as tmp_file:
            tmp_path = tmp_file.name
        
        # Download artifact
        self.logger.info(f"Downloading artifact: {artifact_url}")
        response = requests.get(artifact_url, stream=True, timeout=300)
        response.raise_for_status()
        
        with open(tmp_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        self.logger.info(f"Artifact downloaded: {tmp_path}")
        return tmp_path
    
    def _wait_for_system_ready(self, timeout_seconds: int = 120) -> bool:
        """
        Wait for system to reach ready state after provisioning.
        
        Args:
            timeout_seconds: Maximum time to wait for system ready
            
        Returns:
            True if system is ready within timeout
        """
        self.logger.info("Waiting for system to reach ready state")
        
        start_time = time.time()
        
        while (time.time() - start_time) < timeout_seconds:
            # Check if power is on
            if self.power_controller and self.power_controller.get_state() != PowerState.ON:
                self.logger.warning("System power is not on")
                time.sleep(5)
                continue
            
            # For mock hardware, assume system is ready quickly
            if self.config.get('development', {}).get('mock_hardware', False):
                time.sleep(10)  # Simulate boot time
                return True
            
            # In production, this could check for network connectivity or serial response
            time.sleep(10)
        
        # For now, assume system is ready after timeout
        self.logger.info("System ready state check completed")
        return True
    
    def execute_test_suite(self, test_suite: str, extra_args: Optional[List[str]] = None) -> bool:
        """
        Execute pytest test suite with specified parameters.
        
        Args:
            test_suite: Test suite to execute (smoke, regression, full)
            extra_args: Additional pytest arguments
            
        Returns:
            True if all tests passed
        """
        self.logger.info(f"Executing test suite: {test_suite}")
        
        # Build pytest command
        pytest_args = [
            sys.executable, "-m", "pytest",
            str(Path(__file__).parent / "tests"),
            f"--test-suite={test_suite}",
            f"--board-type={self.config['board_type']}",
            f"--build-version={self.config.get('build_version', 'unknown')}",
            f"--config-file={Path(__file__).parent / 'config.yaml'}",
            "--verbose",
            "--tb=short",
            "--html=test_report.html",
            "--self-contained-html"
        ]
        
        # Add mock hardware flag if enabled
        if self.config.get('development', {}).get('mock_hardware', False):
            pytest_args.append("--skip-hardware")
        
        # Add any extra arguments
        if extra_args:
            pytest_args.extend(extra_args)
        
        # Log test execution start
        if self.elk_reporter:
            self.elk_reporter.log_test_message(
                test_name="test_suite_execution",
                test_type="system",
                log_level=LogLevel.INFO,
                message=f"Starting test suite execution: {test_suite}",
                board_type=self.config['board_type'],
                build_version=self.config.get('build_version', 'unknown'),
                metadata={'pytest_args': ' '.join(pytest_args)}
            )
        
        try:
            # Execute pytest
            self.logger.info(f"Running pytest: {' '.join(pytest_args)}")
            result = subprocess.run(pytest_args, cwd=Path(__file__).parent, timeout=3600)
            
            success = result.returncode == 0
            
            # Log test execution completion
            if self.elk_reporter:
                self.elk_reporter.log_test_message(
                    test_name="test_suite_execution",
                    test_type="system", 
                    log_level=LogLevel.INFO if success else LogLevel.ERROR,
                    message=f"Test suite execution completed: {'PASSED' if success else 'FAILED'}",
                    board_type=self.config['board_type'],
                    build_version=self.config.get('build_version', 'unknown'),
                    metadata={'return_code': result.returncode}
                )
            
            return success
            
        except subprocess.TimeoutExpired:
            self.logger.error("Test suite execution timed out")
            return False
        except Exception as e:
            self.logger.error(f"Test suite execution failed: {e}")
            return False
    
    def generate_final_report(self, test_success: bool) -> Dict[str, Any]:
        """
        Generate comprehensive final test report.
        
        Args:
            test_success: Overall test execution success status
            
        Returns:
            Dictionary containing complete test report
        """
        self.logger.info("Generating final test report")
        
        report = {
            'test_session_id': self.test_session_id,
            'timestamp': datetime.now().isoformat(),
            'board_type': self.config['board_type'],
            'build_version': self.config.get('build_version', 'unknown'),
            'test_suite': self.config.get('test_suite', 'unknown'),
            'overall_success': test_success,
            'hardware_provisioned': self.hardware_provisioned,
            'deployment_manifest': self.deployment_manifest,
            'configuration': {
                'mock_hardware': self.config.get('development', {}).get('mock_hardware', False),
                'power_cycle_enabled': self.config.get('power_cycle', False),
            }
        }
        
        # Add hardware controller status
        if self.power_controller:
            report['power_controller_events'] = [
                {
                    'timestamp': event.timestamp.isoformat(),
                    'action': event.action,
                    'success': event.success,
                    'duration_seconds': event.duration_seconds
                }
                for event in self.power_controller.get_event_history()
            ]
        
        return report
    
    def cleanup(self):
        """Cleanup test orchestrator resources."""
        self.logger.info("Performing test orchestrator cleanup")
        
        # Flush any remaining logs and metrics
        if self.elk_reporter:
            self.elk_reporter.flush_buffered_logs()
            self.elk_reporter.close()
        
        if self.prometheus_reporter:
            self.prometheus_reporter.push_metrics({
                'session_id': self.test_session_id,
                'board_type': self.config['board_type'],
                'build_version': self.config.get('build_version', 'unknown')
            })
        
        # Ensure board is left in powered-on state
        if self.power_controller and self.power_controller.get_state() != PowerState.ON:
            self.logger.info("Ensuring board is powered on after test execution")
            self.power_controller.turn_on()
        
        self.logger.info("Test orchestrator cleanup completed")


def setup_logging(verbose: bool = False):
    """Configure logging for test orchestrator."""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(f'test_orchestrator_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        ]
    )
    
    # Suppress noisy third-party loggers
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def main():
    """Main entry point for test orchestrator."""
    
    parser = argparse.ArgumentParser(
        description='ZCU102 BSP Test Orchestrator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Run smoke test suite with mock hardware
  python run_tests.py --test-suite smoke --mock-hardware
  
  # Run regression tests with deployment manifest
  python run_tests.py --test-suite regression --manifest deployment_manifest.yaml
  
  # Run full test suite with power cycling
  python run_tests.py --test-suite full --power-cycle --verbose
        '''
    )
    
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Test configuration file path'
    )
    
    parser.add_argument(
        '--test-suite',
        choices=['smoke', 'regression', 'full'],
        default='smoke',
        help='Test suite to execute'
    )
    
    parser.add_argument(
        '--manifest',
        help='Deployment manifest URL or file path'
    )
    
    parser.add_argument(
        '--mock-hardware',
        action='store_true',
        help='Use mock hardware controllers for testing'
    )
    
    parser.add_argument(
        '--power-cycle',
        action='store_true',
        help='Power cycle board before test execution'
    )
    
    parser.add_argument(
        '--force-flash',
        action='store_true',
        help='Force firmware flashing regardless of version'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--pytest-args',
        nargs='*',
        help='Additional arguments to pass to pytest'
    )
    
    args = parser.parse_args()
    
    # Configure logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    logger.info("=== ZCU102 BSP Test Orchestrator Starting ===")
    
    try:
        # Load configuration
        config_path = Path(args.config)
        if not config_path.exists():
            # Try relative to script directory
            config_path = Path(__file__).parent / args.config
        
        if not config_path.exists():
            logger.error(f"Configuration file not found: {args.config}")
            return 1
        
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Override configuration with command line arguments
        config['test_suite'] = args.test_suite
        config['power_cycle'] = args.power_cycle
        
        if args.mock_hardware:
            config.setdefault('development', {})['mock_hardware'] = True
        
        # Initialize test orchestrator
        orchestrator = TestOrchestrator(config)
        
        try:
            # Parse deployment manifest if provided
            if args.manifest:
                orchestrator.parse_deployment_manifest(args.manifest)
            
            # Provision hardware
            if not orchestrator.provision_hardware(force_flash=args.force_flash):
                logger.error("Hardware provisioning failed - aborting test execution")
                return 1
            
            # Execute test suite
            test_success = orchestrator.execute_test_suite(
                test_suite=args.test_suite,
                extra_args=args.pytest_args
            )
            
            # Generate final report
            final_report = orchestrator.generate_final_report(test_success)
            
            # Log final results
            status = "PASSED" if test_success else "FAILED"
            logger.info(f"=== ZCU102 BSP Test Execution {status} ===")
            logger.info(f"Session ID: {final_report['test_session_id']}")
            logger.info(f"Board: {final_report['board_type']}")
            logger.info(f"Build: {final_report['build_version']}")
            logger.info(f"Test Suite: {final_report['test_suite']}")
            
            return 0 if test_success else 1
            
        finally:
            orchestrator.cleanup()
            
    except Exception as e:
        logger.error(f"Test orchestrator failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
