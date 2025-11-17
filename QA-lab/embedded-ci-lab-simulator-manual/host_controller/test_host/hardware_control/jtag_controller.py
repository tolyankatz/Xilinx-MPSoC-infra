"""
ZCU102 JTAG Control Interface

This module provides comprehensive JTAG control capabilities for the ZCU102 embedded
system, enabling automated firmware flashing, device recovery, and diagnostic operations.
It supports Xilinx development tools and programming cables for reliable board recovery.

The JTAG controller is critical for test automation, providing the ability to recover
from failed boot scenarios and ensure consistent test starting conditions.
"""

import os
import subprocess
import time
import logging
import tempfile
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
from pathlib import Path


class JTAGOperation(Enum):
    """Enumeration of JTAG operations."""
    FLASH_BOOTLOADER = "flash_bootloader"
    FLASH_FPGA = "flash_fpga"
    DEVICE_DETECT = "device_detect"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    DEVICE_RESET = "device_reset"


class JTAGCableType(Enum):
    """Enumeration of supported JTAG cable types."""
    PLATFORM_CABLE = "platform_cable"
    DIGILENT_HS2 = "digilent_hs2"
    DIGILENT_HS3 = "digilent_hs3"
    USB_BLASTER = "usb_blaster"


@dataclass
class JTAGDevice:
    """Information about a detected JTAG device."""
    position: int
    idcode: str
    part_name: str
    manufacturer: str
    description: Optional[str] = None


@dataclass
class JTAGOperationResult:
    """Result of a JTAG operation with comprehensive status information."""
    operation: JTAGOperation
    success: bool
    duration_seconds: float
    command_output: str
    error_message: Optional[str] = None
    devices_detected: List[JTAGDevice] = None
    start_timestamp: Optional[datetime] = None
    end_timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.devices_detected is None:
            self.devices_detected = []


class JTAGControllerBase(ABC):
    """
    Abstract base class for JTAG control implementations.
    
    This interface ensures consistent JTAG operations across different
    programming cable types and Xilinx tool versions.
    """
    
    def __init__(self, cable_type: JTAGCableType, device_part: str, 
                 vivado_path: Optional[str] = None, **kwargs):
        """
        Initialize JTAG controller base class.
        
        Args:
            cable_type: Type of JTAG programming cable
            device_part: Target device part number (e.g., 'xczu9eg')
            vivado_path: Path to Vivado installation
            **kwargs: Implementation-specific configuration parameters
        """
        self.cable_type = cable_type
        self.device_part = device_part
        self.vivado_path = vivado_path or self._find_vivado_installation()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Validate Vivado installation
        if not self.vivado_path or not Path(self.vivado_path).exists():
            raise RuntimeError(f"Vivado installation not found at: {self.vivado_path}")
            
    @abstractmethod
    def detect_devices(self) -> JTAGOperationResult:
        """Detect JTAG devices in the chain."""
        pass
        
    @abstractmethod
    def flash_image(self, image_path: str, target: str = "fpga") -> JTAGOperationResult:
        """Flash firmware image to device."""
        pass
        
    def _find_vivado_installation(self) -> Optional[str]:
        """Automatically locate Vivado installation."""
        common_paths = [
            "/opt/Xilinx/Vivado/2023.1/bin/vivado",
            "/opt/Xilinx/Vivado/2022.2/bin/vivado", 
            "/tools/Xilinx/Vivado/2023.1/bin/vivado",
            "C:/Xilinx/Vivado/2023.1/bin/vivado.bat",
            "C:/Xilinx/Vivado/2022.2/bin/vivado.bat",
        ]
        
        for path in common_paths:
            if Path(path).exists():
                return str(Path(path).parent.parent)
                
        # Try to find via environment variables
        xilinx_vivado = os.environ.get('XILINX_VIVADO')
        if xilinx_vivado and Path(xilinx_vivado).exists():
            return xilinx_vivado
            
        return None
    
    def _execute_command(self, command: List[str], timeout: int = 300) -> Tuple[int, str, str]:
        """
        Execute system command with timeout and logging.
        
        Args:
            command: Command and arguments to execute
            timeout: Command timeout in seconds
            
        Returns:
            Tuple of (return_code, stdout, stderr)
        """
        self.logger.debug(f"Executing command: {' '.join(command)}")
        
        try:
            result = subprocess.run(
                command,
                timeout=timeout,
                capture_output=True,
                text=True,
                cwd=Path(self.vivado_path).parent if self.vivado_path else None
            )
            
            self.logger.debug(f"Command return code: {result.returncode}")
            if result.stdout:
                self.logger.debug(f"Command stdout: {result.stdout}")
            if result.stderr:
                self.logger.debug(f"Command stderr: {result.stderr}")
                
            return result.returncode, result.stdout, result.stderr
            
        except subprocess.TimeoutExpired:
            self.logger.error(f"Command timeout after {timeout} seconds")
            return -1, "", "Command timeout"
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            return -1, "", str(e)


class VivadoJTAGController(JTAGControllerBase):
    """
    Vivado-based JTAG controller for Xilinx devices.
    
    This implementation uses Vivado's built-in JTAG capabilities through
    TCL scripts for reliable device programming and control.
    """
    
    def __init__(self, cable_type: JTAGCableType, device_part: str, 
                 vivado_path: Optional[str] = None, chain_position: int = 1, **kwargs):
        """
        Initialize Vivado JTAG controller.
        
        Args:
            cable_type: Type of JTAG programming cable
            device_part: Target device part number
            vivado_path: Path to Vivado installation 
            chain_position: Position of target device in JTAG chain
            **kwargs: Additional configuration parameters
        """
        super().__init__(cable_type, device_part, vivado_path, **kwargs)
        self.chain_position = chain_position
        self.vivado_executable = self._get_vivado_executable()
        
    def _get_vivado_executable(self) -> str:
        """Get platform-specific Vivado executable path."""
        if os.name == 'nt':  # Windows
            return str(Path(self.vivado_path) / "bin" / "vivado.bat")
        else:  # Linux/Unix
            return str(Path(self.vivado_path) / "bin" / "vivado")
    
    def detect_devices(self) -> JTAGOperationResult:
        """
        Detect JTAG devices using Vivado hardware manager.
        
        Returns:
            JTAGOperationResult containing detected device information
        """
        operation_start = datetime.now()
        
        # Create TCL script for device detection
        tcl_script = f"""
        # Open hardware manager
        open_hw_manager
        
        # Connect to hardware server
        connect_hw_server
        
        # Open hardware target
        open_hw_target
        
        # Get hardware devices
        set devices [get_hw_devices]
        
        # Print device information
        foreach device $devices {{
            puts "DEVICE_INFO: [get_property PROGRAM.HW_DEVICE_PART $device] [get_property PROGRAM.HW_DEVICE_IDCODE $device]"
        }}
        
        # Close connections
        close_hw_target
        disconnect_hw_server
        close_hw_manager
        
        exit
        """
        
        try:
            # Write TCL script to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.tcl', delete=False) as tcl_file:
                tcl_file.write(tcl_script)
                tcl_path = tcl_file.name
            
            # Execute Vivado with TCL script
            command = [
                self.vivado_executable,
                "-mode", "batch",
                "-source", tcl_path,
                "-nojournal",
                "-nolog"
            ]
            
            return_code, stdout, stderr = self._execute_command(command, timeout=120)
            
            # Parse device information from output
            devices = []
            for line in stdout.splitlines():
                if line.startswith("DEVICE_INFO:"):
                    parts = line.split()
                    if len(parts) >= 3:
                        device = JTAGDevice(
                            position=len(devices) + 1,
                            idcode=parts[2] if len(parts) > 2 else "unknown",
                            part_name=parts[1] if len(parts) > 1 else "unknown",
                            manufacturer="Xilinx"
                        )
                        devices.append(device)
            
            success = return_code == 0 and len(devices) > 0
            error_message = stderr if not success and stderr else None
            
            result = JTAGOperationResult(
                operation=JTAGOperation.DEVICE_DETECT,
                success=success,
                duration_seconds=(datetime.now() - operation_start).total_seconds(),
                command_output=stdout,
                error_message=error_message,
                devices_detected=devices,
                start_timestamp=operation_start,
                end_timestamp=datetime.now()
            )
            
            if success:
                self.logger.info(f"JTAG device detection successful: {len(devices)} devices found")
            else:
                self.logger.error(f"JTAG device detection failed: {error_message}")
                
            return result
            
        except Exception as e:
            result = JTAGOperationResult(
                operation=JTAGOperation.DEVICE_DETECT,
                success=False,
                duration_seconds=(datetime.now() - operation_start).total_seconds(),
                command_output="",
                error_message=str(e),
                start_timestamp=operation_start,
                end_timestamp=datetime.now()
            )
            self.logger.error(f"JTAG device detection exception: {e}")
            return result
        finally:
            # Clean up temporary TCL script
            try:
                os.unlink(tcl_path)
            except:
                pass
    
    def flash_image(self, image_path: str, target: str = "fpga") -> JTAGOperationResult:
        """
        Flash firmware image to target device via JTAG.
        
        Args:
            image_path: Path to firmware image file
            target: Target type ('fpga' for bitstream, 'boot' for bootloader)
            
        Returns:
            JTAGOperationResult containing programming status
        """
        operation_start = datetime.now()
        
        if not Path(image_path).exists():
            result = JTAGOperationResult(
                operation=JTAGOperation.FLASH_BOOTLOADER if target == "boot" else JTAGOperation.FLASH_FPGA,
                success=False,
                duration_seconds=0,
                command_output="",
                error_message=f"Image file not found: {image_path}",
                start_timestamp=operation_start,
                end_timestamp=datetime.now()
            )
            return result
        
        # Determine programming method based on target and file extension
        file_extension = Path(image_path).suffix.lower()
        
        if target == "fpga" or file_extension in ['.bit', '.bin']:
            return self._flash_fpga_bitstream(image_path, operation_start)
        elif target == "boot" or file_extension in ['.elf', '.mcs']:
            return self._flash_boot_image(image_path, operation_start)
        else:
            result = JTAGOperationResult(
                operation=JTAGOperation.FLASH_BOOTLOADER,
                success=False,
                duration_seconds=0,
                command_output="",
                error_message=f"Unsupported image type for target '{target}': {file_extension}",
                start_timestamp=operation_start,
                end_timestamp=datetime.now()
            )
            return result
    
    def _flash_fpga_bitstream(self, bitstream_path: str, operation_start: datetime) -> JTAGOperationResult:
        """Flash FPGA bitstream via JTAG."""
        
        tcl_script = f"""
        # Open hardware manager
        open_hw_manager
        
        # Connect to hardware server
        connect_hw_server
        
        # Open hardware target
        open_hw_target
        
        # Get the device (assume first device if multiple)
        set device [lindex [get_hw_devices] {self.chain_position - 1}]
        
        # Set bitstream file
        set_property PROGRAM.FILE {{{bitstream_path}}} $device
        
        # Program the device
        program_hw_devices $device
        
        # Verify programming
        if {{[get_property PROGRAM.HW_DEVICE_STATE $device] eq "PROGRAMMED"}} {{
            puts "PROGRAMMING_SUCCESS: Device programmed successfully"
        }} else {{
            puts "PROGRAMMING_FAILED: Device programming failed" 
        }}
        
        # Close connections
        close_hw_target
        disconnect_hw_server  
        close_hw_manager
        
        exit
        """
        
        try:
            # Write and execute TCL script
            with tempfile.NamedTemporaryFile(mode='w', suffix='.tcl', delete=False) as tcl_file:
                tcl_file.write(tcl_script)
                tcl_path = tcl_file.name
            
            command = [
                self.vivado_executable,
                "-mode", "batch",
                "-source", tcl_path,
                "-nojournal", 
                "-nolog"
            ]
            
            return_code, stdout, stderr = self._execute_command(command, timeout=300)
            
            # Check for programming success
            success = "PROGRAMMING_SUCCESS" in stdout and return_code == 0
            error_message = stderr if not success and stderr else None
            
            if not success and "PROGRAMMING_FAILED" in stdout:
                error_message = "Device programming verification failed"
            
            result = JTAGOperationResult(
                operation=JTAGOperation.FLASH_FPGA,
                success=success,
                duration_seconds=(datetime.now() - operation_start).total_seconds(),
                command_output=stdout,
                error_message=error_message,
                start_timestamp=operation_start,
                end_timestamp=datetime.now()
            )
            
            if success:
                self.logger.info(f"FPGA programming successful: {bitstream_path}")
            else:
                self.logger.error(f"FPGA programming failed: {error_message}")
                
            return result
            
        except Exception as e:
            result = JTAGOperationResult(
                operation=JTAGOperation.FLASH_FPGA,
                success=False,
                duration_seconds=(datetime.now() - operation_start).total_seconds(),
                command_output="",
                error_message=str(e),
                start_timestamp=operation_start,
                end_timestamp=datetime.now()
            )
            self.logger.error(f"FPGA programming exception: {e}")
            return result
        finally:
            try:
                os.unlink(tcl_path)
            except:
                pass
    
    def _flash_boot_image(self, boot_image_path: str, operation_start: datetime) -> JTAGOperationResult:
        """Flash boot image (FSBL/U-Boot) via JTAG."""
        
        tcl_script = f"""
        # Open hardware manager
        open_hw_manager
        
        # Connect to hardware server  
        connect_hw_server
        
        # Open hardware target
        open_hw_target
        
        # Get the device
        set device [lindex [get_hw_devices] {self.chain_position - 1}]
        
        # Configure for boot image programming
        set_property PROGRAM.FILE {{{boot_image_path}}} $device
        
        # Set boot mode (assuming JTAG boot)
        set_property PROGRAM.ADDRESS_RANGE {{use_file}} $device
        set_property PROGRAM.UNUSED_PIN_TERMINATION {{pull-none}} $device
        
        # Program the boot image
        program_hw_devices $device
        
        # Reset the device to start boot sequence
        reset_hw_device $device
        
        puts "BOOT_PROGRAMMING_COMPLETE: Boot image programmed and device reset"
        
        # Close connections
        close_hw_target
        disconnect_hw_server
        close_hw_manager
        
        exit
        """
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.tcl', delete=False) as tcl_file:
                tcl_file.write(tcl_script)
                tcl_path = tcl_file.name
            
            command = [
                self.vivado_executable,
                "-mode", "batch", 
                "-source", tcl_path,
                "-nojournal",
                "-nolog"
            ]
            
            return_code, stdout, stderr = self._execute_command(command, timeout=300)
            
            success = "BOOT_PROGRAMMING_COMPLETE" in stdout and return_code == 0
            error_message = stderr if not success and stderr else None
            
            result = JTAGOperationResult(
                operation=JTAGOperation.FLASH_BOOTLOADER,
                success=success,
                duration_seconds=(datetime.now() - operation_start).total_seconds(),
                command_output=stdout,
                error_message=error_message,
                start_timestamp=operation_start,
                end_timestamp=datetime.now()
            )
            
            if success:
                self.logger.info(f"Boot image programming successful: {boot_image_path}")
            else:
                self.logger.error(f"Boot image programming failed: {error_message}")
                
            return result
            
        except Exception as e:
            result = JTAGOperationResult(
                operation=JTAGOperation.FLASH_BOOTLOADER,
                success=False,
                duration_seconds=(datetime.now() - operation_start).total_seconds(),
                command_output="",
                error_message=str(e),
                start_timestamp=operation_start,
                end_timestamp=datetime.now()
            )
            self.logger.error(f"Boot image programming exception: {e}")
            return result
        finally:
            try:
                os.unlink(tcl_path)
            except:
                pass
    
    def reset_device(self) -> JTAGOperationResult:
        """
        Reset target device via JTAG.
        
        Returns:
            JTAGOperationResult containing reset operation status
        """
        operation_start = datetime.now()
        
        tcl_script = f"""
        # Open hardware manager
        open_hw_manager
        connect_hw_server
        open_hw_target
        
        # Get the device and reset it
        set device [lindex [get_hw_devices] {self.chain_position - 1}]
        reset_hw_device $device
        
        puts "DEVICE_RESET_COMPLETE: Device reset via JTAG"
        
        # Close connections
        close_hw_target
        disconnect_hw_server
        close_hw_manager
        
        exit
        """
        
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.tcl', delete=False) as tcl_file:
                tcl_file.write(tcl_script)
                tcl_path = tcl_file.name
            
            command = [
                self.vivado_executable,
                "-mode", "batch",
                "-source", tcl_path,
                "-nojournal",
                "-nolog"
            ]
            
            return_code, stdout, stderr = self._execute_command(command, timeout=60)
            
            success = "DEVICE_RESET_COMPLETE" in stdout and return_code == 0
            error_message = stderr if not success and stderr else None
            
            result = JTAGOperationResult(
                operation=JTAGOperation.DEVICE_RESET,
                success=success,
                duration_seconds=(datetime.now() - operation_start).total_seconds(),
                command_output=stdout,
                error_message=error_message,
                start_timestamp=operation_start,
                end_timestamp=datetime.now()
            )
            
            if success:
                self.logger.info("Device reset via JTAG successful")
            else:
                self.logger.error(f"Device reset via JTAG failed: {error_message}")
                
            return result
            
        except Exception as e:
            result = JTAGOperationResult(
                operation=JTAGOperation.DEVICE_RESET,
                success=False,
                duration_seconds=(datetime.now() - operation_start).total_seconds(),
                command_output="",
                error_message=str(e),
                start_timestamp=operation_start,
                end_timestamp=datetime.now()
            )
            self.logger.error(f"Device reset exception: {e}")
            return result
        finally:
            try:
                os.unlink(tcl_path)
            except:
                pass


def create_jtag_controller(cable_type: str, device_part: str, **kwargs) -> JTAGControllerBase:
    """
    Factory function to create appropriate JTAG controller instance.
    
    Args:
        cable_type: Type of JTAG programming cable
        device_part: Target device part number
        **kwargs: Controller-specific configuration parameters
        
    Returns:
        Configured JTAG controller instance
        
    Raises:
        ValueError: If cable type is not supported
    """
    try:
        cable_enum = JTAGCableType(cable_type)
    except ValueError:
        raise ValueError(f"Unsupported JTAG cable type: {cable_type}")
    
    # Currently only Vivado-based controller is implemented
    # Additional implementations could be added for other tool chains
    return VivadoJTAGController(
        cable_type=cable_enum,
        device_part=device_part,
        **kwargs
    )
