# Transparency-evaluation-tool

## Como remover a sincronização com o UX-Tracking
- Na pasta tet-extension, vá no arquivo popup.js
- Na função ``` // Sincronizar código com API DO UX-TRACKING
document.getElementById("syncButton").addEventListener("click", function () { ... ``` 
- defina a variável ```let uxt_mode = true; // Opção de fazer a avaliação com UX-Tracking ou não``` para ```false```