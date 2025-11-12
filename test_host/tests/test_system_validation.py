"""
ZCU102 System Validation Test Suite

This comprehensive test suite validates all critical aspects of the ZCU102 embedded
Linux BSP including boot sequence, communication interfaces, and system stability.
The tests are designed to provide complete "glass box" visibility into system behavior
and ensure reliable operation across all functional areas.

Test Categories:
- Boot sequence validation and performance measurement
- UART communication functionality and reliability  
- Ethernet network performance and stability
- GPIO functionality (when hardware fixtures are available)
- System stability and stress testing
"""

import time
import pytest
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from framework.boot_validator import BootValidator, BootMetrics
from framework.uart_test import UartTester, UartTestMetrics
from framework.ethernet_test import EthernetTester, EthernetTestMetrics
from reporters.prometheus_reporter import PrometheusReporter
from reporters.elk_reporter import ELKReporter, LogLevel, TestResultDocument

logger = logging.getLogger(__name__)


class TestBootSequence:
    """Test suite for boot sequence validation and performance measurement."""
    
    @pytest.mark.boot
    @pytest.mark.hardware
    def test_boot_sequence_validation(self, boot_validator: BootValidator,
                                    test_config: Dict[str, Any],
                                    prometheus_reporter: Optional[PrometheusReporter],
                                    elk_reporter: Optional[ELKReporter]):
        """
        Validate complete boot sequence from power-on to login prompt.
        
        This test verifies that the ZCU102 boots successfully within acceptable
        time limits and without critical errors. It captures detailed metrics
        about each boot stage for performance analysis and regression detection.
        """
        logger.info("Starting comprehensive boot sequence validation")
        
        test_start = datetime.now()
        
        try:
            # Execute boot validation
            boot_metrics = boot_validator.validate_boot_sequence()
            
            # Assert boot success
            assert boot_metrics.boot_successful, f"Boot sequence failed in stage {boot_metrics.final_stage.value}"
            
            # Log success metrics
            logger.info(f"Boot validation successful: {boot_metrics.total_boot_time_seconds:.2f}s total")
            
            # Report to Prometheus
            if prometheus_reporter:
                prometheus_reporter.record_boot_metrics(
                    total_boot_time=boot_metrics.total_boot_time_seconds,
                    stage_durations={stage.value: duration for stage, duration in boot_metrics.stage_durations.items()},
                    board_type=test_config['board_type'],
                    build_version=test_config['build_version']
                )
                
                prometheus_reporter.record_test_execution(
                    test_name="boot_sequence_validation",
                    test_type="boot",
                    duration_seconds=(datetime.now() - test_start).total_seconds(),
                    success=True,
                    board_type=test_config['board_type'],
                    build_version=test_config['build_version']
                )
            
            # Report to ELK
            if elk_reporter:
                test_result = TestResultDocument(
                    test_execution_id=f"boot_validation_{int(time.time())}",
                    test_name="boot_sequence_validation",
                    test_type="boot",
                    start_time=test_start,
                    end_time=datetime.now(),
                    duration_seconds=(datetime.now() - test_start).total_seconds(),
                    success=True,
                    board_type=test_config['board_type'],
                    build_version=test_config['build_version'],
                    metrics={
                        'total_boot_time_seconds': boot_metrics.total_boot_time_seconds,
                        'stage_durations': {stage.value: duration for stage, duration in boot_metrics.stage_durations.items()},
                        'error_count': len(boot_metrics.error_messages),
                        'warning_count': len(boot_metrics.warning_messages)
                    }
                )
                elk_reporter.log_test_result(test_result)
            
        except AssertionError:
            # Re-raise assertion errors for pytest
            raise
        except Exception as e:
            # Handle unexpected errors
            logger.error(f"Boot validation failed with exception: {e}")
            
            # Report failure metrics
            if prometheus_reporter:
                prometheus_reporter.record_test_execution(
                    test_name="boot_sequence_validation",
                    test_type="boot", 
                    duration_seconds=(datetime.now() - test_start).total_seconds(),
                    success=False,
                    board_type=test_config['board_type'],
                    build_version=test_config['build_version'],
                    failure_reason=str(e)
                )
            
            pytest.fail(f"Boot validation exception: {e}")
    
    @pytest.mark.boot
    @pytest.mark.hardware
    @pytest.mark.slow
    def test_boot_reliability_cycles(self, boot_validator: BootValidator, power_controller,
                                   test_config: Dict[str, Any],
                                   prometheus_reporter: Optional[PrometheusReporter]):
        """
        Test boot reliability across multiple power cycles.
        
        This test validates boot consistency by performing multiple power cycle
        and boot operations, ensuring the system can reliably boot under
        various conditions and detecting intermittent issues.
        """
        if test_config['test_suite'] == 'smoke':
            pytest.skip("Boot reliability test not included in smoke test suite")
        
        logger.info("Starting boot reliability test with power cycles")
        
        cycle_count = 3 if test_config['test_suite'] == 'regression' else 10
        successful_boots = 0
        boot_times = []
        
        for cycle in range(cycle_count):
            logger.info(f"Boot reliability cycle {cycle + 1}/{cycle_count}")
            
            try:
                # Power cycle the board
                assert power_controller.power_cycle(), f"Power cycle {cycle + 1} failed"
                
                # Wait for power stabilization
                time.sleep(5)
                
                # Validate boot sequence
                boot_metrics = boot_validator.validate_boot_sequence()
                
                if boot_metrics.boot_successful:
                    successful_boots += 1
                    boot_times.append(boot_metrics.total_boot_time_seconds)
                    logger.info(f"Boot cycle {cycle + 1} successful: {boot_metrics.total_boot_time_seconds:.2f}s")
                else:
                    logger.error(f"Boot cycle {cycle + 1} failed in stage {boot_metrics.final_stage.value}")
                
            except Exception as e:
                logger.error(f"Boot cycle {cycle + 1} exception: {e}")
        
        # Calculate reliability metrics
        reliability_rate = successful_boots / cycle_count
        avg_boot_time = sum(boot_times) / len(boot_times) if boot_times else 0
        boot_time_variance = max(boot_times) - min(boot_times) if len(boot_times) > 1 else 0
        
        # Assert reliability requirements
        min_reliability = test_config.get('acceptance_criteria', {}).get('boot', {}).get('min_reliability_rate', 0.9)
        assert reliability_rate >= min_reliability, f"Boot reliability {reliability_rate:.1%} below minimum {min_reliability:.1%}"
        
        # Report reliability metrics
        if prometheus_reporter:
            prometheus_reporter.record_test_execution(
                test_name="boot_reliability_cycles",
                test_type="boot",
                duration_seconds=0,  # Duration not meaningful for this test
                success=True,
                board_type=test_config['board_type'],
                build_version=test_config['build_version']
            )
        
        logger.info(f"Boot reliability test completed: {reliability_rate:.1%} success rate, {avg_boot_time:.2f}s avg boot time")


class TestUARTCommunication:
    """Test suite for UART communication validation."""
    
    @pytest.mark.uart
    @pytest.mark.hardware
    def test_uart_console_interaction(self, uart_tester: UartTester,
                                    test_config: Dict[str, Any],
                                    prometheus_reporter: Optional[PrometheusReporter],
                                    elk_reporter: Optional[ELKReporter]):
        """
        Test UART console interaction and command execution.
        
        This test validates that the UART interface correctly handles console
        interactions, command execution, and response parsing. It ensures
        reliable communication with the embedded system.
        """
        logger.info("Starting UART console interaction test")
        
        test_start = datetime.now()
        
        try:
            # Execute UART console test
            metrics = uart_tester.test_console_interaction()
            
            # Assert test success
            assert metrics.test_successful, f"UART console test failed with {len(metrics.error_messages)} errors"
            
            # Log success metrics  
            logger.info(f"UART console test successful: {metrics.command_success_rate:.1%} command success rate")
            
            # Report metrics
            if prometheus_reporter:
                prometheus_reporter.record_uart_metrics(
                    baud_rate=115200,  # From test config
                    board_type=test_config['board_type'],
                    build_version=test_config['build_version']
                )
                
                prometheus_reporter.record_test_execution(
                    test_name="uart_console_interaction",
                    test_type="uart",
                    duration_seconds=metrics.duration_seconds,
                    success=True,
                    board_type=test_config['board_type'],
                    build_version=test_config['build_version']
                )
            
            if elk_reporter:
                test_result = TestResultDocument(
                    test_execution_id=f"uart_console_{int(time.time())}",
                    test_name="uart_console_interaction",
                    test_type="uart",
                    start_time=test_start,
                    end_time=datetime.now(),
                    duration_seconds=metrics.duration_seconds,
                    success=True,
                    board_type=test_config['board_type'],
                    build_version=test_config['build_version'],
                    metrics={
                        'command_success_rate': metrics.command_success_rate,
                        'commands_executed': metrics.commands_executed,
                        'average_latency_ms': metrics.average_latency_ms,
                        'max_latency_ms': metrics.max_latency_ms
                    }
                )
                elk_reporter.log_test_result(test_result)
                
        except Exception as e:
            logger.error(f"UART console test failed: {e}")
            
            if prometheus_reporter:
                prometheus_reporter.record_test_execution(
                    test_name="uart_console_interaction",
                    test_type="uart",
                    duration_seconds=(datetime.now() - test_start).total_seconds(),
                    success=False,
                    board_type=test_config['board_type'],
                    build_version=test_config['build_version'],
                    failure_reason=str(e)
                )
            
            pytest.fail(f"UART console test exception: {e}")
    
    @pytest.mark.uart
    @pytest.mark.hardware
    def test_uart_comprehensive_suite(self, uart_tester: UartTester,
                                    test_config: Dict[str, Any],
                                    prometheus_reporter: Optional[PrometheusReporter]):
        """
        Execute comprehensive UART test suite covering all functionality.
        
        This test runs the complete UART validation including console interaction,
        data integrity verification, and performance measurement.
        """
        if test_config['test_suite'] == 'smoke':
            pytest.skip("Comprehensive UART test not included in smoke test suite")
        
        logger.info("Starting comprehensive UART test suite")
        
        # Execute full UART test suite
        test_results = uart_tester.run_comprehensive_test_suite()
        
        # Validate all tests passed
        failed_tests = [name for name, metrics in test_results.items() if not metrics.test_successful]
        assert not failed_tests, f"UART tests failed: {failed_tests}"
        
        # Report aggregate metrics
        if prometheus_reporter:
            for test_name, metrics in test_results.items():
                prometheus_reporter.record_test_execution(
                    test_name=f"uart_{test_name}",
                    test_type="uart",
                    duration_seconds=metrics.duration_seconds,
                    success=metrics.test_successful,
                    board_type=test_config['board_type'],
                    build_version=test_config['build_version']
                )
        
        logger.info(f"Comprehensive UART test suite completed: {len(test_results)} tests passed")


class TestEthernetNetworking:
    """Test suite for Ethernet network validation."""
    
    @pytest.mark.ethernet
    @pytest.mark.hardware  
    def test_ethernet_connectivity(self, ethernet_tester: EthernetTester,
                                 test_config: Dict[str, Any],
                                 prometheus_reporter: Optional[PrometheusReporter],
                                 elk_reporter: Optional[ELKReporter]):
        """
        Test basic Ethernet connectivity and ping functionality.
        
        This test validates that the Ethernet interface is properly configured
        and can establish basic network connectivity with acceptable latency
        and packet loss characteristics.
        """
        logger.info("Starting Ethernet connectivity test")
        
        test_start = datetime.now()
        
        try:
            # Execute connectivity test
            metrics = ethernet_tester.test_basic_connectivity()
            
            # Assert connectivity success
            assert metrics.test_successful, f"Ethernet connectivity test failed"
            
            logger.info(f"Ethernet connectivity successful: {metrics.ping_success_rate:.1%} success rate, {metrics.average_ping_latency_ms:.2f}ms latency")
            
            # Report metrics
            if prometheus_reporter:
                prometheus_reporter.record_network_metrics(
                    ping_latency=metrics.average_ping_latency_ms,
                    packet_loss=metrics.packet_loss_percentage,
                    board_type=test_config['board_type'],
                    build_version=test_config['build_version']
                )
                
                prometheus_reporter.record_test_execution(
                    test_name="ethernet_connectivity",
                    test_type="ethernet",
                    duration_seconds=metrics.duration_seconds,
                    success=True,
                    board_type=test_config['board_type'],
                    build_version=test_config['build_version']
                )
            
            if elk_reporter:
                test_result = TestResultDocument(
                    test_execution_id=f"ethernet_connectivity_{int(time.time())}",
                    test_name="ethernet_connectivity", 
                    test_type="ethernet",
                    start_time=test_start,
                    end_time=datetime.now(),
                    duration_seconds=metrics.duration_seconds,
                    success=True,
                    board_type=test_config['board_type'],
                    build_version=test_config['build_version'],
                    metrics={
                        'ping_success_rate': metrics.ping_success_rate,
                        'average_ping_latency_ms': metrics.average_ping_latency_ms,
                        'packet_loss_percentage': metrics.packet_loss_percentage
                    }
                )
                elk_reporter.log_test_result(test_result)
                
        except Exception as e:
            logger.error(f"Ethernet connectivity test failed: {e}")
            
            if prometheus_reporter:
                prometheus_reporter.record_test_execution(
                    test_name="ethernet_connectivity",
                    test_type="ethernet",
                    duration_seconds=(datetime.now() - test_start).total_seconds(),
                    success=False,
                    board_type=test_config['board_type'],
                    build_version=test_config['build_version'],
                    failure_reason=str(e)
                )
            
            pytest.fail(f"Ethernet connectivity test exception: {e}")
    
    @pytest.mark.ethernet
    @pytest.mark.hardware
    def test_ethernet_performance(self, ethernet_tester: EthernetTester,
                                test_config: Dict[str, Any], 
                                prometheus_reporter: Optional[PrometheusReporter]):
        """
        Test Ethernet performance using iperf3 throughput measurement.
        
        This test measures TCP and UDP throughput to validate that the Ethernet
        interface can achieve expected performance levels and identify any
        performance regressions in the network stack.
        """
        if test_config['test_suite'] == 'smoke':
            pytest.skip("Ethernet performance test not included in smoke test suite")
        
        logger.info("Starting Ethernet performance test")
        
        # Execute performance test
        metrics = ethernet_tester.test_performance_iperf(duration_seconds=30)
        
        # Assert performance requirements
        assert metrics.test_successful, "Ethernet performance test failed to meet requirements"
        
        logger.info(f"Ethernet performance test successful: TCP={metrics.tcp_throughput_mbps:.1f}Mbps, UDP={metrics.udp_throughput_mbps:.1f}Mbps")
        
        # Report performance metrics
        if prometheus_reporter:
            prometheus_reporter.record_network_metrics(
                tcp_throughput=metrics.tcp_throughput_mbps,
                udp_throughput=metrics.udp_throughput_mbps,
                board_type=test_config['board_type'],
                build_version=test_config['build_version']
            )
            
            prometheus_reporter.record_test_execution(
                test_name="ethernet_performance",
                test_type="ethernet",
                duration_seconds=metrics.duration_seconds,
                success=True,
                board_type=test_config['board_type'],
                build_version=test_config['build_version']
            )
    
    @pytest.mark.ethernet
    @pytest.mark.hardware
    @pytest.mark.slow
    def test_ethernet_comprehensive_suite(self, ethernet_tester: EthernetTester,
                                        test_config: Dict[str, Any],
                                        prometheus_reporter: Optional[PrometheusReporter]):
        """
        Execute comprehensive Ethernet test suite covering all functionality.
        
        This test runs the complete Ethernet validation including connectivity,
        configuration verification, performance measurement, and stability testing.
        """
        if test_config['test_suite'] == 'smoke':
            pytest.skip("Comprehensive Ethernet test not included in smoke test suite")
        
        logger.info("Starting comprehensive Ethernet test suite")
        
        # Execute full Ethernet test suite
        test_results = ethernet_tester.run_comprehensive_test_suite()
        
        # Validate all tests passed
        failed_tests = [name for name, metrics in test_results.items() if not metrics.test_successful]
        assert not failed_tests, f"Ethernet tests failed: {failed_tests}"
        
        # Report aggregate metrics
        if prometheus_reporter:
            for test_name, metrics in test_results.items():
                prometheus_reporter.record_test_execution(
                    test_name=f"ethernet_{test_name}",
                    test_type="ethernet", 
                    duration_seconds=metrics.duration_seconds,
                    success=metrics.test_successful,
                    board_type=test_config['board_type'],
                    build_version=test_config['build_version']
                )
        
        logger.info(f"Comprehensive Ethernet test suite completed: {len(test_results)} tests passed")


class TestSystemStability:
    """Test suite for system stability and stress testing."""
    
    @pytest.mark.hardware
    @pytest.mark.slow
    def test_system_stability_soak(self, ethernet_tester: EthernetTester,
                                 test_config: Dict[str, Any],
                                 prometheus_reporter: Optional[PrometheusReporter]):
        """
        Test system stability under extended operation (soak test).
        
        This test validates system stability by running continuous network
        activity for an extended period to detect memory leaks, performance
        degradation, or other stability issues.
        """
        if test_config['test_suite'] in ['smoke', 'regression']:
            pytest.skip("System stability soak test only included in full test suite")
        
        logger.info("Starting system stability soak test")
        
        # Execute stability test (reduced duration for CI)
        stability_duration = 10  # minutes - would be longer in production
        metrics = ethernet_tester.test_stability_stress(duration_minutes=stability_duration)
        
        # Assert stability requirements
        assert metrics.test_successful, f"System stability test failed: {len(metrics.error_messages)} errors"
        
        logger.info(f"System stability test successful: {metrics.ping_success_rate:.1%} stability rate")
        
        # Report stability metrics
        if prometheus_reporter:
            prometheus_reporter.record_test_execution(
                test_name="system_stability_soak",
                test_type="stability",
                duration_seconds=metrics.duration_seconds,
                success=True,
                board_type=test_config['board_type'],
                build_version=test_config['build_version']
            )


# Test collection functions for different test suites
def pytest_collection_modifyitems(config, items):
    """
    Modify test collection based on selected test suite.
    
    This function filters tests based on the selected test suite
    (smoke, regression, full) to provide appropriate test coverage
    for different validation scenarios.
    """
    test_suite = config.getoption("--test-suite")
    
    if test_suite == "smoke":
        # Only run basic functionality tests for smoke suite
        selected_tests = []
        for item in items:
            if not any(marker in item.keywords for marker in ["slow", "comprehensive"]):
                selected_tests.append(item)
        items[:] = selected_tests
        
    elif test_suite == "regression":
        # Skip only the most time-consuming tests
        selected_tests = []
        for item in items:
            if "soak" not in item.name and "reliability_cycles" not in item.name:
                selected_tests.append(item)
        items[:] = selected_tests
