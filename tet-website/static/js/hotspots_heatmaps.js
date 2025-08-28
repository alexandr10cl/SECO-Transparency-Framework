document.addEventListener('DOMContentLoaded', () => {
  const idElem = document.getElementById('id-avaliacao');
  if (!idElem) {
    console.warn('Element #evaluation-id not found. No heatmap will be loaded.');
    return;
  }

  const id = idElem.textContent.trim();
  const root = document.getElementById('heatmaps-root');
  if (!root) return;

  root.innerHTML = '<p class="loading">Loading heatmaps...</p>';

  fetch(`/api/view_heatmap/${id}`)
    .then(response => {
      if (!response.ok) throw new Error(`Network error: ${response.status} ${response.statusText}`);
      return response.json();
    })
    .then(data => {
      root.innerHTML = '';

      const heatmapsParaProcessar = Array.isArray(data) ? data : (data && typeof data === 'object' ? [data] : []);

      if (heatmapsParaProcessar.length === 0) {
        root.innerHTML = '<p>No heatmaps found for this evaluation.</p>';
        return;
      }

      heatmapsParaProcessar.forEach((heatmapData, index) => {
        // cria wrapper e placeholders
        const container = document.createElement('div');
        container.classList.add('heatmap-wrapper');
        container.style.position = 'relative';
        container.style.maxWidth = '100%';
        container.style.border = '1px solid #e6e6e6';
        container.style.marginBottom = '24px';
        container.style.overflow = 'hidden';
        container.style.borderRadius = '6px';
        // deixamos largura/altura temporárias mínimas para evitar 0
        container.style.width = heatmapData.width ? `${heatmapData.width}px` : '640px';
        container.style.height = heatmapData.height ? `${heatmapData.height}px` : '360px';

        // cria a imagem
        const img = new Image();
        // tenta detectar tipo — assume jpeg se não especificado
        const mime = heatmapData.mime || 'image/jpeg';
        img.src = `data:${mime};base64,${heatmapData.image}`;
        img.alt = heatmapData.title || `Heatmap ${index + 1}`;
        img.style.position = 'absolute';
        img.style.top = '0';
        img.style.left = '0';
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.objectFit = 'cover';
        img.style.display = 'block';

        // adiciona o container ao DOM antes (heatmap.js precisa do container visível)
        root.appendChild(container);

        // função para inicializar o heatmap após a imagem carregar e termos dimensões válidas
        const initHeatmap = () => {
          // ajusta dimensões do container com base na imagem natural ou nas dimensões fornecidas pela API
          const naturalW = img.naturalWidth || heatmapData.width || container.clientWidth;
          const naturalH = img.naturalHeight || heatmapData.height || container.clientHeight;

          // se a API informou dimensões de referência (coordenadas dos points), usamos para escalar
          const sourceW = heatmapData.width || naturalW;
          const sourceH = heatmapData.height || naturalH;

          container.style.width = `${naturalW}px`;
          container.style.height = `${naturalH}px`;

          // anexamos a imagem após ajustar tamanhos
          container.appendChild(img);

          // cria a instância do heatmap (após container estar no DOM e com tamanho)
          const heatmapInstance = h337.create({
            container: container,
            radius: 40,
            maxOpacity: 0.6,
            blur: 0.9,
          });

          // calcula escala entre coordenadas da API e o tamanho atual exibido
          const scaleX = container.clientWidth / sourceW;
          const scaleY = container.clientHeight / sourceH;

          // prepara os pontos (protege contra ausência)
          const pts = (heatmapData.points || []).map(point => ({
            x: Math.round((point.x || 0) * scaleX),
            y: Math.round((point.y || 0) * scaleY),
            value: Math.max(1, Math.round((point.intensity || 0) * 700)),
          }));

          const maxVal = pts.length ? Math.max(...pts.map(p => p.value)) : 100;
          try {
            heatmapInstance.setData({ max: Math.max(maxVal, 100), data: pts });
          } catch (err) {
            console.error('Error setting data on heatmapInstance:', err);
            const errMsg = document.createElement('p');
            errMsg.textContent = `Error rendering heatmap ${index + 1}: ${err.message}`;
            root.appendChild(errMsg);
          }

          // opcional: legenda/título abaixo do container
          if (heatmapData.title) {
            const caption = document.createElement('div');
            caption.classList.add('heatmap-caption');
            caption.textContent = heatmapData.title;
            caption.style.margin = '8px 0 16px 0';
            caption.style.fontSize = '14px';
            caption.style.color = '#333';
            root.appendChild(caption);
          }
        };

        // aguarda carregamento da imagem. usa decode() se disponível (promessa), senão onload.
        if (img.decode) {
          img.decode().then(initHeatmap).catch(err => {
            // fallback: tenta onload
            console.warn('img.decode failed, using onload as fallback', err);
            img.onload = initHeatmap;
            img.onerror = () => {
              console.error('Error loading heatmap image (img.onerror)');
              container.remove();
              const em = document.createElement('p');
              em.textContent = `Error loading heatmap image ${index + 1}.`;
              root.appendChild(em);
            };
          });
        } else {
          img.onload = initHeatmap;
          img.onerror = () => {
            console.error('Error loading heatmap image (img.onerror)');
            container.remove();
            const em = document.createElement('p');
            em.textContent = `Error loading heatmap image ${index + 1}.`;
            root.appendChild(em);
          };
        }
      });
    })
    .catch(error => {
      console.error('Error loading or processing heatmap data:', error);
      root.innerHTML = `<p>Error loading heatmaps: ${error.message}</p>`;
    });
});
