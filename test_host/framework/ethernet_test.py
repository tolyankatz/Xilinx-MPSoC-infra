"""
ZCU102 Ethernet Network Test Framework

This module provides comprehensive validation of Ethernet network functionality on 
the ZCU102 embedded Linux system. It tests connectivity, performance, and reliability
to ensure robust network communication capabilities.

The Ethernet tests cover basic connectivity, throughput measurement, latency analysis,
and stress testing to validate the network stack and driver implementation.
"""

import subprocess
import time
import re
import socket
import struct
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

import paramiko


class EthernetTestType(Enum):
    """Enumeration of Ethernet test categories."""
    CONNECTIVITY = "connectivity"
    PERFORMANCE = "performance" 
    STABILITY = "stability"
    CONFIGURATION = "configuration"


@dataclass
class EthernetTestMetrics:
    """Comprehensive Ethernet test metrics for analysis and reporting."""
    test_type: EthernetTestType
    test_successful: bool = False
    start_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # Connectivity metrics
    ping_success_rate: float = 0.0
    average_ping_latency_ms: float = 0.0
    packet_loss_percentage: float = 0.0
    
    # Performance metrics  
    tcp_throughput_mbps: float = 0.0
    udp_throughput_mbps: float = 0.0
    tcp_bandwidth_utilization: float = 0.0
    
    # Stability metrics
    connection_drops: int = 0
    retransmission_count: int = 0
    error_rate: float = 0.0
    
    # Configuration metrics
    link_speed_mbps: int = 0
    duplex_mode: str = ""
    mtu_size: int = 0
    
    # Error tracking
    error_messages: List[str] = field(default_factory=list)
    
    def add_error(self, error_message: str) -> None:
        """Record an error message for analysis."""
        self.error_messages.append(error_message)


class EthernetTester:
    """
    Advanced Ethernet testing framework for ZCU102 embedded Linux systems.
    
    This class provides comprehensive validation of Ethernet functionality including
    connectivity verification, performance characterization, and stability testing.
    """
    
    def __init__(self, target_ip: str, test_host_ip: str, interface: str = "eth0",
                 ssh_username: str = "root", ssh_password: Optional[str] = None,
                 acceptance_criteria: Optional[Dict] = None):
        """
        Initialize Ethernet tester with network configuration.
        
        Args:
            target_ip: IP address of the ZCU102 DUT
            test_host_ip: IP address of the test host
            interface: Network interface name on DUT
            ssh_username: SSH username for DUT access
            ssh_password: SSH password (None for key-based auth)
            acceptance_criteria: Dict containing network test acceptance criteria
        """
        self.target_ip = target_ip
        self.test_host_ip = test_host_ip
        self.interface = interface
        self.ssh_username = ssh_username
        self.ssh_password = ssh_password
        self.acceptance_criteria = acceptance_criteria or {}
        
        self.logger = logging.getLogger(__name__)
        self.ssh_client: Optional[paramiko.SSHClient] = None
        
    def __enter__(self):
        """Context manager entry - establish SSH connection to DUT."""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Attempt SSH connection
            self.ssh_client.connect(
                hostname=self.target_ip,
                username=self.ssh_username,
                password=self.ssh_password,
                timeout=30,
                look_for_keys=True if not self.ssh_password else False
            )
            
            self.logger.info(f"SSH connection established to {self.target_ip}")
            return self
        except Exception as e:
            self.logger.error(f"Failed to establish SSH connection to {self.target_ip}: {e}")
            raise
            
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup SSH connection."""
        if self.ssh_client:
            self.ssh_client.close()
            self.logger.info("SSH connection closed")
    
    def _execute_remote_command(self, command: str, timeout: int = 30) -> Tuple[int, str, str]:
        """
        Execute command on remote DUT via SSH.
        
        Args:
            command: Command to execute on DUT
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        if not self.ssh_client:
            raise RuntimeError("SSH connection not established")
            
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)
            
            exit_code = stdout.channel.recv_exit_status()
            stdout_data = stdout.read().decode('utf-8').strip()
            stderr_data = stderr.read().decode('utf-8').strip()
            
            return exit_code, stdout_data, stderr_data
            
        except Exception as e:
            self.logger.error(f"Remote command execution failed: {e}")
            return -1, "", str(e)
    
    def _execute_local_command(self, command: str, timeout: int = 30) -> Tuple[int, str, str]:
        """
        Execute command on local test host.
        
        Args:
            command: Command to execute locally
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                timeout=timeout,
                capture_output=True,
                text=True
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
            
        except subprocess.TimeoutExpired:
            return -1, "", "Command timeout"
        except Exception as e:
            return -1, "", str(e)
    
    def test_basic_connectivity(self, ping_count: int = 10) -> EthernetTestMetrics:
        """
        Test basic network connectivity using ICMP ping.
        
        Args:
            ping_count: Number of ping packets to send
            
        Returns:
            EthernetTestMetrics containing connectivity results
        """
        metrics = EthernetTestMetrics(test_type=EthernetTestType.CONNECTIVITY)
        metrics.start_timestamp = datetime.now()
        
        self.logger.info(f"Starting Ethernet connectivity test: ping {self.target_ip}")
        
        try:
            # Execute ping from test host to DUT
            ping_command = f"ping -c {ping_count} -W 5 {self.target_ip}"
            exit_code, stdout, stderr = self._execute_local_command(ping_command, timeout=60)
            
            if exit_code == 0:
                # Parse ping results
                packet_loss_match = re.search(r'(\d+)% packet loss', stdout)
                if packet_loss_match:
                    metrics.packet_loss_percentage = float(packet_loss_match.group(1))
                
                # Extract average latency
                latency_match = re.search(r'min/avg/max/mdev = [\d.]+/([\d.]+)/[\d.]+/[\d.]+', stdout)
                if latency_match:
                    metrics.average_ping_latency_ms = float(latency_match.group(1))
                
                # Calculate success rate
                metrics.ping_success_rate = (100 - metrics.packet_loss_percentage) / 100
                
                # Test success criteria
                max_packet_loss = self.acceptance_criteria.get('network', {}).get('max_packet_loss_percent', 5)
                max_latency = self.acceptance_criteria.get('network', {}).get('max_ping_latency_ms', 10)
                
                metrics.test_successful = (
                    metrics.packet_loss_percentage <= max_packet_loss and
                    metrics.average_ping_latency_ms <= max_latency
                )
                
            else:
                metrics.add_error(f"Ping command failed: {stderr}")
                metrics.test_successful = False
                
            # Test reverse connectivity (DUT to test host)
            if self.ssh_client:
                reverse_ping_command = f"ping -c 5 -W 2 {self.test_host_ip}"
                exit_code, stdout, stderr = self._execute_remote_command(reverse_ping_command)
                
                if exit_code != 0:
                    metrics.add_error(f"Reverse ping failed: {stderr}")
                
        except Exception as e:
            metrics.add_error(f"Connectivity test failed: {e}")
            metrics.test_successful = False
            
        finally:
            metrics.end_timestamp = datetime.now()
            metrics.duration_seconds = (metrics.end_timestamp - metrics.start_timestamp).total_seconds()
        
        self.logger.info(f"Connectivity test completed: {metrics.ping_success_rate:.1%} success rate, {metrics.average_ping_latency_ms:.2f}ms latency")
        return metrics
    
    def test_performance_iperf(self, duration_seconds: int = 30, 
                              test_tcp: bool = True, test_udp: bool = True) -> EthernetTestMetrics:
        """
        Test network performance using iperf3 throughput measurement.
        
        Args:
            duration_seconds: Duration for each iperf test
            test_tcp: Whether to test TCP throughput
            test_udp: Whether to test UDP throughput
            
        Returns:
            EthernetTestMetrics containing performance results
        """
        metrics = EthernetTestMetrics(test_type=EthernetTestType.PERFORMANCE)
        metrics.start_timestamp = datetime.now()
        
        self.logger.info(f"Starting Ethernet performance test: iperf3 for {duration_seconds}s")
        
        try:
            # Start iperf3 server on DUT
            server_command = "pkill iperf3 2>/dev/null; iperf3 -s -D"  # Daemon mode
            exit_code, stdout, stderr = self._execute_remote_command(server_command)
            
            if exit_code != 0:
                metrics.add_error(f"Failed to start iperf3 server: {stderr}")
                metrics.test_successful = False
                return metrics
            
            # Allow server to start
            time.sleep(2)
            
            # Test TCP throughput
            if test_tcp:
                tcp_command = f"iperf3 -c {self.target_ip} -t {duration_seconds} -f m"
                exit_code, stdout, stderr = self._execute_local_command(tcp_command, timeout=duration_seconds + 30)
                
                if exit_code == 0:
                    # Parse TCP throughput
                    throughput_match = re.search(r'sender.*?(\d+\.?\d*)\s+Mbits/sec', stdout)
                    if throughput_match:
                        metrics.tcp_throughput_mbps = float(throughput_match.group(1))
                else:
                    metrics.add_error(f"TCP throughput test failed: {stderr}")
            
            # Test UDP throughput
            if test_udp:
                udp_command = f"iperf3 -c {self.target_ip} -t {duration_seconds} -u -b 1000M -f m"
                exit_code, stdout, stderr = self._execute_local_command(udp_command, timeout=duration_seconds + 30)
                
                if exit_code == 0:
                    # Parse UDP throughput
                    throughput_match = re.search(r'sender.*?(\d+\.?\d*)\s+Mbits/sec', stdout)
                    if throughput_match:
                        metrics.udp_throughput_mbps = float(throughput_match.group(1))
                else:
                    metrics.add_error(f"UDP throughput test failed: {stderr}")
            
            # Calculate bandwidth utilization (assuming Gigabit Ethernet)
            theoretical_max_mbps = 1000
            if metrics.tcp_throughput_mbps > 0:
                metrics.tcp_bandwidth_utilization = metrics.tcp_throughput_mbps / theoretical_max_mbps
            
            # Performance acceptance criteria
            min_tcp_throughput = self.acceptance_criteria.get('network', {}).get('min_tcp_throughput_mbps', 900)
            min_udp_throughput = self.acceptance_criteria.get('network', {}).get('min_udp_throughput_mbps', 900)
            
            metrics.test_successful = (
                metrics.tcp_throughput_mbps >= min_tcp_throughput and
                (not test_udp or metrics.udp_throughput_mbps >= min_udp_throughput)
            )
            
            # Stop iperf3 server
            self._execute_remote_command("pkill iperf3")
            
        except Exception as e:
            metrics.add_error(f"Performance test failed: {e}")
            metrics.test_successful = False
            
        finally:
            metrics.end_timestamp = datetime.now()
            metrics.duration_seconds = (metrics.end_timestamp - metrics.start_timestamp).total_seconds()
        
        self.logger.info(f"Performance test completed: TCP={metrics.tcp_throughput_mbps:.1f}Mbps, UDP={metrics.udp_throughput_mbps:.1f}Mbps")
        return metrics
    
    def test_interface_configuration(self) -> EthernetTestMetrics:
        """
        Test Ethernet interface configuration and status.
        
        Returns:
            EthernetTestMetrics containing configuration results
        """
        metrics = EthernetTestMetrics(test_type=EthernetTestType.CONFIGURATION)
        metrics.start_timestamp = datetime.now()
        
        self.logger.info(f"Starting Ethernet configuration test: interface {self.interface}")
        
        try:
            # Get interface status
            status_command = f"ip link show {self.interface}"
            exit_code, stdout, stderr = self._execute_remote_command(status_command)
            
            if exit_code == 0:
                # Parse link status
                if "UP" in stdout and "LOWER_UP" in stdout:
                    link_up = True
                else:
                    link_up = False
                    metrics.add_error("Interface link is down")
                
                # Extract MTU
                mtu_match = re.search(r'mtu (\d+)', stdout)
                if mtu_match:
                    metrics.mtu_size = int(mtu_match.group(1))
            else:
                metrics.add_error(f"Failed to get interface status: {stderr}")
                link_up = False
            
            # Get ethtool information for speed and duplex
            ethtool_command = f"ethtool {self.interface}"
            exit_code, stdout, stderr = self._execute_remote_command(ethtool_command)
            
            if exit_code == 0:
                # Parse link speed
                speed_match = re.search(r'Speed: (\d+)Mb/s', stdout)
                if speed_match:
                    metrics.link_speed_mbps = int(speed_match.group(1))
                
                # Parse duplex mode
                duplex_match = re.search(r'Duplex: (\w+)', stdout)
                if duplex_match:
                    metrics.duplex_mode = duplex_match.group(1).lower()
            else:
                self.logger.warning(f"ethtool command failed: {stderr}")
            
            # Get IP configuration
            ip_command = f"ip addr show {self.interface}"
            exit_code, stdout, stderr = self._execute_remote_command(ip_command)
            
            has_ip = False
            if exit_code == 0:
                # Check for IPv4 address
                if re.search(r'inet \d+\.\d+\.\d+\.\d+', stdout):
                    has_ip = True
                else:
                    metrics.add_error("No IPv4 address configured on interface")
            
            # Configuration acceptance criteria
            expected_speed = self.acceptance_criteria.get('network', {}).get('expected_link_speed_mbps', 1000)
            expected_duplex = self.acceptance_criteria.get('network', {}).get('expected_duplex_mode', 'full')
            min_mtu = self.acceptance_criteria.get('network', {}).get('min_mtu_size', 1500)
            
            metrics.test_successful = (
                link_up and 
                has_ip and
                metrics.link_speed_mbps >= expected_speed and
                metrics.duplex_mode == expected_duplex and
                metrics.mtu_size >= min_mtu
            )
            
        except Exception as e:
            metrics.add_error(f"Configuration test failed: {e}")
            metrics.test_successful = False
            
        finally:
            metrics.end_timestamp = datetime.now()
            metrics.duration_seconds = (metrics.end_timestamp - metrics.start_timestamp).total_seconds()
        
        self.logger.info(f"Configuration test completed: {metrics.link_speed_mbps}Mbps {metrics.duplex_mode} duplex, MTU {metrics.mtu_size}")
        return metrics
    
    def test_stability_stress(self, duration_minutes: int = 10) -> EthernetTestMetrics:
        """
        Test network stability under stress conditions.
        
        Args:
            duration_minutes: Duration to run stress test
            
        Returns:
            EthernetTestMetrics containing stability results  
        """
        metrics = EthernetTestMetrics(test_type=EthernetTestType.STABILITY)
        metrics.start_timestamp = datetime.now()
        
        self.logger.info(f"Starting Ethernet stability test: {duration_minutes} minute stress test")
        
        try:
            # Start continuous ping monitoring
            duration_seconds = duration_minutes * 60
            ping_interval = 1  # 1 second between pings
            
            successful_pings = 0
            total_pings = 0
            connection_drops = 0
            previous_ping_success = True
            
            start_time = time.time()
            
            while (time.time() - start_time) < duration_seconds:
                # Single ping test
                ping_command = f"ping -c 1 -W 2 {self.target_ip}"
                exit_code, stdout, stderr = self._execute_local_command(ping_command, timeout=5)
                
                total_pings += 1
                current_ping_success = (exit_code == 0)
                
                if current_ping_success:
                    successful_pings += 1
                    
                    # Check for connection recovery
                    if not previous_ping_success:
                        self.logger.info("Network connection recovered")
                else:
                    # Check for new connection drop
                    if previous_ping_success:
                        connection_drops += 1
                        metrics.add_error(f"Network connection drop detected at {time.time() - start_time:.1f}s")
                
                previous_ping_success = current_ping_success
                time.sleep(ping_interval)
            
            metrics.connection_drops = connection_drops
            if total_pings > 0:
                metrics.ping_success_rate = successful_pings / total_pings
                metrics.error_rate = (total_pings - successful_pings) / total_pings
            
            # Stability acceptance criteria
            max_connection_drops = self.acceptance_criteria.get('network', {}).get('max_connection_drops', 0)
            min_stability_rate = self.acceptance_criteria.get('network', {}).get('min_stability_rate', 0.99)
            
            metrics.test_successful = (
                metrics.connection_drops <= max_connection_drops and
                metrics.ping_success_rate >= min_stability_rate
            )
            
        except Exception as e:
            metrics.add_error(f"Stability test failed: {e}")
            metrics.test_successful = False
            
        finally:
            metrics.end_timestamp = datetime.now()
            metrics.duration_seconds = (metrics.end_timestamp - metrics.start_timestamp).total_seconds()
        
        self.logger.info(f"Stability test completed: {metrics.ping_success_rate:.1%} stability rate, {metrics.connection_drops} drops")
        return metrics
    
    def run_comprehensive_test_suite(self) -> Dict[str, EthernetTestMetrics]:
        """
        Execute comprehensive Ethernet test suite covering all test categories.
        
        Returns:
            Dictionary mapping test names to their respective metrics
        """
        test_results = {}
        
        self.logger.info("Starting comprehensive Ethernet test suite")
        
        # Execute all test categories
        test_suite = [
            ("connectivity", lambda: self.test_basic_connectivity(ping_count=20)),
            ("configuration", self.test_interface_configuration),
            ("performance", lambda: self.test_performance_iperf(duration_seconds=30)),
            ("stability", lambda: self.test_stability_stress(duration_minutes=5)),
        ]
        
        for test_name, test_function in test_suite:
            try:
                self.logger.info(f"Executing Ethernet test: {test_name}")
                metrics = test_function()
                test_results[test_name] = metrics
                
                status = "PASS" if metrics.test_successful else "FAIL"
                self.logger.info(f"Ethernet test {test_name}: {status}")
                
            except Exception as e:
                self.logger.error(f"Ethernet test {test_name} failed with exception: {e}")
                # Create failure metrics
                failed_metrics = EthernetTestMetrics(test_type=EthernetTestType.CONNECTIVITY)
                failed_metrics.test_successful = False
                failed_metrics.add_error(str(e))
                test_results[test_name] = failed_metrics
        
        # Overall test suite success
        overall_success = all(metrics.test_successful for metrics in test_results.values())
        self.logger.info(f"Ethernet comprehensive test suite completed: {'PASS' if overall_success else 'FAIL'}")
        
        return test_results
    
    def generate_test_report(self, test_results: Dict[str, EthernetTestMetrics]) -> Dict[str, Any]:
        """
        Generate comprehensive Ethernet test report.
        
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
            "network_configuration": {
                "target_ip": self.target_ip,
                "test_host_ip": self.test_host_ip,
                "interface": self.interface,
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
                "ping_success_rate": getattr(metrics, 'ping_success_rate', None),
                "average_ping_latency_ms": getattr(metrics, 'average_ping_latency_ms', None),
                "tcp_throughput_mbps": getattr(metrics, 'tcp_throughput_mbps', None),
                "udp_throughput_mbps": getattr(metrics, 'udp_throughput_mbps', None),
                "link_speed_mbps": getattr(metrics, 'link_speed_mbps', None),
                "duplex_mode": getattr(metrics, 'duplex_mode', None),
                "mtu_size": getattr(metrics, 'mtu_size', None),
                "connection_drops": getattr(metrics, 'connection_drops', None),
            }
        
        return report
