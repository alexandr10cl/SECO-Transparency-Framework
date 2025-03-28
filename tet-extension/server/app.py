from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_cors import CORS 

app = Flask(__name__)
CORS(app) # Permite que qualquer origem acesse a API
#CORS(app, origins=["chrome-extension://abc123"]) bloquear depois com o id da extensao para apenas ela poder acessar a api

# Guardar os JSON recebidos
collections_data = []

@app.route('/')
def index():
    return render_template('index.html', collections=collections_data)

@app.route('/submit_tasks', methods=['POST'])
def dashboard():
    data = request.json  # Obtém os dados JSON enviados pela extensão
    collections_data.append(data)
    print("Dados recebidos:", data) 
    return jsonify({"message": "Dados recebidos com sucesso"}), 200


@app.route('/gettasks', methods=['GET'])
def get_tasks():
    selected_tasks = [{
        "id": 1,
        "title": "Task 1",
        "description": "Translate the page into Portuguese.",
        "questions": [
        { "text": "Could you solve the task? If not, could you explain why?" },
        { "text": "In your opinion, is the portal's translation system effective?" },
        { "text": "What do you think about the page design?" }
        ]
    },
    {
        "id": 2,
        "title": "Task 2",
        "description": "Find the language documentation.",
        "questions": [
        { "text": "Could you solve the task? If not, could you explain why?" },
        { "text": "Q2?" }
        ]
    },{
        "id": 3,
        "title": "Task 3",
        "description": "Task description.",
        "questions": [
        { "text": "Q1?" },
        { "text": "Q2?" }
        ]
    }]
    return jsonify(selected_tasks)

if __name__ == '__main__':
    app.run(debug=True)