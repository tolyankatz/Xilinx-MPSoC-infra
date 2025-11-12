# Onboarding New Test Case

## Overview
This guide walks through the process of adding a new test case to the ZCU102 BSP validation framework. It covers the complete workflow from test design to integration with the CI/CD pipeline.

## Prerequisites

### Required Knowledge
- **Python Programming**: Familiarity with Python 3.10+ and object-oriented programming
- **pytest Framework**: Understanding of pytest fixtures, parametrization, and assertions
- **Hardware Interfaces**: Basic knowledge of UART, Ethernet, GPIO, I2C/SPI protocols
- **Version Control**: Git workflow and branch management

### Development Environment Setup
```bash
# Clone the monorepo
git clone https://git.company.com/embedded/zcu102-bsp-validation-monorepo.git
cd zcu102-bsp-validation-monorepo

# Set up Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r test_host/requirements.txt
pip install -r test_host/requirements-dev.txt  # Development dependencies
```

## Step 1: Test Case Design

### Define Test Objectives
Before writing code, clearly define:

1. **What are you testing?** (Specific feature, protocol, or behavior)
2. **Why is it important?** (Risk mitigation, regression prevention, compliance)
3. **How will you measure success?** (Pass/fail criteria, performance thresholds)
4. **What hardware is required?** (Special fixtures, cables, external devices)

### Example: Adding CAN Bus Testing
```python
"""
Test Objective: Validate CAN bus communication on the ZCU102
- Feature: CAN controller driver functionality
- Importance: Critical for automotive applications
- Success Criteria: Send/receive CAN frames with <1ms latency
- Hardware: CAN transceiver board, loopback cable
"""
```

### Test Case Template
```python
# test_host/framework/can_test.py
"""
CAN Bus Communication Test Module

This module provides functionality to test CAN bus communication
on the ZCU102 platform, including basic frame transmission,
reception, and error handling.
"""

import logging
import time
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class CANFrame:
    """Represents a CAN frame for testing"""
    id: int
    data: bytes
    extended: bool = False
    
class CANTester:
    """Main class for CAN bus testing functionality"""
    
    def __init__(self, interface: str = "can0", bitrate: int = 500000):
        """
        Initialize CAN tester
        
        Args:
            interface: CAN interface name (e.g., 'can0')
            bitrate: CAN bus bitrate in bps
        """
        self.interface = interface
        self.bitrate = bitrate
        self.socket = None
        
    def setup(self) -> bool:
        """Set up CAN interface and socket"""
        try:
            # Implementation for CAN setup
            logger.info(f"Setting up CAN interface {self.interface} at {self.bitrate} bps")
            return True
        except Exception as e:
            logger.error(f"CAN setup failed: {e}")
            return False
            
    def send_frame(self, frame: CANFrame) -> bool:
        """Send a CAN frame"""
        # Implementation here
        pass
        
    def receive_frame(self, timeout: float = 1.0) -> Optional[CANFrame]:
        """Receive a CAN frame with timeout"""
        # Implementation here
        pass
        
    def test_loopback(self) -> Dict[str, any]:
        """Test CAN loopback functionality"""
        # Implementation here
        pass
        
    def cleanup(self):
        """Clean up CAN resources"""
        # Implementation here
        pass
```

## Step 2: Framework Integration

### Add to Test Framework Structure
```bash
test_host/
├── framework/
│   ├── boot_validator.py      # Existing
│   ├── uart_test.py          # Existing
│   ├── ethernet_test.py      # Existing
│   └── can_test.py           # ← Your new module
├── tests/
│   ├── test_system_validation.py  # Existing
│   └── test_can_communication.py  # ← Your new test file
```

### Create Test Implementation
```python
# test_host/tests/test_can_communication.py
"""
CAN Communication System Tests

This module contains system-level tests for CAN bus communication
on the ZCU102 platform.
"""

import pytest
import time
from framework.can_test import CANTester, CANFrame

class TestCANCommunication:
    """Test suite for CAN bus communication"""
    
    @pytest.fixture(scope="class")
    def can_tester(self, request):
        """Fixture to provide CAN tester instance"""
        tester = CANTester(interface="can0", bitrate=500000)
        
        # Setup
        if not tester.setup():
            pytest.skip("CAN interface setup failed")
            
        yield tester
        
        # Cleanup
        tester.cleanup()
    
    def test_can_interface_initialization(self, can_tester):
        """Test CAN interface can be initialized properly"""
        assert can_tester.socket is not None
        assert can_tester.interface == "can0"
        
    def test_can_loopback_basic(self, can_tester):
        """Test basic CAN loopback functionality"""
        test_frame = CANFrame(id=0x123, data=b'\x01\x02\x03\x04')
        
        # Send frame
        assert can_tester.send_frame(test_frame)
        
        # Receive frame
        received = can_tester.receive_frame(timeout=2.0)
        assert received is not None
        assert received.id == test_frame.id
        assert received.data == test_frame.data
        
    @pytest.mark.parametrize("frame_id,data", [
        (0x100, b'\x00\x01\x02\x03'),
        (0x200, b'\xFF\xFE\xFD\xFC'),
        (0x7FF, b'\xAA\x55\xAA\x55'),
    ])
    def test_can_frame_variations(self, can_tester, frame_id, data):
        """Test CAN communication with various frame IDs and data"""
        frame = CANFrame(id=frame_id, data=data)
        
        assert can_tester.send_frame(frame)
        received = can_tester.receive_frame(timeout=1.0)
        
        assert received is not None
        assert received.id == frame_id
        assert received.data == data
        
    def test_can_performance(self, can_tester):
        """Test CAN bus performance characteristics"""
        frame_count = 100
        test_frame = CANFrame(id=0x555, data=b'\x01\x02\x03\x04')
        
        start_time = time.time()
        
        for _ in range(frame_count):
            assert can_tester.send_frame(test_frame)
            received = can_tester.receive_frame(timeout=0.1)
            assert received is not None
            
        end_time = time.time()
        total_time = end_time - start_time
        frames_per_second = frame_count / total_time
        
        # Assert minimum performance requirement
        assert frames_per_second >= 50, f"CAN performance too low: {frames_per_second:.1f} fps"
        
    def test_can_error_handling(self, can_tester):
        """Test CAN error detection and handling"""
        # Test invalid frame ID
        invalid_frame = CANFrame(id=0x1000, data=b'\x01')  # ID too large for standard CAN
        
        # Should handle gracefully without crashing
        result = can_tester.send_frame(invalid_frame)
        # Depending on implementation, this might return False or raise exception
```

## Step 3: Configuration Integration

### Update Test Configuration
```yaml
# test_host/config.yaml - Add CAN-specific configuration
hardware:
  serial_port: "/dev/ttyUSB0"
  baud_rate: 115200
  target_ip: "192.168.1.101"
  
  # Add CAN configuration section
  can:
    interface: "can0"
    bitrate: 500000
    test_timeout: 5.0
    performance_threshold:
      min_frames_per_second: 50
      max_latency_ms: 1.0

test_suites:
  quick:
    - "boot_validation"
    - "uart_tests"
    - "ethernet_connectivity"
  
  full:
    - "boot_validation"
    - "uart_tests"
    - "ethernet_connectivity"
    - "ethernet_performance"
    - "can_communication"  # ← Add your new test suite
```

### Update Dependencies
```txt
# test_host/requirements.txt - Add any new dependencies
pytest>=7.0.0
pyserial>=3.5
pyyaml>=6.0
paramiko>=2.9.0
prometheus-client>=0.15.0
python-json-logger>=2.0.0
python-can>=4.0.0  # ← Add CAN library dependency
```

## Step 4: CI/CD Integration

### Update Jenkins Pipeline
```groovy
// jenkins/Jenkinsfile - Add CAN test stage
pipeline {
    agent {
        dockerfile {
            filename 'infra/docker/Dockerfile.test-host'
        }
    }
    
    stages {
        // ... existing stages ...
        
        stage('Hardware Tests') {
            parallel {
                stage('Boot & UART Tests') {
                    steps {
                        sh 'python test_host/run_tests.py --suite quick'
                    }
                }
                
                stage('Network Tests') {
                    steps {
                        sh 'python test_host/run_tests.py --suite ethernet'
                    }
                }
                
                // Add new CAN test stage
                stage('CAN Communication Tests') {
                    when {
                        anyOf {
                            branch 'main'
                            changeRequest()
                        }
                    }
                    steps {
                        sh 'python test_host/run_tests.py --suite can_communication'
                    }
                    post {
                        always {
                            archiveArtifacts artifacts: 'test_results/can_*.json'
                        }
                    }
                }
            }
        }
    }
}
```

### Update Test Runner
```python
# test_host/run_tests.py - Add CAN test suite support
TEST_SUITES = {
    'quick': ['test_system_validation.py::TestBootSequence', 
              'test_system_validation.py::TestUARTBasic'],
    'full': ['test_system_validation.py', 'test_can_communication.py'],
    'can_communication': ['test_can_communication.py'],  # ← Add new suite
    # ... other suites
}
```

## Step 5: Documentation and Review

### Create Test Documentation
```markdown
# test_host/docs/CAN_Testing_Guide.md

## CAN Bus Testing on ZCU102

### Hardware Setup
1. Connect CAN transceiver board to ZCU102 CAN pins
2. Install loopback cable between CAN_H and CAN_L
3. Verify 120Ω termination resistors

### Test Coverage
- Basic frame transmission/reception
- Extended frame support  
- Error frame handling
- Performance benchmarking

### Troubleshooting
- Check `dmesg | grep can` for kernel driver messages
- Verify interface with `ip link show can0`
- Monitor traffic with `candump can0`
```

### Code Review Checklist
- [ ] **Code Quality**: Follows PEP8, has type hints, proper docstrings
- [ ] **Test Coverage**: Tests both positive and negative cases
- [ ] **Error Handling**: Graceful handling of hardware failures
- [ ] **Configuration**: All hardcoded values moved to config files
- [ ] **Documentation**: Clear setup instructions and troubleshooting
- [ ] **CI Integration**: Pipeline updated to run new tests
- [ ] **Performance**: Tests complete within reasonable time

## Step 6: Deployment and Monitoring

### Gradual Rollout Strategy
1. **Development Branch**: Test on development hardware first
2. **Feature Branch**: Create pull request with comprehensive tests
3. **Staging Environment**: Validate on staging/pre-production systems  
4. **Production**: Deploy to main branch after approval

### Monitoring Integration
```python
# Add metrics reporting to your test
from reporters.prometheus_reporter import push_metrics

def test_can_performance_with_metrics(self, can_tester):
    """Test with integrated metrics reporting"""
    # ... test implementation ...
    
    # Report metrics
    metrics = {
        'can_frames_per_second': frames_per_second,
        'can_average_latency_ms': avg_latency,
        'can_error_rate': error_count / total_frames
    }
    push_metrics(metrics)
```

## Common Pitfalls to Avoid

### Hardware-Related Issues
- **Insufficient hardware validation** → Always test on actual hardware before CI integration
- **Missing dependencies** → Document all required hardware and software
- **Race conditions** → Add appropriate delays and timeouts

### Framework Integration Problems  
- **Breaking existing tests** → Run full test suite before submitting PR
- **Resource conflicts** → Ensure proper cleanup in fixtures
- **Configuration drift** → Use version-controlled configuration files

### CI/CD Integration Issues
- **Long test execution** → Set realistic timeouts, parallelize when possible
- **Flaky tests** → Add retry logic and proper error handling
- **Missing artifacts** → Archive all relevant test outputs

## Getting Help

### Internal Resources
- **Framework Documentation**: [Architecture Guide](../architecture.md)
- **Team Chat**: #test-automation Slack channel
- **Code Review**: Create PR and tag @test-infrastructure team

### External Resources
- **pytest Documentation**: https://docs.pytest.org/
- **Python CAN Library**: https://python-can.readthedocs.io/
- **ZCU102 Reference**: Xilinx Documentation Portal

---
**Last Updated**: November 2024  
**Document Owner**: Test Infrastructure Team  
**Review Cycle**: Per release cycle
