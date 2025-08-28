/**
 * API Client Service for FUSE Test Data Generator Performance Monitoring
 * 
 * Provides a centralized interface for all communication with the FastAPI backend.
 * Implements axios-based HTTP methods for fetching performance metrics, run histories,
 * and comparison data with comprehensive error handling, retry logic, and response transformation.
 * 
 * Features:
 * - Centralized axios configuration with base URL and CORS support
 * - Comprehensive error handling with user-friendly error messages
 * - Retry logic with exponential backoff for transient failures
 * - Request/response interceptors for logging and debugging
 * - Caching strategy for frequently accessed data
 * - Request cancellation support for long-running requests
 * - Response transformation to match frontend component expectations
 */

import axios from 'axios';

// Configuration constants
const BASE_URL = 'http://localhost:8000';
const DEFAULT_TIMEOUT = 10000; // 10 seconds
const MAX_RETRIES = 3;
const INITIAL_RETRY_DELAY = 1000; // 1 second
const CACHE_TIMEOUT = 300000; // 5 minutes

/**
 * Cache implementation for storing API responses
 */
class ApiCache {
    constructor() {
        this.cache = new Map();
        this.timeouts = new Map();
    }

    set(key, value, ttl = CACHE_TIMEOUT) {
        // Clear existing timeout for this key
        if (this.timeouts.has(key)) {
            clearTimeout(this.timeouts.get(key));
        }

        // Store the value
        this.cache.set(key, {
            data: value,
            timestamp: Date.now(),
            ttl: ttl
        });

        // Set timeout to remove the cached item
        const timeoutId = setTimeout(() => {
            this.delete(key);
        }, ttl);

        this.timeouts.set(key, timeoutId);
    }

    get(key) {
        const item = this.cache.get(key);
        if (!item) {
            return null;
        }

        // Check if item has expired
        const now = Date.now();
        if (now - item.timestamp > item.ttl) {
            this.delete(key);
            return null;
        }

        return item.data;
    }

    has(key) {
        return this.get(key) !== null;
    }

    delete(key) {
        if (this.timeouts.has(key)) {
            clearTimeout(this.timeouts.get(key));
            this.timeouts.delete(key);
        }
        return this.cache.delete(key);
    }

    clear() {
        // Clear all timeouts
        for (const timeoutId of this.timeouts.values()) {
            clearTimeout(timeoutId);
        }
        this.timeouts.clear();
        this.cache.clear();
    }
}

/**
 * Create axios instance with default configuration
 */
const apiClient = axios.create({
    baseURL: BASE_URL,
    timeout: DEFAULT_TIMEOUT,
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    },
});

// Create cache instance
const cache = new ApiCache();

// Store active requests for cancellation
const activeRequests = new Map();

/**
 * Retry logic implementation with exponential backoff
 */
const retryRequest = async (requestConfig, retryCount = 0) => {
    try {
        const response = await apiClient(requestConfig);
        return response;
    } catch (error) {
        // Don't retry if request was cancelled
        if (axios.isCancel(error)) {
            throw error;
        }

        // Don't retry client errors (4xx)
        if (error.response && error.response.status >= 400 && error.response.status < 500) {
            throw error;
        }

        // Retry on network errors or server errors (5xx)
        if (retryCount < MAX_RETRIES && (!error.response || error.response.status >= 500)) {
            const delay = INITIAL_RETRY_DELAY * Math.pow(2, retryCount);
            
            console.warn(`API request failed, retrying in ${delay}ms (attempt ${retryCount + 1}/${MAX_RETRIES})`);
            
            await new Promise(resolve => setTimeout(resolve, delay));
            return retryRequest(requestConfig, retryCount + 1);
        }

        throw error;
    }
};

/**
 * Request interceptor for logging and debugging
 */
apiClient.interceptors.request.use(
    (config) => {
        console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
        return config;
    },
    (error) => {
        console.error('API Request Error:', error);
        return Promise.reject(error);
    }
);

/**
 * Response interceptor for error handling and logging
 */
apiClient.interceptors.response.use(
    (response) => {
        console.log(`API Response: ${response.status} ${response.config.url}`);
        return response;
    },
    (error) => {
        if (!axios.isCancel(error)) {
            console.error('API Response Error:', error);
        }
        return Promise.reject(error);
    }
);

/**
 * Transform API error to user-friendly format
 */
const transformError = (error) => {
    if (axios.isCancel(error)) {
        return {
            type: 'CANCELLED',
            message: 'Request was cancelled',
            originalError: error
        };
    }

    if (!error.response) {
        // Network error
        return {
            type: 'NETWORK_ERROR',
            message: 'Unable to connect to the metrics service. Please ensure the FastAPI backend is running.',
            originalError: error
        };
    }

    const { status, data } = error.response;

    switch (status) {
        case 404:
            return {
                type: 'NOT_FOUND',
                message: 'The requested resource was not found',
                originalError: error
            };
        case 422:
            return {
                type: 'VALIDATION_ERROR',
                message: data?.error?.message || 'Invalid request parameters',
                details: data?.error?.details,
                originalError: error
            };
        case 500:
            return {
                type: 'SERVER_ERROR',
                message: 'Internal server error occurred while processing your request',
                originalError: error
            };
        default:
            return {
                type: 'API_ERROR',
                message: data?.error?.message || `Request failed with status ${status}`,
                originalError: error
            };
    }
};

/**
 * Transform API response to match frontend expectations
 */
const transformResponse = (response) => {
    // Extract data from envelope format
    if (response.data && response.data.status === 'success') {
        return {
            data: response.data.data,
            metadata: response.data.metadata,
            timestamp: response.data.timestamp
        };
    }

    // Fallback for direct data responses
    return {
        data: response.data,
        metadata: {},
        timestamp: new Date().toISOString()
    };
};

/**
 * Generate cache key for requests
 */
const generateCacheKey = (method, url, params = null) => {
    const paramString = params ? JSON.stringify(params) : '';
    return `${method}:${url}:${paramString}`;
};

/**
 * Core API methods
 */
const api = {
    /**
     * Fetch list of all available performance run metrics
     * @returns {Promise<Object>} List of historical run summaries with metadata
     */
    async getRunsList() {
        const cacheKey = generateCacheKey('GET', '/api/runs');
        
        // Check cache first
        if (cache.has(cacheKey)) {
            console.log('Returning cached runs list');
            return cache.get(cacheKey);
        }

        try {
            const cancelToken = axios.CancelToken.source();
            activeRequests.set('getRunsList', cancelToken);

            const requestConfig = {
                method: 'GET',
                url: '/api/runs',
                cancelToken: cancelToken.token
            };

            const response = await retryRequest(requestConfig);
            const transformedResponse = transformResponse(response);
            
            // Cache the response
            cache.set(cacheKey, transformedResponse);
            
            return transformedResponse;
        } catch (error) {
            throw transformError(error);
        } finally {
            activeRequests.delete('getRunsList');
        }
    },

    /**
     * Retrieve detailed metrics for a specific performance run
     * @param {string} runId - Unique identifier for the run
     * @returns {Promise<Object>} Complete metrics for individual run
     */
    async getRunDetails(runId) {
        if (!runId) {
            throw {
                type: 'VALIDATION_ERROR',
                message: 'Run ID is required'
            };
        }

        const cacheKey = generateCacheKey('GET', `/api/runs/${runId}`);
        
        // Check cache first
        if (cache.has(cacheKey)) {
            console.log(`Returning cached run details for ${runId}`);
            return cache.get(cacheKey);
        }

        try {
            const cancelToken = axios.CancelToken.source();
            activeRequests.set(`getRunDetails_${runId}`, cancelToken);

            const requestConfig = {
                method: 'GET',
                url: `/api/runs/${runId}`,
                cancelToken: cancelToken.token
            };

            const response = await retryRequest(requestConfig);
            const transformedResponse = transformResponse(response);
            
            // Cache the response
            cache.set(cacheKey, transformedResponse);
            
            return transformedResponse;
        } catch (error) {
            throw transformError(error);
        } finally {
            activeRequests.delete(`getRunDetails_${runId}`);
        }
    },

    /**
     * Compare performance metrics across multiple runs
     * @param {Array<string>} runIds - Array of run IDs to compare
     * @returns {Promise<Object>} Side-by-side performance comparisons
     */
    async compareRuns(runIds) {
        if (!Array.isArray(runIds) || runIds.length === 0) {
            throw {
                type: 'VALIDATION_ERROR',
                message: 'Run IDs array is required and must not be empty'
            };
        }

        if (runIds.length < 2) {
            throw {
                type: 'VALIDATION_ERROR',
                message: 'At least two run IDs are required for comparison'
            };
        }

        const cacheKey = generateCacheKey('GET', '/api/runs/compare', { run_ids: runIds.sort() });
        
        // Check cache first
        if (cache.has(cacheKey)) {
            console.log(`Returning cached run comparison for ${runIds.length} runs`);
            return cache.get(cacheKey);
        }

        try {
            const cancelToken = axios.CancelToken.source();
            activeRequests.set('compareRuns', cancelToken);

            const requestConfig = {
                method: 'GET',
                url: '/api/runs/compare',
                params: {
                    run_ids: runIds.join(',')
                },
                cancelToken: cancelToken.token
            };

            const response = await retryRequest(requestConfig);
            const transformedResponse = transformResponse(response);
            
            // Cache the response
            cache.set(cacheKey, transformedResponse);
            
            return transformedResponse;
        } catch (error) {
            throw transformError(error);
        } finally {
            activeRequests.delete('compareRuns');
        }
    },

    /**
     * Fetch current/latest performance metrics for active or most recent run
     * @returns {Promise<Object>} Current execution performance data
     */
    async getLatestMetrics() {
        try {
            const cancelToken = axios.CancelToken.source();
            activeRequests.set('getLatestMetrics', cancelToken);

            const requestConfig = {
                method: 'GET',
                url: '/api/metrics/latest',
                cancelToken: cancelToken.token
            };

            // Don't cache latest metrics as they should always be fresh
            const response = await retryRequest(requestConfig);
            const transformedResponse = transformResponse(response);
            
            return transformedResponse;
        } catch (error) {
            throw transformError(error);
        } finally {
            activeRequests.delete('getLatestMetrics');
        }
    },

    /**
     * Cancel active API requests
     * @param {string} requestKey - Specific request to cancel, or null for all
     */
    cancelRequest(requestKey = null) {
        if (requestKey) {
            const cancelToken = activeRequests.get(requestKey);
            if (cancelToken) {
                cancelToken.cancel(`Request ${requestKey} cancelled by user`);
                activeRequests.delete(requestKey);
                console.log(`Cancelled request: ${requestKey}`);
            }
        } else {
            // Cancel all active requests
            for (const [key, cancelToken] of activeRequests.entries()) {
                cancelToken.cancel(`Request ${key} cancelled by user`);
                console.log(`Cancelled request: ${key}`);
            }
            activeRequests.clear();
        }
    },

    /**
     * Clear cached API responses
     * @param {string} pattern - Optional pattern to match keys for selective clearing
     */
    clearCache(pattern = null) {
        if (pattern) {
            // Clear cache entries matching pattern
            const keysToDelete = [];
            for (const key of cache.cache.keys()) {
                if (key.includes(pattern)) {
                    keysToDelete.push(key);
                }
            }
            keysToDelete.forEach(key => cache.delete(key));
            console.log(`Cleared ${keysToDelete.length} cached entries matching pattern: ${pattern}`);
        } else {
            // Clear all cache
            cache.clear();
            console.log('Cleared all cached API responses');
        }
    }
};

export default api;