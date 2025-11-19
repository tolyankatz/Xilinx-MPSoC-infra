"""
TCP Serial Adapter for connecting to network-based serial consoles.

This module provides a serial-like interface for TCP connections to devices
like the DUT simulator that expose console interfaces over TCP.
"""

import socket
import time
import logging
from typing import Optional, Union


class TCPSerialAdapter:
    """
    Adapter that provides a serial.Serial-like interface for TCP connections.
    
    This allows existing serial-based code to work with TCP console connections
    without modification.
    """
    
    def __init__(self, host: str, port: int, timeout: float = 1.0):
        """
        Initialize TCP serial adapter.
        
        Args:
            host: Target hostname or IP address
            port: Target TCP port
            timeout: Socket timeout for read operations
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.socket: Optional[socket.socket] = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
    def open(self):
        """Open TCP connection."""
        if self.socket is not None:
            return  # Already open
            
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            self.logger.info(f"TCP serial connection established: {self.host}:{self.port}")
        except Exception as e:
            self.logger.error(f"Failed to connect to {self.host}:{self.port}: {e}")
            if self.socket:
                self.socket.close()
                self.socket = None
            raise
    
    def close(self):
        """Close TCP connection."""
        if self.socket:
            try:
                self.socket.close()
                self.logger.info(f"TCP serial connection closed: {self.host}:{self.port}")
            except Exception as e:
                self.logger.warning(f"Error closing TCP connection: {e}")
            finally:
                self.socket = None
    
    def write(self, data: Union[str, bytes]) -> int:
        """
        Write data to TCP connection.
        
        Args:
            data: Data to write (string or bytes)
            
        Returns:
            Number of bytes written
        """
        if self.socket is None:
            raise RuntimeError("TCP connection not open")
            
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        try:
            return self.socket.send(data)
        except Exception as e:
            self.logger.error(f"TCP write error: {e}")
            raise
    
    def read(self, size: int = 1) -> bytes:
        """
        Read data from TCP connection.
        
        Args:
            size: Maximum number of bytes to read
            
        Returns:
            Bytes read from connection
        """
        if self.socket is None:
            raise RuntimeError("TCP connection not open")
            
        try:
            return self.socket.recv(size)
        except socket.timeout:
            return b''  # Return empty bytes on timeout, similar to serial behavior
        except Exception as e:
            self.logger.error(f"TCP read error: {e}")
            raise
    
    def readline(self, size: int = -1) -> bytes:
        """
        Read a line from TCP connection.
        
        Args:
            size: Maximum number of bytes to read (-1 for unlimited)
            
        Returns:
            Line data as bytes
        """
        if self.socket is None:
            raise RuntimeError("TCP connection not open")
            
        line = b''
        while True:
            try:
                char = self.socket.recv(1)
                if not char:
                    break
                line += char
                if char == b'\n':
                    break
                if size > 0 and len(line) >= size:
                    break
            except socket.timeout:
                break
            except Exception as e:
                self.logger.error(f"TCP readline error: {e}")
                raise
                
        return line
    
    @property
    def in_waiting(self) -> int:
        """
        Return number of bytes available for reading.
        
        Note: This is a simplified implementation that doesn't accurately
        reflect buffer size, but provides compatibility with serial interface.
        
        Returns:
            Estimated bytes available (0 or 1)
        """
        if self.socket is None:
            return 0
            
        # Use non-blocking peek to check if data is available
        original_timeout = self.socket.gettimeout()
        try:
            self.socket.settimeout(0)
            data = self.socket.recv(1, socket.MSG_PEEK)
            return len(data)
        except socket.error:
            return 0
        finally:
            self.socket.settimeout(original_timeout)
    
    def flush(self):
        """Flush write buffer (no-op for TCP)."""
        pass
    
    def reset_input_buffer(self):
        """Clear input buffer by reading available data."""
        if self.socket is None:
            return
            
        original_timeout = self.socket.gettimeout()
        try:
            self.socket.settimeout(0.1)  # Short timeout for clearing buffer
            while True:
                data = self.socket.recv(1024)
                if not data:
                    break
        except socket.error:
            pass  # Expected when buffer is empty
        finally:
            self.socket.settimeout(original_timeout)
    
    def reset_output_buffer(self):
        """Clear output buffer (no-op for TCP)."""
        pass
    
    @property
    def is_open(self) -> bool:
        """Check if connection is open."""
        return self.socket is not None
    
    # Context manager support
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def create_serial_connection(port: str, baud_rate: int = 115200, timeout: float = 1.0):
    """
    Create a serial connection, supporting both real serial ports and TCP connections.
    
    Args:
        port: Serial port path or TCP URL (socket://host:port)
        baud_rate: Baud rate (ignored for TCP connections)
        timeout: Connection timeout
        
    Returns:
        Serial connection object (serial.Serial or TCPSerialAdapter)
    """
    if port.startswith("socket://"):
        # Parse TCP connection string: socket://host:port
        tcp_part = port[9:]  # Remove "socket://" prefix
        if ":" not in tcp_part:
            raise ValueError(f"Invalid TCP connection string: {port}")
            
        host, port_str = tcp_part.rsplit(":", 1)
        try:
            tcp_port = int(port_str)
        except ValueError:
            raise ValueError(f"Invalid port number in TCP connection string: {port}")
            
        return TCPSerialAdapter(host, tcp_port, timeout)
    else:
        # Use standard serial connection
        import serial
        return serial.Serial(port=port, baudrate=baud_rate, timeout=timeout,
                           xonxoff=False, rtscts=False, dsrdtr=False)
