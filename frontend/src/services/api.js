/**
 * Frontend API Client Service for FUSE Test Data Generator
 * 
 * Provides a centralized interface for all communication with the FastAPI backend,
 * implementing comprehensive error handling, retry logic, caching, and response
 * transformation for performance metrics and run data.
 * 
 * @author Blitzy Platform
 * @version 1.0.0
 */

import axios from 'axios';

/**
 * Development-only logging utility to avoid console warnings in production
 */
const devLog = {
    log: (...args) => {
        if (process.env.NODE_ENV === 'development') {
            console.log(...args); // eslint-disable-line no-console
        }
    },
    error: (...args) => {
        if (process.env.NODE_ENV === 'development') {
            console.error(...args); // eslint-disable-line no-console
        }
    },
    warn: (...args) => {
        if (process.env.NODE_ENV === 'development') {
            console.warn(...args); // eslint-disable-line no-console
        }
    }
};

/**
 * API Configuration Constants
 */
const API_CONFIG = {
    BASE_URL: 'http://localhost:8000',
    TIMEOUT: 10000,
    MAX_RETRIES: 3,
    RETRY_DELAY: 1000,
    CACHE_TTL: 5 * 60 * 1000, // 5 minutes
};

/**
 * API Error Types
 */
const API_ERRORS = {
    NETWORK_ERROR: 'NETWORK_ERROR',
    TIMEOUT: 'TIMEOUT',
    SERVER_ERROR: 'SERVER_ERROR',
    NOT_FOUND: 'NOT_FOUND',
    INVALID_REQUEST: 'INVALID_REQUEST',
    CANCELLED: 'CANCELLED',
};

/**
 * In-memory cache for API responses
 */
class APICache {
    constructor() {
        this.cache = new Map();
        this.timestamps = new Map();
    }

    set(key, data, ttl = API_CONFIG.CACHE_TTL) {
        this.cache.set(key, data);
        this.timestamps.set(key, Date.now() + ttl);
    }

    get(key) {
        const timestamp = this.timestamps.get(key);
        if (!timestamp || Date.now() > timestamp) {
            this.cache.delete(key);
            this.timestamps.delete(key);
            return null;
        }
        return this.cache.get(key);
    }

    clear() {
        this.cache.clear();
        this.timestamps.clear();
    }

    delete(key) {
        this.cache.delete(key);
        this.timestamps.delete(key);
    }
}

/**
 * Custom API Error Class
 */
class APIError extends Error {
    constructor(message, code, status, details) {
        super(message);
        this.name = 'APIError';
        this.code = code;
        this.status = status;
        this.details = details;
    }
}

/**
 * API Client Class
 */
class APIClient {
    constructor() {
        this.cache = new APICache();
        this.cancelTokens = new Map();
        this.loadingStates = new Map();
        
        // Create axios instance with base configuration
        this.axiosInstance = axios.create({
            baseURL: API_CONFIG.BASE_URL,
            timeout: API_CONFIG.TIMEOUT,
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            },
        });

        // Setup request interceptor
        this.axiosInstance.interceptors.request.use(
            (config) => {
                // Add request logging
                devLog.log(`[API] ${config.method?.toUpperCase()} ${config.url}`, {
                    params: config.params,
                    data: config.data,
                });

                // Add timestamp for request timing
                config.metadata = { startTime: Date.now() };
                return config;
            },
            (error) => {
                devLog.error('[API] Request interceptor error:', error);
                return Promise.reject(error);
            }
        );

        // Setup response interceptor
        this.axiosInstance.interceptors.response.use(
            (response) => {
                // Log response time
                const duration = Date.now() - response.config.metadata.startTime;
                devLog.log(`[API] Response ${response.status} in ${duration}ms`);

                // Validate response envelope
                if (response.data && response.data.status === 'success') {
                    return response;
                }
                
                // Handle error responses with success status code
                const errorMessage = response.data?.error?.message || 'Unknown server error';
                const errorCode = response.data?.error?.code || API_ERRORS.SERVER_ERROR;
                throw new APIError(errorMessage, errorCode, response.status, response.data?.error?.details);
            },
            (error) => {
                const duration = error.config?.metadata ? 
                    Date.now() - error.config.metadata.startTime : 0;
                
                devLog.error(`[API] Error response in ${duration}ms:`, {
                    message: error.message,
                    status: error.response?.status,
                    data: error.response?.data,
                });

                // Transform axios errors to APIError
                if (axios.isCancel(error)) {
                    throw new APIError('Request cancelled', API_ERRORS.CANCELLED, null, error);
                }

                if (error.code === 'ECONNABORTED') {
                    throw new APIError('Request timeout', API_ERRORS.TIMEOUT, null, error);
                }

                if (!error.response) {
                    throw new APIError('Network error', API_ERRORS.NETWORK_ERROR, null, error);
                }

                const status = error.response.status;
                const data = error.response.data;

                if (status === 404) {
                    throw new APIError('Resource not found', API_ERRORS.NOT_FOUND, status, data);
                }

                if (status >= 400 && status < 500) {
                    const message = data?.error?.message || 'Invalid request';
                    throw new APIError(message, API_ERRORS.INVALID_REQUEST, status, data);
                }

                if (status >= 500) {
                    const message = data?.error?.message || 'Server error';
                    throw new APIError(message, API_ERRORS.SERVER_ERROR, status, data);
                }

                throw error;
            }
        );
    }

    /**
     * Execute request with retry logic and exponential backoff
     * @param {Function} requestFn - Function that returns a promise
     * @param {number} maxRetries - Maximum retry attempts
     * @param {number} delay - Initial delay between retries
     * @returns {Promise} Request promise
     */
    async executeWithRetry(requestFn, maxRetries = API_CONFIG.MAX_RETRIES, delay = API_CONFIG.RETRY_DELAY) {
        let lastError;

        for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
                return await requestFn();
            } catch (error) {
                lastError = error;

                // Don't retry cancelled requests or client errors
                if (error.code === API_ERRORS.CANCELLED || 
                    (error.status >= 400 && error.status < 500)) {
                    throw error;
                }

                // Don't retry on last attempt
                if (attempt === maxRetries) {
                    break;
                }

                // Exponential backoff with jitter
                const backoffDelay = delay * Math.pow(2, attempt) + Math.random() * 1000;
                devLog.log(`[API] Retry attempt ${attempt + 1}/${maxRetries + 1} in ${Math.round(backoffDelay)}ms`);
                await new Promise(resolve => setTimeout(resolve, backoffDelay));
            }
        }

        throw lastError;
    }

    /**
     * Generate cache key for request
     * @param {string} endpoint - API endpoint
     * @param {Object} params - Request parameters
     * @returns {string} Cache key
     */
    generateCacheKey(endpoint, params = {}) {
        const paramString = Object.keys(params)
            .sort()
            .map(key => `${key}=${JSON.stringify(params[key])}`)
            .join('&');
        return `${endpoint}?${paramString}`;
    }

    /**
     * Set loading state for a request
     * @param {string} key - Loading key
     * @param {boolean} loading - Loading state
     */
    setLoadingState(key, loading) {
        this.loadingStates.set(key, loading);
    }

    /**
     * Get loading state for a request
     * @param {string} key - Loading key
     * @returns {boolean} Loading state
     */
    getLoadingState(key) {
        return this.loadingStates.get(key) || false;
    }

    /**
     * Create cancellation token for a request
     * @param {string} key - Request key
     * @returns {Object} Cancel token
     */
    createCancelToken(key) {
        // Cancel existing request if any
        const existingSource = this.cancelTokens.get(key);
        if (existingSource) {
            existingSource.cancel('New request initiated');
        }

        // Create new cancel token
        const source = axios.CancelToken.source();
        this.cancelTokens.set(key, source);
        return source.token;
    }

    /**
     * Get list of all historical runs
     * @returns {Promise<Array>} Array of run metadata objects
     */
    async getRunsList() {
        const endpoint = '/api/runs';
        const cacheKey = this.generateCacheKey(endpoint);
        const loadingKey = 'getRunsList';

        // Check cache first
        const cachedData = this.cache.get(cacheKey);
        if (cachedData) {
            devLog.log('[API] Returning cached runs list');
            return cachedData;
        }

        // Check if already loading
        if (this.getLoadingState(loadingKey)) {
            throw new APIError('Request already in progress', API_ERRORS.INVALID_REQUEST, 409);
        }

        try {
            this.setLoadingState(loadingKey, true);
            const cancelToken = this.createCancelToken(loadingKey);

            const response = await this.executeWithRetry(async () => {
                return await this.axiosInstance.get(endpoint, { cancelToken });
            });

            // Transform and cache response
            const runs = response.data.data || [];
            const transformedRuns = runs.map(run => ({
                id: run.id,
                timestamp: new Date(run.timestamp),
                duration: run.duration,
                recordsGenerated: run.records_generated,
                status: run.status,
                metrics: {
                    throughput: run.metrics?.throughput || 0,
                    cpuUsage: run.metrics?.cpu_usage || 0,
                    memoryUsage: run.metrics?.memory_usage || 0,
                    errorCount: run.metrics?.error_count || 0,
                }
            }));

            this.cache.set(cacheKey, transformedRuns, API_CONFIG.CACHE_TTL);
            return transformedRuns;

        } finally {
            this.setLoadingState(loadingKey, false);
            this.cancelTokens.delete(loadingKey);
        }
    }

    /**
     * Get detailed metrics for a specific run
     * @param {string} runId - Unique run identifier
     * @returns {Promise<Object>} Detailed run metrics object
     */
    async getRunDetails(runId) {
        if (!runId) {
            throw new APIError('Run ID is required', API_ERRORS.INVALID_REQUEST, 400);
        }

        const endpoint = `/api/runs/${runId}`;
        const cacheKey = this.generateCacheKey(endpoint);
        const loadingKey = `getRunDetails:${runId}`;

        // Check cache first
        const cachedData = this.cache.get(cacheKey);
        if (cachedData) {
            devLog.log(`[API] Returning cached run details for ${runId}`);
            return cachedData;
        }

        // Check if already loading
        if (this.getLoadingState(loadingKey)) {
            throw new APIError('Request already in progress', API_ERRORS.INVALID_REQUEST, 409);
        }

        try {
            this.setLoadingState(loadingKey, true);
            const cancelToken = this.createCancelToken(loadingKey);

            const response = await this.executeWithRetry(async () => {
                return await this.axiosInstance.get(endpoint, { cancelToken });
            });

            // Transform response data
            const runData = response.data.data;
            const transformedRun = {
                id: runData.id,
                timestamp: new Date(runData.timestamp),
                duration: runData.duration,
                status: runData.status,
                configuration: runData.configuration || {},
                metrics: {
                    timing: {
                        totalDuration: runData.metrics?.timing?.total_duration || 0,
                        setupTime: runData.metrics?.timing?.setup_time || 0,
                        generationTime: runData.metrics?.timing?.generation_time || 0,
                        writeTime: runData.metrics?.timing?.write_time || 0,
                        cleanupTime: runData.metrics?.timing?.cleanup_time || 0,
                    },
                    performance: {
                        recordsPerSecond: runData.metrics?.performance?.records_per_second || 0,
                        avgBatchSize: runData.metrics?.performance?.avg_batch_size || 0,
                        peakMemoryUsage: runData.metrics?.performance?.peak_memory_usage || 0,
                        avgCpuUsage: runData.metrics?.performance?.avg_cpu_usage || 0,
                        diskIOOperations: runData.metrics?.performance?.disk_io_operations || 0,
                    },
                    stages: {
                        coordinator: runData.metrics?.stages?.coordinator || {},
                        creators: runData.metrics?.stages?.creators || [],
                        writers: runData.metrics?.stages?.writers || [],
                    },
                    errors: runData.metrics?.errors || [],
                },
                outputs: runData.outputs || [],
            };

            this.cache.set(cacheKey, transformedRun, API_CONFIG.CACHE_TTL);
            return transformedRun;

        } finally {
            this.setLoadingState(loadingKey, false);
            this.cancelTokens.delete(loadingKey);
        }
    }

    /**
     * Compare performance metrics across multiple runs
     * @param {Array<string>} runIds - Array of run IDs to compare
     * @returns {Promise<Object>} Comparison analysis object
     */
    async compareRuns(runIds) {
        if (!runIds || !Array.isArray(runIds) || runIds.length === 0) {
            throw new APIError('At least one run ID is required for comparison', API_ERRORS.INVALID_REQUEST, 400);
        }

        if (runIds.length > 10) {
            throw new APIError('Cannot compare more than 10 runs at once', API_ERRORS.INVALID_REQUEST, 400);
        }

        const endpoint = '/api/runs/compare';
        const params = { run_ids: runIds.join(',') };
        const cacheKey = this.generateCacheKey(endpoint, params);
        const loadingKey = `compareRuns:${runIds.join(',')}`;

        // Check cache first
        const cachedData = this.cache.get(cacheKey);
        if (cachedData) {
            devLog.log(`[API] Returning cached comparison for runs: ${runIds.join(', ')}`);
            return cachedData;
        }

        // Check if already loading
        if (this.getLoadingState(loadingKey)) {
            throw new APIError('Comparison request already in progress', API_ERRORS.INVALID_REQUEST, 409);
        }

        try {
            this.setLoadingState(loadingKey, true);
            const cancelToken = this.createCancelToken(loadingKey);

            const response = await this.executeWithRetry(async () => {
                return await this.axiosInstance.get(endpoint, { 
                    params,
                    cancelToken 
                });
            });

            // Transform comparison data
            const comparisonData = response.data.data;
            const transformedComparison = {
                runIds: runIds,
                comparedAt: new Date(response.data.timestamp),
                summary: {
                    totalRuns: comparisonData.summary?.total_runs || runIds.length,
                    avgDuration: comparisonData.summary?.avg_duration || 0,
                    avgThroughput: comparisonData.summary?.avg_throughput || 0,
                    bestPerformingRun: comparisonData.summary?.best_performing_run || null,
                    worstPerformingRun: comparisonData.summary?.worst_performing_run || null,
                },
                metrics: {
                    duration: comparisonData.metrics?.duration || [],
                    throughput: comparisonData.metrics?.throughput || [],
                    memoryUsage: comparisonData.metrics?.memory_usage || [],
                    cpuUsage: comparisonData.metrics?.cpu_usage || [],
                    errorRates: comparisonData.metrics?.error_rates || [],
                },
                analysis: {
                    performanceTrend: comparisonData.analysis?.performance_trend || 'stable',
                    significantDifferences: comparisonData.analysis?.significant_differences || [],
                    recommendations: comparisonData.analysis?.recommendations || [],
                },
                runDetails: (comparisonData.run_details || []).map(run => ({
                    id: run.id,
                    timestamp: new Date(run.timestamp),
                    duration: run.duration,
                    recordsGenerated: run.records_generated,
                    throughput: run.throughput,
                    status: run.status,
                })),
            };

            // Cache with shorter TTL for comparison data
            this.cache.set(cacheKey, transformedComparison, API_CONFIG.CACHE_TTL / 2);
            return transformedComparison;

        } finally {
            this.setLoadingState(loadingKey, false);
            this.cancelTokens.delete(loadingKey);
        }
    }

    /**
     * Get real-time metrics for currently active or most recent run
     * @returns {Promise<Object>} Latest metrics object
     */
    async getLatestMetrics() {
        const endpoint = '/api/metrics/latest';
        const loadingKey = 'getLatestMetrics';

        // Don't cache latest metrics as they should be real-time
        // Check if already loading
        if (this.getLoadingState(loadingKey)) {
            throw new APIError('Latest metrics request already in progress', API_ERRORS.INVALID_REQUEST, 409);
        }

        try {
            this.setLoadingState(loadingKey, true);
            const cancelToken = this.createCancelToken(loadingKey);

            const response = await this.executeWithRetry(async () => {
                return await this.axiosInstance.get(endpoint, { cancelToken });
            }, 1, 500); // Fewer retries for real-time data

            // Transform latest metrics data
            const metricsData = response.data.data;
            const transformedMetrics = {
                timestamp: new Date(response.data.timestamp),
                isActive: metricsData.is_active || false,
                currentRunId: metricsData.current_run_id || null,
                status: metricsData.status || 'idle',
                progress: {
                    percentage: metricsData.progress?.percentage || 0,
                    recordsProcessed: metricsData.progress?.records_processed || 0,
                    recordsTotal: metricsData.progress?.records_total || 0,
                    estimatedTimeRemaining: metricsData.progress?.estimated_time_remaining || null,
                },
                realtime: {
                    currentThroughput: metricsData.realtime?.current_throughput || 0,
                    avgThroughput: metricsData.realtime?.avg_throughput || 0,
                    cpuUsage: metricsData.realtime?.cpu_usage || 0,
                    memoryUsage: metricsData.realtime?.memory_usage || 0,
                    activeCreators: metricsData.realtime?.active_creators || 0,
                    activeWriters: metricsData.realtime?.active_writers || 0,
                    queueDepth: metricsData.realtime?.queue_depth || 0,
                },
                lastCompleted: metricsData.last_completed ? {
                    runId: metricsData.last_completed.run_id,
                    timestamp: new Date(metricsData.last_completed.timestamp),
                    duration: metricsData.last_completed.duration,
                    recordsGenerated: metricsData.last_completed.records_generated,
                    status: metricsData.last_completed.status,
                } : null,
            };

            return transformedMetrics;

        } finally {
            this.setLoadingState(loadingKey, false);
            this.cancelTokens.delete(loadingKey);
        }
    }

    /**
     * Cancel a specific request by key
     * @param {string} requestKey - Key identifying the request to cancel
     * @returns {boolean} True if request was cancelled, false if not found
     */
    cancelRequest(requestKey) {
        const cancelSource = this.cancelTokens.get(requestKey);
        if (cancelSource) {
            cancelSource.cancel(`Request ${requestKey} cancelled by user`);
            this.cancelTokens.delete(requestKey);
            this.setLoadingState(requestKey, false);
            devLog.log(`[API] Cancelled request: ${requestKey}`);
            return true;
        }
        return false;
    }

    /**
     * Cancel all active requests
     * @returns {number} Number of requests cancelled
     */
    cancelAllRequests() {
        let cancelledCount = 0;
        
        this.cancelTokens.forEach((cancelSource, key) => {
            cancelSource.cancel('All requests cancelled');
            this.setLoadingState(key, false);
            cancelledCount++;
        });

        this.cancelTokens.clear();
        devLog.log(`[API] Cancelled ${cancelledCount} active requests`);
        return cancelledCount;
    }

    /**
     * Clear all cached data
     * @param {string} pattern - Optional pattern to match cache keys for selective clearing
     */
    clearCache(pattern = null) {
        if (pattern) {
            // Clear cache entries matching pattern
            const keysToDelete = [];
            this.cache.cache.forEach((value, key) => {
                if (key.includes(pattern)) {
                    keysToDelete.push(key);
                }
            });

            keysToDelete.forEach(key => this.cache.delete(key));
            devLog.log(`[API] Cleared ${keysToDelete.length} cache entries matching pattern: ${pattern}`);
        } else {
            // Clear all cache
            this.cache.clear();
            devLog.log('[API] Cleared all cache entries');
        }
    }

    /**
     * Get current cache statistics
     * @returns {Object} Cache statistics
     */
    getCacheStats() {
        return {
            totalEntries: this.cache.cache.size,
            memoryUsage: JSON.stringify([...this.cache.cache.entries()]).length,
            oldestEntry: Math.min(...Array.from(this.cache.timestamps.values())),
            newestEntry: Math.max(...Array.from(this.cache.timestamps.values())),
        };
    }

    /**
     * Get current loading states
     * @returns {Object} Loading states map
     */
    getLoadingStates() {
        return Object.fromEntries(this.loadingStates);
    }

    /**
     * Health check for the API service
     * @returns {Promise<Object>} Health status
     */
    async healthCheck() {
        try {
            const response = await this.axiosInstance.get('/health', {
                timeout: 5000,
            });
            
            return {
                status: 'healthy',
                timestamp: new Date(),
                version: response.data.version || 'unknown',
                uptime: response.data.uptime || 0,
            };
        } catch (error) {
            return {
                status: 'unhealthy',
                timestamp: new Date(),
                error: error.message,
            };
        }
    }
}

// Create singleton instance
const apiClient = new APIClient();

// Export the api object with all required methods
const api = {
    /**
     * Get list of all historical runs
     * @returns {Promise<Array>} Array of run metadata objects
     */
    getRunsList: () => apiClient.getRunsList(),

    /**
     * Get detailed metrics for a specific run
     * @param {string} runId - Unique run identifier
     * @returns {Promise<Object>} Detailed run metrics object
     */
    getRunDetails: (runId) => apiClient.getRunDetails(runId),

    /**
     * Compare performance metrics across multiple runs
     * @param {Array<string>} runIds - Array of run IDs to compare
     * @returns {Promise<Object>} Comparison analysis object
     */
    compareRuns: (runIds) => apiClient.compareRuns(runIds),

    /**
     * Get real-time metrics for currently active or most recent run
     * @returns {Promise<Object>} Latest metrics object
     */
    getLatestMetrics: () => apiClient.getLatestMetrics(),

    /**
     * Cancel a specific request or all requests
     * @param {string} requestKey - Optional key identifying specific request to cancel
     * @returns {boolean|number} True/count if requests were cancelled
     */
    cancelRequest: (requestKey = null) => {
        return requestKey ? 
            apiClient.cancelRequest(requestKey) : 
            apiClient.cancelAllRequests();
    },

    /**
     * Clear cached data
     * @param {string} pattern - Optional pattern to match cache keys for selective clearing
     */
    clearCache: (pattern = null) => apiClient.clearCache(pattern),

    /**
     * Utility methods for debugging and monitoring
     */
    _debug: {
        getCacheStats: () => apiClient.getCacheStats(),
        getLoadingStates: () => apiClient.getLoadingStates(),
        healthCheck: () => apiClient.healthCheck(),
        cancelAllRequests: () => apiClient.cancelAllRequests(),
    }
};

export default api;