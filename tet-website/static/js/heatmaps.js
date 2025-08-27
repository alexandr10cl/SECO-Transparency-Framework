// 1. Pega o ID da avaliação que está no HTML
const id = document.getElementById('id-avaliacao').textContent.trim();
console.log('=== INICIO DEBUG HEATMAPS ===');
console.log('ID da avaliação:', id);

// 2. Faz a requisição para a API do backend
fetch(`/api/view_heatmap/${id}`)
    .then(response => {
        console.log('Status da resposta:', response.status);
        // Verifica se a resposta da rede foi bem-sucedida
        if (!response.ok) {
            throw new Error(`Erro na rede: ${response.statusText}`);
        }
        return response.json();
    })
    .then(data => {
        console.log('=== DADOS RECEBIDOS DA API ===');
        console.log('Dados completos:', data);
        console.log('Tipo dos dados:', typeof data);
        console.log('É array?:', Array.isArray(data));
        console.log('Quantidade de items:', data.length);

        // 3. Garante que os dados estejam sempre em um formato de array para o loop
        let heatmapsParaProcessar = [];
        if (Array.isArray(data)) {
            heatmapsParaProcessar = data;
            console.log('Dados já eram array');
        } else if (data && typeof data === 'object') {
            // Se a API retornar um único objeto, coloca ele dentro de um array
            heatmapsParaProcessar = [data];
            console.log('Dados convertidos para array');
        } else {
            console.error('Dados recebidos em formato inesperado:', data);
            return;
        }

        console.log('=== PROCESSANDO HEATMAPS ===');
        console.log('Número de heatmaps para processar:', heatmapsParaProcessar.length);

        // 4. Para cada heatmap recebido, cria os elementos na página
        heatmapsParaProcessar.forEach((heatmapData, index) => {
            console.log(`--- Processando heatmap ${index + 1} ---`);
            console.log('Estrutura do heatmap:', heatmapData);
            console.log('Propriedades disponíveis:', Object.keys(heatmapData));
            
            // Validações de dados recebidos
            if (!heatmapData) {
                console.error(`Heatmap ${index + 1}: Dados vazios`);
                return;
            }

            // Verifica se as propriedades esperadas existem
            const hasDirectProps = heatmapData.width && heatmapData.height && heatmapData.points && heatmapData.image;
            const hasPageImages = heatmapData.page_images && Array.isArray(heatmapData.page_images) && heatmapData.page_images.length > 0;
            
            console.log('Tem propriedades diretas?', hasDirectProps);
            console.log('Tem page_images?', hasPageImages);

            let imageData, width, height, points;

            if (hasDirectProps) {
                // Formato direto (como o frontend espera)
                console.log('Usando formato direto');
                imageData = heatmapData.image;
                width = heatmapData.width;
                height = heatmapData.height;
                points = heatmapData.points;
            } else if (hasPageImages) {
                // Formato com page_images (como o backend retorna)
                console.log('Usando formato page_images');
                const pageImage = heatmapData.page_images[0];
                console.log('Primeira page_image:', pageImage);
                console.log('Propriedades da page_image:', Object.keys(pageImage));
                
                imageData = pageImage.image;
                width = pageImage.width;
                height = pageImage.height;
                points = pageImage.points;
            } else {
                console.error(`Heatmap ${index + 1}: Estrutura de dados inválida`);
                console.error('Dados esperados: width, height, points, image OU page_images array');
                return;
            }

            console.log('Dados extraídos:');
            console.log('- Width:', width);
            console.log('- Height:', height);
            console.log('- Points length:', points ? points.length : 0);
            console.log('- Image length:', imageData ? imageData.length : 0);

            // Validações finais
            if (!width || !height) {
                console.error(`Heatmap ${index + 1}: Dimensões inválidas - width: ${width}, height: ${height}`);
                return;
            }

            if (!points || !Array.isArray(points)) {
                console.error(`Heatmap ${index + 1}: Points inválidos:`, points);
                return;
            }

            if (!imageData) {
                console.error(`Heatmap ${index + 1}: Imagem não encontrada`);
                return;
            }

            // Cria um contêiner principal para a imagem e o heatmap
            const container = document.createElement('div');
            container.style.position = 'relative';
            container.style.width = `${width}px`;
            container.style.height = `${height}px`;
            container.style.border = '1px solid #ccc'; // Borda sutil para visualização
            container.style.marginBottom = '50px';

            console.log(`Container criado com dimensões: ${width}x${height}`);

            // Cria o elemento da imagem de fundo
            const img = document.createElement('img');
            
            // Detecta o tipo de imagem baseado no início da string base64
            let imageType = 'jpeg'; // padrão
            if (imageData.startsWith('/9j/')) {
                imageType = 'jpeg';
            } else if (imageData.startsWith('iVBORw0KGgo')) {
                imageType = 'png';
            }
            
            img.src = `data:image/${imageType};base64,${imageData}`;
            console.log(`Imagem configurada como: ${imageType}`);
            
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

            console.log('Heatmap instance criada');

            // Mapeia os pontos recebidos da API para o formato que a biblioteca heatmap.js espera
            console.log('Processando pontos...');
            const processedPoints = points.map((point, pointIndex) => {
                if (!point || typeof point.x === 'undefined' || typeof point.y === 'undefined' || typeof point.intensity === 'undefined') {
                    console.warn(`Ponto ${pointIndex} inválido:`, point);
                    return null;
                }
                
                const processedPoint = {
                    x: Math.round(point.x),
                    y: Math.round(point.y),
                    value: Math.round(point.intensity * 700) // Multiplicador para dar peso à intensidade
                };
                
                if (pointIndex < 5) { // Log dos primeiros 5 pontos
                    console.log(`Ponto ${pointIndex}:`, point, '→', processedPoint);
                }
                
                return processedPoint;
            }).filter(point => point !== null); // Remove pontos inválidos

            console.log(`Pontos processados: ${processedPoints.length} de ${points.length}`);

            // Define os dados para a instância do heatmap
            const heatmapConfig = {
                max: 1000, // Valor máximo esperado para a intensidade de um ponto
                data: processedPoints
            };

            console.log('Configuração do heatmap:', heatmapConfig);
            heatmapInstance.setData(heatmapConfig);
            console.log(`Heatmap ${index + 1} processado com sucesso!`);
        });
        
        console.log('=== FIM DO PROCESSAMENTO ===');
    })
    .catch(error => {
        console.error('=== ERRO NO PROCESSAMENTO ===');
        console.error('Error loading or processing heatmap data:', error);
        console.error('Stack trace:', error.stack);
    });