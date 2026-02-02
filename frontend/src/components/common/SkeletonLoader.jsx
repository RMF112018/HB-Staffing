import React from 'react';
import './SkeletonLoader.css';

const SkeletonLoader = ({
  type = 'text',
  width = '100%',
  height = '1rem',
  lines = 1,
  className = ''
}) => {
  const renderSkeleton = () => {
    switch (type) {
      case 'text':
        return (
          <div className={`skeleton-text ${className}`}>
            {Array.from({ length: lines }, (_, index) => (
              <div
                key={index}
                className="skeleton-line"
                style={{
                  width: index === lines - 1 ? '60%' : width,
                  height: height
                }}
              />
            ))}
          </div>
        );

      case 'circle':
        return (
          <div
            className={`skeleton-circle ${className}`}
            style={{
              width: width,
              height: width
            }}
          />
        );

      case 'rectangle':
        return (
          <div
            className={`skeleton-rectangle ${className}`}
            style={{
              width: width,
              height: height
            }}
          />
        );

      case 'table':
        return (
          <div className={`skeleton-table ${className}`}>
            <div className="skeleton-table-header">
              <div className="skeleton-line" style={{ width: '20%', height: '1.5rem' }} />
              <div className="skeleton-line" style={{ width: '30%', height: '1.5rem' }} />
              <div className="skeleton-line" style={{ width: '25%', height: '1.5rem' }} />
              <div className="skeleton-line" style={{ width: '15%', height: '1.5rem' }} />
            </div>
            {Array.from({ length: 5 }, (_, index) => (
              <div key={index} className="skeleton-table-row">
                <div className="skeleton-line" style={{ width: '20%', height: '1rem' }} />
                <div className="skeleton-line" style={{ width: '30%', height: '1rem' }} />
                <div className="skeleton-line" style={{ width: '25%', height: '1rem' }} />
                <div className="skeleton-line" style={{ width: '15%', height: '1rem' }} />
              </div>
            ))}
          </div>
        );

      case 'card':
        return (
          <div className={`skeleton-card ${className}`}>
            <div className="skeleton-card-header">
              <div className="skeleton-line" style={{ width: '70%', height: '1.5rem' }} />
              <div className="skeleton-line" style={{ width: '50%', height: '1rem' }} />
            </div>
            <div className="skeleton-card-body">
              <div className="skeleton-line" style={{ width: '100%', height: '1rem' }} />
              <div className="skeleton-line" style={{ width: '90%', height: '1rem' }} />
              <div className="skeleton-line" style={{ width: '80%', height: '1rem' }} />
            </div>
          </div>
        );

      default:
        return (
          <div
            className={`skeleton-default ${className}`}
            style={{
              width: width,
              height: height
            }}
          />
        );
    }
  };

  return renderSkeleton();
};

export default SkeletonLoader;
