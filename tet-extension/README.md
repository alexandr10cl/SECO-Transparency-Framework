# Transparency-evaluation-tool

## Configuração de Ambiente (Development vs Production)

### Como trocar entre localhost e site deployado:

1. **Abra o arquivo `popup.js`**
2. **Localize a seção de configuração no topo do arquivo:**
   ```javascript
   // API Configuration
   const CONFIG = {
     isDevelopment: true, // Set to false for production
     DEVELOPMENT_URL: "http://127.0.0.1:5000",
     PRODUCTION_URL: "https://your-deployed-site.com", // Replace with your actual deployed URL
     get API_BASE_URL() {
       return this.isDevelopment ? this.DEVELOPMENT_URL : this.PRODUCTION_URL;
     }
   };
   ```

3. **Para desenvolvimento (localhost):**
   - Mantenha `isDevelopment: true`

4. **Para produção (site deployado):**
   - Altere para `isDevelopment: false`
   - Substitua `"https://your-deployed-site.com"` pela URL real do seu site deployado

### APIs utilizadas:
- `/auth_evaluation` - Validação do código de autenticação
- `/load_tasks` - Carregamento das tarefas da avaliação
- `/submit_tasks` - Envio dos dados coletados

## Como remover a sincronização com o UX-Tracking
- Na pasta tet-extension, vá no arquivo popup.js
- Na função ``` // Sincronizar código com API DO UX-TRACKING
document.getElementById("syncButton").addEventListener("click", function () { ... ``` 
- defina a variável ```let uxt_mode = true; // Opção de fazer a avaliação com UX-Tracking ou não``` para ```false```