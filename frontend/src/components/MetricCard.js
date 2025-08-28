import React, { memo } from 'react';
import PropTypes from 'prop-types';

/**
 * MetricCard - Reusable component for displaying individual performance metrics
 * 
 * Features:
 * - Prominent metric value display with proper formatting
 * - Clear typography hierarchy for labels and units
 * - Optional trend indicators with color coding
 * - Performance threshold color coding (green/yellow/red)
 * - CSS Flexbox responsive layout
 * - Interactive hover effects
 * - Loading state with skeleton placeholder
 * - Graceful handling of null/undefined values
 * - Optimized with React.memo to prevent unnecessary re-renders
 */
const MetricCard = ({
  name,
  value,
  unit = '',
  trend = null,
  icon = null,
  loading = false,
  threshold = null
}) => {
  // Format numeric values with appropriate separators and decimal places
  const formatValue = (val) => {
    if (val === null || val === undefined || val === '') {
      return '--';
    }
    
    if (typeof val === 'number') {
      // For large numbers, use thousands separators
      if (Math.abs(val) >= 1000) {
        return val.toLocaleString('en-US', {
          maximumFractionDigits: 2,
          minimumFractionDigits: 0
        });
      }
      
      // For small numbers, show appropriate decimal places
      if (val % 1 !== 0) {
        return val.toFixed(2);
      }
      
      return val.toString();
    }
    
    return val.toString();
  };

  // Determine color coding based on performance thresholds
  const getThresholdColor = (val, thresholds) => {
    if (!thresholds || val === null || val === undefined || typeof val !== 'number') {
      return 'default';
    }

    const { good, warning } = thresholds;
    
    if (good !== undefined) {
      if (thresholds.higher_is_better) {
        if (val >= good) return 'good';
        if (val >= warning) return 'warning';
        return 'critical';
      } else {
        if (val <= good) return 'good';
        if (val <= warning) return 'warning';
        return 'critical';
      }
    }
    
    return 'default';
  };

  // Format trend percentage and determine trend direction
  const formatTrend = (trendData) => {
    if (!trendData || trendData.percentage === null || trendData.percentage === undefined) {
      return null;
    }

    const percentage = Math.abs(trendData.percentage);
    const direction = trendData.percentage >= 0 ? 'up' : 'down';
    const formattedPercentage = percentage.toFixed(1);
    
    return {
      direction,
      percentage: formattedPercentage,
      isImprovement: trendData.is_improvement !== false
    };
  };

  const formattedValue = formatValue(value);
  const thresholdColor = getThresholdColor(value, threshold);
  const formattedTrend = formatTrend(trend);

  // Loading skeleton placeholder
  if (loading) {
    return (
      <div className="metric-card metric-card--loading">
        <div className="metric-card__header">
          <div className="metric-card__icon skeleton-placeholder"></div>
          <div className="metric-card__name skeleton-placeholder"></div>
        </div>
        <div className="metric-card__value skeleton-placeholder skeleton-placeholder--large"></div>
        <div className="metric-card__unit skeleton-placeholder"></div>
      </div>
    );
  }

  return (
    <div className={`metric-card metric-card--${thresholdColor}`}>
      <div className="metric-card__header">
        {icon && (
          <div className="metric-card__icon">
            {typeof icon === 'string' ? (
              <i className={`icon ${icon}`} aria-hidden="true" />
            ) : (
              icon
            )}
          </div>
        )}
        <h3 className="metric-card__name">{name}</h3>
      </div>
      
      <div className="metric-card__content">
        <div className="metric-card__value-container">
          <span className="metric-card__value">{formattedValue}</span>
          {unit && <span className="metric-card__unit">{unit}</span>}
        </div>
        
        {formattedTrend && (
          <div className={`metric-card__trend metric-card__trend--${formattedTrend.direction} ${
            formattedTrend.isImprovement ? 'metric-card__trend--improvement' : 'metric-card__trend--degradation'
          }`}>
            <span className="metric-card__trend-icon">
              {formattedTrend.direction === 'up' ? '↗' : '↙'}
            </span>
            <span className="metric-card__trend-value">{formattedTrend.percentage}%</span>
          </div>
        )}
      </div>
    </div>
  );
};

// PropTypes for runtime type validation
MetricCard.propTypes = {
  name: PropTypes.string.isRequired,
  value: PropTypes.oneOfType([
    PropTypes.number,
    PropTypes.string
  ]),
  unit: PropTypes.string,
  trend: PropTypes.object,
  icon: PropTypes.oneOfType([
    PropTypes.string,
    PropTypes.element
  ]),
  loading: PropTypes.bool,
  threshold: PropTypes.object
};

// CSS Styles for the MetricCard component
const styles = `
.metric-card {
  display: flex;
  flex-direction: column;
  padding: 1.5rem;
  border-radius: 0.75rem;
  border: 1px solid #e5e7eb;
  background-color: #ffffff;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease-in-out;
  min-height: 140px;
  position: relative;
  overflow: hidden;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border-color: #d1d5db;
}

/* Threshold color coding */
.metric-card--good {
  border-left: 4px solid #10b981;
}

.metric-card--good .metric-card__value {
  color: #059669;
}

.metric-card--warning {
  border-left: 4px solid #f59e0b;
}

.metric-card--warning .metric-card__value {
  color: #d97706;
}

.metric-card--critical {
  border-left: 4px solid #ef4444;
}

.metric-card--critical .metric-card__value {
  color: #dc2626;
}

.metric-card--default {
  border-left: 4px solid #6b7280;
}

/* Header section with icon and name */
.metric-card__header {
  display: flex;
  align-items: center;
  margin-bottom: 1rem;
}

.metric-card__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  margin-right: 0.75rem;
  border-radius: 0.375rem;
  background-color: #f3f4f6;
  color: #6b7280;
  font-size: 1rem;
}

.metric-card__name {
  margin: 0;
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
  line-height: 1.25;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

/* Content section with value and trend */
.metric-card__content {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.metric-card__value-container {
  display: flex;
  align-items: baseline;
  margin-bottom: 0.5rem;
}

.metric-card__value {
  font-size: 2rem;
  font-weight: 700;
  color: #1f2937;
  line-height: 1;
  margin-right: 0.5rem;
}

.metric-card__unit {
  font-size: 0.875rem;
  font-weight: 500;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Trend indicator */
.metric-card__trend {
  display: flex;
  align-items: center;
  font-size: 0.75rem;
  font-weight: 500;
  margin-top: auto;
}

.metric-card__trend-icon {
  margin-right: 0.25rem;
  font-size: 1rem;
}

.metric-card__trend--improvement {
  color: #059669;
}

.metric-card__trend--degradation {
  color: #dc2626;
}

/* Loading skeleton styles */
.metric-card--loading {
  pointer-events: none;
}

.skeleton-placeholder {
  background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
  background-size: 200% 100%;
  animation: loading 1.5s infinite;
  border-radius: 0.25rem;
  height: 1rem;
  width: 60%;
}

.skeleton-placeholder--large {
  height: 2rem;
  width: 80%;
}

@keyframes loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* Responsive design adjustments */
@media (max-width: 768px) {
  .metric-card {
    padding: 1rem;
    min-height: 120px;
  }
  
  .metric-card__value {
    font-size: 1.5rem;
  }
  
  .metric-card__name {
    font-size: 0.75rem;
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .metric-card {
    border-width: 2px;
  }
  
  .metric-card__value {
    font-weight: 800;
  }
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  .metric-card {
    transition: none;
  }
  
  .metric-card:hover {
    transform: none;
  }
  
  .skeleton-placeholder {
    animation: none;
  }
}
`;

// Inject styles if not already present (for standalone component usage)
if (typeof document !== 'undefined' && !document.querySelector('#metric-card-styles')) {
  const styleElement = document.createElement('style');
  styleElement.id = 'metric-card-styles';
  styleElement.textContent = styles;
  document.head.appendChild(styleElement);
}

// Export component wrapped with React.memo for performance optimization
export default memo(MetricCard);