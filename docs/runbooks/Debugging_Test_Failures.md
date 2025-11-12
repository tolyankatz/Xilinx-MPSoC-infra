# Debugging Test Failures

## Overview
This runbook provides systematic approaches to diagnosing and resolving test failures in the ZCU102 BSP validation framework. It covers analysis of logs, dashboards, and test artifacts to quickly identify root causes.

## Quick Reference Decision Tree

```
Test Failure Detected
├── Boot Related? → Check Boot Logs → [Boot Troubleshooting]
├── Network Related? → Check Network Config → [Network Troubleshooting]  
├── Hardware Related? → Check Power/JTAG → [Hardware Troubleshooting]
└── Framework Related? → Check Test Logs → [Framework Troubleshooting]
```

## Step 1: Initial Triage

### Gather Basic Information
```bash
# Check recent test run status
kubectl get jobs -n test-automation
# Or for Jenkins
curl -s http://jenkins:8080/api/json | jq '.jobs[] | select(.name | contains("zcu102"))'

# Check system resources on test host
df -h
free -m
ps aux | grep -E "(python|pytest)"
```

### Classify the Failure Type
1. **Build Failure**: Error during BSP compilation
2. **Deployment Failure**: Error flashing/provisioning DUT  
3. **Test Execution Failure**: Test ran but failed assertions
4. **Infrastructure Failure**: Test host or framework issues
5. **Timeout Failure**: Test exceeded expected runtime

## Step 2: Analyzing S3 Logs

### Accessing Test Artifacts
```bash
# List recent test runs (requires AWS CLI configured)
aws s3 ls s3://zcu102-test-artifacts/ --recursive | tail -20

# Download specific test run artifacts
TEST_RUN="bsp-main-137-20241112-1430"
aws s3 sync s3://zcu102-test-artifacts/${TEST_RUN}/ ./debug/${TEST_RUN}/
```

### Key Files to Examine
- **`console.log`**: Complete serial console output
- **`test_results.json`**: Structured test results and timings
- **`pytest_report.html`**: Detailed pytest execution report  
- **`system_info.json`**: DUT hardware and software information
- **`network_capture.pcap`**: Network traffic during testing (if enabled)

### Log Analysis Commands
```bash
# Quick scan for errors in console log
grep -i -E "(error|fail|exception|panic|oops)" console.log

# Check boot timing
grep -E "(U-Boot|Linux version|login:)" console.log | \
  awk '{print $1, $2, $0}' | head -20

# Network connectivity check
grep -E "(eth0|DHCP|IP)" console.log

# Memory/resource issues
grep -E "(oom|memory|killed)" console.log
```

## Step 3: Querying Kibana

### Accessing the Dashboard
- **URL**: http://kibana.test-lab.company.com:5601
- **Index Pattern**: `zcu102-tests-*`

### Common Queries

#### Find All Failures for a Specific Build
```json
{
  "query": {
    "bool": {
      "must": [
        {"match": {"build_id": "bsp-main-137"}},
        {"match": {"test_result": "FAILED"}}
      ]
    }
  }
}
```

#### Boot Time Trend Analysis
```json
{
  "query": {"match_all": {}},
  "aggs": {
    "boot_time_over_time": {
      "date_histogram": {
        "field": "@timestamp",
        "interval": "1d"
      },
      "aggs": {
        "avg_boot_time": {
          "avg": {"field": "metrics.boot_time_seconds"}
        }
      }
    }
  }
}
```

#### Network Performance Regression Detection
```json
{
  "query": {
    "range": {
      "@timestamp": {
        "gte": "now-7d"
      }
    }
  },
  "aggs": {
    "throughput_trend": {
      "terms": {"field": "test_name.keyword"},
      "aggs": {
        "avg_throughput": {
          "avg": {"field": "metrics.network_throughput_mbps"}
        }
      }
    }
  }
}
```

### Kibana Visualization Tips
1. **Create Time-based Charts**: Use @timestamp field for trend analysis
2. **Filter by Test Type**: Use `test_name.keyword` for specific test filtering  
3. **Correlate with Build Info**: Cross-reference with `build_id` and `commit_hash`
4. **Set Up Alerts**: Configure Watcher for automatic failure notifications

## Step 4: Interpreting Grafana Dashboards

### Key Dashboard URLs
- **System Overview**: http://grafana:3000/d/zcu102-overview
- **Test Metrics**: http://grafana:3000/d/zcu102-test-metrics  
- **Infrastructure Health**: http://grafana:3000/d/test-host-health

### Critical Metrics to Monitor

#### Performance Regression Indicators
```promql
# Boot time trend (7-day moving average)
avg_over_time(boot_time_seconds[7d])

# Network throughput deviation
(network_throughput_mbps - avg_over_time(network_throughput_mbps[7d])) / 
avg_over_time(network_throughput_mbps[7d]) * 100
```

#### Infrastructure Health Checks
```promql
# Test host resource utilization
100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Available disk space
node_filesystem_avail_bytes{mountpoint="/"} / 1024^3

# Test framework memory usage
process_resident_memory_bytes{job="pytest"}
```

#### Test Success Rate
```promql
# Overall test success rate (last 24h)
(sum(test_results{result="PASSED"}) / sum(test_results)) * 100

# Success rate by test category
sum by(test_category) (test_results{result="PASSED"}) / 
sum by(test_category) (test_results) * 100
```

## Step 5: Common Failure Patterns & Solutions

### Boot Failures

#### Symptom: "No console output after power on"
**Diagnosis**:
```bash
# Check serial connection
sudo lsusb | grep -i ftdi
sudo dmesg | grep -i ttyUSB
```
**Solution**: Verify USB-to-serial adapter and cable connections

#### Symptom: "U-Boot loads but kernel fails"
**Diagnosis**: Look for kernel panic or initramfs errors in console.log
**Solution**: Check device tree compatibility or rootfs integrity

### Network Failures

#### Symptom: "DHCP timeout during boot"
**Diagnosis**: 
```bash
# Check network infrastructure
ping 192.168.1.1  # Gateway
nmap -sn 192.168.1.0/24  # Network scan
```
**Solution**: Verify switch configuration and DHCP server

#### Symptom: "Ethernet performance degradation"
**Diagnosis**: Compare current vs. historical throughput in Grafana
**Solution**: Check for driver changes or network congestion

### Test Framework Issues

#### Symptom: "pytest collection failures"
**Diagnosis**:
```bash
# Run pytest in verbose mode
cd test_host
python -m pytest --collect-only -v
```
**Solution**: Check for import errors or missing dependencies

#### Symptom: "Hardware control timeouts"
**Diagnosis**: Check power controller and JTAG connections
**Solution**: Verify hardware interfaces and permissions

## Step 6: Automated Debugging Tools

### Log Analysis Script
```python
#!/usr/bin/env python3
"""
Automated log analyzer for ZCU102 test failures
"""
import json
import re
from pathlib import Path

def analyze_console_log(log_path):
    """Extract key information from console log"""
    with open(log_path) as f:
        content = f.read()
    
    # Extract boot stages and timings
    boot_stages = re.findall(r'(\d+:\d+:\d+\.\d+).*?(U-Boot|Starting kernel|login:)', content)
    
    # Check for errors
    errors = re.findall(r'(?i)(error|panic|oops|exception).*', content)
    
    return {
        'boot_stages': boot_stages,
        'errors': errors,
        'boot_complete': 'login:' in content
    }

if __name__ == "__main__":
    result = analyze_console_log("debug/console.log")
    print(json.dumps(result, indent=2))
```

### Health Check Automation
```bash
#!/bin/bash
# health_check.sh - Quick system health verification

echo "=== ZCU102 Test Infrastructure Health Check ==="

# Check test host resources
echo "Test Host Resources:"
echo "  CPU Usage: $(top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1)%"
echo "  Memory Usage: $(free | grep Mem | awk '{printf "%.1f%%", $3/$2 * 100.0}')"
echo "  Disk Usage: $(df -h / | awk 'NR==2{print $5}')"

# Check DUT connectivity
echo -e "\nDUT Connectivity:"
if ping -c 1 192.168.1.101 >/dev/null 2>&1; then
    echo "  Network: ✓ Reachable"
else
    echo "  Network: ✗ Unreachable"
fi

# Check services
echo -e "\nServices:"
systemctl is-active --quiet jenkins && echo "  Jenkins: ✓ Running" || echo "  Jenkins: ✗ Down"
systemctl is-active --quiet elasticsearch && echo "  Elasticsearch: ✓ Running" || echo "  Elasticsearch: ✗ Down"
```

## Emergency Escalation

### When to Escalate
- **Hardware damage suspected** → Hardware Team immediately
- **Infrastructure down >2 hours** → Infrastructure Team + Management  
- **Test success rate <50% for >24h** → BSP Team + QA Management
- **Security-related failures** → Security Team immediately

### Escalation Contacts
- **L1 Support**: test-infrastructure@company.com
- **BSP Engineering**: bsp-team@company.com  
- **Hardware Team**: hardware-lab@company.com
- **Emergency Hotline**: +1-555-TEST-911

---
**Last Updated**: November 2024  
**Document Owner**: Test Infrastructure Team  
**Review Cycle**: Monthly
