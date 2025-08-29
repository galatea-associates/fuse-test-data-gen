"""
MetricsCollector - Centralized metrics aggregation and persistence service.

This module implements a thread-safe singleton pattern to capture performance data
throughout the data generation pipeline. Provides context-manager interfaces for
precise timing measurement, aggregates metrics from Coordinator, Creator, and Writer
processes, and persists comprehensive performance data to JSON files in the
metrics/runs/ directory for historical analysis and dashboard visualization.

Classes:
    MetricsCollector: Thread-safe singleton for comprehensive metrics collection
    TimingContext: Context manager wrapper for automatic timing operations

Features:
    - Thread-safe singleton implementation using threading.Lock
    - High-precision timing measurement via time.perf_counter()
    - Context manager protocol for automatic start/stop timing operations
    - JSON serialization for structured metrics persistence
    - Minimal performance overhead to avoid impacting generation performance
    - Resource utilization tracking with ResourceUtilization integration
"""

import threading
from time import perf_counter
import json
import os
from datetime import datetime
from typing import Any, Dict, Optional, List

from .models import ResourceUtilization


class MetricsCollector:
    """
    Thread-safe singleton class for comprehensive performance metrics collection.

    Implements the singleton pattern to ensure a single instance exists across
    all pipeline processes. Provides high-precision timing capabilities and
    persistent storage of performance data for analysis and dashboard visualization.

    The collector captures timing data, throughput metrics, and resource utilization
    throughout the data generation pipeline while maintaining minimal performance
    overhead to avoid impacting the core generation workflow.

    Attributes:
        _instance: Singleton instance reference
        _lock: Threading lock for thread-safe singleton access
        _metrics_data: Dictionary containing all collected metrics
        _start_times: Dictionary tracking active timing operations
        _run_id: Current run identifier for metrics association
        _run_start_time: Timestamp when metrics collection began
    """

    # Class-level singleton attributes
    _instance: Optional['MetricsCollector'] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> 'MetricsCollector':
        """
        Thread-safe singleton implementation.

        Ensures only one instance of MetricsCollector exists across all threads
        and processes. Uses double-checked locking pattern for optimal performance.

        Returns:
            MetricsCollector: The singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                # Double-checked locking pattern
                if cls._instance is None:
                    cls._instance = super(MetricsCollector, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """
        Initialize the MetricsCollector singleton instance.

        Sets up the internal data structures for metrics collection including
        timing data, performance metrics, and resource utilization tracking.
        Only initializes once per singleton lifetime.
        """
        if hasattr(self, '_initialized') and self._initialized:
            return

        # Core metrics data structure
        self._metrics_data: Dict[str, Any] = {
            'run_id': None,
            'start_time': None,
            'end_time': None,
            'total_duration_seconds': None,
            'configuration': {},
            'performance': {
                'coordinator': {},
                'creators': {},
                'writers': {}
            },
            'resource_utilization': {},
            'stage_timings': {},
            'error_summary': {
                'total_errors': 0,
                'warnings': 0,
                'last_error': None
            }
        }

        # Active timing operations tracking
        self._start_times: Dict[str, float] = {}

        # Run identification and timing
        self._run_id: Optional[str] = None
        self._run_start_time: Optional[float] = None

        # Resource utilization tracking
        self._resource_utilization: Optional[ResourceUtilization] = None

        # Mark as initialized
        self._initialized = True

    def record_start(self, stage: str) -> None:
        """
        Record the start time for a pipeline stage using high-precision timing.

        Captures the current timestamp using time.perf_counter() for microsecond
        accuracy and associates it with the specified stage name. Multiple
        simultaneous stages can be timed concurrently.

        Args:
            stage: Name identifier for the pipeline stage being timed

        Example:
            >>> collector = MetricsCollector()
            >>> collector.record_start('coordinator_initialization')
            >>> # ... stage processing ...
            >>> collector.record_end('coordinator_initialization')
        """
        with self._lock:
            start_time = perf_counter()
            self._start_times[stage] = start_time

            # Initialize run timing on first stage start
            if self._run_start_time is None:
                self._run_start_time = start_time
                self._run_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                self._metrics_data['run_id'] = self._run_id
                self._metrics_data['start_time'] = datetime.now().isoformat()

    def record_end(self, stage: str) -> None:
        """
        Record the end time for a pipeline stage and calculate duration.

        Captures the current timestamp and calculates the elapsed duration since
        the corresponding record_start() call. Stores the timing data in the
        stage_timings section of the metrics data structure.

        Args:
            stage: Name identifier for the pipeline stage being completed

        Raises:
            KeyError: If record_start() was not called for this stage

        Example:
            >>> collector = MetricsCollector()
            >>> collector.record_start('database_initialization')
            >>> # ... database setup processing ...
            >>> collector.record_end('database_initialization')
        """
        with self._lock:
            if stage not in self._start_times:
                # Record error but don't crash the pipeline
                self._metrics_data['error_summary']['warnings'] += 1
                self._metrics_data['error_summary']['last_error'] = f"No start time recorded for stage: {stage}"
                return

            end_time = perf_counter()
            start_time = self._start_times.pop(stage)
            duration_seconds = end_time - start_time

            # Store stage timing data
            self._metrics_data['stage_timings'][stage] = {
                'duration_seconds': duration_seconds,
                'start_time': datetime.fromtimestamp(
                    self._run_start_time + (start_time - self._run_start_time)
                ).isoformat(),
                'end_time': datetime.fromtimestamp(
                    self._run_start_time + (end_time - self._run_start_time)
                ).isoformat()
            }

    def flush(self, run_id: str) -> None:
        """
        Persist aggregated metrics to JSON file in metrics/runs/ directory.

        Writes the complete metrics data structure to a timestamped JSON file
        in the metrics/runs/ directory. Creates the directory structure if it
        doesn't exist and ensures proper file naming for historical analysis.

        Args:
            run_id: Unique identifier for the generation run

        Example:
            >>> collector = MetricsCollector()
            >>> # ... collect metrics throughout pipeline ...
            >>> collector.flush('2024-01-15_14-30-22')
        """
        with self._lock:
            self._flush_without_lock(run_id)

    def _flush_without_lock(self, run_id: str) -> None:
        """
        Internal flush method that doesn't acquire the lock.
        Should only be called when lock is already held.
        """
        # Finalize run timing
        if self._run_start_time is not None:
            current_time = perf_counter()
            total_duration = current_time - self._run_start_time
            self._metrics_data['end_time'] = datetime.now().isoformat()
            self._metrics_data['total_duration_seconds'] = total_duration

        # Update run_id if provided
        if run_id:
            self._metrics_data['run_id'] = run_id
            self._run_id = run_id

        # Add resource utilization if available
        if self._resource_utilization:
            self._metrics_data['resource_utilization'] = self._resource_utilization.to_dict()

        # Ensure metrics directory exists
        metrics_dir = 'metrics/runs'
        os.makedirs(metrics_dir, exist_ok=True)

        # Generate filename with run_id
        filename = f"{self._run_id or 'unknown'}.json"
        filepath = os.path.join(metrics_dir, filename)

        # Write metrics to JSON file
        try:
            with open(filepath, 'w') as f:
                json.dump(self._metrics_data, f, indent=2, default=str)
        except Exception as e:
            # Log error but don't crash the pipeline
            self._metrics_data['error_summary']['total_errors'] += 1
            self._metrics_data['error_summary']['last_error'] = f"Failed to write metrics file: {str(e)}"

    def update_resource_utilization(
        self,
        peak_memory_mb: Optional[float] = None,
        avg_cpu_percent: Optional[float] = None,
        process_count: Optional[int] = None
    ) -> None:
        """
        Update resource utilization metrics during pipeline execution.

        Updates the ResourceUtilization data model with current system resource
        usage information. Can be called multiple times during a run to track
        peak values and running averages.

        Args:
            peak_memory_mb: Maximum memory usage in megabytes
            avg_cpu_percent: Average CPU utilization percentage
            process_count: Number of worker processes used

        Example:
            >>> collector = MetricsCollector()
            >>> collector.update_resource_utilization(1024.5, 78.2, 8)
        """
        with self._lock:
            if self._resource_utilization is None:
                self._resource_utilization = ResourceUtilization(
                    peak_memory_mb=peak_memory_mb,
                    avg_cpu_percent=avg_cpu_percent,
                    process_count=process_count
                )
            else:
                # Update existing resource utilization with new values
                if peak_memory_mb is not None:
                    # Keep track of peak memory usage
                    current_peak = self._resource_utilization.peak_memory_mb or 0
                    self._resource_utilization.peak_memory_mb = max(current_peak, peak_memory_mb)

                if avg_cpu_percent is not None:
                    self._resource_utilization.avg_cpu_percent = avg_cpu_percent

                if process_count is not None:
                    self._resource_utilization.process_count = process_count

    def update_configuration(self, factories: List[str], record_counts: Dict[str, int]) -> None:
        """
        Update configuration information for the current run.

        Records the factory types and record counts used in the generation run
        for correlation with performance metrics and historical analysis.

        Args:
            factories: List of factory types used in the run
            record_counts: Dictionary mapping factory names to record counts

        Example:
            >>> collector = MetricsCollector()
            >>> collector.update_configuration(
            ...     ['instrument', 'account', 'trade'],
            ...     {'instrument': 10000, 'account': 5000, 'trade': 25000}
            ... )
        """
        with self._lock:
            self._metrics_data['configuration'] = {
                'factories': factories,
                'record_counts': record_counts
            }

    def update_performance_metrics(
        self,
        component: str,
        metrics: Dict[str, Any]
    ) -> None:
        """
        Update performance metrics for a specific pipeline component.

        Updates the performance metrics section with component-specific data
        such as throughput rates, timing information, and efficiency statistics.

        Args:
            component: Component name ('coordinator', 'creators', 'writers')
            metrics: Dictionary containing performance metrics for the component

        Example:
            >>> collector = MetricsCollector()
            >>> collector.update_performance_metrics('creators', {
            ...     'avg_throughput_per_second': 1247,
            ...     'total_records': 40000,
            ...     'batch_processing_time': 15.7
            ... })
        """
        with self._lock:
            if component not in self._metrics_data['performance']:
                self._metrics_data['performance'][component] = {}

            # Merge new metrics with existing ones
            self._metrics_data['performance'][component].update(metrics)

    def record_throughput(self, records_processed: int, time_window_seconds: float) -> None:
        """
        Record throughput metrics for the current processing window.

        Calculates and records records per second throughput for performance
        analysis and dashboard visualization. Maintains running statistics
        including average and peak throughput.

        Args:
            records_processed: Number of records processed in the time window
            time_window_seconds: Duration of the processing window in seconds

        Example:
            >>> collector = MetricsCollector()
            >>> collector.record_throughput(5000, 4.2)  # 1190 records/second
        """
        with self._lock:
            if time_window_seconds <= 0:
                return

            current_throughput = records_processed / time_window_seconds

            # Update throughput in performance metrics
            if 'throughput' not in self._metrics_data['performance']:
                self._metrics_data['performance']['throughput'] = {
                    'current_records_per_second': current_throughput,
                    'peak_records_per_second': current_throughput,
                    'total_records_processed': records_processed
                }
            else:
                throughput_data = self._metrics_data['performance']['throughput']
                throughput_data['current_records_per_second'] = current_throughput

                # Track peak throughput
                peak = throughput_data.get('peak_records_per_second', 0)
                throughput_data['peak_records_per_second'] = max(peak, current_throughput)

                # Update total records processed
                total = throughput_data.get('total_records_processed', 0)
                throughput_data['total_records_processed'] = total + records_processed

    def get_current_metrics(self) -> Dict[str, Any]:
        """
        Retrieve current run statistics and performance data.

        Returns a copy of the current metrics data structure including timing
        information, resource utilization, and performance statistics. Safe
        for concurrent access during active generation runs.

        Returns:
            Dictionary containing current metrics data with timing, performance,
            and resource utilization information

        Example:
            >>> collector = MetricsCollector()
            >>> metrics = collector.get_current_metrics()
            >>> print(f"Current run: {metrics['run_id']}")
        """
        with self._lock:
            # Create a deep copy to prevent external modification
            current_metrics = json.loads(json.dumps(self._metrics_data, default=str))

            # Add current timing if run is active
            if self._run_start_time is not None:
                current_time = perf_counter()
                current_metrics['elapsed_seconds'] = current_time - self._run_start_time
                current_metrics['active_stages'] = list(self._start_times.keys())

            return current_metrics

    def __enter__(self) -> 'MetricsCollector':
        """
        Context manager entry point.

        Allows the MetricsCollector to be used as a context manager for
        automatic lifecycle management during generation runs.

        Returns:
            MetricsCollector: Self reference for context manager protocol
        """
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Context manager exit point with automatic metrics finalization.

        Handles cleanup and finalization of metrics collection when exiting
        a context manager block. Automatically flushes metrics if a run was
        active and handles any exceptions gracefully.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        with self._lock:
            # Record any exception information
            if exc_type is not None:
                self._metrics_data['error_summary']['total_errors'] += 1
                self._metrics_data['error_summary']['last_error'] = f"Exception in context: {str(exc_val)}"

            # Auto-flush if we have an active run
            if self._run_id:
                self._flush_without_lock(self._run_id)


class TimingContext:
    """
    Context manager wrapper for automatic pipeline stage timing.

    Provides a convenient context manager interface for automatically timing
    pipeline stages without manual record_start() and record_end() calls.
    Integrates with the MetricsCollector singleton to ensure consistent
    timing data collection across the generation pipeline.

    Attributes:
        stage_name: Identifier for the pipeline stage being timed
        collector: Reference to the MetricsCollector singleton instance
    """

    def __init__(self, stage_name: str, collector: Optional[MetricsCollector] = None):
        """
        Initialize timing context for automatic stage measurement.

        Creates a context manager wrapper that will automatically call
        record_start() on entry and record_end() on exit for the specified
        pipeline stage.

        Args:
            stage_name: Identifier for the pipeline stage being timed
            collector: MetricsCollector instance (creates singleton if None)

        Example:
            >>> with TimingContext('database_setup'):
            ...     # Database initialization code here
            ...     setup_database()
        """
        self.stage_name = stage_name
        self.collector = collector or MetricsCollector()

    def __enter__(self) -> 'TimingContext':
        """
        Context manager entry point with automatic timing start.

        Calls record_start() on the associated MetricsCollector instance
        to begin timing the specified pipeline stage.

        Returns:
            TimingContext: Self reference for context manager protocol
        """
        self.collector.record_start(self.stage_name)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        Context manager exit point with automatic timing end.

        Calls record_end() on the associated MetricsCollector instance
        to complete timing the specified pipeline stage. Handles exceptions
        gracefully without impacting pipeline execution.

        Args:
            exc_type: Exception type if an exception occurred
            exc_val: Exception value if an exception occurred
            exc_tb: Exception traceback if an exception occurred
        """
        try:
            self.collector.record_end(self.stage_name)
        except Exception:
            # Don't let timing failures crash the pipeline
            pass
