document.addEventListener('DOMContentLoaded', () => {
    const container = document.getElementById('gallery-container');
    const statsContainer = document.getElementById('stats-container');
    const searchInput = document.getElementById('search-input');
    const hideZeroToggle = document.getElementById('hide-zero-toggle');
    const modal = document.getElementById('image-modal');
    const modalImg = document.getElementById('modal-img');
    const modalBackdrop = document.querySelector('.modal-backdrop');
    const closeBtn = document.querySelector('.close-btn');

    let currentFirstItemKey = null;
    let currentTotalImages = 0;
    let allGalleryData = [];

    // Fetch backend data
    async function fetchGallery(isPolling = false) {
        try {
            const response = await fetch('/api/gallery');
            const result = await response.json();
            const data = result.data;
            
            const totalPrompts = data.length;
            const totalImages = data.reduce((sum, item) => sum + item.image_count, 0);
            const firstItemKey = data.length > 0 ? data[0].sort_key : null;

            // Re-render only if there are updates
            if (!isPolling || firstItemKey !== currentFirstItemKey || totalImages !== currentTotalImages) {
                currentFirstItemKey = firstItemKey;
                currentTotalImages = totalImages;
                allGalleryData = data;
                
                applySearchFilter();
            }
        } catch (error) {
            console.error("Failed to fetch gallery:", error);
            if (!isPolling) {
                container.innerHTML = `<div class="no-images">Failed to load gallery data, please check if backend is running.</div>`;
            }
        }
    }

    // Apply search filter and render
    function applySearchFilter() {
        const keyword = (searchInput.value || '').toLowerCase().trim();
        const hideZero = hideZeroToggle.checked;
        let filteredData = allGalleryData;
        
        filteredData = allGalleryData.filter(item => {
            if (hideZero && item.image_count === 0) return false;
            
            if (keyword) {
                const promptText = (item.prompt || '').toLowerCase();
                const timeText = (item.display_time || '').toLowerCase();
                return promptText.includes(keyword) || timeText.includes(keyword);
            }
            return true;
        });
        
        const totalPrompts = filteredData.length;
        const totalImages = filteredData.reduce((sum, item) => sum + item.image_count, 0);

        renderGallery(filteredData);
        
        if (keyword === '') {
            statsContainer.innerHTML = `${totalPrompts} Prompts &nbsp;|&nbsp; ${totalImages} Images`;
        } else {
            statsContainer.innerHTML = `🔍 Found ${totalPrompts} &nbsp;|&nbsp; ${totalImages} Images`;
        }
    }

    searchInput.addEventListener('input', applySearchFilter);
    hideZeroToggle.addEventListener('change', applySearchFilter);

    // Render cards
    function renderGallery(data) {
        if (!data || data.length === 0) {
            container.innerHTML = `<div class="no-images">No matching results found.</div>`;
            return;
        }

        const html = data.map(item => {
            let imagesHtml = '';
            if (item.image_count === 0) {
                imagesHtml = `<div class="no-images">No generated images (or blocked by moderation)</div>`;
            } else {
                const imgClass = item.image_count <= 4 ? `img-count-${item.image_count}` : 'img-count-4';
                imagesHtml = `<div class="images-area ${imgClass}">
                    ${item.images.map(img => `
                        <div class="image-wrapper">
                            <img src="${img}" alt="Generated Image" loading="lazy" data-action="zoom">
                        </div>
                    `).join('')}
                </div>`;
            }

            return `
                <article class="job-card">
                    <div class="card-header">
                        <span class="timestamp">📸 ${item.display_time}</span>
                        <span class="image-count">${item.image_count} Pics</span>
                    </div>
                    <div class="prompt-area">
                        <div class="prompt-header">
                            <span class="prompt-label">Prompt</span>
                            <button class="copy-btn" data-action="copy" data-prompt="${escapeHtml(item.prompt)}">
                                📋 Copy
                            </button>
                        </div>
                        <p class="prompt-text">${escapeHtml(item.prompt)}</p>
                    </div>
                    ${imagesHtml}
                </article>
            `;
        }).join('');

        container.innerHTML = html;
    }

    // Anti-XSS function
    function escapeHtml(unsafe) {
        if (!unsafe) return 'No prompt record';
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // ==========================================
    // Zoom, scale, and pan logic
    // ==========================================
    let scale = 1;
    let translateX = 0;
    let translateY = 0;
    let isPanning = false;
    let startX = 0;
    let startY = 0;

    function applyTransform() {
        modalImg.style.transform = `translate(${translateX}px, ${translateY}px) scale(${scale})`;
    }

    function resetTransform() {
        scale = 1;
        translateX = 0;
        translateY = 0;
        applyTransform();
    }

    function closeModal() {
        modal.classList.remove('active');
        setTimeout(() => { 
            modalImg.src = ''; 
            resetTransform();
        }, 300);
    }

    // Delegate image clicks (zoom functionality) and button clicks (copy functionality)
    container.addEventListener('click', async (e) => {
        const target = e.target;
        
        // Handle copy button
        const copyBtn = target.closest('button[data-action="copy"]');
        if (copyBtn) {
            const textToCopy = copyBtn.dataset.prompt;
            try {
                await navigator.clipboard.writeText(textToCopy);
                const originalHtml = copyBtn.innerHTML;
                copyBtn.innerHTML = '✅ Copied!';
                copyBtn.style.color = '#4ade80';
                copyBtn.style.borderColor = '#4ade80';
                setTimeout(() => {
                    copyBtn.innerHTML = originalHtml;
                    copyBtn.style.color = '';
                    copyBtn.style.borderColor = '';
                }, 2000);
            } catch (err) {
                console.error('Failed to copy', err);
            }
            return;
        }

        // Handle image zoom
        if (target.tagName === 'IMG' && target.dataset.action === 'zoom') {
            resetTransform();
            modalImg.src = target.src;
            modal.classList.add('active');
        }
    });

    // Close events
    closeBtn.addEventListener('click', closeModal);
    modalBackdrop.addEventListener('click', closeModal);
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('active')) {
            closeModal();
        }
    });

    // --- Wheel zoom logic ---
    modal.addEventListener('wheel', (e) => {
        if (!modal.classList.contains('active')) return;
        e.preventDefault(); // Prevent page background scrolling
        // Adjust size based on wheel direction
        const zoomIntensity = 0.05;
        if (e.deltaY < 0) {
            scale *= (1 + zoomIntensity);
        } else {
            scale /= (1 + zoomIntensity);
        }
        // Limit zoom range (0.2x to 10x)
        scale = Math.min(Math.max(0.2, scale), 10);
        applyTransform();
    }, { passive: false }); // Must specify non-passive to allow preventDefault

    // --- Right-click pan logic ---
    // Disable context menu inside Modal
    modal.addEventListener('contextmenu', e => e.preventDefault());

    modal.addEventListener('mousedown', (e) => {
        if (e.button === 2 && modal.classList.contains('active')) { // 2 is right click
            e.preventDefault();
            isPanning = true;
            startX = e.clientX - translateX;
            startY = e.clientY - translateY;
            modalImg.style.cursor = 'grabbing';
        }
    });

    window.addEventListener('mousemove', (e) => {
        if (!isPanning || !modal.classList.contains('active')) return;
        translateX = e.clientX - startX;
        translateY = e.clientY - startY;
        applyTransform();
    });

    window.addEventListener('mouseup', (e) => {
        if (e.button === 2) {
            isPanning = false;
            modalImg.style.cursor = 'auto';
        }
    });

    // Initial load and start auto-polling (every 3 seconds)
    fetchGallery();
    setInterval(() => fetchGallery(true), 3000);
});
