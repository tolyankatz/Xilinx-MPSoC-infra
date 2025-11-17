"""
ELK Stack (Elasticsearch, Logstash, Kibana) Reporter

This module provides comprehensive logging and analytics integration with the ELK stack
for the ZCU102 test framework. It enables rich log aggregation, search capabilities,
and visualization of test execution data.

The ELK integration supports the "glass box" philosophy by providing searchable,
analyzable logs and enabling deep-dive debugging capabilities.
"""

import json
import logging
import socket
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum

try:
    from elasticsearch import Elasticsearch
    from elasticsearch.exceptions import ConnectionError, RequestError
    ELASTICSEARCH_AVAILABLE = True
except ImportError:
    ELASTICSEARCH_AVAILABLE = False
    logging.getLogger(__name__).warning("Elasticsearch not available - install 'elasticsearch' package for full functionality")


class LogLevel(Enum):
    """Log level enumeration for structured logging."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class TestLogEntry:
    """Structured test log entry for ELK ingestion."""
    timestamp: datetime
    test_name: str
    test_type: str
    log_level: LogLevel
    message: str
    board_type: str = "zcu102"
    build_version: str = "unknown"
    session_id: str = ""
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        
        # Ensure timestamp is timezone-aware
        if self.timestamp.tzinfo is None:
            self.timestamp = self.timestamp.replace(tzinfo=timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary for JSON serialization."""
        entry_dict = asdict(self)
        entry_dict['timestamp'] = self.timestamp.isoformat()
        entry_dict['log_level'] = self.log_level.value
        return entry_dict


@dataclass
class ELKTestResultDocument:
    """Complete test result document for Elasticsearch indexing."""
    test_execution_id: str
    test_name: str
    test_type: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    success: bool
    board_type: str = "zcu102"
    build_version: str = "unknown"
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = None
    log_entries: List[TestLogEntry] = None
    environment: Dict[str, str] = None
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}
        if self.log_entries is None:
            self.log_entries = []
        if self.environment is None:
            self.environment = {}
            
        # Ensure timestamps are timezone-aware
        if self.start_time.tzinfo is None:
            self.start_time = self.start_time.replace(tzinfo=timezone.utc)
        if self.end_time.tzinfo is None:
            self.end_time = self.end_time.replace(tzinfo=timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result document to dictionary for Elasticsearch."""
        doc_dict = asdict(self)
        doc_dict['start_time'] = self.start_time.isoformat()
        doc_dict['end_time'] = self.end_time.isoformat()
        
        # Convert log entries
        doc_dict['log_entries'] = [entry.to_dict() for entry in self.log_entries]
        
        return doc_dict


class ELKReporter:
    """
    Advanced ELK Stack reporter for ZCU102 test framework.
    
    This class provides comprehensive integration with Elasticsearch for log storage,
    Logstash for log processing, and supports Kibana visualization through proper
    document structuring and indexing strategies.
    """
    
    def __init__(self, elasticsearch_hosts: List[str], 
                 index_prefix: str = "zcu102-test-logs",
                 logstash_host: Optional[str] = None,
                 logstash_port: int = 5044,
                 session_id: Optional[str] = None):
        """
        Initialize ELK Stack reporter.
        
        Args:
            elasticsearch_hosts: List of Elasticsearch host URLs
            index_prefix: Prefix for Elasticsearch indices
            logstash_host: Logstash host for TCP log shipping
            logstash_port: Logstash TCP input port
            session_id: Unique session identifier for test execution
        """
        self.elasticsearch_hosts = elasticsearch_hosts
        self.index_prefix = index_prefix
        self.logstash_host = logstash_host
        self.logstash_port = logstash_port
        self.session_id = session_id or f"test_session_{int(time.time())}"
        
        self.logger = logging.getLogger(__name__)
        self.es_client = None
        self.logstash_socket = None
        
        # Initialize Elasticsearch client if available
        if ELASTICSEARCH_AVAILABLE:
            self._initialize_elasticsearch()
        
        # Buffer for log entries when direct shipping is not available
        self.log_buffer: List[TestLogEntry] = []
        
        self.logger.info(f"ELK reporter initialized: session_id={self.session_id}")
    
    def _initialize_elasticsearch(self) -> None:
        """Initialize Elasticsearch client connection."""
        try:
            self.es_client = Elasticsearch(
                self.elasticsearch_hosts,
                timeout=30,
                max_retries=3,
                retry_on_timeout=True
            )
            
            # Test connection
            if self.es_client.ping():
                self.logger.info(f"Elasticsearch connection established: {self.elasticsearch_hosts}")
                self._create_index_templates()
            else:
                self.logger.error("Elasticsearch ping failed")
                self.es_client = None
                
        except Exception as e:
            self.logger.error(f"Failed to initialize Elasticsearch client: {e}")
            self.es_client = None
    
    def _create_index_templates(self) -> None:
        """Create Elasticsearch index templates for optimal data storage."""
        
        # Template for test log entries
        log_template = {
            "index_patterns": [f"{self.index_prefix}-logs-*"],
            "template": {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "index.refresh_interval": "5s"
                },
                "mappings": {
                    "properties": {
                        "timestamp": {"type": "date"},
                        "test_name": {"type": "keyword"},
                        "test_type": {"type": "keyword"},
                        "log_level": {"type": "keyword"},
                        "message": {"type": "text", "analyzer": "standard"},
                        "board_type": {"type": "keyword"},
                        "build_version": {"type": "keyword"},
                        "session_id": {"type": "keyword"},
                        "metadata": {"type": "object", "dynamic": True}
                    }
                }
            }
        }
        
        # Template for test results
        result_template = {
            "index_patterns": [f"{self.index_prefix}-results-*"],
            "template": {
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0
                },
                "mappings": {
                    "properties": {
                        "test_execution_id": {"type": "keyword"},
                        "test_name": {"type": "keyword"},
                        "test_type": {"type": "keyword"},
                        "start_time": {"type": "date"},
                        "end_time": {"type": "date"},
                        "duration_seconds": {"type": "float"},
                        "success": {"type": "boolean"},
                        "board_type": {"type": "keyword"},
                        "build_version": {"type": "keyword"},
                        "error_message": {"type": "text"},
                        "metrics": {"type": "object", "dynamic": True},
                        "environment": {"type": "object", "dynamic": True}
                    }
                }
            }
        }
        
        try:
            # Create templates (Elasticsearch 7.8+ syntax)
            self.es_client.indices.put_index_template(
                name=f"{self.index_prefix}-logs-template",
                body=log_template
            )
            
            self.es_client.indices.put_index_template(
                name=f"{self.index_prefix}-results-template", 
                body=result_template
            )
            
            self.logger.info("Elasticsearch index templates created successfully")
            
        except Exception as e:
            self.logger.warning(f"Failed to create Elasticsearch templates: {e}")
    
    def _get_current_log_index(self) -> str:
        """Get current log index name with date-based rotation."""
        current_date = datetime.now().strftime("%Y.%m.%d")
        return f"{self.index_prefix}-logs-{current_date}"
    
    def _get_current_result_index(self) -> str:
        """Get current result index name with date-based rotation."""
        current_date = datetime.now().strftime("%Y.%m")
        return f"{self.index_prefix}-results-{current_date}"
    
    def log_test_message(self, test_name: str, test_type: str, 
                        log_level: LogLevel, message: str,
                        board_type: str = "zcu102", build_version: str = "unknown",
                        metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Log a test message to ELK stack.
        
        Args:
            test_name: Name of the test generating the log
            test_type: Type/category of the test
            log_level: Severity level of the log message
            message: Log message content
            board_type: Target board type
            build_version: BSP build version
            metadata: Additional metadata to include
            
        Returns:
            True if log was successfully sent
        """
        log_entry = TestLogEntry(
            timestamp=datetime.now(timezone.utc),
            test_name=test_name,
            test_type=test_type,
            log_level=log_level,
            message=message,
            board_type=board_type,
            build_version=build_version,
            session_id=self.session_id,
            metadata=metadata or {}
        )
        
        # Try direct Elasticsearch indexing first
        if self.es_client:
            if self._index_log_entry(log_entry):
                return True
        
        # Try Logstash TCP shipping as fallback
        if self.logstash_host:
            if self._ship_to_logstash(log_entry):
                return True
        
        # Buffer the log entry for later processing
        self.log_buffer.append(log_entry)
        self.logger.debug(f"Log entry buffered: {test_name} - {message}")
        
        return True
    
    def _index_log_entry(self, log_entry: TestLogEntry) -> bool:
        """Index log entry directly to Elasticsearch."""
        try:
            index_name = self._get_current_log_index()
            
            response = self.es_client.index(
                index=index_name,
                body=log_entry.to_dict()
            )
            
            self.logger.debug(f"Log entry indexed: {response['_id']}")
            return True
            
        except Exception as e:
            self.logger.warning(f"Failed to index log entry to Elasticsearch: {e}")
            return False
    
    def _ship_to_logstash(self, log_entry: TestLogEntry) -> bool:
        """Ship log entry to Logstash via TCP."""
        try:
            if not self.logstash_socket:
                self.logstash_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.logstash_socket.connect((self.logstash_host, self.logstash_port))
            
            # Send JSON formatted log entry
            log_json = json.dumps(log_entry.to_dict()) + '\n'
            self.logstash_socket.send(log_json.encode('utf-8'))
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Failed to ship log to Logstash: {e}")
            # Close and reset socket on error
            if self.logstash_socket:
                try:
                    self.logstash_socket.close()
                except:
                    pass
                self.logstash_socket = None
            return False
    
    def log_test_result(self, test_result: ELKTestResultDocument) -> bool:
        """
        Log complete test result document to Elasticsearch.
        
        Args:
            test_result: Complete test result document
            
        Returns:
            True if result was successfully indexed
        """
        if not self.es_client:
            self.logger.error("Elasticsearch client not available for test result logging")
            return False
        
        try:
            index_name = self._get_current_result_index()
            
            response = self.es_client.index(
                index=index_name,
                id=test_result.test_execution_id,  # Use test execution ID as document ID
                body=test_result.to_dict()
            )
            
            self.logger.info(f"Test result indexed: {test_result.test_name} ({response['_id']})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to index test result: {e}")
            return False
    
    def flush_buffered_logs(self) -> int:
        """
        Flush buffered log entries to ELK stack.
        
        Returns:
            Number of log entries successfully flushed
        """
        if not self.log_buffer:
            return 0
        
        flushed_count = 0
        failed_entries = []
        
        for log_entry in self.log_buffer:
            # Try Elasticsearch first, then Logstash
            if (self.es_client and self._index_log_entry(log_entry)) or \
               (self.logstash_host and self._ship_to_logstash(log_entry)):
                flushed_count += 1
            else:
                failed_entries.append(log_entry)
        
        # Keep failed entries in buffer for retry
        self.log_buffer = failed_entries
        
        if flushed_count > 0:
            self.logger.info(f"Flushed {flushed_count} buffered log entries")
        
        return flushed_count
    
    def search_logs(self, query: Dict[str, Any], 
                   start_date: Optional[datetime] = None,
                   end_date: Optional[datetime] = None,
                   size: int = 100) -> List[Dict[str, Any]]:
        """
        Search test logs in Elasticsearch.
        
        Args:
            query: Elasticsearch query DSL
            start_date: Start date for time range filter
            end_date: End date for time range filter  
            size: Maximum number of results to return
            
        Returns:
            List of matching log entries
        """
        if not self.es_client:
            self.logger.error("Elasticsearch client not available for log search")
            return []
        
        try:
            # Build search query with time range if specified
            search_body = {"query": query, "size": size, "sort": [{"timestamp": {"order": "desc"}}]}
            
            if start_date or end_date:
                time_range = {}
                if start_date:
                    time_range["gte"] = start_date.isoformat()
                if end_date:
                    time_range["lte"] = end_date.isoformat()
                
                # Add time range filter
                if "bool" not in search_body["query"]:
                    search_body["query"] = {"bool": {"must": [search_body["query"]]}}
                
                if "filter" not in search_body["query"]["bool"]:
                    search_body["query"]["bool"]["filter"] = []
                
                search_body["query"]["bool"]["filter"].append({
                    "range": {"timestamp": time_range}
                })
            
            # Search across log indices
            index_pattern = f"{self.index_prefix}-logs-*"
            response = self.es_client.search(index=index_pattern, body=search_body)
            
            # Extract hit sources
            results = [hit["_source"] for hit in response["hits"]["hits"]]
            
            self.logger.debug(f"Log search returned {len(results)} results")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to search logs: {e}")
            return []
    
    def get_test_statistics(self, test_type: Optional[str] = None,
                           board_type: Optional[str] = None,
                           days_back: int = 7) -> Dict[str, Any]:
        """
        Get aggregated test statistics from Elasticsearch.
        
        Args:
            test_type: Filter by specific test type
            board_type: Filter by specific board type
            days_back: Number of days to look back for statistics
            
        Returns:
            Dictionary containing test statistics
        """
        if not self.es_client:
            self.logger.error("Elasticsearch client not available for statistics")
            return {}
        
        try:
            # Build aggregation query
            agg_query = {
                "size": 0,
                "query": {
                    "bool": {
                        "filter": [
                            {
                                "range": {
                                    "start_time": {
                                        "gte": f"now-{days_back}d"
                                    }
                                }
                            }
                        ]
                    }
                },
                "aggs": {
                    "success_rate": {
                        "terms": {"field": "success"}
                    },
                    "test_types": {
                        "terms": {"field": "test_type.keyword"}
                    },
                    "average_duration": {
                        "avg": {"field": "duration_seconds"}
                    },
                    "daily_tests": {
                        "date_histogram": {
                            "field": "start_time",
                            "calendar_interval": "day"
                        }
                    }
                }
            }
            
            # Add filters if specified
            if test_type:
                agg_query["query"]["bool"]["filter"].append({
                    "term": {"test_type.keyword": test_type}
                })
            
            if board_type:
                agg_query["query"]["bool"]["filter"].append({
                    "term": {"board_type.keyword": board_type}
                })
            
            # Execute aggregation query
            index_pattern = f"{self.index_prefix}-results-*"
            response = self.es_client.search(index=index_pattern, body=agg_query)
            
            # Process aggregation results
            aggregations = response["aggregations"]
            
            statistics = {
                "total_tests": response["hits"]["total"]["value"],
                "success_rate": self._calculate_success_rate(aggregations["success_rate"]["buckets"]),
                "average_duration_seconds": aggregations["average_duration"]["value"],
                "test_type_breakdown": {
                    bucket["key"]: bucket["doc_count"] 
                    for bucket in aggregations["test_types"]["buckets"]
                },
                "daily_test_counts": [
                    {
                        "date": bucket["key_as_string"], 
                        "count": bucket["doc_count"]
                    }
                    for bucket in aggregations["daily_tests"]["buckets"]
                ]
            }
            
            return statistics
            
        except Exception as e:
            self.logger.error(f"Failed to get test statistics: {e}")
            return {}
    
    def _calculate_success_rate(self, success_buckets: List[Dict]) -> float:
        """Calculate success rate from Elasticsearch aggregation buckets."""
        total_tests = sum(bucket["doc_count"] for bucket in success_buckets)
        if total_tests == 0:
            return 0.0
        
        successful_tests = next(
            (bucket["doc_count"] for bucket in success_buckets if bucket["key"]), 0
        )
        
        return (successful_tests / total_tests) * 100
    
    def close(self) -> None:
        """Close ELK reporter connections and flush remaining logs."""
        # Flush any remaining buffered logs
        self.flush_buffered_logs()
        
        # Close Logstash socket
        if self.logstash_socket:
            try:
                self.logstash_socket.close()
            except:
                pass
            self.logstash_socket = None
        
        # Close Elasticsearch connection
        if self.es_client:
            try:
                self.es_client.transport.connection_pool.close()
            except:
                pass
            self.es_client = None
        
        self.logger.info("ELK reporter connections closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure proper cleanup."""
        self.close()


def create_elk_reporter(elasticsearch_hosts: List[str], **kwargs) -> ELKReporter:
    """
    Factory function to create ELK reporter instance.
    
    Args:
        elasticsearch_hosts: List of Elasticsearch host URLs
        **kwargs: Additional configuration parameters
        
    Returns:
        Configured ELK reporter instance
    """
    return ELKReporter(elasticsearch_hosts=elasticsearch_hosts, **kwargs)
