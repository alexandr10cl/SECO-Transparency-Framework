# SECO Transparency Framework

Collaborative repository between VU, UNIRIO and UFPA universities for developing tools to evaluate transparency in Software Ecosystem portals.

## Prerequisites

Before running the application, ensure you have the following installed:

- Python 3.8 or higher

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
   pip install -r requirements.txt
   ```

## Running the Application

1. Start the Flask development server:
   ```bash
   python app.py
   ```

2. Open your browser and navigate to:
   ```
   http://127.0.0.1:5000/
   ```

## Project Structure

- `app/`: Contains the main application logic.
- `models/`: Defines the database models.
- `views/`: Contains the route handlers and views.
- `templates/`: HTML templates for rendering the UI.
- `static/`: Static files like CSS, JavaScript, and images.
