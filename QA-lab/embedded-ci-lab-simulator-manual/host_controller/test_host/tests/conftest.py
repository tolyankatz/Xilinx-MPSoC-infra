"""
pytest Configuration and Fixtures for ZCU102 Test Framework

This module provides comprehensive pytest fixtures and configuration for the ZCU102
hardware test suite. It manages hardware resources, test environment setup, and
reporting integration to ensure reliable and repeatable test execution.

The fixtures embody the "glass box" philosophy by providing complete visibility
into test setup, execution, and teardown processes.
"""

import os
import sys
import time
import yaml
import logging
import pytest
from typing import Dict, Any, Generator, Optional
from datetime import datetime
from pathlib import Path

# Add framework modules to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from framework.boot_validator import BootValidator
from framework.uart_test import UartTester
from framework.ethernet_test import EthernetTester
from hardware_control.power_controller import create_power_controller, PowerState
from hardware_control.jtag_controller import create_jtag_controller
from reporters.prometheus_reporter import PrometheusReporter
from reporters.elk_reporter import ELKReporter, LogLevel


# Configure logging for test execution
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_execution.log')
    ]
)

logger = logging.getLogger(__name__)


def pytest_addoption(parser):
    """Add custom command line options for pytest."""
    parser.addoption(
        "--board-type",
        action="store",
        default="zcu102", 
        help="Target board type for testing"
    )
    
    parser.addoption(
        "--build-version",
        action="store",
        default="unknown",
        help="BSP build version being tested"
    )
    
    parser.addoption(
        "--test-suite",
        action="store",
        default="smoke",
        choices=["smoke", "regression", "full"],
        help="Test suite to execute"
    )
    
    parser.addoption(
        "--skip-hardware",
        action="store_true",
        default=False,
        help="Skip hardware-dependent tests (mock mode)"
    )
    
    parser.addoption(
        "--power-cycle",
        action="store_true", 
        default=False,
        help="Power cycle board before test execution"
    )


def pytest_configure(config):
    """Configure pytest environment and markers."""
    # Register custom markers
    config.addinivalue_line(
        "markers", 
        "boot: Boot sequence validation tests"
    )
    config.addinivalue_line(
        "markers",
        "uart: UART communication tests"  
    )
    config.addinivalue_line(
        "markers",
        "ethernet: Ethernet network tests"
    )
    config.addinivalue_line(
        "markers", 
        "gpio: GPIO functionality tests"
    )
    config.addinivalue_line(
        "markers",
        "hardware: Tests requiring physical hardware"
    )
    config.addinivalue_line(
        "markers",
        "slow: Tests with extended execution time"
    )


def pytest_runtest_setup(item):
    """Setup actions before each test."""
    # Skip hardware tests if in mock mode
    if item.get_closest_marker("hardware") and item.config.getoption("--skip-hardware"):
        pytest.skip("Skipping hardware test in mock mode")


@pytest.fixture(scope="session")
def test_config(request) -> Dict[str, Any]:
    """
    Load and provide test configuration.
    
    Returns:
        Dictionary containing complete test configuration
    """
    # Load config from default location
    config_path = Path(__file__).parent.parent / "config.yaml"
    
    if not config_path.exists():
        pytest.fail(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Override with command line options
        config['board_type'] = request.config.getoption("--board-type")
        config['build_version'] = request.config.getoption("--build-version") 
        config['test_suite'] = request.config.getoption("--test-suite")
        config['skip_hardware'] = request.config.getoption("--skip-hardware")
        config['power_cycle'] = request.config.getoption("--power-cycle")
        
        logger.info(f"Test configuration loaded: {config_path}")
        return config
        
    except Exception as e:
        pytest.fail(f"Failed to load configuration: {e}")


@pytest.fixture(scope="session")
def test_session_id() -> str:
    """
    Generate unique test session identifier.
    
    Returns:
        Unique session ID for test execution tracking
    """
    session_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.getpid()}"
    logger.info(f"Test session ID: {session_id}")
    return session_id


@pytest.fixture(scope="session")
def prometheus_reporter(test_config: Dict[str, Any], test_session_id: str) -> Optional[PrometheusReporter]:
    """
    Initialize Prometheus metrics reporter.
    
    Args:
        test_config: Test configuration dictionary
        test_session_id: Unique session identifier
        
    Returns:
        Prometheus reporter instance or None if disabled
    """
    reporting_config = test_config.get('reporting', {})
    prometheus_config = reporting_config.get('prometheus', {})
    
    if not prometheus_config.get('enabled', True):
        logger.info("Prometheus reporting disabled")
        return None
    
    try:
        reporter = PrometheusReporter(
            pushgateway_url=prometheus_config['pushgateway_url'],
            job_name=prometheus_config.get('job_name', 'zcu102_hardware_tests'),
            instance_id=test_session_id,
            namespace='zcu102'
        )
        
        logger.info("Prometheus reporter initialized")
        return reporter
        
    except Exception as e:
        logger.warning(f"Failed to initialize Prometheus reporter: {e}")
        return None


@pytest.fixture(scope="session")
def elk_reporter(test_config: Dict[str, Any], test_session_id: str) -> Optional[ELKReporter]:
    """
    Initialize ELK Stack reporter.
    
    Args:
        test_config: Test configuration dictionary
        test_session_id: Unique session identifier
        
    Returns:
        ELK reporter instance or None if disabled
    """
    reporting_config = test_config.get('reporting', {})
    elk_config = reporting_config.get('elasticsearch', {})
    
    if not elk_config.get('enabled', True):
        logger.info("ELK reporting disabled")
        return None
    
    try:
        reporter = ELKReporter(
            elasticsearch_hosts=elk_config['hosts'],
            index_prefix=elk_config.get('index_prefix', 'zcu102-test-logs'),
            session_id=test_session_id
        )
        
        logger.info("ELK reporter initialized")
        return reporter
        
    except Exception as e:
        logger.warning(f"Failed to initialize ELK reporter: {e}")
        return None


@pytest.fixture(scope="session")
def power_controller(test_config: Dict[str, Any]):
    """
    Initialize power controller for board management.
    
    Args:
        test_config: Test configuration dictionary
        
    Yields:
        Power controller instance
    """
    if test_config.get('skip_hardware', False):
        # Use mock power controller for testing
        controller = create_power_controller(
            controller_type="mock",
            device_id=test_config['board_type']
        )
    else:
        power_config = test_config['hardware']['power']
        controller = create_power_controller(
            controller_type=power_config['controller_type'],
            device_id=power_config['device_id'],
            ip_address=power_config.get('ip_address'),
            cycle_delay_seconds=power_config.get('cycle_delay_seconds', 5)
        )
    
    logger.info(f"Power controller initialized: {controller.__class__.__name__}")
    
    try:
        yield controller
    finally:
        # Ensure board is powered on after tests
        if controller.get_state() != PowerState.ON:
            logger.info("Ensuring board is powered on after tests")
            controller.turn_on()


@pytest.fixture(scope="session")
def jtag_controller(test_config: Dict[str, Any]):
    """
    Initialize JTAG controller for firmware management.
    
    Args:
        test_config: Test configuration dictionary
        
    Returns:
        JTAG controller instance or None if disabled
    """
    if test_config.get('skip_hardware', False):
        logger.info("JTAG controller disabled in mock mode")
        return None
    
    try:
        jtag_config = test_config['hardware']['jtag']
        controller = create_jtag_controller(
            cable_type=jtag_config['cable_type'],
            device_part=jtag_config['device_part'],
            vivado_path=jtag_config.get('vivado_path'),
            chain_position=jtag_config.get('chain_position', 1)
        )
        
        logger.info("JTAG controller initialized")
        return controller
        
    except Exception as e:
        logger.warning(f"Failed to initialize JTAG controller: {e}")
        return None


@pytest.fixture
def boot_validator(test_config: Dict[str, Any]) -> Generator[BootValidator, None, None]:
    """
    Initialize boot sequence validator with serial connection.
    
    Args:
        test_config: Test configuration dictionary
        
    Yields:
        Boot validator instance with active serial connection
    """
    if test_config.get('skip_hardware', False):
        pytest.skip("Boot validator requires hardware connection")
    
    serial_config = test_config['hardware']['serial']
    acceptance_criteria = test_config.get('acceptance_criteria', {})
    
    validator = BootValidator(
        serial_port=serial_config['port'],
        baud_rate=serial_config['baud_rate'],
        timeout=serial_config.get('timeout_seconds', 300),
        acceptance_criteria=acceptance_criteria
    )
    
    try:
        with validator:
            logger.info("Boot validator connection established")
            yield validator
    except Exception as e:
        pytest.fail(f"Failed to establish boot validator connection: {e}")


@pytest.fixture
def uart_tester(test_config: Dict[str, Any]) -> Generator[UartTester, None, None]:
    """
    Initialize UART tester with serial connection.
    
    Args:
        test_config: Test configuration dictionary
        
    Yields:
        UART tester instance with active serial connection
    """
    if test_config.get('skip_hardware', False):
        pytest.skip("UART tester requires hardware connection")
    
    serial_config = test_config['hardware']['serial']
    acceptance_criteria = test_config.get('acceptance_criteria', {})
    
    tester = UartTester(
        serial_port=serial_config['port'],
        baud_rate=serial_config['baud_rate'],
        timeout=serial_config.get('timeout_seconds', 30),
        acceptance_criteria=acceptance_criteria
    )
    
    try:
        with tester:
            logger.info("UART tester connection established")
            yield tester
    except Exception as e:
        pytest.fail(f"Failed to establish UART tester connection: {e}")


@pytest.fixture
def ethernet_tester(test_config: Dict[str, Any]) -> Generator[EthernetTester, None, None]:
    """
    Initialize Ethernet tester with network connection.
    
    Args:
        test_config: Test configuration dictionary
        
    Yields:
        Ethernet tester instance with active SSH connection
    """
    if test_config.get('skip_hardware', False):
        pytest.skip("Ethernet tester requires hardware connection")
    
    network_config = test_config['hardware']['network']
    acceptance_criteria = test_config.get('acceptance_criteria', {})
    
    tester = EthernetTester(
        target_ip=network_config['target_ip'],
        test_host_ip=network_config['test_host_ip'],
        interface=network_config.get('interface', 'eth0'),
        acceptance_criteria=acceptance_criteria
    )
    
    try:
        with tester:
            logger.info("Ethernet tester connection established")
            yield tester
    except Exception as e:
        pytest.fail(f"Failed to establish Ethernet tester connection: {e}")


@pytest.fixture(autouse=True)
def test_execution_logging(request, elk_reporter: Optional[ELKReporter], 
                         test_config: Dict[str, Any]):
    """
    Automatic test execution logging fixture.
    
    This fixture runs before and after each test to provide comprehensive
    logging of test execution details.
    """
    test_name = request.node.name
    test_file = request.node.fspath.basename
    
    # Extract test type from markers or file name
    test_type = "unknown"
    if request.node.get_closest_marker("boot"):
        test_type = "boot"
    elif request.node.get_closest_marker("uart"):
        test_type = "uart"
    elif request.node.get_closest_marker("ethernet"):
        test_type = "ethernet"
    elif request.node.get_closest_marker("gpio"):
        test_type = "gpio"
    else:
        # Infer from test file name
        if "boot" in test_file:
            test_type = "boot"
        elif "uart" in test_file:
            test_type = "uart"
        elif "ethernet" in test_file:
            test_type = "ethernet"
    
    start_time = time.time()
    
    # Log test start
    logger.info(f"Starting test: {test_name} (type: {test_type})")
    
    if elk_reporter:
        elk_reporter.log_test_message(
            test_name=test_name,
            test_type=test_type,
            log_level=LogLevel.INFO,
            message=f"Test execution started",
            board_type=test_config['board_type'],
            build_version=test_config['build_version'],
            metadata={'test_file': test_file, 'start_time': datetime.now().isoformat()}
        )
    
    # Execute test
    yield
    
    # Calculate test duration
    duration = time.time() - start_time
    
    # Determine test outcome
    test_passed = not request.node.rep_call.failed if hasattr(request.node, 'rep_call') else True
    
    # Log test completion
    status = "PASSED" if test_passed else "FAILED"
    logger.info(f"Test completed: {test_name} - {status} ({duration:.2f}s)")
    
    if elk_reporter:
        elk_reporter.log_test_message(
            test_name=test_name,
            test_type=test_type,
            log_level=LogLevel.INFO if test_passed else LogLevel.ERROR,
            message=f"Test execution completed: {status}",
            board_type=test_config['board_type'],
            build_version=test_config['build_version'],
            metadata={
                'test_file': test_file,
                'duration_seconds': duration,
                'test_passed': test_passed,
                'end_time': datetime.now().isoformat()
            }
        )


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Hook to capture test results for reporting.
    
    This hook captures detailed test execution results including failures
    for comprehensive reporting and analysis.
    """
    outcome = yield
    rep = outcome.get_result()
    
    # Store report on the item for use in fixtures
    setattr(item, f"rep_{rep.when}", rep)


@pytest.fixture(scope="session", autouse=True)
def session_setup_teardown(test_config: Dict[str, Any], power_controller, 
                         prometheus_reporter: Optional[PrometheusReporter],
                         elk_reporter: Optional[ELKReporter]):
    """
    Session-level setup and teardown operations.
    
    This fixture handles test session initialization and cleanup,
    including hardware preparation and metrics reporting.
    """
    logger.info("=== ZCU102 Test Session Starting ===")
    logger.info(f"Board Type: {test_config['board_type']}")
    logger.info(f"Build Version: {test_config['build_version']}")
    logger.info(f"Test Suite: {test_config['test_suite']}")
    logger.info(f"Hardware Mode: {'Mock' if test_config.get('skip_hardware') else 'Physical'}")
    
    # Power cycle board if requested
    if test_config.get('power_cycle', False) and not test_config.get('skip_hardware'):
        logger.info("Power cycling board before test execution")
        if not power_controller.power_cycle():
            pytest.exit("Failed to power cycle board - aborting test session")
        
        # Wait for boot completion
        time.sleep(30)
    
    # Session start logging
    if elk_reporter:
        elk_reporter.log_test_message(
            test_name="session_start",
            test_type="system",
            log_level=LogLevel.INFO,
            message="Test session initialized",
            board_type=test_config['board_type'],
            build_version=test_config['build_version'],
            metadata=test_config
        )
    
    # Execute test session
    yield
    
    # Session cleanup
    logger.info("=== ZCU102 Test Session Completed ===")
    
    # Flush any remaining logs
    if elk_reporter:
        elk_reporter.log_test_message(
            test_name="session_end",
            test_type="system",
            log_level=LogLevel.INFO,
            message="Test session completed",
            board_type=test_config['board_type'],
            build_version=test_config['build_version']
        )
        elk_reporter.flush_buffered_logs()
    
    # Push final metrics
    if prometheus_reporter:
        prometheus_reporter.push_metrics({
            'session_id': test_config.get('session_id', 'unknown'),
            'board_type': test_config['board_type'],
            'build_version': test_config['build_version']
        })
    
    logger.info("Test session cleanup completed")
