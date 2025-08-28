/**
 * Performance Dashboard Container Component
 * 
 * Aggregates and displays comprehensive run metrics in a unified view.
 * Serves as the main dashboard page showing real-time and historical metrics
 * with automatic refresh intervals, visual health indicators, and interactive
 * charts using Recharts for data visualization.
 * 
 * Features:
 * - Real-time metrics display with automatic polling
 * - Historical run comparison and selection
 * - Interactive time-series charts for performance trends
 * - Responsive CSS Grid layout for all screen sizes
 * - Visual health indicators with color-coded thresholds
 * - Loading states with skeleton placeholders
 * - Comprehensive error handling with retry mechanisms
 * - Automatic cleanup of polling intervals
 * 
 * @author Blitzy Platform
 * @version 1.0.0
 */

import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts';
import MetricCard from './MetricCard';
import api from '../services/api';

/**
 * Main Dashboard Component
 * 
 * Provides comprehensive performance monitoring interface with real-time updates,
 * historical data analysis, and interactive visualization components.
 */
const Dashboard = () => {
  // State management for dashboard data and UI
  const [currentMetrics, setCurrentMetrics] = useState(null);
  const [selectedRunId, setSelectedRunId] = useState(null);
  const [runsList, setRunsList] = useState([]);
  const [runDetails, setRunDetails] = useState(null);
  const [chartData, setChartData] = useState([]);
  const [loading, setLoading] = useState({
    metrics: false,
    runs: false,
    details: false,
    charts: false
  });
  const [errors, setErrors] = useState({
    metrics: null,
    runs: null,
    details: null,
    charts: null
  });
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [refreshInterval, setRefreshInterval] = useState(5000); // 5 seconds default
  const [isPollingActive, setIsPollingActive] = useState(true);

  /**
   * Clear specific error state
   */
  const clearError = (errorKey) => {
    setErrors(prev => ({ ...prev, [errorKey]: null }));
  };

  /**
   * Set specific loading state
   */
  const setSpecificLoading = (loadingKey, isLoading) => {
    setLoading(prev => ({ ...prev, [loadingKey]: isLoading }));
  };

  /**
   * Handle API errors with retry functionality
   */
  const handleApiError = (error, operation, retryFn = null) => {
    const errorMessage = {
      message: error.message || 'An unexpected error occurred',
      code: error.code || 'UNKNOWN_ERROR',
      timestamp: new Date(),
      retryFn
    };

    setErrors(prev => ({ ...prev, [operation]: errorMessage }));
    console.error(`[Dashboard] ${operation} error:`, error);
  };

  /**
   * Fetch latest metrics data with error handling
   */
  const fetchLatestMetrics = async () => {
    try {
      setSpecificLoading('metrics', true);
      clearError('metrics');

      const metrics = await api.getLatestMetrics();
      setCurrentMetrics(metrics);
      setLastUpdated(new Date());

      // Adjust refresh interval based on run status
      if (metrics.isActive) {
        setRefreshInterval(5000); // 5 seconds for active runs
      } else {
        setRefreshInterval(30000); // 30 seconds for idle state
      }

    } catch (error) {
      handleApiError(error, 'metrics', fetchLatestMetrics);
    } finally {
      setSpecificLoading('metrics', false);
    }
  };

  /**
   * Fetch historical runs list
   */
  const fetchRunsList = async () => {
    try {
      setSpecificLoading('runs', true);
      clearError('runs');

      const runs = await api.getRunsList();
      setRunsList(runs);

      // Auto-select most recent run if none selected
      if (!selectedRunId && runs.length > 0) {
        setSelectedRunId(runs[0].id);
      }

    } catch (error) {
      handleApiError(error, 'runs', fetchRunsList);
    } finally {
      setSpecificLoading('runs', false);
    }
  };

  /**
   * Fetch detailed metrics for selected run
   */
  const fetchRunDetails = async (runId) => {
    if (!runId) return;

    try {
      setSpecificLoading('details', true);
      clearError('details');

      const details = await api.getRunDetails(runId);
      setRunDetails(details);

      // Generate chart data from run details
      generateChartData(details);

    } catch (error) {
      handleApiError(error, 'details', () => fetchRunDetails(runId));
    } finally {
      setSpecificLoading('details', false);
    }
  };

  /**
   * Generate chart data for time-series visualization
   */
  const generateChartData = (details) => {
    if (!details || !details.metrics) {
      setChartData([]);
      return;
    }

    try {
      setSpecificLoading('charts', true);
      clearError('charts');

      // Create time-series data from performance metrics
      const chartPoints = [];
      const { timing, performance, stages } = details.metrics;

      // Generate data points based on stage completion times
      const stageData = [
        { name: 'Setup', time: timing.setupTime, throughput: 0, memory: 0 },
        { 
          name: 'Generation', 
          time: timing.setupTime + timing.generationTime,
          throughput: performance.recordsPerSecond,
          memory: performance.peakMemoryUsage * 0.7 // Estimated during generation
        },
        { 
          name: 'Writing', 
          time: timing.setupTime + timing.generationTime + timing.writeTime,
          throughput: performance.recordsPerSecond * 0.5, // Lower during I/O
          memory: performance.peakMemoryUsage
        },
        { 
          name: 'Cleanup', 
          time: timing.totalDuration,
          throughput: 0,
          memory: performance.peakMemoryUsage * 0.2 // Lower after cleanup
        }
      ];

      setChartData(stageData);

    } catch (error) {
      handleApiError(error, 'charts', () => generateChartData(details));
    } finally {
      setSpecificLoading('charts', false);
    }
  };

  /**
   * Handle run selection change
   */
  const handleRunSelection = (event) => {
    const runId = event.target.value;
    setSelectedRunId(runId);
    setRunDetails(null); // Clear previous details
    
    if (runId && runId !== 'latest') {
      fetchRunDetails(runId);
    }
  };

  /**
   * Retry failed operation
   */
  const retryOperation = (errorKey) => {
    const error = errors[errorKey];
    if (error && error.retryFn && typeof error.retryFn === 'function') {
      error.retryFn();
    }
  };

  /**
   * Calculate performance thresholds for metric cards
   */
  const getPerformanceThresholds = (metricType) => {
    const thresholds = {
      throughput: {
        good: 1000,
        warning: 500,
        higher_is_better: true
      },
      duration: {
        good: 60,
        warning: 120,
        higher_is_better: false
      },
      memory: {
        good: 512,
        warning: 1024,
        higher_is_better: false
      },
      cpu: {
        good: 80,
        warning: 95,
        higher_is_better: false
      }
    };

    return thresholds[metricType] || null;
  };

  /**
   * Format duration in human-readable format
   */
  const formatDuration = (seconds) => {
    if (!seconds) return '0s';
    
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.round(seconds % 60);
    
    if (minutes > 0) {
      return `${minutes}m ${remainingSeconds}s`;
    }
    return `${remainingSeconds}s`;
  };

  /**
   * Format memory usage in human-readable format
   */
  const formatMemory = (bytes) => {
    if (!bytes) return '0 MB';
    
    const mb = bytes / (1024 * 1024);
    if (mb >= 1024) {
      return `${(mb / 1024).toFixed(1)} GB`;
    }
    return `${Math.round(mb)} MB`;
  };

  /**
   * Setup polling for real-time updates
   */
  useEffect(() => {
    let pollingTimer;

    const startPolling = () => {
      if (isPollingActive) {
        fetchLatestMetrics();
        pollingTimer = setTimeout(startPolling, refreshInterval);
      }
    };

    startPolling();

    // Cleanup function
    return () => {
      if (pollingTimer) {
        clearTimeout(pollingTimer);
      }
    };
  }, [refreshInterval, isPollingActive]);

  /**
   * Initial data fetching
   */
  useEffect(() => {
    fetchRunsList();
  }, []);

  /**
   * Fetch run details when selection changes
   */
  useEffect(() => {
    if (selectedRunId && selectedRunId !== 'latest') {
      fetchRunDetails(selectedRunId);
    }
  }, [selectedRunId]);

  /**
   * Cleanup on component unmount
   */
  useEffect(() => {
    return () => {
      // Cancel any active API requests
      api.cancelRequest();
      setIsPollingActive(false);
    };
  }, []);

  /**
   * Get metrics data for display based on current selection
   */
  const getDisplayMetrics = () => {
    // Show current metrics for latest/real-time, run details for historical
    if (!selectedRunId || selectedRunId === 'latest') {
      return currentMetrics;
    }
    return runDetails;
  };

  /**
   * Calculate trend data for metric cards
   */
  const calculateTrend = (currentValue, previousValue) => {
    if (!currentValue || !previousValue) return null;
    
    const percentage = ((currentValue - previousValue) / previousValue) * 100;
    const isImprovement = Math.abs(percentage) > 5 ? percentage > 0 : null;
    
    return {
      percentage,
      is_improvement: isImprovement
    };
  };

  /**
   * Get previous run for trend calculation
   */
  const getPreviousRun = () => {
    if (runsList.length < 2) return null;
    
    const currentIndex = runsList.findIndex(run => run.id === selectedRunId);
    return currentIndex > 0 ? runsList[currentIndex + 1] : runsList[1];
  };

  const displayMetrics = getDisplayMetrics();
  const previousRun = getPreviousRun();

  return (
    <div className="dashboard">
      {/* Dashboard Header */}
      <div className="dashboard__header">
        <div className="dashboard__title-section">
          <h1 className="dashboard__title">Performance Dashboard</h1>
          <p className="dashboard__subtitle">
            Real-time monitoring and analysis of FUSE Test Data Generator performance
          </p>
        </div>
        
        <div className="dashboard__controls">
          {/* Run Selection Dropdown */}
          <div className="dashboard__run-selector">
            <label htmlFor="run-select" className="dashboard__label">
              Select Run:
            </label>
            <select
              id="run-select"
              value={selectedRunId || 'latest'}
              onChange={handleRunSelection}
              className="dashboard__select"
              disabled={loading.runs}
            >
              <option value="latest">Latest / Live</option>
              {runsList.map(run => (
                <option key={run.id} value={run.id}>
                  {run.timestamp.toLocaleString()} - {formatDuration(run.duration)}
                </option>
              ))}
            </select>
          </div>

          {/* Polling Control */}
          <div className="dashboard__polling-control">
            <button
              onClick={() => setIsPollingActive(!isPollingActive)}
              className={`dashboard__polling-btn ${isPollingActive ? 'active' : 'inactive'}`}
            >
              {isPollingActive ? '⏸️ Pause' : '▶️ Resume'}
            </button>
          </div>

          {/* Last Updated */}
          <div className="dashboard__last-updated">
            <span className="dashboard__update-label">Last Updated:</span>
            <span className="dashboard__update-time">
              {lastUpdated.toLocaleTimeString()}
            </span>
          </div>
        </div>
      </div>

      {/* Error Messages */}
      {Object.entries(errors).map(([key, error]) => 
        error && (
          <div key={key} className="dashboard__error">
            <div className="dashboard__error-content">
              <span className="dashboard__error-icon">⚠️</span>
              <span className="dashboard__error-message">{error.message}</span>
              {error.retryFn && (
                <button
                  onClick={() => retryOperation(key)}
                  className="dashboard__error-retry"
                >
                  Retry
                </button>
              )}
            </div>
          </div>
        )
      )}

      {/* Main Dashboard Content */}
      <div className="dashboard__content">
        {/* Metrics Cards Section */}
        <div className="dashboard__metrics-grid">
          <MetricCard
            name="Throughput"
            value={displayMetrics?.realtime?.currentThroughput || displayMetrics?.metrics?.performance?.recordsPerSecond || 0}
            unit="rec/sec"
            icon="📊"
            loading={loading.metrics || loading.details}
            threshold={getPerformanceThresholds('throughput')}
            trend={calculateTrend(
              displayMetrics?.realtime?.currentThroughput || displayMetrics?.metrics?.performance?.recordsPerSecond,
              previousRun?.metrics?.throughput
            )}
          />

          <MetricCard
            name="Duration"
            value={displayMetrics?.progress?.estimatedTimeRemaining !== null ? 
              displayMetrics.progress.estimatedTimeRemaining :
              (displayMetrics?.metrics?.timing?.totalDuration || displayMetrics?.lastCompleted?.duration || 0)
            }
            unit={displayMetrics?.progress?.estimatedTimeRemaining !== null ? "sec remaining" : "seconds"}
            icon="⏱️"
            loading={loading.metrics || loading.details}
            threshold={getPerformanceThresholds('duration')}
            trend={calculateTrend(
              displayMetrics?.metrics?.timing?.totalDuration || displayMetrics?.lastCompleted?.duration,
              previousRun?.duration
            )}
          />

          <MetricCard
            name="Memory Usage"
            value={displayMetrics?.realtime?.memoryUsage || displayMetrics?.metrics?.performance?.peakMemoryUsage || 0}
            unit="MB"
            icon="💾"
            loading={loading.metrics || loading.details}
            threshold={getPerformanceThresholds('memory')}
            trend={calculateTrend(
              displayMetrics?.realtime?.memoryUsage || displayMetrics?.metrics?.performance?.peakMemoryUsage,
              previousRun?.metrics?.memoryUsage
            )}
          />

          <MetricCard
            name="CPU Usage"
            value={displayMetrics?.realtime?.cpuUsage || displayMetrics?.metrics?.performance?.avgCpuUsage || 0}
            unit="%"
            icon="⚡"
            loading={loading.metrics || loading.details}
            threshold={getPerformanceThresholds('cpu')}
            trend={calculateTrend(
              displayMetrics?.realtime?.cpuUsage || displayMetrics?.metrics?.performance?.avgCpuUsage,
              previousRun?.metrics?.cpuUsage
            )}
          />

          <MetricCard
            name="Records Generated"
            value={displayMetrics?.progress?.recordsProcessed || displayMetrics?.lastCompleted?.recordsGenerated || 0}
            unit="records"
            icon="📝"
            loading={loading.metrics || loading.details}
            threshold={null}
            trend={calculateTrend(
              displayMetrics?.progress?.recordsProcessed || displayMetrics?.lastCompleted?.recordsGenerated,
              previousRun?.recordsGenerated
            )}
          />

          <MetricCard
            name="Active Status"
            value={displayMetrics?.isActive ? "Running" : 
              (displayMetrics?.status === 'idle' ? "Idle" : 
              (displayMetrics?.lastCompleted?.status || "Unknown"))}
            unit=""
            icon={displayMetrics?.isActive ? "🟢" : (displayMetrics?.status === 'idle' ? "🔵" : "🔴")}
            loading={loading.metrics || loading.details}
            threshold={null}
            trend={null}
          />
        </div>

        {/* Progress Section for Active Runs */}
        {displayMetrics?.isActive && displayMetrics?.progress && (
          <div className="dashboard__progress-section">
            <h2 className="dashboard__section-title">Current Progress</h2>
            <div className="dashboard__progress-container">
              <div className="dashboard__progress-bar">
                <div 
                  className="dashboard__progress-fill"
                  style={{ width: `${displayMetrics.progress.percentage}%` }}
                />
              </div>
              <div className="dashboard__progress-details">
                <span>{displayMetrics.progress.percentage.toFixed(1)}% Complete</span>
                <span>
                  {displayMetrics.progress.recordsProcessed?.toLocaleString()} / {displayMetrics.progress.recordsTotal?.toLocaleString()} records
                </span>
                {displayMetrics.progress.estimatedTimeRemaining && (
                  <span>
                    ETA: {formatDuration(displayMetrics.progress.estimatedTimeRemaining)}
                  </span>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Charts Section */}
        {chartData.length > 0 && (
          <div className="dashboard__charts-section">
            <h2 className="dashboard__section-title">Performance Timeline</h2>
            
            {loading.charts ? (
              <div className="dashboard__chart-skeleton">
                <div className="skeleton-placeholder skeleton-placeholder--chart" />
              </div>
            ) : (
              <div className="dashboard__charts-grid">
                {/* Throughput Chart */}
                <div className="dashboard__chart-container">
                  <h3 className="dashboard__chart-title">Throughput Over Time</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip 
                        formatter={(value, name) => [
                          `${value} ${name === 'throughput' ? 'rec/sec' : 'MB'}`,
                          name === 'throughput' ? 'Throughput' : 'Memory Usage'
                        ]}
                      />
                      <Legend />
                      <Line 
                        type="monotone" 
                        dataKey="throughput" 
                        stroke="#10b981" 
                        strokeWidth={2}
                        name="Throughput"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>

                {/* Memory Usage Chart */}
                <div className="dashboard__chart-container">
                  <h3 className="dashboard__chart-title">Memory Usage Timeline</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <Tooltip 
                        formatter={(value) => [`${value} MB`, 'Memory Usage']}
                      />
                      <Legend />
                      <Line 
                        type="monotone" 
                        dataKey="memory" 
                        stroke="#f59e0b" 
                        strokeWidth={2}
                        name="Memory Usage"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Summary Statistics Section */}
        {runDetails && (
          <div className="dashboard__summary-section">
            <h2 className="dashboard__section-title">Run Summary</h2>
            <div className="dashboard__summary-grid">
              <div className="dashboard__summary-card">
                <h4>Timing Breakdown</h4>
                <ul>
                  <li>Setup: {formatDuration(runDetails.metrics.timing.setupTime)}</li>
                  <li>Generation: {formatDuration(runDetails.metrics.timing.generationTime)}</li>
                  <li>Writing: {formatDuration(runDetails.metrics.timing.writeTime)}</li>
                  <li>Cleanup: {formatDuration(runDetails.metrics.timing.cleanupTime)}</li>
                </ul>
              </div>
              
              <div className="dashboard__summary-card">
                <h4>Performance Metrics</h4>
                <ul>
                  <li>Avg Batch Size: {runDetails.metrics.performance.avgBatchSize?.toLocaleString()}</li>
                  <li>Disk I/O Ops: {runDetails.metrics.performance.diskIOOperations?.toLocaleString()}</li>
                  <li>Error Count: {runDetails.metrics.errors?.length || 0}</li>
                </ul>
              </div>

              <div className="dashboard__summary-card">
                <h4>Run Configuration</h4>
                <ul>
                  <li>Run ID: {runDetails.id}</li>
                  <li>Status: {runDetails.status}</li>
                  <li>Started: {runDetails.timestamp.toLocaleString()}</li>
                  <li>Outputs: {runDetails.outputs?.length || 0} files</li>
                </ul>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* CSS Styles */}
      <style jsx>{`
        .dashboard {
          padding: 1.5rem;
          max-width: 1400px;
          margin: 0 auto;
          background-color: #f8fafc;
          min-height: 100vh;
        }

        .dashboard__header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 2rem;
          padding-bottom: 1rem;
          border-bottom: 2px solid #e5e7eb;
        }

        .dashboard__title {
          margin: 0 0 0.5rem 0;
          font-size: 2rem;
          font-weight: 700;
          color: #1f2937;
        }

        .dashboard__subtitle {
          margin: 0;
          color: #6b7280;
          font-size: 1rem;
          line-height: 1.5;
        }

        .dashboard__controls {
          display: flex;
          gap: 1.5rem;
          align-items: center;
          flex-wrap: wrap;
        }

        .dashboard__run-selector {
          display: flex;
          flex-direction: column;
          gap: 0.5rem;
        }

        .dashboard__label {
          font-size: 0.875rem;
          font-weight: 500;
          color: #374151;
        }

        .dashboard__select {
          padding: 0.5rem;
          border: 1px solid #d1d5db;
          border-radius: 0.375rem;
          background-color: white;
          font-size: 0.875rem;
          min-width: 200px;
        }

        .dashboard__polling-btn {
          padding: 0.5rem 1rem;
          border-radius: 0.375rem;
          border: none;
          font-size: 0.875rem;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s;
        }

        .dashboard__polling-btn.active {
          background-color: #10b981;
          color: white;
        }

        .dashboard__polling-btn.inactive {
          background-color: #6b7280;
          color: white;
        }

        .dashboard__last-updated {
          display: flex;
          flex-direction: column;
          align-items: center;
          font-size: 0.75rem;
          color: #6b7280;
        }

        .dashboard__update-time {
          font-weight: 500;
          color: #374151;
        }

        .dashboard__error {
          background-color: #fef2f2;
          border: 1px solid #fecaca;
          border-radius: 0.5rem;
          padding: 1rem;
          margin-bottom: 1rem;
        }

        .dashboard__error-content {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .dashboard__error-message {
          flex: 1;
          color: #dc2626;
          font-weight: 500;
        }

        .dashboard__error-retry {
          background-color: #dc2626;
          color: white;
          border: none;
          padding: 0.25rem 0.75rem;
          border-radius: 0.25rem;
          cursor: pointer;
          font-size: 0.75rem;
        }

        .dashboard__metrics-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
          gap: 1.5rem;
          margin-bottom: 2rem;
        }

        .dashboard__progress-section {
          background: white;
          border-radius: 0.75rem;
          padding: 1.5rem;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
          margin-bottom: 2rem;
        }

        .dashboard__section-title {
          margin: 0 0 1rem 0;
          font-size: 1.25rem;
          font-weight: 600;
          color: #1f2937;
        }

        .dashboard__progress-container {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .dashboard__progress-bar {
          width: 100%;
          height: 8px;
          background-color: #e5e7eb;
          border-radius: 4px;
          overflow: hidden;
        }

        .dashboard__progress-fill {
          height: 100%;
          background-color: #10b981;
          transition: width 0.3s ease;
        }

        .dashboard__progress-details {
          display: flex;
          justify-content: space-between;
          font-size: 0.875rem;
          color: #6b7280;
          flex-wrap: wrap;
          gap: 0.5rem;
        }

        .dashboard__charts-section {
          background: white;
          border-radius: 0.75rem;
          padding: 1.5rem;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
          margin-bottom: 2rem;
        }

        .dashboard__chart-skeleton {
          width: 100%;
          height: 300px;
        }

        .dashboard__charts-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 2rem;
        }

        .dashboard__chart-container {
          min-height: 300px;
        }

        .dashboard__chart-title {
          margin: 0 0 1rem 0;
          font-size: 1rem;
          font-weight: 600;
          color: #374151;
        }

        .dashboard__summary-section {
          background: white;
          border-radius: 0.75rem;
          padding: 1.5rem;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .dashboard__summary-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 1.5rem;
        }

        .dashboard__summary-card {
          background: #f9fafb;
          border-radius: 0.5rem;
          padding: 1rem;
        }

        .dashboard__summary-card h4 {
          margin: 0 0 0.75rem 0;
          font-size: 0.875rem;
          font-weight: 600;
          color: #374151;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .dashboard__summary-card ul {
          list-style: none;
          padding: 0;
          margin: 0;
        }

        .dashboard__summary-card li {
          padding: 0.25rem 0;
          font-size: 0.875rem;
          color: #6b7280;
          border-bottom: 1px solid #e5e7eb;
        }

        .dashboard__summary-card li:last-child {
          border-bottom: none;
        }

        .skeleton-placeholder--chart {
          height: 300px;
          width: 100%;
        }

        /* Responsive Design */
        @media (max-width: 1024px) {
          .dashboard__charts-grid {
            grid-template-columns: 1fr;
          }
          
          .dashboard__metrics-grid {
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
          }
        }

        @media (max-width: 768px) {
          .dashboard {
            padding: 1rem;
          }
          
          .dashboard__header {
            flex-direction: column;
            gap: 1rem;
            align-items: stretch;
          }
          
          .dashboard__controls {
            flex-direction: column;
            align-items: stretch;
            gap: 1rem;
          }
          
          .dashboard__metrics-grid {
            grid-template-columns: 1fr;
            gap: 1rem;
          }
          
          .dashboard__summary-grid {
            grid-template-columns: 1fr;
          }
        }

        /* High contrast mode support */
        @media (prefers-contrast: high) {
          .dashboard__error {
            border-width: 2px;
          }
          
          .dashboard__progress-fill {
            background-color: #047857;
          }
        }

        /* Reduced motion support */
        @media (prefers-reduced-motion: reduce) {
          .dashboard__progress-fill,
          .dashboard__polling-btn {
            transition: none;
          }
        }
      `}</style>
    </div>
  );
};

export default Dashboard;