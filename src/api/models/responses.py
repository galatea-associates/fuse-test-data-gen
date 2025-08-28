"""
Pydantic response models for FastAPI metrics endpoints.

This module defines comprehensive type-safe data contracts for all
metrics-related API responses in the FUSE Test Data Generator performance
monitoring system.
All models support automatic validation, JSON serialization, and OpenAPI
documentation generation.

The response models implement a consistent envelope pattern with standardized
success/error structures, timestamp metadata, and pagination support where
applicable.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """
    Standardized error response model for consistent API error handling.

    Used across all endpoints to provide structured error information with
    appropriate error codes, human-readable messages, and debugging details.
    """
    error_code: str = Field(
        ...,
        description=("Standardized error code for programmatic handling "
                     "(e.g., 'INVALID_RUN_ID', 'METRICS_NOT_FOUND')"),
        example="INVALID_RUN_ID"
    )
    message: str = Field(
        ...,
        description=("Human-readable error message providing clear "
                     "explanation of the issue"),
        example="Run ID not found in metrics storage"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional error context and debugging information",
        example={"requested_run_id": "run_20240801_101530",
                 "available_runs": 42}
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="ISO 8601 timestamp when the error occurred",
        example="2024-08-01T10:15:30.123456"
    )

    class Config:
        """Pydantic model configuration for optimal JSON serialization."""
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class BaseResponse(BaseModel):
    """
    Generic envelope model for consistent API response structure.

    Implements the standard envelope pattern used across all successful API
    responses with status indicators, data payloads, error information, and
    timestamps.
    """
    status: str = Field(
        default="success",
        description="Response status indicator ('success' or 'error')",
        example="success"
    )
    data: Optional[Any] = Field(
        default=None,
        description="Main response payload containing the requested data"
    )
    error: Optional[str] = Field(
        default=None,
        description=("Error message for failed requests "
                     "(null for successful responses)"),
        example=None
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="ISO 8601 timestamp when the response was generated",
        example="2024-08-01T10:15:30.123456"
    )

    class Config:
        """Pydantic model configuration for optimal JSON serialization."""
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class PaginationMeta(BaseModel):
    """
    Pagination metadata model for paginated API responses.

    Provides comprehensive pagination information including current page,
    total counts, and navigation indicators for client-side pagination
    controls.
    """
    page: int = Field(
        ...,
        ge=1,
        description="Current page number (1-based indexing)",
        example=1
    )
    limit: int = Field(
        ...,
        ge=1,
        le=1000,
        description="Maximum number of items per page",
        example=50
    )
    total_pages: int = Field(
        ...,
        ge=1,
        description="Total number of available pages",
        example=5
    )
    total_items: int = Field(
        ...,
        ge=0,
        description="Total number of items across all pages",
        example=237
    )
    has_next: bool = Field(
        ...,
        description="Whether there is a next page available",
        example=True
    )
    has_previous: bool = Field(
        ...,
        description="Whether there is a previous page available",
        example=False
    )


class RunSummary(BaseModel):
    """
    Model for individual run summary information.

    Contains high-level metadata and key performance indicators for a single
    data generation run, used in run listing endpoints and summary displays.
    """
    run_id: str = Field(
        ...,
        description="Unique identifier for the data generation run",
        example="run_20240801_101530"
    )
    timestamp: datetime = Field(
        ...,
        description="ISO 8601 timestamp when the run was executed",
        example="2024-08-01T10:15:30.123456"
    )
    total_duration: float = Field(
        ...,
        ge=0.0,
        description="Total execution time in seconds",
        example=45.67
    )
    records_processed: int = Field(
        ...,
        ge=0,
        description="Total number of records generated during the run",
        example=100000
    )
    throughput: float = Field(
        ...,
        ge=0.0,
        description="Processing throughput in records per second",
        example=2190.0
    )
    status: str = Field(
        ...,
        description="Run completion status ('completed', 'failed', 'running')",
        example="completed"
    )
    configuration_summary: Dict[str, Any] = Field(
        ...,
        description="Key configuration parameters used for this run",
        example={
            "batch_size": 1000,
            "output_formats": ["csv", "json"],
            "parallel_workers": 4
        }
    )

    class Config:
        """Pydantic model configuration for optimal JSON serialization."""
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class RunDetailMetrics(BaseModel):
    """
    Detailed metrics model with stage-level performance breakdowns.

    Provides comprehensive performance data including timing for each pipeline
    stage, throughput metrics, resource utilization, and error statistics.
    """
    stage_timings: Dict[str, float] = Field(
        ...,
        description="Execution time in seconds for each pipeline stage",
        example={
            "initialization": 0.5,
            "record_creation": 38.2,
            "file_writing": 6.8,
            "finalization": 0.17
        }
    )
    throughput_metrics: Dict[str, float] = Field(
        ...,
        description="Throughput measurements for different processing stages",
        example={
            "overall_throughput": 2190.0,
            "creation_throughput": 2618.0,
            "writing_throughput": 14705.0
        }
    )
    resource_utilization: Dict[str, Any] = Field(
        ...,
        description="System resource usage statistics during execution",
        example={
            "peak_memory_mb": 512.3,
            "cpu_cores_used": 4,
            "disk_io_mb": 245.7,
            "network_io_mb": 0.0
        }
    )
    error_statistics: Dict[str, int] = Field(
        ...,
        description="Count of errors by type during execution",
        example={
            "validation_errors": 0,
            "io_errors": 0,
            "timeout_errors": 0,
            "total_errors": 0
        }
    )
    performance_breakdowns: Dict[str, Any] = Field(
        ...,
        description="Detailed performance analysis by component",
        example={
            "coordinator_overhead": 2.1,
            "creator_efficiency": 0.95,
            "writer_batch_size": 1000,
            "queue_wait_time": 0.03
        }
    )


class RunListResponse(BaseModel):
    """
    Response model for the /api/runs endpoint providing paginated run listings.

    Contains a list of run summaries with pagination metadata and aggregate
    statistics for efficient browsing of historical data generation runs.
    """
    runs: List[RunSummary] = Field(
        ...,
        description="List of run summary objects for the current page",
        example=[]
    )
    pagination: PaginationMeta = Field(
        ...,
        description="Pagination metadata for the current request"
    )
    total_runs: int = Field(
        ...,
        ge=0,
        description="Total number of runs available across all pages",
        example=237
    )
    summary_statistics: Dict[str, Any] = Field(
        ...,
        description="Aggregate statistics across all available runs",
        example={
            "average_duration": 42.5,
            "total_records_generated": 23700000,
            "success_rate": 0.987
        }
    )


class RunDetailResponse(BaseModel):
    """
    Response model for the /api/runs/{run_id} endpoint providing complete run details.

    Contains comprehensive metrics, configuration, execution context, and file outputs
    for a specific data generation run.
    """
    run_id: str = Field(
        ...,
        description="Unique identifier for the requested run",
        example="run_20240801_101530"
    )
    metrics: RunDetailMetrics = Field(
        ...,
        description="Comprehensive performance metrics for this run"
    )
    configuration: Dict[str, Any] = Field(
        ...,
        description="Complete configuration parameters used for this run",
        example={
            "batch_size": 1000,
            "output_formats": ["csv", "json"],
            "parallel_workers": 4,
            "domain_objects": ["accounts", "trades", "positions"]
        }
    )
    execution_context: Dict[str, Any] = Field(
        ...,
        description="Runtime environment and execution context information",
        example={
            "python_version": "3.9.7",
            "system_platform": "linux",
            "available_memory_gb": 8.0,
            "cpu_count": 8
        }
    )
    file_outputs: List[Dict[str, Any]] = Field(
        ...,
        description="List of generated output files with metadata",
        example=[
            {
                "filename": "accounts_20240801_101530.csv",
                "format": "csv",
                "size_bytes": 1048576,
                "record_count": 10000,
                "created_at": "2024-08-01T10:16:15.123456"
            }
        ]
    )


class ComparisonMetrics(BaseModel):
    """
    Model for side-by-side metrics comparison between runs.

    Provides performance data for individual runs along with delta analysis
    and relative performance rankings for comparative analysis.
    """
    run_id: str = Field(
        ...,
        description="Unique identifier for this run in the comparison",
        example="run_20240801_101530"
    )
    metrics: RunDetailMetrics = Field(
        ...,
        description="Complete performance metrics for this run"
    )
    delta_analysis: Dict[str, Union[float, str]] = Field(
        ...,
        description="Performance deltas compared to other runs in the comparison",
        example={
            "duration_delta_seconds": -5.2,
            "throughput_delta_percent": 12.5,
            "relative_performance": "better"
        }
    )
    performance_ranking: Dict[str, int] = Field(
        ...,
        description="Ranking of this run across different performance metrics",
        example={
            "duration_rank": 2,
            "throughput_rank": 1,
            "resource_efficiency_rank": 3
        }
    )


class CompareRunsResponse(BaseModel):
    """
    Response model for the /api/runs/compare endpoint providing multi-run analysis.

    Contains comparison data for multiple runs with differential analysis,
    performance rankings, and optimization recommendations.
    """
    runs: List[ComparisonMetrics] = Field(
        ...,
        description="List of runs with their comparison metrics and analysis"
    )
    comparison_analysis: Dict[str, Any] = Field(
        ...,
        description="Aggregate comparison analysis across all selected runs",
        example={
            "performance_variance": 0.15,
            "optimization_opportunities": ["batch_size_tuning", "worker_count_optimization"],
            "trend_analysis": "improving"
        }
    )
    best_performer: Dict[str, str] = Field(
        ...,
        description="Identification of best performing run by different metrics",
        example={
            "fastest_duration": "run_20240801_143022",
            "highest_throughput": "run_20240801_101530",
            "most_efficient": "run_20240801_143022"
        }
    )
    recommendations: List[Dict[str, Any]] = Field(
        ...,
        description="Performance optimization recommendations based on comparison analysis",
        example=[
            {
                "category": "configuration",
                "recommendation": "Increase batch size to 1500 for optimal throughput",
                "expected_improvement": "8-12% throughput increase"
            }
        ]
    )


class LatestMetricsResponse(BaseModel):
    """
    Response model for the /api/metrics/latest endpoint providing real-time data.

    Contains current run information, latest completed run metrics, active status,
    and real-time performance indicators for live monitoring.
    """
    current_run: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Information about the currently executing run, if any",
        example={
            "run_id": "run_20240801_153045",
            "started_at": "2024-08-01T15:30:45.123456",
            "progress_percent": 65.2,
            "estimated_completion": "2024-08-01T15:32:10.000000"
        }
    )
    latest_completed: Optional[RunSummary] = Field(
        default=None,
        description="Summary information for the most recently completed run"
    )
    is_active: bool = Field(
        ...,
        description="Whether a data generation run is currently executing",
        example=True
    )

    real_time_metrics: Dict[str, Any] = Field(
        ...,
        description="Live performance metrics for the active run or system status",
        example={
            "current_throughput": 2150.0,
            "records_processed": 65200,
            "elapsed_time": 30.3,
            "memory_usage_mb": 387.2,
            "cpu_utilization_percent": 78.5
        }
    )
