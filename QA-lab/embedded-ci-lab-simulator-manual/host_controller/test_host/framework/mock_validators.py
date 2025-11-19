"""
Mock implementations for hardware validators to enable testing without physical hardware.

These mock classes simulate the behavior of hardware-dependent components to allow
comprehensive testing in CI/CD environments without requiring physical boards.
"""

import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from .boot_validator import BootValidator, BootMetrics, BootStage
from .uart_test import UartTester, UartTestMetrics, UartTestType
from .ethernet_test import EthernetTester, EthernetTestMetrics, EthernetTestType


logger = logging.getLogger(__name__)


class MockBootValidator:
    """Mock boot validator that simulates successful boot sequence validation."""
    
    def __init__(self, serial_port: str = "/dev/ttyUSB0", baud_rate: int = 115200, 
                 timeout: int = 300, acceptance_criteria: Optional[Dict] = None):
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.acceptance_criteria = acceptance_criteria or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def __enter__(self):
        self.logger.info("Mock boot validator connection established")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.info("Mock boot validator connection closed")
        
    def validate_boot_sequence(self, power_cycle: bool = True) -> BootMetrics:
        """Simulate a successful boot sequence validation."""
        self.logger.info("Starting mock boot sequence validation")
        
        # Simulate boot time
        time.sleep(2)  # Brief delay to simulate processing
        
        metrics = BootMetrics()
        metrics.boot_successful = True
        metrics.total_boot_time_seconds = 45.2  # Realistic boot time
        metrics.start_timestamp = datetime.now() - timedelta(seconds=45.2)
        metrics.end_timestamp = datetime.now()
        metrics.final_stage = BootStage.BOOT_COMPLETE
        
        # Add realistic stage durations
        metrics.stage_durations = {
            BootStage.FSBL: 3.1,
            BootStage.UBOOT: 8.4,
            BootStage.KERNEL: 22.3,
            BootStage.USERSPACE: 9.8,
            BootStage.LOGIN_READY: 1.6
        }
        
        # Add some realistic boot messages
        metrics.boot_messages = [
            "Xilinx Zynq MP First Stage Boot Loader",
            "U-Boot 2021.01",
            "Linux version 5.15.36",
            "systemd[1]: Reached target Basic System",
            "Welcome to PetaLinux 2022.2"
        ]
        
        self.logger.info("Mock boot sequence validation completed successfully")
        return metrics


class MockUartTester:
    """Mock UART tester that simulates successful UART communication tests."""
    
    def __init__(self, serial_port: str = "/dev/ttyUSB0", baud_rate: int = 115200,
                 timeout: int = 30, acceptance_criteria: Optional[Dict] = None):
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.acceptance_criteria = acceptance_criteria or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def __enter__(self):
        self.logger.info("Mock UART tester connection established")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.info("Mock UART tester connection closed")
        
    def test_console_interaction(self) -> UartTestMetrics:
        """Simulate successful UART console interaction test."""
        self.logger.info("Starting mock UART console interaction test")
        
        # Simulate test execution time
        time.sleep(1)
        
        metrics = UartTestMetrics(test_type=UartTestType.CONSOLE_INTERACTION)
        metrics.test_successful = True
        metrics.command_success_rate = 1.0  # 100% success
        metrics.commands_executed = 5
        metrics.average_latency_ms = 12.3
        metrics.max_latency_ms = 18.7
        metrics.duration_seconds = 15.2
        
        self.logger.info("Mock UART console interaction test completed successfully")
        return metrics
    
    def run_comprehensive_test_suite(self) -> Dict[str, UartTestMetrics]:
        """Simulate comprehensive UART test suite execution."""
        self.logger.info("Starting mock comprehensive UART test suite")
        
        # Simulate multiple test executions
        time.sleep(2)
        
        results = {}
        
        # Console interaction test
        console_metrics = UartTestMetrics(test_type=UartTestType.CONSOLE_INTERACTION)
        console_metrics.test_successful = True
        console_metrics.command_success_rate = 1.0
        console_metrics.commands_executed = 10
        console_metrics.average_latency_ms = 11.5
        console_metrics.duration_seconds = 25.3
        results["console_interaction"] = console_metrics
        
        # Data integrity test
        integrity_metrics = UartTestMetrics(test_type=UartTestType.DATA_INTEGRITY)
        integrity_metrics.test_successful = True
        integrity_metrics.command_success_rate = 1.0
        integrity_metrics.commands_executed = 20
        integrity_metrics.average_latency_ms = 9.8
        integrity_metrics.duration_seconds = 18.7
        results["data_integrity"] = integrity_metrics
        
        # Performance test
        performance_metrics = UartTestMetrics(test_type=UartTestType.PERFORMANCE)
        performance_metrics.test_successful = True
        performance_metrics.command_success_rate = 1.0
        performance_metrics.commands_executed = 50
        performance_metrics.average_latency_ms = 8.2
        performance_metrics.duration_seconds = 35.6
        results["performance"] = performance_metrics
        
        self.logger.info("Mock comprehensive UART test suite completed successfully")
        return results


class MockEthernetTester:
    """Mock Ethernet tester that simulates successful network tests."""
    
    def __init__(self, target_ip: str = "192.168.1.100", test_host_ip: str = "192.168.1.1",
                 interface: str = "eth0", acceptance_criteria: Optional[Dict] = None):
        self.target_ip = target_ip
        self.test_host_ip = test_host_ip
        self.interface = interface
        self.acceptance_criteria = acceptance_criteria or {}
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def __enter__(self):
        self.logger.info("Mock Ethernet tester connection established")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.logger.info("Mock Ethernet tester connection closed")
        
    def test_basic_connectivity(self) -> EthernetTestMetrics:
        """Simulate successful basic connectivity test."""
        self.logger.info("Starting mock Ethernet connectivity test")
        
        # Simulate test execution time
        time.sleep(1.5)
        
        metrics = EthernetTestMetrics(test_type=EthernetTestType.CONNECTIVITY)
        metrics.test_successful = True
        metrics.ping_success_rate = 1.0  # 100% success
        metrics.average_ping_latency_ms = 0.8
        metrics.packet_loss_percentage = 0.0
        metrics.duration_seconds = 10.5
        
        self.logger.info("Mock Ethernet connectivity test completed successfully")
        return metrics
    
    def test_performance_iperf(self, duration_seconds: int = 30) -> EthernetTestMetrics:
        """Simulate successful performance test using iperf3."""
        self.logger.info("Starting mock Ethernet performance test")
        
        # Simulate test execution time
        time.sleep(2)
        
        metrics = EthernetTestMetrics(test_type=EthernetTestType.PERFORMANCE)
        metrics.test_successful = True
        metrics.tcp_throughput_mbps = 950.2  # Near-gigabit performance
        metrics.udp_throughput_mbps = 940.5
        metrics.duration_seconds = duration_seconds
        
        self.logger.info("Mock Ethernet performance test completed successfully")
        return metrics
    
    def test_stability_stress(self, duration_minutes: int = 10) -> EthernetTestMetrics:
        """Simulate successful stability stress test."""
        self.logger.info("Starting mock Ethernet stability stress test")
        
        # Simulate test execution time (reduced for mock)
        time.sleep(3)
        
        metrics = EthernetTestMetrics(test_type=EthernetTestType.STABILITY)
        metrics.test_successful = True
        metrics.ping_success_rate = 0.998  # Very high stability
        metrics.average_ping_latency_ms = 1.2
        metrics.packet_loss_percentage = 0.2
        metrics.duration_seconds = duration_minutes * 60
        
        self.logger.info("Mock Ethernet stability stress test completed successfully")
        return metrics
    
    def run_comprehensive_test_suite(self) -> Dict[str, EthernetTestMetrics]:
        """Simulate comprehensive Ethernet test suite execution."""
        self.logger.info("Starting mock comprehensive Ethernet test suite")
        
        # Simulate multiple test executions
        time.sleep(3)
        
        results = {}
        
        # Basic connectivity test
        connectivity_metrics = EthernetTestMetrics(test_type=EthernetTestType.CONNECTIVITY)
        connectivity_metrics.test_successful = True
        connectivity_metrics.ping_success_rate = 1.0
        connectivity_metrics.average_ping_latency_ms = 0.9
        connectivity_metrics.packet_loss_percentage = 0.0
        connectivity_metrics.duration_seconds = 12.3
        results["basic_connectivity"] = connectivity_metrics
        
        # Configuration verification test
        config_metrics = EthernetTestMetrics(test_type=EthernetTestType.CONFIGURATION)
        config_metrics.test_successful = True
        config_metrics.duration_seconds = 8.7
        results["configuration_verification"] = config_metrics
        
        # Performance test
        performance_metrics = EthernetTestMetrics(test_type=EthernetTestType.PERFORMANCE)
        performance_metrics.test_successful = True
        performance_metrics.tcp_throughput_mbps = 945.6
        performance_metrics.udp_throughput_mbps = 938.2
        performance_metrics.duration_seconds = 35.4
        results["performance"] = performance_metrics
        
        self.logger.info("Mock comprehensive Ethernet test suite completed successfully")
        return results
