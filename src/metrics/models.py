"""
Data models for metric types and run metadata.

This module defines the structure and schema for performance metrics collected
during data generation runs. Provides Pydantic-compatible data classes for
type-safe serialization and validation of metrics data used by both the
MetricsCollector and the FastAPI service endpoints.

Classes:
    RunMetrics: Core run information including timing and duration
    PerformanceMetrics: Pipeline stage performance measurements
    ResourceUtilization: System resource usage metrics
    ConfigurationMetrics: Run configuration and record count information
    StageTiming: Individual pipeline stage timing data
    ThroughputMetrics: Records per second and throughput statistics
    ComparisonMetrics: Cross-run performance analysis data
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from uuid import uuid4


class RunMetrics:
    """
    Core run metadata including timing and execution context.

    Captures essential information about each data generation run including
    unique identifiers, execution timestamps, and overall duration metrics.
    Used as the primary container for run-level performance data.
    """

    def __init__(
        self,
        run_id: Optional[str] = None,
        start_time: Optional[datetime] = ...,
        end_time: Optional[datetime] = None,
        total_duration_seconds: Optional[float] = None
    ):
        """
        Initialize run metrics with timing and identification data.

        Args:
            run_id: Unique identifier for the run (UUID4 if not provided)
            start_time: Run start timestamp (current time if not provided)
            end_time: Run completion timestamp (None if run in progress)
            total_duration_seconds: Total execution time in seconds
        """
        self.run_id = run_id or str(uuid4())
        if start_time is ...:
            self.start_time = datetime.now()
        else:
            self.start_time = start_time
        self.end_time = end_time
        self.total_duration_seconds = total_duration_seconds

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert run metrics to dictionary for JSON serialization.

        Returns:
            Dictionary representation with ISO 8601 formatted timestamps
        """
        return {
            "run_id": self.run_id,
            "start_time": (self.start_time.isoformat()
                           if self.start_time else None),
            "end_time": (self.end_time.isoformat()
                         if self.end_time else None),
            "total_duration_seconds": self.total_duration_seconds
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunMetrics":
        """
        Create RunMetrics instance from dictionary data.

        Args:
            data: Dictionary containing run metrics data

        Returns:
            RunMetrics instance with parsed datetime objects
        """
        start_time_val = data.get("start_time")
        end_time_val = data.get("end_time")
        return cls(
            run_id=data.get("run_id"),
            start_time=(datetime.fromisoformat(start_time_val)
                        if start_time_val else None),
            end_time=(datetime.fromisoformat(end_time_val)
                      if end_time_val else None),
            total_duration_seconds=data.get("total_duration_seconds")
        )


class PerformanceMetrics:
    """
    Pipeline stage performance measurements and timing data.

    Contains detailed timing and throughput metrics for each major pipeline
    component including coordinator orchestration, creator pool operations,
    and writer output generation. Used for performance analysis and
    optimization.
    """

    def __init__(
        self,
        coordinator: Optional[Dict[str, Any]] = None,
        creators: Optional[Dict[str, Any]] = None,
        writers: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize performance metrics for pipeline components.

        Args:
            coordinator: Coordinator timing and orchestration metrics
            creators: Creator pool throughput and processing metrics
            writers: Writer output performance and file generation metrics
        """
        self.coordinator = coordinator or {}
        self.creators = creators or {}
        self.writers = writers or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert performance metrics to dictionary for JSON serialization.

        Returns:
            Dictionary representation of all pipeline stage metrics
        """
        return {
            "coordinator": self.coordinator,
            "creators": self.creators,
            "writers": self.writers
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PerformanceMetrics":
        """
        Create PerformanceMetrics instance from dictionary data.

        Args:
            data: Dictionary containing performance metrics data

        Returns:
            PerformanceMetrics instance with parsed component data
        """
        return cls(
            coordinator=data.get("coordinator", {}),
            creators=data.get("creators", {}),
            writers=data.get("writers", {})
        )


class ResourceUtilization:
    """
    System resource usage metrics during generation runs.

    Captures CPU, memory, and process utilization data to enable resource
    optimization and capacity planning. Used for identifying bottlenecks
    and ensuring efficient resource utilization across generation runs.
    """

    def __init__(
        self,
        peak_memory_mb: Optional[float] = None,
        avg_cpu_percent: Optional[float] = None,
        process_count: Optional[int] = None
    ):
        """
        Initialize resource utilization metrics.

        Args:
            peak_memory_mb: Maximum memory usage in megabytes
            avg_cpu_percent: Average CPU utilization percentage
            process_count: Number of worker processes used
        """
        self.peak_memory_mb = peak_memory_mb
        self.avg_cpu_percent = avg_cpu_percent
        self.process_count = process_count

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert resource metrics to dictionary for JSON serialization.

        Returns:
            Dictionary representation of resource utilization data
        """
        return {
            "peak_memory_mb": self.peak_memory_mb,
            "avg_cpu_percent": self.avg_cpu_percent,
            "process_count": self.process_count
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResourceUtilization":
        """
        Create ResourceUtilization instance from dictionary data.

        Args:
            data: Dictionary containing resource utilization data

        Returns:
            ResourceUtilization instance with parsed metrics
        """
        return cls(
            peak_memory_mb=data.get("peak_memory_mb"),
            avg_cpu_percent=data.get("avg_cpu_percent"),
            process_count=data.get("process_count")
        )


class ConfigurationMetrics:
    """
    Run configuration and record generation count information.

    Captures the configuration parameters and record counts for each factory
    type used in the generation run. Essential for correlating performance
    metrics with specific configuration settings and data volumes.
    """

    def __init__(
        self,
        factories: Optional[List[str]] = None,
        record_counts: Optional[Dict[str, int]] = None
    ):
        """
        Initialize configuration metrics.

        Args:
            factories: List of factory types used in the run
            record_counts: Dictionary mapping factory names to record counts
        """
        self.factories = factories or []
        self.record_counts = record_counts or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration metrics to dictionary for JSON serialization.

        Returns:
            Dictionary representation of configuration and count data
        """
        return {
            "factories": self.factories,
            "record_counts": self.record_counts
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConfigurationMetrics":
        """
        Create ConfigurationMetrics instance from dictionary data.

        Args:
            data: Dictionary containing configuration metrics data

        Returns:
            ConfigurationMetrics instance with parsed configuration
        """
        return cls(
            factories=data.get("factories", []),
            record_counts=data.get("record_counts", {})
        )


class StageTiming:
    """
    Individual pipeline stage timing and duration data.

    Provides detailed timing information for individual stages within the
    data generation pipeline. Used for identifying performance bottlenecks
    and optimizing pipeline stage execution order and parallelization.
    """

    def __init__(
        self,
        stage_name: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        duration_seconds: Optional[float] = None
    ):
        """
        Initialize stage timing metrics.

        Args:
            stage_name: Name identifier for the pipeline stage
            start_time: Stage start timestamp
            end_time: Stage completion timestamp
            duration_seconds: Stage execution duration in seconds
        """
        self.stage_name = stage_name
        self.start_time = start_time
        self.end_time = end_time
        self.duration_seconds = duration_seconds

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert stage timing to dictionary for JSON serialization.

        Returns:
            Dictionary representation with ISO 8601 formatted timestamps
        """
        return {
            "stage_name": self.stage_name,
            "start_time": (self.start_time.isoformat()
                           if self.start_time else None),
            "end_time": (self.end_time.isoformat()
                         if self.end_time else None),
            "duration_seconds": self.duration_seconds
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StageTiming":
        """
        Create StageTiming instance from dictionary data.

        Args:
            data: Dictionary containing stage timing data

        Returns:
            StageTiming instance with parsed datetime objects
        """
        start_time_val = data.get("start_time")
        end_time_val = data.get("end_time")
        return cls(
            stage_name=data["stage_name"],
            start_time=(datetime.fromisoformat(start_time_val)
                        if start_time_val else None),
            end_time=(datetime.fromisoformat(end_time_val)
                      if end_time_val else None),
            duration_seconds=data.get("duration_seconds")
        )


class ThroughputMetrics:
    """
    Records per second and throughput performance statistics.

    Captures detailed throughput measurements including instantaneous rates,
    average performance over time, and peak throughput achieved during
    generation runs. Critical for performance optimization and capacity
    planning.
    """

    def __init__(
        self,
        records_per_second: Optional[float] = None,
        avg_throughput: Optional[float] = None,
        peak_throughput: Optional[float] = None
    ):
        """
        Initialize throughput metrics.

        Args:
            records_per_second: Current or final records per second rate
            avg_throughput: Average throughput over the entire run
            peak_throughput: Maximum throughput achieved during run
        """
        self.records_per_second = records_per_second
        self.avg_throughput = avg_throughput
        self.peak_throughput = peak_throughput

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert throughput metrics to dictionary for JSON serialization.

        Returns:
            Dictionary representation of throughput performance data
        """
        return {
            "records_per_second": self.records_per_second,
            "avg_throughput": self.avg_throughput,
            "peak_throughput": self.peak_throughput
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ThroughputMetrics":
        """
        Create ThroughputMetrics instance from dictionary data.

        Args:
            data: Dictionary containing throughput metrics data

        Returns:
            ThroughputMetrics instance with parsed performance data
        """
        return cls(
            records_per_second=data.get("records_per_second"),
            avg_throughput=data.get("avg_throughput"),
            peak_throughput=data.get("peak_throughput")
        )


class ComparisonMetrics:
    """
    Cross-run performance analysis and comparison data.

    Provides comparative analysis capabilities between multiple generation
    runs, including delta calculations, performance rankings, and trend
    analysis. Used by the dashboard for historical performance comparison
    and optimization guidance.
    """

    def __init__(
        self,
        run_id: str,
        metrics: Optional[Dict[str, Any]] = None,
        delta_analysis: Optional[Dict[str, Any]] = None,
        performance_ranking: Optional[Dict[str, Union[int, float]]] = None
    ):
        """
        Initialize comparison metrics for cross-run analysis.

        Args:
            run_id: Identifier for the run being compared
            metrics: Core performance metrics for the run
            delta_analysis: Comparison deltas against baseline or previous
                           runs
            performance_ranking: Ranking metrics compared to historical runs
        """
        self.run_id = run_id
        self.metrics = metrics or {}
        self.delta_analysis = delta_analysis or {}
        self.performance_ranking = performance_ranking or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert comparison metrics to dictionary for JSON serialization.

        Returns:
            Dictionary representation of comparison analysis data
        """
        return {
            "run_id": self.run_id,
            "metrics": self.metrics,
            "delta_analysis": self.delta_analysis,
            "performance_ranking": self.performance_ranking
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComparisonMetrics":
        """
        Create ComparisonMetrics instance from dictionary data.

        Args:
            data: Dictionary containing comparison metrics data

        Returns:
            ComparisonMetrics instance with parsed comparison data
        """
        return cls(
            run_id=data["run_id"],
            metrics=data.get("metrics", {}),
            delta_analysis=data.get("delta_analysis", {}),
            performance_ranking=data.get("performance_ranking", {})
        )
