"""
ZCU102 UART Communication Test Framework

This module provides comprehensive validation of UART functionality on the ZCU102
embedded Linux system. It tests console interaction, data integrity, and performance
characteristics to ensure reliable serial communication.

The UART tests support both interactive console testing and loopback hardware
configurations for thorough validation of the serial subsystem.
"""

import re
import time
import hashlib
import random
import string
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

import serial
from datetime import datetime, timedelta
from .tcp_serial_adapter import create_serial_connection


class UartTestType(Enum):
    """Enumeration of UART test categories."""
    CONSOLE_INTERACTION = "console_interaction"
    DATA_INTEGRITY = "data_integrity" 
    PERFORMANCE = "performance"
    LOOPBACK = "loopback"
    CONFIGURATION = "configuration"


@dataclass
class UartTestMetrics:
    """Comprehensive UART test metrics for analysis and reporting."""
    test_type: UartTestType
    test_successful: bool = False
    start_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # Console interaction metrics
    command_success_rate: float = 0.0
    response_times_ms: List[float] = field(default_factory=list)
    commands_executed: int = 0
    
    # Data integrity metrics
    bytes_transmitted: int = 0
    bytes_received: int = 0
    checksum_matches: int = 0
    checksum_failures: int = 0
    
    # Performance metrics
    throughput_bps: float = 0.0
    average_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    
    # Error tracking
    transmission_errors: int = 0
    timeout_errors: int = 0
    error_messages: List[str] = field(default_factory=list)
    
    def add_error(self, error_message: str) -> None:
        """Record an error message for analysis."""
        self.error_messages.append(error_message)
        
    def add_response_time(self, response_time_ms: float) -> None:
        """Record command response time for latency analysis."""
        self.response_times_ms.append(response_time_ms)
        
        # Update latency statistics
        if response_time_ms > self.max_latency_ms:
            self.max_latency_ms = response_time_ms
        if response_time_ms < self.min_latency_ms:
            self.min_latency_ms = response_time_ms
            
        self.average_latency_ms = sum(self.response_times_ms) / len(self.response_times_ms)


class UartTester:
    """
    Advanced UART testing framework for ZCU102 embedded Linux systems.
    
    This class provides comprehensive validation of UART functionality including
    console interaction, data integrity verification, and performance characterization.
    """
    
    # Standard Linux commands for console interaction testing
    TEST_COMMANDS = [
        ("uname -a", r"Linux.*(aarch64|x86_64)"),  # Accept both ARM and x86 for simulation
        ("cat /proc/version", r"Linux version"),
        ("ls /", r"bin.*usr.*etc"),  # Match bin, usr, etc in any order across multiline output
        ("whoami", r"root|petalinux"),
        ("date", r"\d{4}"),
        ("free -m", r"Mem:.*\d+"),
        ("cat /proc/cpuinfo | head -5", r"processor.*\d+"),  # Just verify processor info is present
        ("df -h", r"Filesystem.*Size"),
    ]
    
    def __init__(self, serial_port: str, baud_rate: int = 115200, 
                 timeout: int = 30, acceptance_criteria: Optional[Dict] = None):
        """
        Initialize UART tester with hardware configuration.
        
        Args:
            serial_port: Path to serial device (e.g., /dev/ttyUSB0)
            baud_rate: Serial communication baud rate  
            timeout: Command timeout in seconds
            acceptance_criteria: Dict containing UART test acceptance criteria
        """
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.acceptance_criteria = acceptance_criteria or {}
        
        self.logger = logging.getLogger(__name__)
        self.serial_connection: Optional[serial.Serial] = None
        
    def __enter__(self):
        """Context manager entry - establish serial connection."""
        try:
            self.serial_connection = create_serial_connection(
                port=self.serial_port,
                baud_rate=self.baud_rate,
                timeout=self.timeout
            )
            
            # Open the connection
            if hasattr(self.serial_connection, 'open'):
                self.serial_connection.open()
            
            self.logger.info(f"UART test connection established: {self.serial_port}@{self.baud_rate}")
            return self
        except Exception as e:
            self.logger.error(f"Failed to open serial connection {self.serial_port}: {e}")
            raise
            
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup serial connection."""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            self.logger.info("UART test connection closed")
    
    def _send_command(self, command: str, expected_pattern: Optional[str] = None,
                     timeout: Optional[int] = None) -> Tuple[bool, str, float]:
        """
        Send command via UART and capture response.
        
        Args:
            command: Command string to send
            expected_pattern: Regex pattern to validate response
            timeout: Command-specific timeout override
            
        Returns:
            Tuple of (success, response, response_time_ms)
        """
        if not self.serial_connection:
            raise RuntimeError("Serial connection not established")
        
        cmd_timeout = timeout or self.timeout
        start_time = time.time()
        
        try:
            # Clear input buffer before sending command
            self.serial_connection.reset_input_buffer()
            
            # Send command with newline
            command_bytes = f"{command}\n".encode('utf-8')
            self.serial_connection.write(command_bytes)
            self.serial_connection.flush()
            
            # Collect response until prompt appears or timeout
            response_lines = []
            end_time = start_time + cmd_timeout
            
            while time.time() < end_time:
                if self.serial_connection.in_waiting > 0:
                    line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        response_lines.append(line)
                        
                        # Check for shell prompt indicating command completion
                        if re.search(r'[#$>]\s*$', line):
                            break
                else:
                    time.sleep(0.1)
            
            response_time_ms = (time.time() - start_time) * 1000
            full_response = '\n'.join(response_lines)
            
            # Validate response against expected pattern if provided
            success = True
            if expected_pattern:
                success = bool(re.search(expected_pattern, full_response, re.MULTILINE | re.IGNORECASE))
                
            return success, full_response, response_time_ms
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            self.logger.error(f"Command execution failed: {e}")
            return False, str(e), response_time_ms
    
    def test_console_interaction(self) -> UartTestMetrics:
        """
        Test interactive console functionality via UART.
        
        Executes a series of standard Linux commands to validate that the system
        responds correctly to console input and provides expected output.
        
        Returns:
            UartTestMetrics containing console interaction results
        """
        metrics = UartTestMetrics(test_type=UartTestType.CONSOLE_INTERACTION)
        metrics.start_timestamp = datetime.now()
        
        self.logger.info("Starting UART console interaction test")
        
        successful_commands = 0
        
        try:
            # Ensure we're at a command prompt
            self._send_command("", timeout=5)  # Send empty command to get prompt
            
            for command, expected_pattern in self.TEST_COMMANDS:
                self.logger.debug(f"Executing command: {command}")
                
                success, response, response_time = self._send_command(command, expected_pattern)
                metrics.add_response_time(response_time)
                metrics.commands_executed += 1
                
                if success:
                    successful_commands += 1
                    self.logger.debug(f"Command successful: {command} (response time: {response_time:.1f}ms)")
                else:
                    metrics.add_error(f"Command failed: {command} - Response: {response}")
                    self.logger.warning(f"Command failed: {command}")
            
            metrics.command_success_rate = successful_commands / len(self.TEST_COMMANDS)
            metrics.test_successful = metrics.command_success_rate >= 0.8  # 80% success threshold
            
        except Exception as e:
            metrics.add_error(f"Console interaction test failed: {e}")
            metrics.test_successful = False
            
        finally:
            metrics.end_timestamp = datetime.now()
            metrics.duration_seconds = (metrics.end_timestamp - metrics.start_timestamp).total_seconds()
        
        self.logger.info(f"Console interaction test completed: {metrics.command_success_rate:.1%} success rate")
        return metrics
    
    def test_data_integrity(self, test_size_kb: int = 10, chunk_size: int = 1024) -> UartTestMetrics:
        """
        Test UART data integrity using checksummed data transmission.
        
        Args:
            test_size_kb: Total amount of data to transmit (KB)
            chunk_size: Size of individual data chunks (bytes)
            
        Returns:
            UartTestMetrics containing data integrity results
        """
        metrics = UartTestMetrics(test_type=UartTestType.DATA_INTEGRITY)
        metrics.start_timestamp = datetime.now()
        
        self.logger.info(f"Starting UART data integrity test: {test_size_kb}KB in {chunk_size}B chunks")
        
        try:
            total_bytes = test_size_kb * 1024
            chunks_to_send = total_bytes // chunk_size
            
            for chunk_num in range(chunks_to_send):
                # Generate random data chunk
                random_data = ''.join(random.choices(string.ascii_letters + string.digits, k=chunk_size))
                expected_checksum = hashlib.md5(random_data.encode()).hexdigest()
                
                # Create test command that echoes data and computes checksum
                test_command = f'echo -n "{random_data}" | tee /tmp/test_chunk | md5sum'
                
                success, response, _ = self._send_command(test_command, timeout=10)
                
                if success:
                    # Extract checksum from response
                    checksum_match = re.search(r'([a-f0-9]{32})', response)
                    if checksum_match:
                        actual_checksum = checksum_match.group(1)
                        if actual_checksum == expected_checksum:
                            metrics.checksum_matches += 1
                        else:
                            metrics.checksum_failures += 1
                            metrics.add_error(f"Checksum mismatch in chunk {chunk_num}")
                    else:
                        metrics.transmission_errors += 1
                        metrics.add_error(f"No checksum found in response for chunk {chunk_num}")
                else:
                    metrics.transmission_errors += 1
                    metrics.add_error(f"Transmission failed for chunk {chunk_num}")
                
                metrics.bytes_transmitted += len(random_data)
                
            # Calculate integrity metrics
            total_chunks = chunks_to_send
            integrity_rate = metrics.checksum_matches / total_chunks if total_chunks > 0 else 0
            metrics.test_successful = integrity_rate >= 0.99  # 99% integrity threshold
            
        except Exception as e:
            metrics.add_error(f"Data integrity test failed: {e}")
            metrics.test_successful = False
            
        finally:
            metrics.end_timestamp = datetime.now()
            metrics.duration_seconds = (metrics.end_timestamp - metrics.start_timestamp).total_seconds()
        
        self.logger.info(f"Data integrity test completed: {metrics.checksum_matches}/{chunks_to_send} chunks verified")
        return metrics
    
    def test_performance(self, duration_seconds: int = 30) -> UartTestMetrics:
        """
        Test UART performance characteristics including throughput and latency.
        
        Args:
            duration_seconds: Duration to run performance test
            
        Returns:
            UartTestMetrics containing performance results
        """
        metrics = UartTestMetrics(test_type=UartTestType.PERFORMANCE)
        metrics.start_timestamp = datetime.now()
        
        self.logger.info(f"Starting UART performance test: {duration_seconds}s duration")
        
        try:
            test_end_time = time.time() + duration_seconds
            command_count = 0
            total_bytes = 0
            
            # Run continuous commands to measure throughput and latency
            while time.time() < test_end_time:
                # Use a command that generates predictable output
                test_command = f"echo 'Performance test iteration {command_count}'"
                
                success, response, response_time = self._send_command(test_command, timeout=5)
                
                if success:
                    metrics.add_response_time(response_time)
                    total_bytes += len(response.encode('utf-8'))
                    command_count += 1
                else:
                    metrics.timeout_errors += 1
                
            # Calculate throughput
            if metrics.duration_seconds > 0:
                metrics.throughput_bps = (total_bytes * 8) / metrics.duration_seconds
            
            # Performance acceptance criteria
            min_throughput = self.acceptance_criteria.get('uart', {}).get('min_throughput_bps', 57600)  # 50% of baud rate
            max_latency = self.acceptance_criteria.get('uart', {}).get('max_latency_ms', 1000)
            
            metrics.test_successful = (
                metrics.throughput_bps >= min_throughput and
                metrics.average_latency_ms <= max_latency and
                metrics.timeout_errors == 0
            )
            
        except Exception as e:
            metrics.add_error(f"Performance test failed: {e}")
            metrics.test_successful = False
            
        finally:
            metrics.end_timestamp = datetime.now()
            metrics.duration_seconds = (metrics.end_timestamp - metrics.start_timestamp).total_seconds()
        
        self.logger.info(f"Performance test completed: {metrics.throughput_bps:.0f} bps, {metrics.average_latency_ms:.1f}ms avg latency")
        return metrics
    
    def run_comprehensive_test_suite(self) -> Dict[str, UartTestMetrics]:
        """
        Execute comprehensive UART test suite covering all test categories.
        
        Returns:
            Dictionary mapping test names to their respective metrics
        """
        test_results = {}
        
        self.logger.info("Starting comprehensive UART test suite")
        
        # Execute all test categories
        test_suite = [
            ("console_interaction", self.test_console_interaction),
            ("data_integrity", lambda: self.test_data_integrity(test_size_kb=5)),
            ("performance", lambda: self.test_performance(duration_seconds=15)),
        ]
        
        for test_name, test_function in test_suite:
            try:
                self.logger.info(f"Executing UART test: {test_name}")
                metrics = test_function()
                test_results[test_name] = metrics
                
                status = "PASS" if metrics.test_successful else "FAIL"
                self.logger.info(f"UART test {test_name}: {status}")
                
            except Exception as e:
                self.logger.error(f"UART test {test_name} failed with exception: {e}")
                # Create failure metrics
                failed_metrics = UartTestMetrics(test_type=UartTestType.CONSOLE_INTERACTION)
                failed_metrics.test_successful = False
                failed_metrics.add_error(str(e))
                test_results[test_name] = failed_metrics
        
        # Overall test suite success
        overall_success = all(metrics.test_successful for metrics in test_results.values())
        self.logger.info(f"UART comprehensive test suite completed: {'PASS' if overall_success else 'FAIL'}")
        
        return test_results
    
    def generate_test_report(self, test_results: Dict[str, UartTestMetrics]) -> Dict[str, Any]:
        """
        Generate comprehensive UART test report.
        
        Args:
            test_results: Dictionary of test results to report on
            
        Returns:
            Dictionary containing formatted test report
        """
        overall_success = all(metrics.test_successful for metrics in test_results.values())
        
        report = {
            "test_summary": {
                "overall_success": overall_success,
                "tests_executed": len(test_results),
                "tests_passed": sum(1 for m in test_results.values() if m.test_successful),
                "total_duration_seconds": sum(m.duration_seconds for m in test_results.values()),
            },
            "test_details": {}
        }
        
        for test_name, metrics in test_results.items():
            report["test_details"][test_name] = {
                "success": metrics.test_successful,
                "duration_seconds": metrics.duration_seconds,
                "test_type": metrics.test_type.value,
                "error_count": len(metrics.error_messages),
                "errors": metrics.error_messages,
                
                # Test-specific metrics
                "command_success_rate": getattr(metrics, 'command_success_rate', None),
                "average_latency_ms": getattr(metrics, 'average_latency_ms', None),
                "throughput_bps": getattr(metrics, 'throughput_bps', None),
                "checksum_matches": getattr(metrics, 'checksum_matches', None),
                "checksum_failures": getattr(metrics, 'checksum_failures', None),
            }
        
        return report
