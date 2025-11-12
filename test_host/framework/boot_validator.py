"""
ZCU102 Boot Sequence Validation Framework

This module implements comprehensive boot sequence validation for the ZCU102 embedded
Linux BSP. It provides real-time analysis of the boot process, capturing critical
metrics and ensuring the system meets reliability and performance standards.

The boot validator embodies the "glass box" philosophy by providing complete visibility
into the boot process, enabling proactive identification of issues and regression detection.
"""

import re
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

import serial
from datetime import datetime, timedelta


class BootStage(Enum):
    """Enumeration of distinct boot stages for granular analysis."""
    PRE_BOOT = "pre_boot"
    FSBL = "fsbl"
    UBOOT = "u_boot"
    KERNEL = "kernel"
    USERSPACE = "userspace" 
    LOGIN_READY = "login_ready"
    BOOT_COMPLETE = "boot_complete"
    BOOT_FAILED = "boot_failed"


@dataclass
class BootMetrics:
    """Comprehensive boot metrics for performance and reliability analysis."""
    total_boot_time_seconds: float = 0.0
    stage_durations: Dict[BootStage, float] = field(default_factory=dict)
    boot_messages: List[str] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)
    warning_messages: List[str] = field(default_factory=list)
    final_stage: BootStage = BootStage.PRE_BOOT
    boot_successful: bool = False
    start_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None
    
    def add_stage_duration(self, stage: BootStage, duration: float) -> None:
        """Record the duration of a specific boot stage."""
        self.stage_durations[stage] = duration
        
    def add_message(self, message: str, message_type: str = "info") -> None:
        """Categorize and store boot messages for analysis."""
        if message_type == "error":
            self.error_messages.append(message)
        elif message_type == "warning":
            self.warning_messages.append(message)
        else:
            self.boot_messages.append(message)


class BootValidator:
    """
    Advanced boot sequence validator for ZCU102 embedded Linux systems.
    
    This class provides real-time monitoring and analysis of the boot process,
    capturing detailed metrics and ensuring compliance with acceptance criteria.
    """
    
    # Boot stage detection patterns - tuned for ZCU102 boot sequence
    STAGE_PATTERNS = {
        BootStage.FSBL: [
            r"Xilinx Zynq MP First Stage Boot Loader",
            r"Release \d+\.\d+",
        ],
        BootStage.UBOOT: [
            r"U-Boot \d+\.\d+",
            r"zynqmp>",
            r"Hit any key to stop autoboot",
        ],
        BootStage.KERNEL: [
            r"Starting kernel",
            r"Linux version \d+\.\d+",
            r"Booting Linux on physical CPU",
        ],
        BootStage.USERSPACE: [
            r"systemd.*running in system mode",
            r"Starting.*service",
            r"Reached target",
        ],
        BootStage.LOGIN_READY: [
            r"login:",
            r"Welcome to",
            r"PetaLinux \d+\.\d+",
        ]
    }
    
    # Critical error patterns that indicate boot failure
    ERROR_PATTERNS = [
        r"kernel panic",
        r"Out of memory",
        r"segmentation fault",
        r"Unable to mount root fs",
        r"FATAL:",
        r"BUG:",
    ]
    
    # Warning patterns for quality assessment  
    WARNING_PATTERNS = [
        r"WARNING:",
        r"deprecated",
        r"failed to",
        r"timeout",
        r"retrying",
    ]
    
    def __init__(self, serial_port: str, baud_rate: int = 115200, 
                 timeout: int = 300, acceptance_criteria: Optional[Dict] = None):
        """
        Initialize boot validator with hardware configuration.
        
        Args:
            serial_port: Path to serial device (e.g., /dev/ttyUSB0)
            baud_rate: Serial communication baud rate
            timeout: Maximum boot time before declaring failure
            acceptance_criteria: Dict containing boot acceptance criteria
        """
        self.serial_port = serial_port
        self.baud_rate = baud_rate
        self.timeout = timeout
        self.acceptance_criteria = acceptance_criteria or {}
        
        self.logger = logging.getLogger(__name__)
        self.serial_connection: Optional[serial.Serial] = None
        self.current_stage = BootStage.PRE_BOOT
        self.stage_start_time: Optional[datetime] = None
        
    def __enter__(self):
        """Context manager entry - establish serial connection."""
        try:
            self.serial_connection = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                timeout=1,  # Non-blocking reads with 1s timeout
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
            self.logger.info(f"Serial connection established: {self.serial_port}@{self.baud_rate}")
            return self
        except serial.SerialException as e:
            self.logger.error(f"Failed to open serial port {self.serial_port}: {e}")
            raise
            
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup serial connection."""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            self.logger.info("Serial connection closed")
    
    def _detect_boot_stage(self, line: str) -> Optional[BootStage]:
        """
        Analyze console output to determine current boot stage.
        
        Args:
            line: Console output line to analyze
            
        Returns:
            Detected boot stage or None if no stage change detected
        """
        for stage, patterns in self.STAGE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    return stage
        return None
    
    def _analyze_message_type(self, line: str) -> str:
        """Categorize console messages as error, warning, or info."""
        for pattern in self.ERROR_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                return "error"
                
        for pattern in self.WARNING_PATTERNS:
            if re.search(pattern, line, re.IGNORECASE):
                return "warning"
                
        return "info"
    
    def _transition_to_stage(self, new_stage: BootStage, metrics: BootMetrics) -> None:
        """Handle transition between boot stages, recording timing metrics."""
        now = datetime.now()
        
        # Record duration of previous stage
        if self.current_stage != BootStage.PRE_BOOT and self.stage_start_time:
            stage_duration = (now - self.stage_start_time).total_seconds()
            metrics.add_stage_duration(self.current_stage, stage_duration)
            self.logger.debug(f"Stage {self.current_stage.value} completed in {stage_duration:.2f}s")
        
        # Transition to new stage
        self.current_stage = new_stage
        self.stage_start_time = now
        self.logger.info(f"Boot stage transition: {new_stage.value}")
    
    def validate_boot_sequence(self, power_cycle: bool = True) -> BootMetrics:
        """
        Execute comprehensive boot sequence validation.
        
        This method performs end-to-end boot validation, capturing detailed metrics
        and ensuring the system meets all acceptance criteria defined in the configuration.
        
        Args:
            power_cycle: Whether to power cycle the board before validation
            
        Returns:
            Comprehensive boot metrics for analysis and reporting
            
        Raises:
            TimeoutError: If boot does not complete within specified timeout
            RuntimeError: If critical boot failures are detected
        """
        metrics = BootMetrics()
        boot_start_time = datetime.now()
        metrics.start_timestamp = boot_start_time
        
        self.logger.info("Starting boot sequence validation")
        
        if not self.serial_connection:
            raise RuntimeError("Serial connection not established - use as context manager")
        
        # Clear any existing data in serial buffer
        self.serial_connection.reset_input_buffer()
        
        try:
            # Monitor boot process until completion or timeout
            while True:
                current_time = datetime.now()
                elapsed_time = (current_time - boot_start_time).total_seconds()
                
                # Check for timeout condition
                if elapsed_time > self.timeout:
                    metrics.final_stage = self.current_stage
                    metrics.boot_successful = False
                    self.logger.error(f"Boot timeout after {elapsed_time:.1f}s in stage {self.current_stage.value}")
                    raise TimeoutError(f"Boot process timeout in stage {self.current_stage.value}")
                
                # Read and process console output
                try:
                    line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                    if not line:
                        continue
                        
                    # Log all console output for debugging
                    self.logger.debug(f"Console: {line}")
                    
                    # Analyze message type and store appropriately
                    message_type = self._analyze_message_type(line)
                    metrics.add_message(line, message_type)
                    
                    # Check for critical boot failures
                    if message_type == "error":
                        self.logger.warning(f"Boot error detected: {line}")
                        # Continue monitoring - some errors may be recoverable
                    
                    # Detect boot stage transitions
                    detected_stage = self._detect_boot_stage(line)
                    if detected_stage and detected_stage != self.current_stage:
                        self._transition_to_stage(detected_stage, metrics)
                        metrics.final_stage = detected_stage
                    
                    # Check for boot completion
                    if self.current_stage == BootStage.LOGIN_READY:
                        # Boot sequence completed successfully
                        metrics.end_timestamp = current_time
                        metrics.total_boot_time_seconds = elapsed_time
                        metrics.boot_successful = True
                        metrics.final_stage = BootStage.BOOT_COMPLETE
                        
                        self.logger.info(f"Boot sequence completed successfully in {elapsed_time:.2f}s")
                        break
                        
                except UnicodeDecodeError:
                    # Handle any character encoding issues gracefully
                    self.logger.debug("Unicode decode error in console output - skipping line")
                    continue
                    
        except Exception as e:
            metrics.end_timestamp = datetime.now()
            metrics.total_boot_time_seconds = (metrics.end_timestamp - boot_start_time).total_seconds()
            metrics.boot_successful = False
            metrics.final_stage = BootStage.BOOT_FAILED
            self.logger.error(f"Boot validation failed: {e}")
            raise
        
        # Validate against acceptance criteria
        self._validate_acceptance_criteria(metrics)
        
        return metrics
    
    def _validate_acceptance_criteria(self, metrics: BootMetrics) -> None:
        """
        Validate boot metrics against defined acceptance criteria.
        
        Args:
            metrics: Boot metrics to validate
            
        Raises:
            AssertionError: If any acceptance criteria are not met
        """
        criteria = self.acceptance_criteria.get('boot', {})
        
        # Validate maximum boot time
        max_boot_time = criteria.get('max_boot_time_seconds', 60)
        if metrics.total_boot_time_seconds > max_boot_time:
            raise AssertionError(
                f"Boot time {metrics.total_boot_time_seconds:.2f}s exceeds maximum {max_boot_time}s"
            )
        
        # Validate required boot messages are present
        required_messages = criteria.get('required_boot_messages', [])
        all_messages = ' '.join(metrics.boot_messages)
        for required_msg in required_messages:
            if required_msg not in all_messages:
                raise AssertionError(f"Required boot message not found: {required_msg}")
        
        # Validate forbidden messages are not present
        forbidden_messages = criteria.get('forbidden_boot_messages', [])
        for forbidden_msg in forbidden_messages:
            if forbidden_msg in all_messages:
                raise AssertionError(f"Forbidden boot message detected: {forbidden_msg}")
        
        # Validate error count is within acceptable limits
        max_errors = criteria.get('max_error_count', 0)
        if len(metrics.error_messages) > max_errors:
            raise AssertionError(
                f"Boot error count {len(metrics.error_messages)} exceeds maximum {max_errors}"
            )
        
        self.logger.info("All boot acceptance criteria validated successfully")
    
    def generate_boot_report(self, metrics: BootMetrics) -> Dict:
        """
        Generate comprehensive boot validation report.
        
        Args:
            metrics: Boot metrics to report on
            
        Returns:
            Dictionary containing formatted boot report
        """
        report = {
            "validation_summary": {
                "boot_successful": metrics.boot_successful,
                "total_boot_time_seconds": metrics.total_boot_time_seconds,
                "final_stage": metrics.final_stage.value,
                "start_time": metrics.start_timestamp.isoformat() if metrics.start_timestamp else None,
                "end_time": metrics.end_timestamp.isoformat() if metrics.end_timestamp else None,
            },
            "stage_breakdown": {
                stage.value: duration 
                for stage, duration in metrics.stage_durations.items()
            },
            "message_analysis": {
                "total_messages": len(metrics.boot_messages),
                "error_count": len(metrics.error_messages),
                "warning_count": len(metrics.warning_messages),
                "errors": metrics.error_messages,
                "warnings": metrics.warning_messages,
            },
            "acceptance_criteria": {
                "criteria_met": metrics.boot_successful,
                "max_boot_time_seconds": self.acceptance_criteria.get('boot', {}).get('max_boot_time_seconds', 'N/A'),
                "actual_boot_time_seconds": metrics.total_boot_time_seconds,
            }
        }
        
        return report
