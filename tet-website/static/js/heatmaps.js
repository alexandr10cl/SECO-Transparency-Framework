// 1. Pega o ID da avaliação que está no HTML
const id = document.getElementById('id-avaliacao').textContent.trim();

// 2. Faz a requisição para a API do backend
fetch(`/api/view_heatmap/${id}`)
    .then(response => {
        // Verifica se a resposta da rede foi bem-sucedida
        if (!response.ok) {
            throw new Error(`Erro na rede: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('Dados recebidos da API:', data);

        // 3. Garante que os dados estejam sempre em um formato de array para o loop
        let heatmapsParaProcessar = [];
        if (Array.isArray(data)) {
            heatmapsParaProcessar = data;
        } else if (data && typeof data === 'object') {
            // Se a API retornar um único objeto, coloca ele dentro de um array
            heatmapsParaProcessar = [data];
        }

        // 4. Para cada heatmap recebido, cria os elementos na página
        heatmapsParaProcessar.forEach((heatmapData) => {
            // Cria um contêiner principal para a imagem e o heatmap
            const container = document.createElement('div');
            container.style.position = 'relative';
            container.style.width = `${heatmapData.width}px`;
            container.style.height = `${heatmapData.height}px`;
            container.style.border = '1px solid #ccc'; // Borda sutil para visualização
            container.style.marginBottom = '50px';

            // Cria o elemento da imagem de fundo
            const img = document.createElement('img');
            img.src = `data:image/jpeg;base64,${heatmapData.image}`; // Corrigido para JPEG
            
            // Estiliza a imagem para preencher o contêiner
            img.style.position = 'absolute';
            img.style.top = '0';
            img.style.left = '0';
            img.style.width = '100%';
            img.style.height = '100%';
            
            // Adiciona a imagem dentro do contêiner
            container.appendChild(img);

            // Adiciona o contêiner principal na div 'heatmaps' do HTML
            document.querySelector('.heatmaps').appendChild(container);

            // Agora, cria a instância do heatmap DENTRO do mesmo contêiner
            const heatmapInstance = h337.create({
                container: container,
                radius: 50,
                maxOpacity: 0.6,
                blur: 0.9,
            });

            // Mapeia os pontos recebidos da API para o formato que a biblioteca heatmap.js espera
            const points = heatmapData.points.map(point => ({
                x: Math.round(point.x),
                y: Math.round(point.y),
                value: Math.round(point.intensity * 700) // Multiplicador para dar peso à intensidade
            }));

            // Define os dados para a instância do heatmap
            const heatmapConfig = {
                max: 1000, // Valor máximo esperado para a intensidade de um ponto
                data: points
            };

            heatmapInstance.setData(heatmapConfig);
        });
    })
    .catch(error => console.error('Erro ao carregar ou processar dados do heatmap:', error));