/**
 * Main React Application Component for FUSE Test Data Generator Frontend
 * 
 * Orchestrates the performance monitoring dashboard with routing setup for different views,
 * initializes API client connections, and provides the overall application structure with
 * navigation and layout components for the metrics visualization interface.
 * 
 * Features:
 * - React Router configuration for navigation between dashboard, run details, and comparison views
 * - State management hooks for global application state
 * - Error boundaries for graceful error handling 
 * - Periodic polling for real-time metrics updates
 * - Responsive design with mobile-first approach
 * - Component-based structure with clear separation of concerns
 * - Automatic cleanup and resource management
 * 
 * @author Blitzy Platform
 * @version 1.0.0
 */

import React, { useState, useEffect, Component } from 'react';
import {
  BrowserRouter,
  Routes,
  Route,
  Link,
  NavLink,
  Navigate
} from 'react-router-dom';

// Internal component imports
import Dashboard from './components/Dashboard.js';
import RunComparison from './components/RunComparison.js';
import api from './services/api.js';

/**
 * Global Error Boundary Component
 * 
 * Catches JavaScript errors anywhere in the child component tree and displays
 * a fallback UI instead of the component tree that crashed.
 */
class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null
    };
  }

  static getDerivedStateFromError(error) {
    // Update state so the next render will show the fallback UI
    return {
      hasError: true,
      errorId: Date.now().toString(36) + Math.random().toString(36).substr(2)
    };
  }

  componentDidCatch(error, errorInfo) {
    // Log error details for debugging
    this.setState({
      error: error,
      errorInfo: errorInfo
    });

    // Development-only error logging
    if (process.env.NODE_ENV === 'development') {
      console.error('Error Boundary caught an error:', error, errorInfo); // eslint-disable-line no-console
    }

    // In production, you might want to log this to an error reporting service
    // logErrorToService(error, errorInfo);
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
      errorId: null
    });
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-boundary">
          <div className="error-boundary__container">
            <div className="error-boundary__icon">⚠️</div>
            <h1 className="error-boundary__title">Something went wrong</h1>
            <p className="error-boundary__message">
              We encountered an unexpected error in the application. This has been logged for our team to investigate.
            </p>
            
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="error-boundary__details">
                <summary>Error Details (Development Mode)</summary>
                <div className="error-boundary__error-info">
                  <p><strong>Error:</strong> {this.state.error.toString()}</p>
                  <p><strong>Stack Trace:</strong></p>
                  <pre>{this.state.errorInfo.componentStack}</pre>
                </div>
              </details>
            )}

            <div className="error-boundary__actions">
              <button 
                onClick={this.handleRetry}
                className="error-boundary__button error-boundary__button--primary"
              >
                Try Again
              </button>
              <button 
                onClick={this.handleReload}
                className="error-boundary__button error-boundary__button--secondary"
              >
                Reload Page
              </button>
            </div>

            <p className="error-boundary__error-id">
              Error ID: {this.state.errorId}
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Navigation Header Component
 * 
 * Provides application navigation with responsive design and active state indicators.
 */
const NavigationHeader = ({ 
  currentRoute, 
  onRefreshData, 
  isPollingActive, 
  onTogglePolling,
  apiHealthStatus 
}) => {
  return (
    <header className="app-header">
      <div className="app-header__container">
        {/* Application Brand/Title */}
        <div className="app-header__brand">
          <Link to="/" className="app-header__brand-link">
            <h1 className="app-header__title">FUSE Monitor</h1>
            <span className="app-header__subtitle">Performance Dashboard</span>
          </Link>
        </div>

        {/* Navigation Links */}
        <nav className="app-header__nav">
          <NavLink 
            to="/"
            className={({ isActive }) => 
              `app-header__nav-link ${isActive ? 'app-header__nav-link--active' : ''}`
            }
            end
          >
            <span className="app-header__nav-icon">📊</span>
            Dashboard
          </NavLink>
          
          <NavLink 
            to="/comparison"
            className={({ isActive }) => 
              `app-header__nav-link ${isActive ? 'app-header__nav-link--active' : ''}`
            }
          >
            <span className="app-header__nav-icon">📈</span>
            Compare Runs
          </NavLink>
        </nav>

        {/* Header Controls */}
        <div className="app-header__controls">
          {/* API Health Indicator */}
          <div className="app-header__health-indicator">
            <span 
              className={`app-header__health-dot ${
                apiHealthStatus === 'healthy' ? 'app-header__health-dot--healthy' :
                apiHealthStatus === 'unhealthy' ? 'app-header__health-dot--unhealthy' :
                'app-header__health-dot--unknown'
              }`}
              title={`API Status: ${apiHealthStatus || 'Unknown'}`}
            />
            <span className="app-header__health-text">API</span>
          </div>

          {/* Global Controls */}
          <button
            onClick={onTogglePolling}
            className={`app-header__control-btn ${
              isPollingActive ? 'app-header__control-btn--active' : 'app-header__control-btn--inactive'
            }`}
            title={isPollingActive ? 'Pause real-time updates' : 'Resume real-time updates'}
          >
            {isPollingActive ? '⏸️' : '▶️'}
            {isPollingActive ? 'Pause' : 'Resume'}
          </button>

          <button
            onClick={onRefreshData}
            className="app-header__control-btn app-header__control-btn--refresh"
            title="Refresh all data"
          >
            🔄 Refresh
          </button>
        </div>
      </div>
    </header>
  );
};

/**
 * Main App Component
 * 
 * Root component that sets up routing, global state management, error boundaries,
 * and orchestrates the overall application structure.
 */
const App = () => {
  // Global application state
  const [globalPollingActive, setGlobalPollingActive] = useState(true);
  const [apiHealthStatus, setApiHealthStatus] = useState(null);
  const [lastGlobalRefresh, setLastGlobalRefresh] = useState(new Date());
  const [selectedRuns, setSelectedRuns] = useState([]);
  const [globalError, setGlobalError] = useState(null);

  /**
   * Initialize API health monitoring
   */
  useEffect(() => {
    const checkApiHealth = async () => {
      try {
        const healthStatus = await api._debug.healthCheck();
        setApiHealthStatus(healthStatus.status);
        
        // Clear any previous global errors if API is healthy
        if (healthStatus.status === 'healthy' && globalError) {
          setGlobalError(null);
        }
      } catch (error) {
        setApiHealthStatus('unhealthy');
        setGlobalError({
          message: 'Failed to connect to API service',
          code: 'API_CONNECTION_ERROR',
          details: error
        });
      }
    };

    // Initial health check
    checkApiHealth();

    // Set up periodic health monitoring (every 30 seconds)
    const healthCheckInterval = setInterval(checkApiHealth, 30000);

    // Cleanup interval on unmount
    return () => {
      clearInterval(healthCheckInterval);
    };
  }, [globalError]);

  /**
   * Handle global polling toggle
   */
  const handleToggleGlobalPolling = () => {
    setGlobalPollingActive(prev => !prev);
  };

  /**
   * Handle global data refresh
   */
  const handleGlobalRefresh = () => {
    // Clear all cached API data
    api.clearCache();
    setLastGlobalRefresh(new Date());
    
    // Clear any global errors
    setGlobalError(null);
  };

  /**
   * Handle run selection changes from RunComparison component
   */
  const handleRunSelectionChange = (newSelectedRuns) => {
    setSelectedRuns(newSelectedRuns);
  };

  /**
   * Global error handler for API errors
   */
  const handleGlobalError = (error) => {
    setGlobalError(error);
  };

  /**
   * Clear global error
   */
  const clearGlobalError = () => {
    setGlobalError(null);
  };

  /**
   * Clean up resources on unmount
   */
  useEffect(() => {
    return () => {
      // Cancel any pending API requests
      api.cancelRequest();
    };
  }, []);

  return (
    <ErrorBoundary>
      <BrowserRouter>
        <div className="app">
          {/* Global Error Display */}
          {globalError && (
            <div className="app__global-error">
              <div className="app__global-error-content">
                <span className="app__global-error-icon">⚠️</span>
                <div className="app__global-error-message">
                  <strong>Global Error:</strong> {globalError.message}
                  {globalError.code && (
                    <span className="app__global-error-code"> ({globalError.code})</span>
                  )}
                </div>
                <button 
                  onClick={clearGlobalError}
                  className="app__global-error-close"
                  title="Dismiss error"
                >
                  ✕
                </button>
                <button 
                  onClick={handleGlobalRefresh}
                  className="app__global-error-retry"
                  title="Try to reconnect"
                >
                  Retry
                </button>
              </div>
            </div>
          )}

          {/* Navigation Header */}
          <NavigationHeader
            currentRoute={window.location.pathname}
            onRefreshData={handleGlobalRefresh}
            isPollingActive={globalPollingActive}
            onTogglePolling={handleToggleGlobalPolling}
            apiHealthStatus={apiHealthStatus}
          />

          {/* Main Content Area */}
          <main className="app__main">
            <Routes>
              {/* Dashboard Route (Home) */}
              <Route 
                path="/" 
                element={
                  <Dashboard 
                    globalPollingActive={globalPollingActive}
                    lastGlobalRefresh={lastGlobalRefresh}
                    onError={handleGlobalError}
                    selectedRunsFromComparison={selectedRuns}
                  />
                } 
              />
              
              {/* Run Comparison Route */}
              <Route 
                path="/comparison" 
                element={
                  <RunComparison 
                    initialSelectedRuns={selectedRuns}
                    onRunSelectionChange={handleRunSelectionChange}
                    globalPollingActive={globalPollingActive}
                    lastGlobalRefresh={lastGlobalRefresh}
                    onError={handleGlobalError}
                    showExports={true}
                    showCharts={true}
                    maxRuns={5}
                    minRuns={2}
                  />
                } 
              />

              {/* Redirect to Dashboard for any unmatched routes */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>

          {/* Footer */}
          <footer className="app__footer">
            <div className="app__footer-content">
              <p className="app__footer-text">
                FUSE Test Data Generator Performance Monitor - 
                <span className="app__footer-status">
                  {apiHealthStatus === 'healthy' ? '🟢 Connected' : 
                   apiHealthStatus === 'unhealthy' ? '🔴 Disconnected' : '🟡 Checking...'}
                </span>
              </p>
              <p className="app__footer-last-refresh">
                Last Refresh: {lastGlobalRefresh.toLocaleTimeString()}
              </p>
            </div>
          </footer>
        </div>
      </BrowserRouter>
    </ErrorBoundary>
  );
};

// CSS Styles for the application
const globalStyles = `
  /* Global App Styles */
  .app {
    min-height: 100vh;
    background-color: #f8fafc;
    display: flex;
    flex-direction: column;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 
                 'Oxygen', 'Ubuntu', 'Cantarell', sans-serif;
  }

  /* Global Error Styles */
  .app__global-error {
    background: linear-gradient(135deg, #fee2e2, #fecaca);
    border-bottom: 3px solid #dc2626;
    padding: 1rem;
    position: sticky;
    top: 0;
    z-index: 1000;
    box-shadow: 0 2px 8px rgba(220, 38, 38, 0.1);
  }

  .app__global-error-content {
    max-width: 1400px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .app__global-error-icon {
    font-size: 1.25rem;
    flex-shrink: 0;
  }

  .app__global-error-message {
    flex: 1;
    min-width: 200px;
    color: #7f1d1d;
    font-weight: 500;
  }

  .app__global-error-code {
    font-size: 0.875rem;
    opacity: 0.8;
    font-family: 'Courier New', monospace;
  }

  .app__global-error-close,
  .app__global-error-retry {
    background: #dc2626;
    color: white;
    border: none;
    padding: 0.5rem 1rem;
    border-radius: 0.25rem;
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: 500;
    transition: background-color 0.2s;
  }

  .app__global-error-close:hover,
  .app__global-error-retry:hover {
    background: #b91c1c;
  }

  .app__global-error-retry {
    background: #059669;
  }

  .app__global-error-retry:hover {
    background: #047857;
  }

  /* Header Styles */
  .app-header {
    background: linear-gradient(135deg, #1e293b, #334155);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    border-bottom: 1px solid #475569;
    position: sticky;
    top: 0;
    z-index: 900;
  }

  .app-header__container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 1rem 1.5rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 2rem;
    flex-wrap: wrap;
  }

  .app-header__brand {
    display: flex;
    align-items: center;
  }

  .app-header__brand-link {
    text-decoration: none;
    color: white;
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .app-header__title {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 700;
    color: #f1f5f9;
    line-height: 1.2;
  }

  .app-header__subtitle {
    font-size: 0.75rem;
    color: #cbd5e1;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .app-header__nav {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }

  .app-header__nav-link {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    text-decoration: none;
    color: #cbd5e1;
    font-weight: 500;
    border-radius: 0.5rem;
    transition: all 0.2s;
    border: 2px solid transparent;
  }

  .app-header__nav-link:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #f1f5f9;
  }

  .app-header__nav-link--active {
    background: rgba(59, 130, 246, 0.2);
    border-color: #3b82f6;
    color: #dbeafe;
  }

  .app-header__nav-icon {
    font-size: 1.25rem;
  }

  .app-header__controls {
    display: flex;
    gap: 1rem;
    align-items: center;
    flex-wrap: wrap;
  }

  .app-header__health-indicator {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.875rem;
    color: #cbd5e1;
  }

  .app-header__health-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
  }

  .app-header__health-dot--healthy {
    background: #10b981;
    box-shadow: 0 0 6px rgba(16, 185, 129, 0.4);
  }

  .app-header__health-dot--unhealthy {
    background: #ef4444;
    box-shadow: 0 0 6px rgba(239, 68, 68, 0.4);
  }

  .app-header__health-dot--unknown {
    background: #f59e0b;
    box-shadow: 0 0 6px rgba(245, 158, 11, 0.4);
  }

  .app-header__control-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 0.375rem;
    font-size: 0.875rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    color: white;
  }

  .app-header__control-btn--active {
    background: #059669;
  }

  .app-header__control-btn--active:hover {
    background: #047857;
  }

  .app-header__control-btn--inactive {
    background: #6b7280;
  }

  .app-header__control-btn--inactive:hover {
    background: #4b5563;
  }

  .app-header__control-btn--refresh {
    background: #3b82f6;
  }

  .app-header__control-btn--refresh:hover {
    background: #2563eb;
  }

  /* Main Content */
  .app__main {
    flex: 1;
    width: 100%;
    max-width: 1400px;
    margin: 0 auto;
    padding: 0;
  }

  /* Footer Styles */
  .app__footer {
    background: #f1f5f9;
    border-top: 1px solid #e2e8f0;
    padding: 1rem 1.5rem;
    margin-top: auto;
  }

  .app__footer-content {
    max-width: 1400px;
    margin: 0 auto;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .app__footer-text {
    margin: 0;
    font-size: 0.875rem;
    color: #64748b;
    display: flex;
    align-items: center;
    gap: 0.75rem;
  }

  .app__footer-status {
    font-weight: 500;
  }

  .app__footer-last-refresh {
    margin: 0;
    font-size: 0.75rem;
    color: #94a3b8;
  }

  /* Error Boundary Styles */
  .error-boundary {
    min-height: 100vh;
    background: linear-gradient(135deg, #fee2e2, #fecaca);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 2rem;
  }

  .error-boundary__container {
    background: white;
    border-radius: 1rem;
    padding: 3rem;
    max-width: 600px;
    text-align: center;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  }

  .error-boundary__icon {
    font-size: 4rem;
    margin-bottom: 1rem;
  }

  .error-boundary__title {
    font-size: 2rem;
    margin: 0 0 1rem 0;
    color: #1f2937;
    font-weight: 700;
  }

  .error-boundary__message {
    font-size: 1.125rem;
    color: #6b7280;
    margin: 0 0 2rem 0;
    line-height: 1.6;
  }

  .error-boundary__details {
    background: #f9fafb;
    border-radius: 0.5rem;
    padding: 1rem;
    margin: 2rem 0;
    text-align: left;
    border: 1px solid #e5e7eb;
  }

  .error-boundary__error-info {
    font-family: 'Courier New', monospace;
    font-size: 0.875rem;
    color: #374151;
  }

  .error-boundary__error-info pre {
    white-space: pre-wrap;
    word-break: break-word;
    max-height: 200px;
    overflow-y: auto;
  }

  .error-boundary__actions {
    display: flex;
    gap: 1rem;
    justify-content: center;
    margin-bottom: 2rem;
    flex-wrap: wrap;
  }

  .error-boundary__button {
    padding: 0.75rem 1.5rem;
    border: none;
    border-radius: 0.5rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
    font-size: 1rem;
  }

  .error-boundary__button--primary {
    background: #3b82f6;
    color: white;
  }

  .error-boundary__button--primary:hover {
    background: #2563eb;
  }

  .error-boundary__button--secondary {
    background: #f3f4f6;
    color: #374151;
    border: 1px solid #d1d5db;
  }

  .error-boundary__button--secondary:hover {
    background: #e5e7eb;
  }

  .error-boundary__error-id {
    font-size: 0.75rem;
    color: #9ca3af;
    font-family: 'Courier New', monospace;
    margin: 0;
  }

  /* Responsive Design */
  @media (max-width: 1024px) {
    .app-header__container {
      padding: 1rem;
      gap: 1rem;
    }
    
    .app-header__nav {
      order: 3;
      width: 100%;
      justify-content: center;
    }
    
    .app__footer-content {
      flex-direction: column;
      text-align: center;
      gap: 0.5rem;
    }
  }

  @media (max-width: 768px) {
    .app-header__title {
      font-size: 1.25rem;
    }
    
    .app-header__nav-link {
      padding: 0.5rem 0.75rem;
    }
    
    .app-header__controls {
      gap: 0.5rem;
    }
    
    .app__global-error-content {
      flex-direction: column;
      align-items: stretch;
    }
    
    .error-boundary__container {
      padding: 2rem;
      margin: 1rem;
    }
    
    .error-boundary__actions {
      flex-direction: column;
    }
  }

  /* High contrast mode support */
  @media (prefers-contrast: high) {
    .app-header {
      border-bottom: 2px solid #000;
    }
    
    .app__global-error {
      border-bottom: 3px solid #000;
    }
  }

  /* Reduced motion support */
  @media (prefers-reduced-motion: reduce) {
    .app-header__nav-link,
    .app-header__control-btn,
    .error-boundary__button {
      transition: none;
    }
  }

  /* Print styles */
  @media print {
    .app-header,
    .app__footer,
    .app__global-error {
      display: none;
    }
    
    .app__main {
      margin: 0;
      max-width: none;
    }
  }
`;

// Inject global styles
if (typeof document !== 'undefined') {
  const styleElement = document.createElement('style');
  styleElement.textContent = globalStyles;
  document.head.appendChild(styleElement);
}

export default App;