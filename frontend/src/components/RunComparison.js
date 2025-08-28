/**
 * RunComparison Component
 * 
 * Multi-run comparison visualization component enabling consultants to analyze 
 * performance trends across historical executions. Provides side-by-side metrics 
 * comparison with visual diff indicators, statistical summaries, and interactive 
 * charts for identifying performance improvements or degradations.
 * 
 * Features:
 * - Multi-run selection (minimum 2, maximum 5)
 * - Side-by-side metrics comparison
 * - Visual diff indicators with percentage changes
 * - Interactive charts using Recharts
 * - Statistical summaries (min, max, avg, stddev)
 * - Export functionality (CSV/JSON)
 * - Responsive design with mobile support
 * - Performance optimization through memoization
 * 
 * @author Blitzy Platform
 * @version 1.0.0
 */

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
    BarChart,
    Bar,
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    Cell
} from 'recharts';
import PropTypes from 'prop-types';
import api from '../services/api.js';

/**
 * Color scheme for visual diff indicators
 */
const DIFF_COLORS = {
    IMPROVEMENT: '#4CAF50',    // Green for improvements
    DEGRADATION: '#F44336',   // Red for degradations
    NEUTRAL: '#9E9E9E',       // Grey for neutral/minimal changes
    BASELINE: '#2196F3'       // Blue for baseline/reference
};

/**
 * Chart color palette for multiple runs
 */
const CHART_COLORS = [
    '#2196F3', '#4CAF50', '#FF9800', '#9C27B0', '#F44336'
];

/**
 * Threshold for determining significant performance changes (percentage)
 */
const SIGNIFICANCE_THRESHOLD = 5;

/**
 * Default component styles
 */
const styles = {
    container: {
        padding: '20px',
        background: '#ffffff',
        borderRadius: '8px',
        boxShadow: '0 2px 8px rgba(0, 0, 0, 0.1)',
        marginBottom: '20px'
    },
    header: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '20px',
        flexWrap: 'wrap',
        gap: '15px'
    },
    title: {
        margin: '0',
        color: '#1976D2',
        fontSize: '24px',
        fontWeight: '600'
    },
    controls: {
        display: 'flex',
        gap: '15px',
        alignItems: 'center',
        flexWrap: 'wrap'
    },
    select: {
        padding: '8px 12px',
        border: '1px solid #ddd',
        borderRadius: '4px',
        fontSize: '14px',
        minWidth: '150px'
    },
    button: {
        padding: '8px 16px',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '14px',
        fontWeight: '500',
        transition: 'background-color 0.2s'
    },
    primaryButton: {
        backgroundColor: '#1976D2',
        color: 'white'
    },
    secondaryButton: {
        backgroundColor: '#f5f5f5',
        color: '#333',
        border: '1px solid #ddd'
    },
    content: {
        display: 'flex',
        flexDirection: 'column',
        gap: '30px'
    },
    section: {
        backgroundColor: '#fafafa',
        padding: '20px',
        borderRadius: '6px',
        border: '1px solid #e0e0e0'
    },
    sectionTitle: {
        margin: '0 0 15px 0',
        fontSize: '18px',
        fontWeight: '600',
        color: '#333'
    },
    loading: {
        textAlign: 'center',
        padding: '40px',
        fontSize: '16px',
        color: '#666'
    },
    error: {
        backgroundColor: '#ffebee',
        border: '1px solid #e57373',
        borderRadius: '4px',
        padding: '15px',
        color: '#c62828',
        marginBottom: '20px'
    },
    table: {
        width: '100%',
        borderCollapse: 'collapse',
        backgroundColor: 'white',
        borderRadius: '6px',
        overflow: 'hidden',
        boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
    },
    th: {
        backgroundColor: '#f5f5f5',
        padding: '12px',
        textAlign: 'left',
        borderBottom: '2px solid #e0e0e0',
        fontWeight: '600',
        color: '#333'
    },
    td: {
        padding: '12px',
        borderBottom: '1px solid #e0e0e0',
        verticalAlign: 'top'
    },
    metricValue: {
        fontWeight: '500',
        fontSize: '14px'
    },
    diffIndicator: {
        display: 'inline-block',
        padding: '2px 6px',
        borderRadius: '4px',
        fontSize: '12px',
        fontWeight: '600',
        marginLeft: '8px'
    },
    chartContainer: {
        width: '100%',
        height: '300px',
        marginTop: '20px'
    },
    statsGrid: {
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '15px',
        marginTop: '20px'
    },
    statCard: {
        backgroundColor: 'white',
        padding: '15px',
        borderRadius: '6px',
        border: '1px solid #e0e0e0',
        textAlign: 'center'
    },
    statLabel: {
        fontSize: '12px',
        color: '#666',
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
        marginBottom: '5px'
    },
    statValue: {
        fontSize: '18px',
        fontWeight: '600',
        color: '#333'
    },
    exportSection: {
        display: 'flex',
        gap: '10px',
        alignItems: 'center',
        marginTop: '15px',
        padding: '15px',
        backgroundColor: '#f9f9f9',
        borderRadius: '6px'
    },
    exportLabel: {
        fontSize: '14px',
        color: '#666',
        marginRight: '10px'
    },
    responsive: {
        '@media (max-width: 768px)': {
            table: {
                fontSize: '12px'
            },
            th: {
                padding: '8px'
            },
            td: {
                padding: '8px'
            },
            chartContainer: {
                height: '250px'
            }
        }
    }
};

/**
 * RunComparison Component
 * 
 * Provides comprehensive multi-run performance comparison functionality
 * with interactive visualizations and statistical analysis.
 */
const RunComparison = ({ 
    initialSelectedRuns = [],
    onRunSelectionChange,
    className = '',
    showExports = true,
    showCharts = true,
    maxRuns = 5,
    minRuns = 2
}) => {
    // State management
    const [availableRuns, setAvailableRuns] = useState([]);
    const [selectedRuns, setSelectedRuns] = useState(initialSelectedRuns);
    const [comparisonData, setComparisonData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [runsLoading, setRunsLoading] = useState(false);

    /**
     * Load available runs from API
     */
    const loadAvailableRuns = useCallback(async () => {
        setRunsLoading(true);
        setError(null);

        try {
            const runs = await api.getRunsList();
            setAvailableRuns(runs.sort((a, b) => b.timestamp - a.timestamp));
        } catch (err) {
            console.error('Failed to load available runs:', err);
            setError(`Failed to load available runs: ${err.message}`);
        } finally {
            setRunsLoading(false);
        }
    }, []);

    /**
     * Load comparison data for selected runs
     */
    const loadComparisonData = useCallback(async (runIds) => {
        if (!runIds || runIds.length < minRuns) {
            setComparisonData(null);
            return;
        }

        setLoading(true);
        setError(null);

        try {
            const comparison = await api.compareRuns(runIds);
            setComparisonData(comparison);
        } catch (err) {
            console.error('Failed to load comparison data:', err);
            setError(`Failed to load comparison data: ${err.message}`);
            setComparisonData(null);
        } finally {
            setLoading(false);
        }
    }, [minRuns]);

    /**
     * Handle run selection changes
     */
    const handleRunSelectionChange = useCallback((runId, isSelected) => {
        setSelectedRuns(prevSelected => {
            let newSelected;

            if (isSelected) {
                // Add run if not already selected and under max limit
                if (!prevSelected.includes(runId) && prevSelected.length < maxRuns) {
                    newSelected = [...prevSelected, runId];
                } else {
                    return prevSelected; // No change if already selected or at max
                }
            } else {
                // Remove run
                newSelected = prevSelected.filter(id => id !== runId);
            }

            // Notify parent component
            if (onRunSelectionChange) {
                onRunSelectionChange(newSelected);
            }

            return newSelected;
        });
    }, [maxRuns, onRunSelectionChange]);

    /**
     * Clear all selected runs
     */
    const clearSelection = useCallback(() => {
        setSelectedRuns([]);
        setComparisonData(null);
        if (onRunSelectionChange) {
            onRunSelectionChange([]);
        }
    }, [onRunSelectionChange]);

    /**
     * Calculate percentage difference between two values
     */
    const calculatePercentageDiff = useCallback((current, previous) => {
        if (!previous || previous === 0) {
            return current > 0 ? 100 : 0;
        }
        return ((current - previous) / previous) * 100;
    }, []);

    /**
     * Get diff indicator styling and text
     */
    const getDiffIndicator = useCallback((percentage, isInverse = false) => {
        const absPercentage = Math.abs(percentage);
        
        if (absPercentage < SIGNIFICANCE_THRESHOLD) {
            return {
                text: `${percentage >= 0 ? '+' : ''}${percentage.toFixed(1)}%`,
                color: DIFF_COLORS.NEUTRAL,
                backgroundColor: '#f5f5f5'
            };
        }

        const isImprovement = isInverse ? percentage < 0 : percentage > 0;
        
        return {
            text: `${percentage >= 0 ? '+' : ''}${percentage.toFixed(1)}%`,
            color: 'white',
            backgroundColor: isImprovement ? DIFF_COLORS.IMPROVEMENT : DIFF_COLORS.DEGRADATION
        };
    }, []);

    /**
     * Calculate statistical summary for a metric across runs
     */
    const calculateStats = useCallback((values, label) => {
        if (!values || values.length === 0) {
            return { min: 0, max: 0, avg: 0, stdDev: 0, label };
        }

        const numericValues = values.filter(v => typeof v === 'number' && !isNaN(v));
        if (numericValues.length === 0) {
            return { min: 0, max: 0, avg: 0, stdDev: 0, label };
        }

        const min = Math.min(...numericValues);
        const max = Math.max(...numericValues);
        const avg = numericValues.reduce((sum, val) => sum + val, 0) / numericValues.length;
        
        // Calculate standard deviation
        const variance = numericValues.reduce((sum, val) => sum + Math.pow(val - avg, 2), 0) / numericValues.length;
        const stdDev = Math.sqrt(variance);

        return { min, max, avg, stdDev, label };
    }, []);

    /**
     * Format numeric value for display
     */
    const formatValue = useCallback((value, type = 'number') => {
        if (value === null || value === undefined || isNaN(value)) {
            return 'N/A';
        }

        switch (type) {
            case 'duration':
                return `${value.toFixed(2)}s`;
            case 'throughput':
                return `${value.toFixed(0)} rec/s`;
            case 'percentage':
                return `${value.toFixed(1)}%`;
            case 'memory':
                return `${(value / 1024 / 1024).toFixed(1)} MB`;
            case 'records':
                return value.toLocaleString();
            default:
                return typeof value === 'number' ? value.toFixed(2) : value;
        }
    }, []);

    /**
     * Export comparison data to CSV
     */
    const exportToCSV = useCallback(() => {
        if (!comparisonData || !comparisonData.runDetails) {
            return;
        }

        const headers = ['Metric', ...comparisonData.runDetails.map(run => `Run ${run.id}`)];
        const rows = [];

        // Add basic metrics
        const basicMetrics = [
            ['Timestamp', ...comparisonData.runDetails.map(run => new Date(run.timestamp).toISOString())],
            ['Duration (s)', ...comparisonData.runDetails.map(run => run.duration)],
            ['Records Generated', ...comparisonData.runDetails.map(run => run.recordsGenerated)],
            ['Throughput (rec/s)', ...comparisonData.runDetails.map(run => run.throughput)],
            ['Status', ...comparisonData.runDetails.map(run => run.status)]
        ];

        rows.push(...basicMetrics);

        // Create CSV content
        const csvContent = [headers, ...rows]
            .map(row => row.map(cell => `"${cell}"`).join(','))
            .join('\n');

        // Download file
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `run-comparison-${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }, [comparisonData]);

    /**
     * Export comparison data to JSON
     */
    const exportToJSON = useCallback(() => {
        if (!comparisonData) {
            return;
        }

        const exportData = {
            exportedAt: new Date().toISOString(),
            comparison: comparisonData
        };

        const blob = new Blob([JSON.stringify(exportData, null, 2)], { 
            type: 'application/json;charset=utf-8;' 
        });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `run-comparison-${new Date().toISOString().split('T')[0]}.json`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }, [comparisonData]);

    /**
     * Memoized chart data preparation
     */
    const chartData = useMemo(() => {
        if (!comparisonData || !comparisonData.runDetails) {
            return {
                barData: [],
                lineData: []
            };
        }

        // Prepare data for bar chart (throughput comparison)
        const barData = comparisonData.runDetails.map((run, index) => ({
            runId: `Run ${run.id.substring(0, 8)}`,
            throughput: run.throughput,
            duration: run.duration,
            records: run.recordsGenerated,
            color: CHART_COLORS[index % CHART_COLORS.length]
        }));

        // Prepare data for line chart (time series if we have timestamps)
        const lineData = comparisonData.runDetails
            .map((run, index) => ({
                timestamp: new Date(run.timestamp).getTime(),
                throughput: run.throughput,
                runId: run.id.substring(0, 8),
                color: CHART_COLORS[index % CHART_COLORS.length]
            }))
            .sort((a, b) => a.timestamp - b.timestamp);

        return { barData, lineData };
    }, [comparisonData]);

    /**
     * Memoized statistical calculations
     */
    const statistics = useMemo(() => {
        if (!comparisonData || !comparisonData.runDetails) {
            return null;
        }

        const durations = comparisonData.runDetails.map(run => run.duration);
        const throughputs = comparisonData.runDetails.map(run => run.throughput);
        const recordCounts = comparisonData.runDetails.map(run => run.recordsGenerated);

        return {
            duration: calculateStats(durations, 'Duration (s)'),
            throughput: calculateStats(throughputs, 'Throughput (rec/s)'),
            records: calculateStats(recordCounts, 'Records Generated')
        };
    }, [comparisonData, calculateStats]);

    // Load available runs on component mount
    useEffect(() => {
        loadAvailableRuns();
    }, [loadAvailableRuns]);

    // Load comparison data when selected runs change
    useEffect(() => {
        if (selectedRuns.length >= minRuns) {
            loadComparisonData(selectedRuns);
        } else {
            setComparisonData(null);
        }
    }, [selectedRuns, loadComparisonData, minRuns]);

    return (
        <div className={`run-comparison ${className}`} style={styles.container}>
            {/* Header */}
            <div style={styles.header}>
                <h2 style={styles.title}>Run Performance Comparison</h2>
                <div style={styles.controls}>
                    <button
                        style={{ ...styles.button, ...styles.secondaryButton }}
                        onClick={clearSelection}
                        disabled={selectedRuns.length === 0}
                    >
                        Clear Selection
                    </button>
                    <button
                        style={{ ...styles.button, ...styles.primaryButton }}
                        onClick={loadAvailableRuns}
                        disabled={runsLoading}
                    >
                        {runsLoading ? 'Loading...' : 'Refresh Runs'}
                    </button>
                </div>
            </div>

            {/* Error Display */}
            {error && (
                <div style={styles.error}>
                    {error}
                </div>
            )}

            {/* Run Selection */}
            <div style={styles.section}>
                <h3 style={styles.sectionTitle}>
                    Select Runs to Compare ({selectedRuns.length}/{maxRuns})
                </h3>
                <p style={{ margin: '0 0 15px 0', color: '#666', fontSize: '14px' }}>
                    Select {minRuns} to {maxRuns} runs for comparison. 
                    {selectedRuns.length < minRuns && ` You need ${minRuns - selectedRuns.length} more run(s).`}
                </p>

                {runsLoading ? (
                    <div style={styles.loading}>Loading available runs...</div>
                ) : (
                    <div style={{ 
                        display: 'grid', 
                        gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', 
                        gap: '10px' 
                    }}>
                        {availableRuns.map(run => {
                            const isSelected = selectedRuns.includes(run.id);
                            const canSelect = !isSelected && selectedRuns.length < maxRuns;
                            
                            return (
                                <label
                                    key={run.id}
                                    style={{
                                        display: 'flex',
                                        alignItems: 'center',
                                        padding: '10px',
                                        border: `2px solid ${isSelected ? '#1976D2' : '#e0e0e0'}`,
                                        borderRadius: '6px',
                                        backgroundColor: isSelected ? '#f3f9ff' : 'white',
                                        cursor: canSelect || isSelected ? 'pointer' : 'not-allowed',
                                        opacity: canSelect || isSelected ? 1 : 0.5,
                                        transition: 'all 0.2s'
                                    }}
                                >
                                    <input
                                        type="checkbox"
                                        checked={isSelected}
                                        onChange={(e) => handleRunSelectionChange(run.id, e.target.checked)}
                                        disabled={!canSelect && !isSelected}
                                        style={{ marginRight: '10px' }}
                                    />
                                    <div style={{ flex: 1 }}>
                                        <div style={{ fontWeight: '500', fontSize: '14px' }}>
                                            Run {run.id.substring(0, 8)}...
                                        </div>
                                        <div style={{ fontSize: '12px', color: '#666' }}>
                                            {new Date(run.timestamp).toLocaleString()} • 
                                            {formatValue(run.duration, 'duration')} • 
                                            {formatValue(run.recordsGenerated, 'records')} records
                                        </div>
                                        <div style={{ fontSize: '12px', color: '#666' }}>
                                            Throughput: {formatValue(run.metrics.throughput, 'throughput')}
                                        </div>
                                    </div>
                                </label>
                            );
                        })}
                    </div>
                )}
            </div>

            {/* Comparison Results */}
            {selectedRuns.length >= minRuns && (
                <>
                    {loading ? (
                        <div style={styles.loading}>Loading comparison data...</div>
                    ) : comparisonData ? (
                        <div style={styles.content}>
                            {/* Summary Statistics */}
                            {statistics && (
                                <div style={styles.section}>
                                    <h3 style={styles.sectionTitle}>Statistical Summary</h3>
                                    <div style={styles.statsGrid}>
                                        {Object.values(statistics).map(stat => (
                                            <div key={stat.label} style={styles.statCard}>
                                                <div style={styles.statLabel}>{stat.label}</div>
                                                <div style={styles.statValue}>
                                                    Min: {formatValue(stat.min, stat.label.includes('Duration') ? 'duration' : 'number')}<br/>
                                                    Max: {formatValue(stat.max, stat.label.includes('Duration') ? 'duration' : 'number')}<br/>
                                                    Avg: {formatValue(stat.avg, stat.label.includes('Duration') ? 'duration' : 'number')}<br/>
                                                    StdDev: {formatValue(stat.stdDev, stat.label.includes('Duration') ? 'duration' : 'number')}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Metrics Comparison Table */}
                            <div style={styles.section}>
                                <h3 style={styles.sectionTitle}>Metrics Comparison</h3>
                                <div style={{ overflowX: 'auto' }}>
                                    <table style={styles.table}>
                                        <thead>
                                            <tr>
                                                <th style={styles.th}>Metric</th>
                                                {comparisonData.runDetails.map((run, index) => (
                                                    <th key={run.id} style={styles.th}>
                                                        Run {run.id.substring(0, 8)}
                                                        <div style={{ fontSize: '11px', fontWeight: 'normal', color: '#666' }}>
                                                            {new Date(run.timestamp).toLocaleDateString()}
                                                        </div>
                                                    </th>
                                                ))}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {/* Duration Row */}
                                            <tr>
                                                <td style={styles.td}>
                                                    <strong>Duration</strong>
                                                    <div style={{ fontSize: '12px', color: '#666' }}>
                                                        Total execution time
                                                    </div>
                                                </td>
                                                {comparisonData.runDetails.map((run, index) => {
                                                    const diff = index > 0 ? 
                                                        calculatePercentageDiff(run.duration, comparisonData.runDetails[0].duration) : 0;
                                                    const diffIndicator = index > 0 ? getDiffIndicator(diff, true) : null;
                                                    
                                                    return (
                                                        <td key={run.id} style={styles.td}>
                                                            <span style={styles.metricValue}>
                                                                {formatValue(run.duration, 'duration')}
                                                            </span>
                                                            {diffIndicator && (
                                                                <span
                                                                    style={{
                                                                        ...styles.diffIndicator,
                                                                        backgroundColor: diffIndicator.backgroundColor,
                                                                        color: diffIndicator.color
                                                                    }}
                                                                >
                                                                    {diffIndicator.text}
                                                                </span>
                                                            )}
                                                        </td>
                                                    );
                                                })}
                                            </tr>

                                            {/* Throughput Row */}
                                            <tr>
                                                <td style={styles.td}>
                                                    <strong>Throughput</strong>
                                                    <div style={{ fontSize: '12px', color: '#666' }}>
                                                        Records per second
                                                    </div>
                                                </td>
                                                {comparisonData.runDetails.map((run, index) => {
                                                    const diff = index > 0 ? 
                                                        calculatePercentageDiff(run.throughput, comparisonData.runDetails[0].throughput) : 0;
                                                    const diffIndicator = index > 0 ? getDiffIndicator(diff, false) : null;
                                                    
                                                    return (
                                                        <td key={run.id} style={styles.td}>
                                                            <span style={styles.metricValue}>
                                                                {formatValue(run.throughput, 'throughput')}
                                                            </span>
                                                            {diffIndicator && (
                                                                <span
                                                                    style={{
                                                                        ...styles.diffIndicator,
                                                                        backgroundColor: diffIndicator.backgroundColor,
                                                                        color: diffIndicator.color
                                                                    }}
                                                                >
                                                                    {diffIndicator.text}
                                                                </span>
                                                            )}
                                                        </td>
                                                    );
                                                })}
                                            </tr>

                                            {/* Records Generated Row */}
                                            <tr>
                                                <td style={styles.td}>
                                                    <strong>Records Generated</strong>
                                                    <div style={{ fontSize: '12px', color: '#666' }}>
                                                        Total records created
                                                    </div>
                                                </td>
                                                {comparisonData.runDetails.map((run, index) => {
                                                    const diff = index > 0 ? 
                                                        calculatePercentageDiff(run.recordsGenerated, comparisonData.runDetails[0].recordsGenerated) : 0;
                                                    const diffIndicator = index > 0 ? getDiffIndicator(diff, false) : null;
                                                    
                                                    return (
                                                        <td key={run.id} style={styles.td}>
                                                            <span style={styles.metricValue}>
                                                                {formatValue(run.recordsGenerated, 'records')}
                                                            </span>
                                                            {diffIndicator && (
                                                                <span
                                                                    style={{
                                                                        ...styles.diffIndicator,
                                                                        backgroundColor: diffIndicator.backgroundColor,
                                                                        color: diffIndicator.color
                                                                    }}
                                                                >
                                                                    {diffIndicator.text}
                                                                </span>
                                                            )}
                                                        </td>
                                                    );
                                                })}
                                            </tr>

                                            {/* Status Row */}
                                            <tr>
                                                <td style={styles.td}>
                                                    <strong>Status</strong>
                                                    <div style={{ fontSize: '12px', color: '#666' }}>
                                                        Run completion status
                                                    </div>
                                                </td>
                                                {comparisonData.runDetails.map(run => (
                                                    <td key={run.id} style={styles.td}>
                                                        <span 
                                                            style={{
                                                                ...styles.metricValue,
                                                                color: run.status === 'completed' ? DIFF_COLORS.IMPROVEMENT : 
                                                                       run.status === 'failed' ? DIFF_COLORS.DEGRADATION : '#666'
                                                            }}
                                                        >
                                                            {run.status}
                                                        </span>
                                                    </td>
                                                ))}
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </div>

                            {/* Charts */}
                            {showCharts && chartData.barData.length > 0 && (
                                <div style={styles.section}>
                                    <h3 style={styles.sectionTitle}>Performance Visualization</h3>
                                    
                                    {/* Throughput Bar Chart */}
                                    <div>
                                        <h4 style={{ margin: '0 0 10px 0', fontSize: '16px', color: '#555' }}>
                                            Throughput Comparison
                                        </h4>
                                        <div style={styles.chartContainer}>
                                            <ResponsiveContainer width="100%" height="100%">
                                                <BarChart data={chartData.barData}>
                                                    <CartesianGrid strokeDasharray="3 3" />
                                                    <XAxis dataKey="runId" />
                                                    <YAxis />
                                                    <Tooltip 
                                                        formatter={(value, name) => [
                                                            formatValue(value, name === 'throughput' ? 'throughput' : 'number'), 
                                                            name
                                                        ]}
                                                    />
                                                    <Legend />
                                                    <Bar dataKey="throughput" name="Throughput (rec/s)">
                                                        {chartData.barData.map((entry, index) => (
                                                            <Cell key={`cell-${index}`} fill={entry.color} />
                                                        ))}
                                                    </Bar>
                                                </BarChart>
                                            </ResponsiveContainer>
                                        </div>
                                    </div>

                                    {/* Throughput Trend Line Chart */}
                                    {chartData.lineData.length > 1 && (
                                        <div style={{ marginTop: '30px' }}>
                                            <h4 style={{ margin: '0 0 10px 0', fontSize: '16px', color: '#555' }}>
                                                Throughput Trend Over Time
                                            </h4>
                                            <div style={styles.chartContainer}>
                                                <ResponsiveContainer width="100%" height="100%">
                                                    <LineChart data={chartData.lineData}>
                                                        <CartesianGrid strokeDasharray="3 3" />
                                                        <XAxis 
                                                            dataKey="timestamp"
                                                            type="number"
                                                            scale="time"
                                                            domain={['dataMin', 'dataMax']}
                                                            tickFormatter={(timestamp) => new Date(timestamp).toLocaleDateString()}
                                                        />
                                                        <YAxis />
                                                        <Tooltip 
                                                            labelFormatter={(timestamp) => new Date(timestamp).toLocaleString()}
                                                            formatter={(value) => [formatValue(value, 'throughput'), 'Throughput']}
                                                        />
                                                        <Legend />
                                                        <Line 
                                                            type="monotone" 
                                                            dataKey="throughput" 
                                                            stroke="#1976D2"
                                                            strokeWidth={3}
                                                            dot={{ fill: '#1976D2', strokeWidth: 2, r: 4 }}
                                                            activeDot={{ r: 6 }}
                                                        />
                                                    </LineChart>
                                                </ResponsiveContainer>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Export Options */}
                            {showExports && (
                                <div style={styles.section}>
                                    <h3 style={styles.sectionTitle}>Export Comparison Data</h3>
                                    <div style={styles.exportSection}>
                                        <span style={styles.exportLabel}>Download as:</span>
                                        <button
                                            style={{ ...styles.button, ...styles.secondaryButton }}
                                            onClick={exportToCSV}
                                        >
                                            CSV
                                        </button>
                                        <button
                                            style={{ ...styles.button, ...styles.secondaryButton }}
                                            onClick={exportToJSON}
                                        >
                                            JSON
                                        </button>
                                    </div>
                                </div>
                            )}
                        </div>
                    ) : null}
                </>
            )}
        </div>
    );
};

// PropTypes validation
RunComparison.propTypes = {
    initialSelectedRuns: PropTypes.array,
    onRunSelectionChange: PropTypes.func,
    className: PropTypes.string,
    showExports: PropTypes.bool,
    showCharts: PropTypes.bool,
    maxRuns: PropTypes.number,
    minRuns: PropTypes.number
};

export default RunComparison;