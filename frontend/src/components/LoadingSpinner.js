import React from 'react';

const LoadingSpinner = ({ size = 'medium', text = 'Memuat...', className = '' }) => {
  const sizeClasses = {
    small: 'loading-spinner-sm',
    medium: 'loading-spinner',
    large: 'loading-spinner-lg'
  };

  return (
    <div className={`text-center ${className}`}>
      <div className={`${sizeClasses[size]}`}></div>
      {text && <p className="mt-3 text-muted">{text}</p>}
    </div>
  );
};

export default LoadingSpinner;
