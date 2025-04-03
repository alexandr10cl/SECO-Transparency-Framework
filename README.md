# SECO Transparency Framework

Collaborative repository between VU, UNIRIO and UFPA universities for developing tools to evaluate transparency in Software Ecosystem portals.

## Prerequisites

Before running the application, ensure you have the following installed:

- Python 3.8 or higher
- Node.js 14 or higher
- npm 6 or higher

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/SECO-Transparency-Framework.git
   cd SECO-Transparency-Framework
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r tet-website/requirements.txt
   ```

4. Build the SECO dashboard for integration:
   ```bash
   cd secodashboard
   npm install
   
   # For Unix/Linux/macOS:
   npm run build-for-flask
   
   # For Windows:
   npm run build-for-flask-win
   
   cd ..
   ```

## Running the Application

1. Start the Flask application:
   ```bash
   cd tet-website
   python app.py
   ```

2. Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

3. Sign in as a SECO manager to access the dashboard at:
   ```
   http://localhost:5000/seco_dashboard
   ```

## Development Workflow

### Working on the Flask Application

1. Make changes to the Flask application as needed
2. Run the Flask server to see changes:
   ```bash
   cd tet-website
   python app.py
   ```

### Working on the Dashboard

For development of the dashboard component:

1. In one terminal, start the Flask server:
   ```bash
   cd tet-website
   python app.py
   ```

2. In another terminal, start the React development server:
   ```bash
   cd secodashboard
   npm start
   ```

3. Access the dashboard development server at:
   ```
   http://localhost:3000
   ```

4. When you're ready to integrate your changes:
   ```bash
   # For Unix/Linux/macOS:
   npm run build-for-flask
   
   # For Windows:
   npm run build-for-flask-win
   ```

## Project Structure

- `tet-website/`: Contains the main Flask application
  - `app.py`: Entry point for the application
  - `models/`: Database models
  - `views/`: Route handlers and views
  - `templates/`: HTML templates
  - `static/`: Static files including the built dashboard
  - `static/dashboard/`: Built React dashboard files

- `secodashboard/`: React dashboard source code
  - `src/`: React component source files
  - `public/`: Public assets

## Authentication

- Only authenticated SECO managers can access the dashboard
- Login through the main application interface
- The dashboard provides visualizations and analysis of evaluation data

## Troubleshooting

If you encounter issues with the dashboard:

1. Make sure the dashboard is properly built and copied to the Flask static folder
2. Check browser console for JavaScript errors
3. Verify that the API endpoints are returning data correctly
