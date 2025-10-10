# 🔥 SECO-TransP Heatmap Testing Guide

## Overview
This guide provides step-by-step instructions for testing the new heatmap functionality implemented in the SECO-TransP extension.

## Phase 1 & 2 Implementation Summary

### What Was Implemented:
1. **Content Script** (`content-script.js`): Captures mouse movements, clicks, keyboard input, and scroll events
2. **Database Model** (`HeatmapPoint`): Stores heatmap data points with task association
3. **Backend Integration** (`submit_tasks`): Processes and stores heatmap data
4. **Extension Integration**: Automatically starts/stops heatmap capture with tasks

### Files Modified:
- `tet-extension/manifest.json` - Added content script
- `tet-extension/content-script.js` - New file for data capture
- `tet-extension/background.js` - Added heatmap data handling
- `tet-extension/popup.js` - Integrated heatmap capture with task tracking
- `tet-website/models/collection_data.py` - Added HeatmapPoint model
- `tet-website/external/tasks.py` - Added heatmap data processing
- `tet-website/migrations/versions/add_heatmap_points_table.py` - Database migration

## Testing Instructions

### Prerequisites
1. Ensure the extension is loaded in Chrome
2. Have access to the backend database
3. Open browser developer tools (F12) to monitor console logs

### Step 1: Database Migration
```bash
cd tet-website
python -m flask db upgrade
```
**Expected Result**: HeatmapPoint table created successfully

### Step 2: Extension Testing

#### 2.1 Load the Extension
1. Open Chrome Extensions page (`chrome://extensions/`)
2. Enable Developer mode
3. Load the SECO-TransP extension
4. Check for any errors in the extension console

#### 2.2 Test Content Script Loading
1. Open any webpage (e.g., `https://www.google.com`)
2. Open Developer Tools (F12) → Console
3. Look for: `🔥 SECO-TransP Content Script loaded on: [URL]`
4. **Expected Result**: Content script loads without errors

#### 2.3 Test Heatmap Capture
1. Open the test page: `tet-extension/test-heatmap.html`
2. Open SECO-TransP extension
3. Start an evaluation and begin a task
4. Move mouse around the test page
5. Click on various elements
6. Type in input fields
7. Scroll up and down

#### 2.4 Monitor Console Logs
Look for these log messages in the browser console:

**Content Script Logs:**
- `🔥 SECO-TransP Content Script loaded on: [URL]`
- `📏 Page height detected: [number]`
- `🎬 Starting heatmap recording for task: [taskId]`
- `📊 Interaction stored: {type, x, y, taskId, url, totalPoints}`
- `📤 Sending heatmap data: {taskId, processId, url, totalPoints}`

**Background Script Logs:**
- `📨 Background script received message: heatmapData`
- `🔥 Received heatmap data: {taskId, processId, url, totalPoints}`
- `✅ Heatmap data forwarded successfully`

**Popup Script Logs:**
- `🔥 Starting heatmap capture for task: [taskId]`
- `📊 Processing heatmap data: {taskId, processId, url, totalPoints}`
- `✅ Heatmap data processed and stored: {newPoints, totalPoints}`

### Step 3: Backend Testing

#### 3.1 Test Data Submission
1. Complete a task in the extension
2. Submit the evaluation
3. Check backend console logs for:
   - `Heatmap points count: [number]`
   - `Heatmap samples: [array of points]`
   - `✅ Heatmap point added: [type] at ([x], [y]) for task [taskId]`

#### 3.2 Verify Database Storage
```sql
-- Check if heatmap points are stored
SELECT COUNT(*) FROM heatmap_points;

-- Check recent heatmap points
SELECT point_id, task_id, url, x, y, point_type, timestamp 
FROM heatmap_points 
ORDER BY timestamp DESC 
LIMIT 10;

-- Check heatmap points by task
SELECT task_id, COUNT(*) as point_count, 
       MIN(timestamp) as first_point, 
       MAX(timestamp) as last_point
FROM heatmap_points 
GROUP BY task_id;
```

### Step 4: Data Quality Verification

#### 4.1 Check Data Completeness
- Verify that heatmap points are captured during task execution
- Ensure points are associated with correct task IDs
- Confirm timestamps are accurate
- Check that URL tracking works correctly

#### 4.2 Check Data Accuracy
- Mouse coordinates should be reasonable (within page bounds)
- Point types should match user actions (mousemove, click, keyboard)
- Scroll positions should reflect actual page scroll
- Page dimensions should match actual page size

## Troubleshooting

### Common Issues

#### 1. Content Script Not Loading
**Symptoms**: No console logs from content script
**Solutions**:
- Check manifest.json has correct content script configuration
- Reload the extension
- Check for JavaScript errors in console

#### 2. Heatmap Data Not Captured
**Symptoms**: No heatmap data in console logs
**Solutions**:
- Ensure task is active (currentPhase === "task")
- Check that startTaskHeatmapCapture() is called
- Verify content script is receiving startHeatmapCapture message

#### 3. Data Not Stored in Database
**Symptoms**: No heatmap points in database
**Solutions**:
- Check backend logs for errors
- Verify database migration was applied
- Check that submit_tasks endpoint processes heatmap_points

#### 4. Performance Issues
**Symptoms**: Browser becomes slow during heatmap capture
**Solutions**:
- Check throttling is working (200ms timeout)
- Monitor memory usage
- Reduce sampling frequency if needed

### Debug Commands

#### Check Extension Status
```javascript
// In browser console
chrome.runtime.sendMessage({type: 'getHeatmapStatus'}, console.log);
```

#### Check Data Collection
```javascript
// In popup console
console.log('Heatmap points:', data_collection.heatmap_points.length);
console.log('Navigation events:', data_collection.navigation.length);
```

## Expected Results

### Successful Implementation Should Show:
1. ✅ Content script loads on all pages
2. ✅ Heatmap capture starts when task begins
3. ✅ Mouse movements, clicks, and keyboard input are captured
4. ✅ Data is sent to background script every 5 seconds
5. ✅ Data is processed and stored in popup
6. ✅ Data is submitted to backend with task completion
7. ✅ Data is stored in database with correct associations
8. ✅ No performance degradation during capture

### Performance Benchmarks:
- Content script load time: < 100ms
- Mouse event processing: < 10ms per event
- Data transmission: Every 5 seconds
- Memory usage: < 50MB additional
- Database storage: ~1KB per 100 points

## Next Steps

After successful testing of Phase 1 & 2:
1. Implement Phase 3: Heatmap generation API
2. Implement Phase 4: Frontend visualization
3. Implement Phase 5: Full integration testing

## Support

If you encounter issues:
1. Check console logs for error messages
2. Verify all files are correctly modified
3. Test with the provided test page
4. Check database connectivity and migrations



