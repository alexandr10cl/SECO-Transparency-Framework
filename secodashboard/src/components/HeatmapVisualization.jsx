import React from 'react';

const HeatmapVisualization = ({ data, width = 260, height = 140 }) => {
  // Basic heatmap implementation without d3 for initial testing
  if (!data || data.length === 0) {
    return (
      <div className="h-full w-full flex items-center justify-center bg-gray-100 rounded">
        <span className="text-sm text-gray-500">No heatmap data available</span>
      </div>
    );
  }

  // Find the bounds of the data
  const maxValue = Math.max(...data.map(d => d.value));
  
  return (
    <div className="relative" style={{ width, height }}>
      <div className="absolute inset-0 bg-gray-100 rounded">
        {data.map((point, index) => (
          <div
            key={index}
            className="absolute rounded-full bg-blue-500"
            style={{
              left: `${(point.x / 400) * 100}%`,
              top: `${(point.y / 300) * 100}%`,
              width: `${Math.max(5, (point.value / maxValue) * 20)}px`,
              height: `${Math.max(5, (point.value / maxValue) * 20)}px`,
              opacity: 0.7,
              transform: 'translate(-50%, -50%)'
            }}
            title={`Interactions: ${point.value}`}
          />
        ))}
      </div>
    </div>
  );
};

export default HeatmapVisualization; 