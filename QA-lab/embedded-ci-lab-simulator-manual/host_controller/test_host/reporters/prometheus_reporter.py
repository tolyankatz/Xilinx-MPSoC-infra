"""
Prometheus Metrics Reporter

This module provides comprehensive metrics reporting to Prometheus for real-time
monitoring and historical analysis of ZCU102 test execution. It supports both
direct Prometheus server integration and Pushgateway for batch job metrics.

The metrics enable the "glass box" philosophy by providing complete visibility
into test performance, trends, and system behavior.
"""

import time
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from prometheus_client import (
    CollectorRegistry, Counter, Gauge, Histogram, Summary,
    push_to_gateway, pushadd_to_gateway, delete_from_gateway
)


class MetricType(Enum):
    """Enumeration of supported metric types."""
    COUNTER = "counter"
    GAUGE = "gauge" 
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class TestMetric:
    """Structure for test metrics with metadata."""
    name: str
    value: Union[float, int]
    labels: Dict[str, str]
    metric_type: MetricType = MetricType.GAUGE
    help_text: str = ""
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class PrometheusReporter:
    """
    Advanced Prometheus metrics reporter for ZCU102 test framework.
    
    This class provides comprehensive metrics collection and reporting capabilities,
    supporting both real-time streaming and batch reporting patterns.
    """
    
    def __init__(self, pushgateway_url: str, job_name: str = "zcu102_tests",
                 instance_id: Optional[str] = None, namespace: str = "zcu102"):
        """
        Initialize Prometheus reporter.
        
        Args:
            pushgateway_url: URL of Prometheus Pushgateway
            job_name: Job name for metrics grouping
            instance_id: Unique instance identifier
            namespace: Metric namespace prefix
        """
        self.pushgateway_url = pushgateway_url
        self.job_name = job_name
        self.instance_id = instance_id or f"test_host_{int(time.time())}"
        self.namespace = namespace
        
        self.logger = logging.getLogger(__name__)
        self.registry = CollectorRegistry()
        
        # Pre-defined metrics for common test scenarios
        self.metrics = self._initialize_standard_metrics()
        
        self.logger.info(f"Prometheus reporter initialized: {pushgateway_url}")
    
    def _initialize_standard_metrics(self) -> Dict[str, Any]:
        """Initialize standard metrics used across all test types."""
        
        metrics = {}
        
        # Test execution metrics
        metrics['test_duration'] = Histogram(
            f'{self.namespace}_test_duration_seconds',
            'Duration of test execution in seconds',
            ['test_type', 'test_name', 'board_type', 'build_version'],
            registry=self.registry,
            buckets=[1, 5, 10, 30, 60, 120, 300, 600, 1800]
        )
        
        metrics['test_success'] = Counter(
            f'{self.namespace}_test_success_total',
            'Total number of successful tests',
            ['test_type', 'test_name', 'board_type', 'build_version'],
            registry=self.registry
        )
        
        metrics['test_failure'] = Counter(
            f'{self.namespace}_test_failure_total', 
            'Total number of failed tests',
            ['test_type', 'test_name', 'board_type', 'build_version', 'failure_reason'],
            registry=self.registry
        )
        
        # Boot sequence metrics
        metrics['boot_time'] = Histogram(
            f'{self.namespace}_boot_time_seconds',
            'Boot sequence duration in seconds',
            ['board_type', 'build_version', 'boot_stage'],
            registry=self.registry,
            buckets=[5, 10, 15, 20, 30, 45, 60, 90, 120]
        )
        
        metrics['boot_stage_duration'] = Gauge(
            f'{self.namespace}_boot_stage_duration_seconds',
            'Duration of individual boot stages',
            ['board_type', 'build_version', 'boot_stage'],
            registry=self.registry
        )
        
        # Network performance metrics
        metrics['network_throughput'] = Gauge(
            f'{self.namespace}_network_throughput_mbps',
            'Network throughput in Mbps',
            ['board_type', 'build_version', 'protocol', 'direction'],
            registry=self.registry
        )
        
        metrics['network_latency'] = Histogram(
            f'{self.namespace}_network_latency_milliseconds',
            'Network latency in milliseconds',
            ['board_type', 'build_version', 'protocol'],
            registry=self.registry,
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0]
        )
        
        metrics['packet_loss'] = Gauge(
            f'{self.namespace}_packet_loss_percentage',
            'Packet loss percentage',
            ['board_type', 'build_version', 'test_duration'],
            registry=self.registry
        )
        
        # UART communication metrics
        metrics['uart_throughput'] = Gauge(
            f'{self.namespace}_uart_throughput_bps',
            'UART throughput in bits per second',
            ['board_type', 'build_version', 'baud_rate'],
            registry=self.registry
        )
        
        metrics['uart_error_rate'] = Gauge(
            f'{self.namespace}_uart_error_rate',
            'UART communication error rate',
            ['board_type', 'build_version', 'error_type'],
            registry=self.registry
        )
        
        # Hardware control metrics
        metrics['power_cycle_duration'] = Histogram(
            f'{self.namespace}_power_cycle_duration_seconds',
            'Power cycle operation duration',
            ['board_type', 'power_controller_type'],
            registry=self.registry,
            buckets=[1, 2, 5, 10, 15, 30, 60]
        )
        
        metrics['jtag_operation_duration'] = Histogram(
            f'{self.namespace}_jtag_operation_duration_seconds',
            'JTAG operation duration',
            ['board_type', 'operation_type', 'cable_type'],
            registry=self.registry,
            buckets=[1, 5, 10, 30, 60, 120, 300]
        )
        
        # System resource metrics
        metrics['memory_usage'] = Gauge(
            f'{self.namespace}_memory_usage_bytes',
            'System memory usage in bytes',
            ['board_type', 'build_version', 'memory_type'],
            registry=self.registry
        )
        
        metrics['cpu_usage'] = Gauge(
            f'{self.namespace}_cpu_usage_percentage',
            'CPU usage percentage',
            ['board_type', 'build_version', 'cpu_core'],
            registry=self.registry
        )
        
        metrics['temperature'] = Gauge(
            f'{self.namespace}_temperature_celsius',
            'System temperature in Celsius',
            ['board_type', 'build_version', 'sensor_location'],
            registry=self.registry
        )
        
        return metrics
    
    def record_test_execution(self, test_name: str, test_type: str, 
                            duration_seconds: float, success: bool,
                            board_type: str = "zcu102", build_version: str = "unknown",
                            failure_reason: Optional[str] = None) -> None:
        """
        Record test execution metrics.
        
        Args:
            test_name: Name of the executed test
            test_type: Category/type of test
            duration_seconds: Test execution duration
            success: Whether test passed or failed
            board_type: Target board type
            build_version: BSP build version being tested
            failure_reason: Reason for failure (if applicable)
        """
        labels = {
            'test_type': test_type,
            'test_name': test_name,
            'board_type': board_type,
            'build_version': build_version
        }
        
        # Record duration
        self.metrics['test_duration'].labels(**labels).observe(duration_seconds)
        
        # Record success or failure
        if success:
            self.metrics['test_success'].labels(**labels).inc()
        else:
            failure_labels = labels.copy()
            failure_labels['failure_reason'] = failure_reason or 'unknown'
            self.metrics['test_failure'].labels(**failure_labels).inc()
        
        self.logger.debug(f"Recorded test execution: {test_name} ({'PASS' if success else 'FAIL'})")
    
    def record_boot_metrics(self, total_boot_time: float, stage_durations: Dict[str, float],
                          board_type: str = "zcu102", build_version: str = "unknown") -> None:
        """
        Record boot sequence performance metrics.
        
        Args:
            total_boot_time: Total boot sequence duration
            stage_durations: Duration of individual boot stages
            board_type: Target board type
            build_version: BSP build version
        """
        base_labels = {
            'board_type': board_type,
            'build_version': build_version
        }
        
        # Record total boot time
        total_labels = base_labels.copy()
        total_labels['boot_stage'] = 'total'
        self.metrics['boot_time'].labels(**total_labels).observe(total_boot_time)
        
        # Record individual stage durations
        for stage, duration in stage_durations.items():
            stage_labels = base_labels.copy()
            stage_labels['boot_stage'] = stage
            
            self.metrics['boot_time'].labels(**stage_labels).observe(duration)
            self.metrics['boot_stage_duration'].labels(**stage_labels).set(duration)
        
        self.logger.debug(f"Recorded boot metrics: {total_boot_time:.2f}s total, {len(stage_durations)} stages")
    
    def record_network_metrics(self, tcp_throughput: Optional[float] = None,
                             udp_throughput: Optional[float] = None,
                             ping_latency: Optional[float] = None,
                             packet_loss: Optional[float] = None,
                             board_type: str = "zcu102", 
                             build_version: str = "unknown") -> None:
        """
        Record network performance metrics.
        
        Args:
            tcp_throughput: TCP throughput in Mbps
            udp_throughput: UDP throughput in Mbps  
            ping_latency: Average ping latency in milliseconds
            packet_loss: Packet loss percentage
            board_type: Target board type
            build_version: BSP build version
        """
        base_labels = {
            'board_type': board_type,
            'build_version': build_version
        }
        
        if tcp_throughput is not None:
            tcp_labels = base_labels.copy()
            tcp_labels.update({'protocol': 'tcp', 'direction': 'download'})
            self.metrics['network_throughput'].labels(**tcp_labels).set(tcp_throughput)
        
        if udp_throughput is not None:
            udp_labels = base_labels.copy()
            udp_labels.update({'protocol': 'udp', 'direction': 'download'})
            self.metrics['network_throughput'].labels(**udp_labels).set(udp_throughput)
        
        if ping_latency is not None:
            latency_labels = base_labels.copy()
            latency_labels['protocol'] = 'icmp'
            self.metrics['network_latency'].labels(**latency_labels).observe(ping_latency)
        
        if packet_loss is not None:
            loss_labels = base_labels.copy()
            loss_labels['test_duration'] = '30s'  # Could be parameterized
            self.metrics['packet_loss'].labels(**loss_labels).set(packet_loss)
        
        self.logger.debug("Recorded network performance metrics")
    
    def record_uart_metrics(self, throughput_bps: Optional[float] = None,
                          error_rate: Optional[float] = None,
                          baud_rate: int = 115200,
                          board_type: str = "zcu102",
                          build_version: str = "unknown") -> None:
        """
        Record UART communication metrics.
        
        Args:
            throughput_bps: UART throughput in bits per second
            error_rate: Communication error rate (0.0 to 1.0)
            baud_rate: Configured baud rate
            board_type: Target board type
            build_version: BSP build version
        """
        base_labels = {
            'board_type': board_type,
            'build_version': build_version,
            'baud_rate': str(baud_rate)
        }
        
        if throughput_bps is not None:
            self.metrics['uart_throughput'].labels(**base_labels).set(throughput_bps)
        
        if error_rate is not None:
            error_labels = base_labels.copy()
            error_labels['error_type'] = 'communication'
            self.metrics['uart_error_rate'].labels(**error_labels).set(error_rate)
        
        self.logger.debug("Recorded UART communication metrics")
    
    def record_hardware_control_metrics(self, power_cycle_duration: Optional[float] = None,
                                      jtag_operation_duration: Optional[float] = None,
                                      jtag_operation_type: Optional[str] = None,
                                      board_type: str = "zcu102") -> None:
        """
        Record hardware control operation metrics.
        
        Args:
            power_cycle_duration: Power cycle duration in seconds
            jtag_operation_duration: JTAG operation duration in seconds
            jtag_operation_type: Type of JTAG operation performed
            board_type: Target board type
        """
        if power_cycle_duration is not None:
            power_labels = {
                'board_type': board_type,
                'power_controller_type': 'smart_plug'  # Could be parameterized
            }
            self.metrics['power_cycle_duration'].labels(**power_labels).observe(power_cycle_duration)
        
        if jtag_operation_duration is not None and jtag_operation_type is not None:
            jtag_labels = {
                'board_type': board_type,
                'operation_type': jtag_operation_type,
                'cable_type': 'digilent_hs2'  # Could be parameterized
            }
            self.metrics['jtag_operation_duration'].labels(**jtag_labels).observe(jtag_operation_duration)
        
        self.logger.debug("Recorded hardware control metrics")
    
    def record_system_metrics(self, memory_usage_mb: Optional[float] = None,
                            cpu_usage_percent: Optional[float] = None,
                            temperature_celsius: Optional[float] = None,
                            board_type: str = "zcu102",
                            build_version: str = "unknown") -> None:
        """
        Record system resource metrics.
        
        Args:
            memory_usage_mb: Memory usage in megabytes
            cpu_usage_percent: CPU usage percentage (0-100)
            temperature_celsius: System temperature in Celsius
            board_type: Target board type
            build_version: BSP build version
        """
        base_labels = {
            'board_type': board_type,
            'build_version': build_version
        }
        
        if memory_usage_mb is not None:
            memory_labels = base_labels.copy()
            memory_labels['memory_type'] = 'physical'
            self.metrics['memory_usage'].labels(**memory_labels).set(memory_usage_mb * 1024 * 1024)  # Convert to bytes
        
        if cpu_usage_percent is not None:
            cpu_labels = base_labels.copy()
            cpu_labels['cpu_core'] = 'average'
            self.metrics['cpu_usage'].labels(**cpu_labels).set(cpu_usage_percent)
        
        if temperature_celsius is not None:
            temp_labels = base_labels.copy()
            temp_labels['sensor_location'] = 'soc'
            self.metrics['temperature'].labels(**temp_labels).set(temperature_celsius)
        
        self.logger.debug("Recorded system resource metrics")
    
    def push_metrics(self, grouping_key: Optional[Dict[str, str]] = None) -> bool:
        """
        Push all collected metrics to Prometheus Pushgateway.
        
        Args:
            grouping_key: Additional grouping labels for metrics
            
        Returns:
            True if push operation succeeded
        """
        try:
            # Prepare grouping key
            gateway_labels = {
                'job': self.job_name,
                'instance': self.instance_id
            }
            
            if grouping_key:
                gateway_labels.update(grouping_key)
            
            # Push metrics to gateway
            push_to_gateway(
                gateway=self.pushgateway_url,
                job=self.job_name,
                registry=self.registry,
                grouping_key=gateway_labels
            )
            
            self.logger.info(f"Successfully pushed metrics to Prometheus Pushgateway: {self.pushgateway_url}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to push metrics to Prometheus: {e}")
            return False
    
    def clear_metrics(self, grouping_key: Optional[Dict[str, str]] = None) -> bool:
        """
        Clear metrics from Prometheus Pushgateway.
        
        Args:
            grouping_key: Grouping labels to identify metrics to clear
            
        Returns:
            True if clear operation succeeded
        """
        try:
            gateway_labels = {
                'job': self.job_name,
                'instance': self.instance_id
            }
            
            if grouping_key:
                gateway_labels.update(grouping_key)
            
            delete_from_gateway(
                gateway=self.pushgateway_url,
                job=self.job_name,
                grouping_key=gateway_labels
            )
            
            self.logger.info("Successfully cleared metrics from Prometheus Pushgateway")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to clear metrics from Prometheus: {e}")
            return False
    
    def push_custom_metric(self, metric: TestMetric) -> bool:
        """
        Push a single custom metric to Prometheus.
        
        Args:
            metric: TestMetric containing metric data
            
        Returns:
            True if push operation succeeded
        """
        try:
            # Create a temporary registry for the custom metric
            temp_registry = CollectorRegistry()
            
            # Create appropriate metric type
            if metric.metric_type == MetricType.GAUGE:
                prometheus_metric = Gauge(
                    f'{self.namespace}_{metric.name}',
                    metric.help_text or f'Custom gauge metric: {metric.name}',
                    list(metric.labels.keys()),
                    registry=temp_registry
                )
                prometheus_metric.labels(**metric.labels).set(metric.value)
                
            elif metric.metric_type == MetricType.COUNTER:
                prometheus_metric = Counter(
                    f'{self.namespace}_{metric.name}',
                    metric.help_text or f'Custom counter metric: {metric.name}',
                    list(metric.labels.keys()),
                    registry=temp_registry
                )
                prometheus_metric.labels(**metric.labels).inc(metric.value)
            
            else:
                self.logger.error(f"Unsupported custom metric type: {metric.metric_type}")
                return False
            
            # Push the custom metric
            gateway_labels = {
                'job': self.job_name,
                'instance': self.instance_id
            }
            
            pushadd_to_gateway(
                gateway=self.pushgateway_url,
                job=self.job_name,
                registry=temp_registry,
                grouping_key=gateway_labels
            )
            
            self.logger.debug(f"Successfully pushed custom metric: {metric.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to push custom metric {metric.name}: {e}")
            return False
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get summary of all registered metrics.
        
        Returns:
            Dictionary containing metrics information
        """
        summary = {
            'namespace': self.namespace,
            'job_name': self.job_name,
            'instance_id': self.instance_id,
            'pushgateway_url': self.pushgateway_url,
            'registered_metrics': list(self.metrics.keys()),
            'metric_count': len(self.metrics)
        }
        
        return summary


def create_prometheus_reporter(pushgateway_url: str, **kwargs) -> PrometheusReporter:
    """
    Factory function to create Prometheus reporter instance.
    
    Args:
        pushgateway_url: URL of Prometheus Pushgateway
        **kwargs: Additional configuration parameters
        
    Returns:
        Configured Prometheus reporter instance
    """
    return PrometheusReporter(pushgateway_url=pushgateway_url, **kwargs)
