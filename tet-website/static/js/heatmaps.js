var id = document.getElementById('id-avaliacao').textContent.trim();

fetch(`/api/view_heatmap/${id}`)
    .then(response => response.json())
    .then(data => {
        
        data.forEach((heatmap, index) => {
            // Create a container for image + heatmap
            const container = document.createElement('div');
            container.style.position = 'relative';
            container.style.width = `${heatmap.width}px`;
            container.style.height = `${heatmap.height}px`;
            container.style.border = '1px solid red'
            container.style.marginBottom = '50px'

            // Create and add images
            const img = document.createElement('img');
            img.src = `data:image/png;base64,${heatmap.image}`;
            img.style.position = 'absolute';
            img.style.top = '0';
            img.style.left = '0';
            img.style.width = '100%';
            img.style.height = '100%';
            container.appendChild(img);

            // Add container to the body or an other element
            document.querySelector('.heatmaps').appendChild(container);

            // Create heatmap inside the container
            const heatmapInstance = h337.create({
                container: container,
                radius: 50,
                maxOpacity: 0.6,
                blur: 0.9,
            });

            const points = heatmap.points.map(point => ({
                x: point.x,
                y: point.y,
                value: point.intensity * 700
            }));

            // To define the data for the heatmap
            const data = {
                max: 1000,
                data: points
            };

            heatmapInstance.setData(data);

        });
    })
    .catch(error => console.error('Error loading heatmap data:', error));