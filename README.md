# SECO-TransP: Transparency Evaluation Framework for Software Ecosystems

## Overview

**SECO-TransP** is a framework for evaluating transparency in software ecosystem portals. It integrates a browser extension, Flask backend, relational database, and interactive dashboards for result analysis. The goal is to provide a robust solution for managers and communities to assess, monitor, and enhance developer experience and portal governance.

---

## Key Features

- Assessment Configuration: Portal managers define parameters, select procedures, and generate unique evaluation codes.  
- Chrome Extension: Developers receive tasks, complete questionnaires, have navigation monitored, and provide real-time feedback.  
- Multimodal Data Collection: Optional integration with UX-Tracking for capturing interactions, emotions, and navigation.  
- Analytical Dashboards: Visualization of KPIs, scores per guideline, heatmaps, word clouds, and satisfaction charts.  
- User and Assessment Management: Control over participants, evaluations, guidelines, and success criteria.  
- RESTful API: Flask backend for data integration and persistence.  

---

## Project Structure

tet-website/  
├── app.py              # Flask initialization  
├── database.py         # Database configuration  
├── requirements.txt    # Python dependencies  
├── models/             # ORM models (SQLAlchemy)  
│   ├── collection_data.py  
│   ├── enums.py  
│   ├── evaluation.py  
│   ├── guideline.py  
│   ├── questionnaire.py  
│   ├── task.py  
│   └── user.py  
├── views/              # Flask routes (MVC)  
│   ├── index.py  
│   ├── pages.py  
│   └── auth.py  
├── external/           # Auxiliary scripts (e.g., task integration)  
│   └── tasks.py  
├── static/             # Static files  
│   ├── css/  
│   ├── js/  
│   ├── images/  
│   └── dashboard/  
├── templates/          # Jinja2 templates (HTML)  
│   ├── index.html  
│   ├── dashboard.html  
│   ├── data_collected.html  
│   ├── guidelines.html  
│   ├── about.html  
│   └── doc.html  
└── migrations/         # Database version control (Alembic)  

---

## Running Locally

1. Prerequisites:

- Python 3.10+  
- MySQL 
- Chrome (for extension testing)  

2. Install dependencies:

    pip install -r requirements.txt

3. Configure the database credentials:

Edit the `.env` file with the correct credentials.

4. Run the Flask server:

    python app.py

The backend will be available at http://localhost:5000

5. Install the Chrome extension:

- Open Chrome and go to chrome://extensions/  
- Enable "Developer Mode"  
- Click on "Load unpacked" and select the extension folder (tet-extension/)  

---

## Evaluation Workflow

- Configuration: The manager registers an evaluation and selects procedures.  
- Distribution: A unique code is generated and sent to developers.  
- Execution: Developers access the extension, fill out the profile questionnaire, and execute tasks.  
- Feedback: After each task, users provide quick feedback and comments.  
- Review: At the end of the process, users answer detailed questions about key success criteria.  
- Completion: The final questionnaire is submitted with all collected data.  
- Analysis: Managers access the dashboard to explore results, charts, heatmaps, and word clouds.  

---

## Technologies Used

- Backend: Python, Flask, SQLAlchemy, Alembic  
- Frontend: HTML5, CSS3, JavaScript (ES6+), Jinja2  
- Database: MySQL 
- Chrome Extension: JavaScript, Manifest V3  
- Visualization: Chart.js, WordCloud.js  
- UX-Tracking: Integration with external tool  

---

## Documentation

Full documentation is available in the `/doc` page at the website.

---

## Credits

Project developed by the LabESC (Complex Systems Engineering Laboratory) at UNIRIO, with contributions from undergraduate, master's, and PhD students.
