"""
FastAPI route handlers for metrics endpoints.

This module implements comprehensive REST API endpoints for retrieving performance
metrics from the FUSE Test Data Generator monitoring system. Provides endpoints
for run listings, detailed run metrics, multi-run comparisons, and real-time
execution data.

All route handlers implement async patterns for optimal performance and use
Pydantic models for request/response validation. The module integrates directly
with the file-based metrics storage system in the metrics/runs/ directory.

Endpoints:
- GET /runs: Paginated listing of all available runs
- GET /runs/{run_id}: Detailed metrics for a specific run
- POST /runs/compare: Side-by-side comparison of multiple runs  
- GET /latest: Real-time metrics from the most recent execution
"""

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

from fastapi import APIRouter, HTTPException, Query, Path as FastAPIPath, status
from pydantic import BaseModel, ValidationError

from src.api.models.responses import (
    RunSummary,
    RunListResponse,
    RunDetailResponse, 
    CompareRunsResponse,
    LatestMetricsResponse,
    ErrorResponse,
    PaginationMeta,
    RunDetailMetrics,
    ComparisonMetrics
)


# Initialize FastAPI router with prefix and tags
router = APIRouter(prefix="/api", tags=["metrics"])

# Constants for metrics storage
METRICS_DIR = Path("metrics/runs")
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 1000


class CompareRunsRequest(BaseModel):
    """
    Request model for the POST /api/runs/compare endpoint.
    
    Accepts a list of run IDs to be compared with optional comparison
    parameters and analysis preferences.
    """
    run_ids: List[str]
    include_recommendations: bool = True
    comparison_basis: str = "duration"  # duration, throughput, efficiency


def _get_run_file_path(run_id: str) -> Path:
    """
    Get the file path for a specific run's metrics data.
    
    Args:
        run_id: Unique identifier for the data generation run
        
    Returns:
        Path object pointing to the run's JSON metrics file
        
    Raises:
        HTTPException: If run_id contains path traversal attempts
    """
    # Security: Prevent path traversal attacks
    if ".." in run_id or "/" in run_id or "\\" in run_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid run_id format: {run_id}"
        )
    
    return METRICS_DIR / f"{run_id}.json"


def _load_run_metrics(run_id: str) -> Dict[str, Any]:
    """
    Load metrics data for a specific run from file storage.
    
    Args:
        run_id: Unique identifier for the data generation run
        
    Returns:
        Dictionary containing the complete metrics data for the run
        
    Raises:
        HTTPException: If run not found or file cannot be parsed
    """
    file_path = _get_run_file_path(run_id)
    
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run {run_id} not found in metrics storage"
        )
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse metrics file for run {run_id}: {str(e)}"
        )
    except IOError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read metrics file for run {run_id}: {str(e)}"
        )


def _list_available_runs() -> List[str]:
    """
    Get a list of all available run IDs from the metrics directory.
    
    Returns:
        List of run IDs sorted by timestamp (newest first)
    """
    if not METRICS_DIR.exists():
        return []
    
    try:
        # Get all JSON files in metrics directory
        json_files = [f for f in os.listdir(str(METRICS_DIR)) 
                     if f.endswith('.json') and os.path.isfile(
                         os.path.join(str(METRICS_DIR), f))]
        
        # Extract run IDs (remove .json extension)
        run_ids = [f[:-5] for f in json_files]
        
        # Sort by modification time (newest first)
        run_ids.sort(key=lambda run_id: os.path.getmtime(
            str(_get_run_file_path(run_id))), reverse=True)
        
        return run_ids
    
    except OSError:
        return []


def _create_run_summary(run_data: Dict[str, Any], run_id: str) -> RunSummary:
    """
    Create a RunSummary object from raw metrics data.
    
    Args:
        run_data: Raw metrics data loaded from JSON file
        run_id: Unique identifier for the run
        
    Returns:
        RunSummary instance with essential run information
    """
    # Extract timestamp from run_data or use file modification time as fallback
    timestamp_str = run_data.get('timestamp')
    if timestamp_str:
        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    else:
        # Fallback to file modification time
        file_path = _get_run_file_path(run_id)
        timestamp = datetime.fromtimestamp(os.path.getmtime(str(file_path)))
    
    # Extract key metrics with safe defaults
    total_duration = run_data.get('total_duration', 0.0)
    records_processed = run_data.get('records_processed', 0)
    
    # Calculate throughput safely
    throughput = 0.0
    if total_duration > 0 and records_processed > 0:
        throughput = records_processed / total_duration
    
    return RunSummary(
        run_id=run_id,
        timestamp=timestamp,
        total_duration=total_duration,
        records_processed=records_processed,
        throughput=throughput,
        status=run_data.get('status', 'unknown'),
        configuration_summary=run_data.get('configuration_summary', {})
    )


@router.get("/runs", response_model=RunListResponse)
async def list_runs(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, 
                      description="Items per page"),
    sort_by: str = Query("timestamp", 
                        description="Sort field (timestamp, duration, throughput)"),
    order: str = Query("desc", regex="^(asc|desc)$", 
                      description="Sort order")
) -> RunListResponse:
    """
    List all available data generation runs with pagination support.
    
    Retrieves run summaries from the metrics storage directory with configurable
    pagination, sorting, and filtering options. Provides aggregate statistics
    for the entire run history.
    
    Query Parameters:
    - page: Page number for pagination (1-based)
    - limit: Number of runs per page (1-1000)
    - sort_by: Field to sort by (timestamp, duration, throughput)  
    - order: Sort direction (asc, desc)
    
    Returns:
        Paginated list of run summaries with metadata
    """
    try:
        # Get all available runs
        all_run_ids = _list_available_runs()
        total_runs = len(all_run_ids)
        
        if total_runs == 0:
            return RunListResponse(
                runs=[],
                pagination=PaginationMeta(
                    page=1,
                    limit=limit,
                    total_pages=0,
                    total_items=0,
                    has_next=False,
                    has_previous=False
                ),
                total_runs=0,
                summary_statistics={
                    "average_duration": 0.0,
                    "total_records_generated": 0,
                    "success_rate": 0.0
                }
            )
        
        # Load run summaries for sorting
        run_summaries = []
        total_records = 0
        total_duration = 0.0
        success_count = 0
        
        for run_id in all_run_ids:
            try:
                run_data = _load_run_metrics(run_id)
                summary = _create_run_summary(run_data, run_id)
                run_summaries.append(summary)
                
                # Collect statistics
                total_records += summary.records_processed
                total_duration += summary.total_duration
                if summary.status == "completed":
                    success_count += 1
                    
            except HTTPException:
                # Skip runs that cannot be loaded
                continue
        
        # Sort runs based on parameters
        reverse_order = (order == "desc")
        if sort_by == "timestamp":
            run_summaries.sort(key=lambda r: r.timestamp, reverse=reverse_order)
        elif sort_by == "duration":
            run_summaries.sort(key=lambda r: r.total_duration, reverse=reverse_order)
        elif sort_by == "throughput":
            run_summaries.sort(key=lambda r: r.throughput, reverse=reverse_order)
        
        # Apply pagination
        total_pages = (len(run_summaries) + limit - 1) // limit
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_runs = run_summaries[start_idx:end_idx]
        
        # Calculate summary statistics
        avg_duration = total_duration / len(run_summaries) if run_summaries else 0.0
        success_rate = success_count / len(run_summaries) if run_summaries else 0.0
        
        return RunListResponse(
            runs=paginated_runs,
            pagination=PaginationMeta(
                page=page,
                limit=limit,
                total_pages=max(1, total_pages),
                total_items=len(run_summaries),
                has_next=(page < total_pages),
                has_previous=(page > 1)
            ),
            total_runs=len(run_summaries),
            summary_statistics={
                "average_duration": avg_duration,
                "total_records_generated": total_records,
                "success_rate": success_rate
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve run list: {str(e)}"
        )


@router.get("/runs/{run_id}", response_model=RunDetailResponse)
async def get_run_details(
    run_id: str = FastAPIPath(..., description="Unique run identifier")
) -> RunDetailResponse:
    """
    Retrieve comprehensive metrics and details for a specific run.
    
    Provides complete performance breakdown including stage-level timing,
    throughput metrics, resource utilization, configuration parameters,
    execution context, and file output information.
    
    Path Parameters:
    - run_id: Unique identifier for the data generation run
    
    Returns:
        Complete run details with comprehensive metrics
        
    Raises:
        HTTPException: 404 if run not found, 500 for processing errors
    """
    try:
        # Load the raw metrics data
        run_data = _load_run_metrics(run_id)
        
        # Extract detailed metrics
        stage_timings = run_data.get('stage_timings', {})
        throughput_metrics = run_data.get('throughput_metrics', {})
        resource_utilization = run_data.get('resource_utilization', {})
        error_statistics = run_data.get('error_statistics', {})
        performance_breakdowns = run_data.get('performance_breakdowns', {})
        
        # Create detailed metrics object
        detailed_metrics = RunDetailMetrics(
            stage_timings=stage_timings,
            throughput_metrics=throughput_metrics,
            resource_utilization=resource_utilization,
            error_statistics=error_statistics,
            performance_breakdowns=performance_breakdowns
        )
        
        return RunDetailResponse(
            run_id=run_id,
            metrics=detailed_metrics,
            configuration=run_data.get('configuration', {}),
            execution_context=run_data.get('execution_context', {}),
            file_outputs=run_data.get('file_outputs', [])
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404)
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve run details for {run_id}: {str(e)}"
        )


@router.post("/runs/compare", response_model=CompareRunsResponse)
async def compare_runs(request: CompareRunsRequest) -> CompareRunsResponse:
    """
    Compare performance metrics across multiple data generation runs.
    
    Analyzes multiple runs side-by-side with delta calculations, performance
    rankings, optimization recommendations, and trend analysis. Supports
    various comparison criteria and analysis depths.
    
    Request Body:
    - run_ids: List of run identifiers to compare
    - include_recommendations: Whether to include optimization suggestions
    - comparison_basis: Primary metric for comparison (duration, throughput, efficiency)
    
    Returns:
        Comprehensive comparison analysis with recommendations
        
    Raises:
        HTTPException: 400 for invalid parameters, 404 if runs not found
    """
    if len(request.run_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 run IDs required for comparison"
        )
    
    if len(request.run_ids) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 runs allowed for comparison"
        )
    
    try:
        # Load metrics for all requested runs
        run_metrics = {}
        for run_id in request.run_ids:
            run_metrics[run_id] = _load_run_metrics(run_id)
        
        # Create comparison metrics for each run
        comparison_runs = []
        durations = []
        throughputs = []
        
        for run_id, run_data in run_metrics.items():
            # Extract basic metrics for comparison calculations
            duration = run_data.get('total_duration', 0.0)
            records = run_data.get('records_processed', 0)
            throughput = records / duration if duration > 0 else 0.0
            
            durations.append(duration)
            throughputs.append(throughput)
            
            # Create detailed metrics
            detailed_metrics = RunDetailMetrics(
                stage_timings=run_data.get('stage_timings', {}),
                throughput_metrics=run_data.get('throughput_metrics', {}),
                resource_utilization=run_data.get('resource_utilization', {}),
                error_statistics=run_data.get('error_statistics', {}),
                performance_breakdowns=run_data.get('performance_breakdowns', {})
            )
            
            # Calculate delta analysis (compared to average)
            avg_duration = sum(durations) / len(durations) if durations else 0.0
            avg_throughput = sum(throughputs) / len(throughputs) if throughputs else 0.0
            
            duration_delta = duration - avg_duration
            throughput_delta_percent = ((throughput - avg_throughput) / avg_throughput * 100 
                                      if avg_throughput > 0 else 0.0)
            
            # Determine relative performance
            if request.comparison_basis == "duration":
                relative_performance = ("better" if duration < avg_duration else 
                                      "worse" if duration > avg_duration else "average")
            else:  # throughput
                relative_performance = ("better" if throughput > avg_throughput else
                                      "worse" if throughput < avg_throughput else "average")
            
            delta_analysis = {
                "duration_delta_seconds": duration_delta,
                "throughput_delta_percent": throughput_delta_percent,
                "relative_performance": relative_performance
            }
            
            # Calculate performance rankings
            duration_rank = sorted(durations).index(duration) + 1
            throughput_rank = len(throughputs) - sorted(throughputs).index(throughput)
            
            performance_ranking = {
                "duration_rank": duration_rank,
                "throughput_rank": throughput_rank,
                "resource_efficiency_rank": duration_rank  # Simplified for now
            }
            
            comparison_runs.append(ComparisonMetrics(
                run_id=run_id,
                metrics=detailed_metrics,
                delta_analysis=delta_analysis,
                performance_ranking=performance_ranking
            ))
        
        # Calculate comparison analysis
        duration_variance = (max(durations) - min(durations)) / max(durations) if durations else 0.0
        throughput_variance = (max(throughputs) - min(throughputs)) / max(throughputs) if throughputs else 0.0
        
        performance_variance = max(duration_variance, throughput_variance)
        
        # Identify optimization opportunities
        optimization_opportunities = []
        if performance_variance > 0.2:  # 20% variance threshold
            optimization_opportunities.append("batch_size_tuning")
        if len(set(throughputs)) > 1:  # Different throughputs
            optimization_opportunities.append("worker_count_optimization")
        
        # Determine trend (simple analysis based on timestamps)
        if len(durations) >= 3:
            recent_avg = sum(durations[:len(durations)//2]) / (len(durations)//2)
            older_avg = sum(durations[len(durations)//2:]) / (len(durations) - len(durations)//2)
            trend_analysis = "improving" if recent_avg < older_avg else "declining"
        else:
            trend_analysis = "insufficient_data"
        
        comparison_analysis = {
            "performance_variance": performance_variance,
            "optimization_opportunities": optimization_opportunities,
            "trend_analysis": trend_analysis
        }
        
        # Identify best performers
        best_duration_idx = durations.index(min(durations))
        best_throughput_idx = throughputs.index(max(throughputs))
        best_efficiency_idx = best_duration_idx  # Simplified
        
        best_performer = {
            "fastest_duration": request.run_ids[best_duration_idx],
            "highest_throughput": request.run_ids[best_throughput_idx],
            "most_efficient": request.run_ids[best_efficiency_idx]
        }
        
        # Generate recommendations
        recommendations = []
        if request.include_recommendations:
            if performance_variance > 0.15:
                recommendations.append({
                    "category": "configuration",
                    "recommendation": "Standardize batch size and worker count for consistent performance",
                    "expected_improvement": f"{int(performance_variance*100)}% variance reduction"
                })
            
            best_throughput = max(throughputs)
            avg_throughput = sum(throughputs) / len(throughputs)
            if (best_throughput - avg_throughput) / avg_throughput > 0.1:
                recommendations.append({
                    "category": "optimization",
                    "recommendation": f"Adopt configuration from {best_performer['highest_throughput']} for improved throughput",
                    "expected_improvement": f"{int((best_throughput - avg_throughput) / avg_throughput * 100)}% throughput increase"
                })
        
        return CompareRunsResponse(
            runs=comparison_runs,
            comparison_analysis=comparison_analysis,
            best_performer=best_performer,
            recommendations=recommendations
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare runs: {str(e)}"
        )


@router.get("/metrics/latest", response_model=LatestMetricsResponse)
async def get_latest_metrics() -> LatestMetricsResponse:
    """
    Retrieve real-time metrics from the most recent data generation execution.
    
    Provides current run status, latest completed run information, and real-time
    performance indicators. Supports both active run monitoring and historical
    data access for the most recent execution.
    
    Returns:
        Latest execution metrics with current status information
        
    Raises:
        HTTPException: 500 for processing errors
    """
    try:
        # Get all available runs sorted by timestamp
        all_run_ids = _list_available_runs()
        
        if not all_run_ids:
            # No runs available
            return LatestMetricsResponse(
                current_run=None,
                latest_completed=None,
                is_active=False,
                real_time_metrics={
                    "current_throughput": 0.0,
                    "records_processed": 0,
                    "elapsed_time": 0.0,
                    "memory_usage_mb": 0.0,
                    "cpu_utilization_percent": 0.0
                }
            )
        
        # Get the most recent run
        latest_run_id = all_run_ids[0]
        latest_run_data = _load_run_metrics(latest_run_id)
        
        # Check if the run is currently active
        run_status = latest_run_data.get('status', 'unknown')
        is_active = (run_status == 'running')
        
        # Create run summary for latest completed run
        latest_completed = None
        if run_status == 'completed':
            latest_completed = _create_run_summary(latest_run_data, latest_run_id)
        elif len(all_run_ids) > 1:
            # Look for the most recent completed run
            for run_id in all_run_ids[1:]:
                try:
                    run_data = _load_run_metrics(run_id)
                    if run_data.get('status') == 'completed':
                        latest_completed = _create_run_summary(run_data, run_id)
                        break
                except HTTPException:
                    continue
        
        # Prepare current run information if active
        current_run = None
        if is_active:
            # Extract timestamp for started_at
            timestamp_str = latest_run_data.get('timestamp')
            started_at = None
            if timestamp_str:
                started_at = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            
            # Calculate progress and estimated completion
            progress_percent = latest_run_data.get('progress_percent', 0.0)
            elapsed_time = latest_run_data.get('elapsed_time', 0.0)
            
            estimated_completion = None
            if progress_percent > 0 and elapsed_time > 0:
                total_estimated_time = elapsed_time / (progress_percent / 100.0)
                remaining_time = total_estimated_time - elapsed_time
                if started_at:
                    estimated_completion = started_at.timestamp() + total_estimated_time
                    estimated_completion = datetime.fromtimestamp(estimated_completion)
            
            current_run = {
                "run_id": latest_run_id,
                "started_at": started_at.isoformat() if started_at else None,
                "progress_percent": progress_percent,
                "estimated_completion": estimated_completion.isoformat() if estimated_completion else None
            }
        
        # Extract real-time metrics
        real_time_data = latest_run_data.get('real_time_metrics', {})
        
        # Calculate current throughput if active
        current_throughput = 0.0
        if is_active:
            records_processed = real_time_data.get('records_processed', 0)
            elapsed_time = real_time_data.get('elapsed_time', 0.0)
            if elapsed_time > 0:
                current_throughput = records_processed / elapsed_time
        elif latest_completed:
            current_throughput = latest_completed.throughput
        
        real_time_metrics = {
            "current_throughput": current_throughput,
            "records_processed": real_time_data.get('records_processed', 0),
            "elapsed_time": real_time_data.get('elapsed_time', 0.0),
            "memory_usage_mb": real_time_data.get('memory_usage_mb', 0.0),
            "cpu_utilization_percent": real_time_data.get('cpu_utilization_percent', 0.0)
        }
        
        return LatestMetricsResponse(
            current_run=current_run,
            latest_completed=latest_completed,
            is_active=is_active,
            real_time_metrics=real_time_metrics
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve latest metrics: {str(e)}"
        )