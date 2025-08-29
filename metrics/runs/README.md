# Metrics Data Storage

## Overview

This directory (`metrics/runs/`) serves as the centralized storage location for performance metrics generated during each execution of the FUSE Test Data Generator pipeline. The metrics data is automatically captured, aggregated, and persisted by the **MetricsCollector** component and consumed by the FastAPI service for the performance dashboard.

## Purpose

The metrics system enables comprehensive performance monitoring and analysis by:

- **Automatic Collection**: Performance data is captured throughout all stages of the multi-processing pipeline without impacting data generation performance
- **Historical Analysis**: All execution runs are preserved for trend analysis and performance regression detection
- **Comparison Analytics**: Multiple runs can be compared side-by-side to identify performance variations and optimization opportunities
- **Real-time Monitoring**: Latest execution metrics are available for immediate performance visibility

## File Structure and Naming Convention

### Naming Pattern
Each metrics file follows the timestamp-based naming convention:
```
metrics_{timestamp}_{run_id}.json
```

Where:
- `timestamp`: ISO 8601 formatted timestamp when the run completed (e.g., `20240315T143022Z`)
- `run_id`: Unique identifier for the specific execution run (UUID format)

### Example Filenames
```
metrics_20240315T143022Z_a1b2c3d4-e5f6-7890-abcd-ef1234567890.json
metrics_20240315T151545Z_b2c3d4e5-f6g7-8901-bcde-f12345678901.json
```

## Metrics Data Format

Each JSON file contains comprehensive performance metrics structured as follows:

### Root Structure
```json
{
  "run_metadata": {
    "run_id": "string",
    "start_time": "ISO 8601 timestamp",
    "end_time": "ISO 8601 timestamp",
    "total_duration_seconds": "float",
    "pipeline_configuration": "object"
  },
  "stage_metrics": {
    "coordinator": { ... },
    "creator_processes": { ... },
    "writer_processes": { ... }
  },
  "throughput_metrics": {
    "records_per_second": "float",
    "files_per_second": "float",
    "data_volume_mb_per_second": "float"
  },
  "resource_utilization": {
    "peak_memory_usage_mb": "float",
    "cpu_utilization_percent": "float",
    "io_operations_count": "integer"
  }
}
```

### Stage-Level Metrics
Each pipeline stage includes:
- **Timing Data**: Start time, end time, duration with microsecond precision
- **Processing Statistics**: Number of items processed, batch sizes, queue depths
- **Performance Indicators**: Throughput rates, processing speeds, efficiency ratios

### Resource Utilization Metrics
System resource consumption including:
- **Memory Usage**: Peak memory consumption during execution
- **CPU Utilization**: Processor usage across all worker processes
- **I/O Statistics**: File system operations and disk utilization

## Data Collection Process

### Automatic Generation
1. **Pipeline Initialization**: MetricsCollector singleton is instantiated when the application orchestrator starts
2. **Stage Instrumentation**: Each pipeline component (Coordinator, Creator processes, Writer processes) uses context-manager wrappers for precise timing
3. **Concurrent Collection**: Thread-safe metric recording occurs throughout parallel execution without performance impact
4. **Aggregation**: At run completion, all stage metrics are aggregated into a comprehensive dataset
5. **Persistence**: Final metrics are flushed to a timestamped JSON file in this directory

### Timing Precision
- Uses Python's `time.perf_counter()` for microsecond-accurate timing measurements
- Context managers ensure precise start/stop timing without manual intervention
- Thread-safe implementation prevents data corruption during concurrent access

## API Integration

### FastAPI Service Access
The metrics files are consumed by the FastAPI service through the following endpoints:

- **`GET /api/runs`**: Lists all available run metrics with pagination support
- **`GET /api/runs/{run_id}`**: Retrieves complete metrics for a specific run
- **`GET /api/runs/compare`**: Enables comparison analysis of multiple runs
- **`GET /api/metrics/latest`**: Provides access to the most recent execution data

### React Dashboard Consumption
The React performance dashboard displays metrics through:
- **Live Metrics Display**: Real-time performance indicators for active runs
- **Historical Trends**: Time-series charts showing performance evolution
- **Comparison Views**: Side-by-side analysis of multiple execution runs
- **Performance Analytics**: Statistical analysis and regression detection

## File Management

### Storage Considerations
- **File Size**: Typical metrics files are 5-50KB depending on pipeline complexity and duration
- **Retention**: All metrics files are preserved for historical analysis (no automatic cleanup)
- **Growth Rate**: One file per execution run (frequency depends on usage patterns)

### Manual Management
If storage space becomes a concern, older metrics files can be safely archived or removed:
```bash
# Archive files older than 30 days
find metrics/runs/ -name "*.json" -mtime +30 -exec mv {} archived_metrics/ \;

# Remove files older than 90 days
find metrics/runs/ -name "*.json" -mtime +90 -delete
```

## Troubleshooting

### Missing Metrics Files
If metrics files are not being generated:
1. Verify MetricsCollector is properly initialized in the application orchestrator
2. Check file system permissions for write access to the metrics/runs/ directory
3. Review application logs for MetricsCollector error messages
4. Ensure pipeline execution completes successfully (metrics flush on completion)

### Corrupted or Invalid JSON
If metrics files cannot be parsed:
1. Check for incomplete writes due to pipeline interruption
2. Verify sufficient disk space during metrics flush operations
3. Review the most recent working metrics file for comparison
4. Restart the pipeline to generate a new clean metrics file

### Performance Impact
The metrics collection system is designed for zero impact on data generation:
- Thread-safe operations prevent blocking of pipeline processes
- Minimal memory overhead through periodic flushing
- High-precision timing with negligible measurement overhead
- Context managers ensure automatic resource cleanup

## Integration Examples

### Accessing Metrics Programmatically
```python
import json
import os
from datetime import datetime

def load_latest_metrics():
    """Load the most recent metrics file"""
    metrics_dir = "metrics/runs"
    files = [f for f in os.listdir(metrics_dir) if f.endswith('.json')]
    if not files:
        return None
    
    latest_file = max(files, key=lambda f: os.path.getctime(os.path.join(metrics_dir, f)))
    
    with open(os.path.join(metrics_dir, latest_file), 'r') as f:
        return json.load(f)

def compare_run_performance(run_id_1, run_id_2):
    """Compare performance between two runs"""
    # Implementation for performance comparison
    pass
```

### Custom Analysis Scripts
The structured JSON format enables custom analysis scripts for:
- Performance trend analysis
- Regression detection
- Capacity planning
- Optimization identification

This metrics storage system provides the foundation for comprehensive performance visibility and continuous optimization of the FUSE Test Data Generator pipeline.