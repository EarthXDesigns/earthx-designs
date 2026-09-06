// EarthX Designs - CMS Admin Panel Logic

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Icons
    const initIcons = () => {
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    };
    initIcons();

    // High-speed client-side image compressor using HTML5 Canvas
    // Slashes 15MB-35MB raw camera & drone photos down to ~250KB in ~100ms before upload
    const compressImageFile = async (file, maxWidth = 1920, maxHeight = 1080, quality = 0.85) => {
        if (!file || !file.type || !file.type.startsWith('image/') || file.type === 'image/svg+xml' || file.type === 'image/gif') {
            return file; // Pass through videos, SVGs, GIFs as-is
        }
        // If image is already smaller than 350KB, keep it untouched
        if (file.size <= 350 * 1024) {
            return file;
        }

        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                const img = new Image();
                img.onload = () => {
                    let { width, height } = img;
                    if (width > maxWidth || height > maxHeight) {
                        const ratio = Math.min(maxWidth / width, maxHeight / height);
                        width = Math.round(width * ratio);
                        height = Math.round(height * ratio);
                    }

                    const canvas = document.createElement('canvas');
                    canvas.width = width;
                    canvas.height = height;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(img, 0, 0, width, height);

                    const outputType = file.type === 'image/webp' ? 'image/webp' : 'image/jpeg';
                    canvas.toBlob((blob) => {
                        if (blob && blob.size < file.size) {
                            const ext = outputType === 'image/webp' ? '.webp' : '.jpg';
                            const newFileName = file.name.replace(/\.[^.]+$/, ext);
                            const optimizedFile = new File([blob], newFileName, {
                                type: outputType,
                                lastModified: Date.now()
                            });
                            resolve(optimizedFile);
                        } else {
                            resolve(file);
                        }
                    }, outputType, quality);
                };
                img.onerror = () => resolve(file);
                img.src = e.target.result;
            };
            reader.onerror = () => resolve(file);
            reader.readAsDataURL(file);
        });
    };

    // 2. Tab Navigation Handling
    const sidebarItems = document.querySelectorAll('.sidebar-item');
    const tabPanels = document.querySelectorAll('.tab-panel');
    const tabTitleText = document.getElementById('tab-title-text');

    sidebarItems.forEach(item => {
        item.addEventListener('click', () => {
            // Remove active classes
            sidebarItems.forEach(i => i.classList.remove('active'));
            tabPanels.forEach(p => p.style.display = 'none');
            
            // Add active class
            item.classList.add('active');
            const targetId = item.getAttribute('data-target');
            const activePanel = document.getElementById(targetId);
            activePanel.style.display = 'block';
            
            // Set header title
            const tabName = item.querySelector('span').textContent;
            tabTitleText.textContent = `Manage ${tabName}`;
            
            // Load corresponding tab data
            loadTabData(targetId);
        });
    });

    const loadTabData = (tabId) => {
        switch (tabId) {
            case 'projects-tab':
                fetchProjects();
                break;
            case 'services-tab':
                fetchServices();
                fetchServiceCategories();
                break;
            case 'service-categories-tab':
                fetchServiceCategories();
                break;
            case 'categories-tab':
                fetchCategories();
                break;

            case 'testimonials-tab':
                fetchTestimonials();
                break;
            case 'blogs-tab':
                fetchBlogs();
                break;
            case 'leads-tab':
                fetchLeads();
                break;
            case 'client-logos-tab':
                fetchClientLogos();
                break;
            case 'home-tab':
                fetchHomeSettings();
                break;
            case 'users-tab':
                fetchUsers();
                break;
        }
    };

    // 3. Modal Handling Utilities
    const openModal = (modalId) => {
        document.getElementById(modalId).style.display = 'flex';
        document.body.style.overflow = 'hidden';
    };

    const closeModal = (modalId) => {
        document.getElementById(modalId).style.display = 'none';
        document.body.style.overflow = 'auto';
    };

    // Bind close buttons for all modals
    document.querySelectorAll('.modal-close, .modal-close-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal');
            if (modal) {
                closeModal(modal.id);
            }
        });
    });

    // Close modal if clicking overlay
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            closeModal(e.target.id);
        }
    });

    // Form inputs change handler for images preview
    const bindImagePreview = (fileInputId, previewId) => {
        const fileInput = document.getElementById(fileInputId);
        const preview = document.getElementById(previewId);
        if (fileInput && preview) {
            fileInput.addEventListener('change', () => {
                const file = fileInput.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        preview.innerHTML = `<img src="${e.target.result}" alt="Preview image">`;
                    };
                    reader.readAsDataURL(file);
                } else {
                    preview.innerHTML = `<i data-lucide="image" style="width: 24px; height: 24px; color: var(--admin-text-light);"></i>`;
                    initIcons();
                }
            });
        }
    };
    bindImagePreview('project-featured-image', 'project-featured-preview');
    bindImagePreview('blog-featured-image', 'blog-featured-preview');


    // ==========================================
    // DATA FETCH & CRUD OPERATIONS
    // ==========================================

    let globalCategories = [];

    // --- CATEGORIES LOGIC ---
    const fetchCategories = async () => {
        try {
            const res = await fetch('/api/categories');
            const data = await res.json();
            globalCategories = data;
            
            // Populate categories tab table
            const tbody = document.getElementById('categories-table-body');
            tbody.innerHTML = '';
            
            data.forEach(c => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${c.id}</td>
                    <td><strong>${c.name}</strong></td>
                    <td><code>/portfolio?category=${c.slug}</code></td>
                    <td>
                        <div class="btn-action-group">
                            <button class="btn-action edit" onclick="editCategory(${c.id}, '${c.name}', '${c.slug}')">
                                <i data-lucide="edit-3" style="width:14px; height:14px;"></i>
                            </button>
                            <button class="btn-action delete" onclick="deleteCategory(${c.id})">
                                <i data-lucide="trash-2" style="width:14px; height:14px;"></i>
                            </button>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });
            initIcons();
            
            // Populate category select list in project modal
            const select = document.getElementById('project-category');
            if (select) {
                select.innerHTML = '<option value="">-- Select Category --</option>';
                data.forEach(c => {
                    const opt = document.createElement('option');
                    opt.value = c.id;
                    opt.textContent = c.name;
                    select.appendChild(opt);
                });
            }
        } catch (err) {
            console.error('Error fetching categories:', err);
        }
    };

    // Category form submission
    document.getElementById('category-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('category-id').value;
        const name = document.getElementById('category-name').value.strip ? document.getElementById('category-name').value.trim() : document.getElementById('category-name').value;
        const slug = document.getElementById('category-slug').value.strip ? document.getElementById('category-slug').value.trim() : document.getElementById('category-slug').value;
        
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/categories/${id}` : '/api/categories';
        
        try {
            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, slug })
            });
            const data = await res.json();
            
            if (res.ok) {
                closeModal('category-modal');
                fetchCategories();
            } else {
                alert(data.error || 'An error occurred.');
            }
        } catch (err) {
            console.error(err);
        }
    });

    document.getElementById('btn-add-category').addEventListener('click', () => {
        document.getElementById('category-form').reset();
        document.getElementById('category-id').value = '';
        document.getElementById('category-modal-title').textContent = 'Add Category';
        openModal('category-modal');
    });

    window.editCategory = (id, name, slug) => {
        document.getElementById('category-id').value = id;
        document.getElementById('category-name').value = name;
        document.getElementById('category-slug').value = slug;
        document.getElementById('category-modal-title').textContent = 'Edit Category';
        openModal('category-modal');
    };

    window.deleteCategory = async (id) => {
        if (confirm('Are you sure you want to delete this category? All projects in this category will lose their association.')) {
            try {
                const res = await fetch(`/api/categories/${id}`, { method: 'DELETE' });
                if (res.ok) fetchCategories();
            } catch (err) {
                console.error(err);
            }
        }
    };

    // Auto-generate category slug from name
    const catNameInput = document.getElementById('category-name');
    if (catNameInput) {
        catNameInput.addEventListener('input', (e) => {
            const nameVal = e.target.value;
            document.getElementById('category-slug').value = nameVal.toLowerCase()
                .replace(/[^a-z0-9 -]/g, '')
                .replace(/\s+/g, '-')
                .replace(/-+/g, '-');
        });
    }

    // ==========================================
    // SERVICES & SERVICE CATEGORIES MANAGEMENT
    // ==========================================

    const isVideoFile = (url) => {
        if (!url) return false;
        const ext = url.split('.').pop().toLowerCase().split('?')[0];
        return ['mp4', 'webm', 'mov', 'ogg'].includes(ext);
    };

    // --- SERVICE CATEGORIES LOGIC ---
    let globalServiceCategories = [];

    const fetchServiceCategories = async () => {
        try {
            const res = await fetch('/api/service-categories');
            const data = await res.json();
            globalServiceCategories = data;

            // 1. Populate Service Categories table in admin
            const tbody = document.getElementById('service-categories-table-body');
            if (tbody) {
                tbody.innerHTML = '';
                if (data.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; color:var(--admin-text-light);">No service categories found.</td></tr>';
                } else {
                    data.forEach(cat => {
                        const tr = document.createElement('tr');
                        
                        // Hero Background thumbnail
                        const bgSrc = cat.hero_bg_image || cat.hero_image || '/uploads/commercial_solar_featured.png';
                        const heroBgThumb = `<div style="width:58px; height:38px; border-radius:4px; overflow:hidden; background:#071815; border:1px solid var(--admin-border);">
                            <img src="${bgSrc}" style="width:100%; height:100%; object-fit:cover;" title="Hero Background Image">
                        </div>`;

                        // Overview Media thumbnail
                        let mediaThumb = '<span style="color:var(--admin-text-light); font-size:0.8rem;">None</span>';
                        if (cat.hero_image) {
                            if (isVideoFile(cat.hero_image)) {
                                mediaThumb = `<div style="position:relative; width:58px; height:38px; border-radius:4px; overflow:hidden; background:#0F172A; display:inline-flex; align-items:center; justify-content:center;">
                                    <video src="${cat.hero_image}" style="width:100%; height:100%; object-fit:cover;"></video>
                                    <span style="position:absolute; background:rgba(0,0,0,0.65); color:#FFF; font-size:9px; padding:1px 3px; border-radius:2px; font-weight:700;">VIDEO</span>
                                </div>`;
                            } else {
                                mediaThumb = `<img src="${cat.hero_image}" style="width:58px; height:38px; object-fit:cover; border-radius:4px; border:1px solid var(--admin-border); display:inline-block;" title="Overview Media">`;
                            }
                        }

                        tr.innerHTML = `
                            <td>${heroBgThumb}</td>
                            <td>${mediaThumb}</td>
                            <td><strong>${cat.name}</strong></td>
                            <td><code>/services/${cat.slug}</code></td>
                            <td><span class="badge badge-info">${cat.service_count || 0} options</span></td>
                            <td><span class="badge ${cat.is_published ? 'badge-success' : 'badge-warning'}">${cat.is_published ? 'Published' : 'Draft'}</span></td>
                            <td>
                                <div class="btn-action-group">
                                    <a href="/services/${cat.slug}" target="_blank" class="btn-action" title="View on Site" style="color:var(--accent);">
                                        <i data-lucide="external-link" style="width:14px; height:14px;"></i>
                                    </a>
                                    <button class="btn-action edit" onclick="editServiceCategory(${cat.id})" title="Edit">
                                        <i data-lucide="edit-3" style="width:14px; height:14px;"></i>
                                    </button>
                                    <button class="btn-action delete" onclick="deleteServiceCategory(${cat.id})" title="Delete">
                                        <i data-lucide="trash-2" style="width:14px; height:14px;"></i>
                                    </button>
                                </div>
                            </td>
                        `;
                        tbody.appendChild(tr);
                    });
                }
            }

            // 2. Populate category filters and select dropdowns
            const filterSelect = document.getElementById('filter-service-category');
            if (filterSelect) {
                const currentVal = filterSelect.value;
                filterSelect.innerHTML = '<option value="">All Categories</option>';
                data.forEach(cat => {
                    const opt = document.createElement('option');
                    opt.value = cat.id;
                    opt.textContent = cat.name;
                    if (String(cat.id) === String(currentVal)) opt.selected = true;
                    filterSelect.appendChild(opt);
                });
            }

            const modalCatSelect = document.getElementById('service-category');
            if (modalCatSelect) {
                const currentVal = modalCatSelect.value;
                modalCatSelect.innerHTML = '<option value="">-- Select Parent Category --</option>';
                data.forEach(cat => {
                    const opt = document.createElement('option');
                    opt.value = cat.id;
                    opt.textContent = cat.name;
                    if (String(cat.id) === String(currentVal)) opt.selected = true;
                    modalCatSelect.appendChild(opt);
                });
            }

            initIcons();
        } catch (err) {
            console.error('Error fetching service categories:', err);
        }
    };

    // Auto-generate service category slug from name
    const svccatNameInput = document.getElementById('svccat-name');
    if (svccatNameInput) {
        svccatNameInput.addEventListener('input', (e) => {
            const nameVal = e.target.value;
            document.getElementById('svccat-slug').value = nameVal.toLowerCase()
                .replace(/[^a-z0-9 -]/g, '')
                .replace(/\s+/g, '-')
                .replace(/-+/g, '-');
        });
    }

    // --- Hero Background Image Controls ---
    const svccatHeroBgFileInput = document.getElementById('svccat-hero-bg-file');
    const svccatPresetHeroBgInput = document.getElementById('svccat-preset-hero-bg');
    const svccatBgPreviewContainer = document.getElementById('svccat-bg-preview-container');
    const svccatRemoveBgBtn = document.getElementById('btn-remove-svccat-bg');
    const svccatRemoveBgFlag = document.getElementById('svccat-remove-hero-bg');

    const setHeroBgPreview = (src, label = 'Background Image Selected:') => {
        if (!svccatBgPreviewContainer) return;
        svccatBgPreviewContainer.innerHTML = `
            <div style="font-size:0.75rem; color:rgba(255,255,255,0.7); margin-bottom:4px;">${label}</div>
            <img src="${src}" style="max-width:100%; max-height:140px; border-radius:4px; object-fit:cover; display:block;">
        `;
        svccatBgPreviewContainer.style.display = 'block';
        if (svccatRemoveBgBtn) svccatRemoveBgBtn.style.display = 'inline-flex';
        initIcons();
    };

    if (svccatHeroBgFileInput) {
        svccatHeroBgFileInput.addEventListener('change', () => {
            const file = svccatHeroBgFileInput.files[0];
            if (file) {
                svccatRemoveBgFlag.value = '0';
                if (svccatPresetHeroBgInput) svccatPresetHeroBgInput.value = '';
                const fileUrl = URL.createObjectURL(file);
                setHeroBgPreview(fileUrl, 'Custom Upload Preview:');
            }
        });
    }

    const wireBgPresetBtn = (btnId, presetPath) => {
        const btn = document.getElementById(btnId);
        if (btn) {
            btn.addEventListener('click', () => {
                if (svccatHeroBgFileInput) svccatHeroBgFileInput.value = '';
                if (svccatPresetHeroBgInput) svccatPresetHeroBgInput.value = presetPath;
                svccatRemoveBgFlag.value = '0';
                setHeroBgPreview(presetPath, 'Preset Selected:');
            });
        }
    };

    wireBgPresetBtn('btn-preset-bg-commercial', '/uploads/commercial_solar_featured.png');
    wireBgPresetBtn('btn-preset-bg-residential', '/uploads/residential_3d_featured.png');
    wireBgPresetBtn('btn-preset-bg-ground', '/uploads/ground_mount_featured.png');
    wireBgPresetBtn('btn-preset-bg-sld', '/uploads/sld_blueprint.png');

    if (svccatRemoveBgBtn) {
        svccatRemoveBgBtn.addEventListener('click', () => {
            if (svccatHeroBgFileInput) svccatHeroBgFileInput.value = '';
            if (svccatPresetHeroBgInput) svccatPresetHeroBgInput.value = '';
            if (svccatBgPreviewContainer) {
                svccatBgPreviewContainer.innerHTML = '';
                svccatBgPreviewContainer.style.display = 'none';
            }
            svccatRemoveBgBtn.style.display = 'none';
            svccatRemoveBgFlag.value = '1';
        });
    }

    // --- Overview Showcase Media Controls (Image or Video) ---
    const svccatMediaFileInput = document.getElementById('svccat-media-file');
    const svccatPresetMediaInput = document.getElementById('svccat-preset-media');
    const svccatPreviewContainer = document.getElementById('svccat-media-preview-container');
    const svccatRemoveBtn = document.getElementById('btn-remove-svccat-media');
    const svccatRemoveFlag = document.getElementById('svccat-remove-hero-image');
    const btnPresetSvccatImg = document.getElementById('btn-preset-svccat-img');
    const btnPresetSvccatVid = document.getElementById('btn-preset-svccat-vid');

    const setOverviewMediaPreview = (src, isVideo = false, label = 'Media Selected:') => {
        if (!svccatPreviewContainer) return;
        if (isVideo) {
            svccatPreviewContainer.innerHTML = `
                <div style="font-size:0.75rem; color:var(--admin-text-light); margin-bottom:4px;">${label}</div>
                <video src="${src}" controls autoplay muted loop style="max-width:100%; max-height:150px; border-radius:4px; display:block;"></video>
            `;
        } else {
            svccatPreviewContainer.innerHTML = `
                <div style="font-size:0.75rem; color:var(--admin-text-light); margin-bottom:4px;">${label}</div>
                <img src="${src}" style="max-width:100%; max-height:150px; border-radius:4px; object-fit:cover; display:block;">
            `;
        }
        svccatPreviewContainer.style.display = 'block';
        if (svccatRemoveBtn) svccatRemoveBtn.style.display = 'inline-flex';
        initIcons();
    };

    if (svccatMediaFileInput && svccatPreviewContainer) {
        svccatMediaFileInput.addEventListener('change', () => {
            const file = svccatMediaFileInput.files[0];
            if (file) {
                svccatRemoveFlag.value = '0';
                if (svccatPresetMediaInput) svccatPresetMediaInput.value = '';
                const fileUrl = URL.createObjectURL(file);
                setOverviewMediaPreview(fileUrl, file.type.startsWith('video/'), 'Custom File Preview:');
            }
        });
    }

    if (btnPresetSvccatImg) {
        btnPresetSvccatImg.addEventListener('click', () => {
            if (svccatMediaFileInput) svccatMediaFileInput.value = '';
            if (svccatPresetMediaInput) svccatPresetMediaInput.value = '/uploads/residential_3d_featured.png';
            svccatRemoveFlag.value = '0';
            setOverviewMediaPreview('/uploads/residential_3d_featured.png', false, 'Preset 3D Render Image:');
        });
    }

    if (btnPresetSvccatVid) {
        btnPresetSvccatVid.addEventListener('click', () => {
            if (svccatMediaFileInput) svccatMediaFileInput.value = '';
            if (svccatPresetMediaInput) svccatPresetMediaInput.value = '/uploads/hero_video.mp4';
            svccatRemoveFlag.value = '0';
            setOverviewMediaPreview('/uploads/hero_video.mp4', true, 'Preset Drone Video:');
        });
    }

    if (svccatRemoveBtn) {
        svccatRemoveBtn.addEventListener('click', () => {
            if (svccatMediaFileInput) svccatMediaFileInput.value = '';
            if (svccatPresetMediaInput) svccatPresetMediaInput.value = '';
            svccatPreviewContainer.innerHTML = '';
            svccatPreviewContainer.style.display = 'none';
            svccatRemoveBtn.style.display = 'none';
            svccatRemoveFlag.value = '1';
        });
    }

    const btnAddServiceCategory = document.getElementById('btn-add-service-category');
    if (btnAddServiceCategory) {
        btnAddServiceCategory.addEventListener('click', () => {
            document.getElementById('service-category-form').reset();
            document.getElementById('svccat-id').value = '';
            svccatRemoveBgFlag.value = '0';
            svccatRemoveFlag.value = '0';
            if (svccatPresetHeroBgInput) svccatPresetHeroBgInput.value = '';
            if (svccatPresetMediaInput) svccatPresetMediaInput.value = '';
            if (svccatBgPreviewContainer) {
                svccatBgPreviewContainer.innerHTML = '';
                svccatBgPreviewContainer.style.display = 'none';
            }
            if (svccatRemoveBgBtn) svccatRemoveBgBtn.style.display = 'none';
            if (svccatPreviewContainer) {
                svccatPreviewContainer.innerHTML = '';
                svccatPreviewContainer.style.display = 'none';
            }
            if (svccatRemoveBtn) svccatRemoveBtn.style.display = 'none';
            document.getElementById('service-category-modal-title').textContent = 'Add Service Category';
            openModal('service-category-modal');
        });
    }

    window.editServiceCategory = async (id) => {
        try {
            document.getElementById('service-category-form').reset();
            if (svccatBgPreviewContainer) {
                svccatBgPreviewContainer.innerHTML = '';
                svccatBgPreviewContainer.style.display = 'none';
            }
            if (svccatPreviewContainer) {
                svccatPreviewContainer.innerHTML = '';
                svccatPreviewContainer.style.display = 'none';
            }
            if (svccatRemoveBgBtn) svccatRemoveBgBtn.style.display = 'none';
            if (svccatRemoveBtn) svccatRemoveBtn.style.display = 'none';
            if (svccatRemoveBgFlag) svccatRemoveBgFlag.value = '0';
            if (svccatRemoveFlag) svccatRemoveFlag.value = '0';
            if (svccatPresetHeroBgInput) svccatPresetHeroBgInput.value = '';
            if (svccatPresetMediaInput) svccatPresetMediaInput.value = '';

            const res = await fetch(`/api/service-categories/${id}?t=${Date.now()}`);
            const cat = await res.json();
            if (!res.ok) return alert(cat.error || 'Failed to fetch category');

            document.getElementById('svccat-id').value = cat.id;
            document.getElementById('svccat-name').value = cat.name;
            document.getElementById('svccat-slug').value = cat.slug;
            document.getElementById('svccat-icon').value = cat.icon || '';
            document.getElementById('svccat-status').value = String(cat.is_published);
            document.getElementById('svccat-hero-heading').value = cat.hero_heading || '';
            document.getElementById('svccat-hero-subtitle').value = cat.hero_subtitle || '';
            document.getElementById('svccat-short-desc').value = cat.short_description || '';
            document.getElementById('svccat-full-desc').value = cat.full_description || '';

            // Hero Background Preview
            if (cat.hero_bg_image) {
                const bgUrl = `${cat.hero_bg_image}${cat.hero_bg_image.includes('?') ? '&' : '?'}t=${Date.now()}`;
                setHeroBgPreview(bgUrl, 'Current Hero Background:');
            } else {
                if (svccatBgPreviewContainer) {
                    svccatBgPreviewContainer.innerHTML = '';
                    svccatBgPreviewContainer.style.display = 'none';
                }
                if (svccatRemoveBgBtn) svccatRemoveBgBtn.style.display = 'none';
            }

            // Overview Media Preview
            if (cat.hero_image) {
                const mediaUrl = `${cat.hero_image}${cat.hero_image.includes('?') ? '&' : '?'}t=${Date.now()}`;
                setOverviewMediaPreview(mediaUrl, isVideoFile(cat.hero_image), isVideoFile(cat.hero_image) ? 'Current Video:' : 'Current Image:');
            } else {
                if (svccatPreviewContainer) {
                    svccatPreviewContainer.innerHTML = '';
                    svccatPreviewContainer.style.display = 'none';
                }
                if (svccatRemoveBtn) svccatRemoveBtn.style.display = 'none';
            }

            document.getElementById('service-category-modal-title').textContent = `Edit Service: ${cat.name}`;
            openModal('service-category-modal');
            initIcons();
        } catch (err) {
            console.error(err);
        }
    };

    window.deleteServiceCategory = async (id) => {
        if (confirm('Delete this service category? All child services under it will be deleted.')) {
            try {
                const res = await fetch(`/api/service-categories/${id}`, { method: 'DELETE' });
                const data = await res.json();
                if (res.ok) {
                    fetchServiceCategories();
                    fetchServices();
                } else {
                    alert(data.error || 'Failed to delete service category.');
                }
            } catch (err) {
                console.error(err);
            }
        }
    };

    const serviceCategoryForm = document.getElementById('service-category-form');
    if (serviceCategoryForm) {
        serviceCategoryForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = serviceCategoryForm.querySelector('button[type="submit"]');
            const originalBtnHtml = submitBtn ? submitBtn.innerHTML : 'Save Category';

            try {
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<i data-lucide="loader-2" class="spin" style="width:14px;height:14px;vertical-align:middle;margin-right:6px;"></i> Optimizing & Saving...';
                    initIcons();
                }

                const id = document.getElementById('svccat-id').value;
                const formData = new FormData(serviceCategoryForm);

                // Auto-compress uploaded media if it is a large camera / drone photo
                const mediaFileInput = document.getElementById('svccat-media-file');
                if (mediaFileInput && mediaFileInput.files && mediaFileInput.files[0]) {
                    const originalFile = mediaFileInput.files[0];
                    if (originalFile.type.startsWith('image/')) {
                        const compressedMedia = await compressImageFile(originalFile);
                        formData.set('hero_image', compressedMedia);
                    }
                }

                const bgFileInput = document.getElementById('svccat-hero-bg-file');
                if (bgFileInput && bgFileInput.files && bgFileInput.files[0]) {
                    const originalBg = bgFileInput.files[0];
                    if (originalBg.type.startsWith('image/')) {
                        const compressedBg = await compressImageFile(originalBg);
                        formData.set('hero_bg_image', compressedBg);
                    }
                }

                const url = id ? `/api/service-categories/${id}` : '/api/service-categories';
                const res = await fetch(url, {
                    method: 'POST',
                    body: formData
                });

                if (res.status === 401) {
                    alert('Your admin session has expired. Please log in again.');
                    window.location.href = '/admin/login';
                    return;
                }

                const data = await res.json();
                if (res.ok) {
                    closeModal('service-category-modal');
                    fetchServiceCategories();
                } else {
                    alert(data.error || 'Failed to save service category.');
                }
            } catch (err) {
                console.error(err);
                alert('An error occurred while saving: ' + (err.message || 'Network error'));
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnHtml;
                    initIcons();
                }
            }
        });
    }

    const btnRestoreServiceCategories = document.getElementById('btn-restore-service-categories');
    if (btnRestoreServiceCategories) {
        btnRestoreServiceCategories.addEventListener('click', async () => {
            if (!confirm('Restore default service categories and standard options? Existing categories will be preserved unless duplicates exist.')) {
                return;
            }
            try {
                btnRestoreServiceCategories.disabled = true;
                btnRestoreServiceCategories.innerHTML = '<i data-lucide="loader" class="spin" style="width:15px;height:15px;"></i> Restoring...';
                initIcons();
                const res = await fetch('/api/admin/restore-service-categories?force=1', { method: 'POST' });
                const data = await res.json();
                if (res.ok) {
                    alert(data.message || 'Service categories restored successfully!');
                    fetchServiceCategories();
                    fetchServices();
                } else {
                    alert(data.error || 'Failed to restore service categories.');
                }
            } catch (err) {
                console.error(err);
                alert('An error occurred while restoring service categories.');
            } finally {
                btnRestoreServiceCategories.disabled = false;
                btnRestoreServiceCategories.innerHTML = '<i data-lucide="rotate-ccw" style="width:15px;height:15px;"></i> <span>Restore Defaults</span>';
                initIcons();
            }
        });
    }

    // --- SERVICES / SERVICE OPTIONS LOGIC ---
    const fetchServices = async (filterCatId = '') => {
        try {
            let url = '/api/services';
            if (filterCatId) {
                url += `?category_id=${filterCatId}`;
            }
            const res = await fetch(url);
            const data = await res.json();

            const tbody = document.getElementById('services-table-body');
            if (tbody) {
                tbody.innerHTML = '';
                if (data.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--admin-text-light);">No services found. Click "Add Service Option" to create one.</td></tr>';
                } else {
                    data.forEach(svc => {
                        const tr = document.createElement('tr');
                        let mediaHtml = '<span style="color:var(--admin-text-light); font-size:0.8rem;">No media</span>';
                        
                        if (svc.image) {
                            if (isVideoFile(svc.image)) {
                                mediaHtml = `
                                    <div style="position:relative; width:65px; height:45px; border-radius:4px; overflow:hidden; background:#0F172A; display:inline-flex; align-items:center; justify-content:center;">
                                        <video src="${svc.image}" style="width:100%; height:100%; object-fit:cover;"></video>
                                        <span style="position:absolute; background:rgba(0,0,0,0.65); color:#FFF; font-size:9px; padding:1px 3px; border-radius:2px;">VIDEO</span>
                                    </div>
                                `;
                            } else {
                                mediaHtml = `<img src="${svc.image}" style="width:65px; height:45px; object-fit:cover; border-radius:4px; display:inline-block;">`;
                            }
                        }

                        tr.innerHTML = `
                            <td>${mediaHtml}</td>
                            <td>
                                <strong>${svc.name}</strong>
                                <div style="font-size:0.78rem; color:var(--admin-text-light);"><code>${svc.slug}</code></div>
                            </td>
                            <td><span class="badge badge-info">${svc.category_name || 'Unassigned'}</span></td>
                            <td><span style="font-size:0.82rem; color:var(--admin-text); display:block; max-width:280px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${svc.short_description || ''}">${svc.short_description || '-'}</span></td>
                            <td><span class="badge ${svc.is_published ? 'badge-success' : 'badge-warning'}">${svc.is_published ? 'Published' : 'Draft'}</span></td>
                            <td>
                                <div class="btn-action-group">
                                    <button class="btn-action edit" onclick="editService(${svc.id})" title="Edit Service">
                                        <i data-lucide="edit-3" style="width:14px; height:14px;"></i>
                                    </button>
                                    <button class="btn-action delete" onclick="deleteService(${svc.id})" title="Delete Service">
                                        <i data-lucide="trash-2" style="width:14px; height:14px;"></i>
                                    </button>
                                </div>
                            </td>
                        `;
                        tbody.appendChild(tr);
                    });
                }
                initIcons();
            }
        } catch (err) {
            console.error('Error fetching services:', err);
        }
    };

    // Category filter in Services tab
    const filterCatDropdown = document.getElementById('filter-service-category');
    if (filterCatDropdown) {
        filterCatDropdown.addEventListener('change', (e) => {
            fetchServices(e.target.value);
        });
    }

    // Auto-generate service slug from name
    const serviceNameInput = document.getElementById('service-name');
    if (serviceNameInput) {
        serviceNameInput.addEventListener('input', (e) => {
            const nameVal = e.target.value;
            document.getElementById('service-slug').value = nameVal.toLowerCase()
                .replace(/[^a-z0-9 -]/g, '')
                .replace(/\s+/g, '-')
                .replace(/-+/g, '-');
        });
    }

    // Media preview handler for Service Option
    const serviceImageFileInput = document.getElementById('service-image-file');
    const serviceMediaPreviewContainer = document.getElementById('service-media-preview-container');
    const serviceRemoveMediaBtn = document.getElementById('btn-remove-service-media');
    const serviceRemoveFlag = document.getElementById('service-remove-image');

    if (serviceImageFileInput && serviceMediaPreviewContainer) {
        serviceImageFileInput.addEventListener('change', () => {
            const file = serviceImageFileInput.files[0];
            if (file) {
                serviceRemoveFlag.value = '0';
                const fileUrl = URL.createObjectURL(file);
                if (file.type.startsWith('video/')) {
                    serviceMediaPreviewContainer.innerHTML = `
                        <div style="font-size:0.75rem; color:var(--admin-text-light); margin-bottom:4px;">Video Preview:</div>
                        <video src="${fileUrl}" controls autoplay muted loop style="max-width:100%; max-height:160px; border-radius:4px; display:block;"></video>
                    `;
                } else {
                    serviceMediaPreviewContainer.innerHTML = `
                        <div style="font-size:0.75rem; color:var(--admin-text-light); margin-bottom:4px;">Image Preview:</div>
                        <img src="${fileUrl}" style="max-width:100%; max-height:160px; border-radius:4px; object-fit:cover; display:block;">
                    `;
                }
                serviceMediaPreviewContainer.style.display = 'block';
                if (serviceRemoveMediaBtn) serviceRemoveMediaBtn.style.display = 'inline-flex';
                initIcons();
            }
        });
    }

    if (serviceRemoveMediaBtn) {
        serviceRemoveMediaBtn.addEventListener('click', () => {
            serviceImageFileInput.value = '';
            serviceMediaPreviewContainer.innerHTML = '';
            serviceMediaPreviewContainer.style.display = 'none';
            serviceRemoveMediaBtn.style.display = 'none';
            serviceRemoveFlag.value = '1';
        });
    }

    const btnAddService = document.getElementById('btn-add-service');
    if (btnAddService) {
        btnAddService.addEventListener('click', async () => {
            await fetchServiceCategories();
            document.getElementById('service-form').reset();
            document.getElementById('service-id').value = '';
            serviceRemoveFlag.value = '0';
            serviceMediaPreviewContainer.innerHTML = '';
            serviceMediaPreviewContainer.style.display = 'none';
            if (serviceRemoveMediaBtn) serviceRemoveMediaBtn.style.display = 'none';
            document.getElementById('service-modal-title').textContent = 'Add Service Option';
            openModal('service-modal');
        });
    }

    window.editService = async (id) => {
        try {
            await fetchServiceCategories();
            document.getElementById('service-form').reset();
            if (serviceMediaPreviewContainer) {
                serviceMediaPreviewContainer.innerHTML = '';
                serviceMediaPreviewContainer.style.display = 'none';
            }
            if (serviceRemoveMediaBtn) serviceRemoveMediaBtn.style.display = 'none';
            if (serviceRemoveFlag) serviceRemoveFlag.value = '0';

            const res = await fetch(`/api/services/${id}?t=${Date.now()}`);
            const svc = await res.json();
            if (!res.ok) return alert(svc.error || 'Failed to fetch service details');

            document.getElementById('service-id').value = svc.id;
            document.getElementById('service-category').value = svc.category_id || '';
            document.getElementById('service-name').value = svc.name;
            document.getElementById('service-slug').value = svc.slug;
            document.getElementById('service-icon').value = svc.icon || '';
            document.getElementById('service-status').value = String(svc.is_published);
            document.getElementById('service-short-desc').value = svc.short_description || '';
            document.getElementById('service-full-desc').value = svc.full_description || '';

            // Parse features & deliverables from JSON string if needed
            let featuresStr = '';
            try {
                const fArray = typeof svc.features === 'string' ? JSON.parse(svc.features || '[]') : svc.features;
                featuresStr = Array.isArray(fArray) ? fArray.join('\n') : '';
            } catch (e) { featuresStr = svc.features || ''; }
            document.getElementById('service-features').value = featuresStr;

            let deliverablesStr = '';
            try {
                const dArray = typeof svc.deliverables === 'string' ? JSON.parse(svc.deliverables || '[]') : svc.deliverables;
                deliverablesStr = Array.isArray(dArray) ? dArray.join('\n') : '';
            } catch (e) { deliverablesStr = svc.deliverables || ''; }
            document.getElementById('service-deliverables').value = deliverablesStr;

            // Media display
            if (svc.image) {
                const mediaUrl = `${svc.image}${svc.image.includes('?') ? '&' : '?'}t=${Date.now()}`;
                if (isVideoFile(svc.image)) {
                    serviceMediaPreviewContainer.innerHTML = `
                        <div style="font-size:0.75rem; color:var(--admin-text-light); margin-bottom:4px;">Current Custom Video:</div>
                        <video src="${mediaUrl}" controls autoplay muted loop style="max-width:100%; max-height:160px; border-radius:4px; display:block;"></video>
                    `;
                } else {
                    serviceMediaPreviewContainer.innerHTML = `
                        <div style="font-size:0.75rem; color:var(--admin-text-light); margin-bottom:4px;">Current Custom Image:</div>
                        <img src="${mediaUrl}" style="max-width:100%; max-height:160px; border-radius:4px; object-fit:cover; display:block;">
                    `;
                }
                serviceMediaPreviewContainer.style.display = 'block';
                if (serviceRemoveMediaBtn) serviceRemoveMediaBtn.style.display = 'inline-flex';
            } else {
                serviceMediaPreviewContainer.innerHTML = '';
                serviceMediaPreviewContainer.style.display = 'none';
                if (serviceRemoveMediaBtn) serviceRemoveMediaBtn.style.display = 'none';
            }

            document.getElementById('service-modal-title').textContent = 'Edit Service Option';
            openModal('service-modal');
            initIcons();
        } catch (err) {
            console.error(err);
        }
    };

    window.deleteService = async (id) => {
        if (confirm('Are you sure you want to delete this service option?')) {
            try {
                const res = await fetch(`/api/services/${id}`, { method: 'DELETE' });
                const data = await res.json();
                if (res.ok) {
                    const activeCatFilter = document.getElementById('filter-service-category').value;
                    fetchServices(activeCatFilter);
                } else {
                    alert(data.error || 'Failed to delete service.');
                }
            } catch (err) {
                console.error(err);
            }
        }
    };

    const serviceForm = document.getElementById('service-form');
    if (serviceForm) {
        serviceForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = serviceForm.querySelector('button[type="submit"]');
            const originalBtnHtml = submitBtn ? submitBtn.innerHTML : 'Save Service Option';

            try {
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<i data-lucide="loader-2" class="spin" style="width:14px;height:14px;vertical-align:middle;margin-right:6px;"></i> Optimizing & Saving...';
                    initIcons();
                }

                const id = document.getElementById('service-id').value;
                const formData = new FormData(serviceForm);

                // Auto-compress service image if uploaded
                const imageInput = document.getElementById('service-image-file');
                if (imageInput && imageInput.files && imageInput.files[0]) {
                    const originalFile = imageInput.files[0];
                    if (originalFile.type.startsWith('image/')) {
                        const compressedImg = await compressImageFile(originalFile);
                        formData.set('image', compressedImg);
                    }
                }

                const url = id ? `/api/services/${id}` : '/api/services';
                const res = await fetch(url, {
                    method: 'POST',
                    body: formData
                });

                if (res.status === 401) {
                    alert('Your admin session has expired. Please log in again.');
                    window.location.href = '/admin/login';
                    return;
                }

                const data = await res.json();
                if (res.ok) {
                    closeModal('service-modal');
                    const activeCatFilter = document.getElementById('filter-service-category').value;
                    fetchServices(activeCatFilter);
                } else {
                    alert(data.error || 'Failed to save service.');
                }
            } catch (err) {
                console.error(err);
                alert('An error occurred while saving: ' + (err.message || 'Network error'));
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnHtml;
                    initIcons();
                }
            }
        });
    }


    // --- PROJECTS LOGIC ---
    const fetchProjects = async () => {
        try {
            const res = await fetch(`/api/projects?t=${Date.now()}`);
            const data = await res.json();
            
            const tbody = document.getElementById('projects-table-body');
            tbody.innerHTML = '';
            
            let pubCount = 0;
            data.forEach(p => {
                if (p.status === 'published') pubCount++;
                
                const tr = document.createElement('tr');
                const featImgSrc = p.featured_image ? `${p.featured_image}${p.featured_image.includes('?') ? '&' : '?'}t=${Date.now()}` : '';
                tr.innerHTML = `
                    <td><img src="${featImgSrc}" style="width:50px; height:35px; object-fit:cover; border-radius:4px;"></td>
                    <td><strong>${p.title}</strong></td>
                    <td>${p.category_name || '<span style="color:var(--admin-text-light);">Unassigned</span>'}</td>
                    <td><code>${p.capacity}</code></td>
                    <td>${p.location}</td>
                    <td>
                        <button class="btn-admin btn-admin-secondary" onclick="openGalleryManager(${p.id})" style="font-size:0.78rem; padding:0.25rem 0.5rem;">
                            <i data-lucide="images" style="width:12px; height:12px;"></i>
                            <span>Drawings (${p.gallery_count})</span>
                        </button>
                    </td>
                    <td>
                        <span class="badge ${p.status === 'published' ? 'badge-success' : 'badge-warning'}">${p.status}</span>
                    </td>
                    <td>
                        <div class="btn-action-group">
                            <button class="btn-action edit" onclick="editProject(${p.id})">
                                <i data-lucide="edit-3" style="width:14px; height:14px;"></i>
                            </button>
                            <button class="btn-action delete" onclick="deleteProject(${p.id})">
                                <i data-lucide="trash-2" style="width:14px; height:14px;"></i>
                            </button>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });
            initIcons();
            
            // Set statistics
            document.getElementById('stat-proj-count').textContent = data.length;
            document.getElementById('stat-proj-pub').textContent = pubCount;
        } catch (err) {
            console.error(err);
        }
    };

    // Helper to completely reset and isolate project modal state
    const resetProjectModal = () => {
        const form = document.getElementById('project-form');
        if (form) form.reset();

        const idInput = document.getElementById('project-id');
        if (idInput) idInput.value = '';

        const featInput = document.getElementById('project-featured-image');
        if (featInput) {
            featInput.value = '';
            featInput.required = true;
        }

        const preview = document.getElementById('project-featured-preview');
        if (preview) {
            preview.innerHTML = `<i data-lucide="image" style="width: 24px; height: 24px; color: var(--admin-text-light);"></i>`;
        }

        const titleEl = document.getElementById('project-modal-title');
        if (titleEl) titleEl.textContent = 'Add Project';

        const helpEl = document.getElementById('project-featured-help');
        if (helpEl) helpEl.textContent = 'Select the main cover image for this project.';

        const galleryInfo = document.getElementById('project-edit-gallery-info');
        if (galleryInfo) galleryInfo.style.display = 'none';

        initIcons();
    };
    window.resetProjectModal = resetProjectModal;

    // Project form submit (Clean metadata + featured image only)
    document.getElementById('project-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalBtnHtml = submitBtn ? submitBtn.innerHTML : 'Save Project';

        try {
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i data-lucide="loader-2" class="spin" style="width:14px;height:14px;vertical-align:middle;margin-right:6px;"></i> Saving...';
                initIcons();
            }

            const id = document.getElementById('project-id').value;
            const formData = new FormData(e.target);

            // Auto-compress featured image if a new file was selected
            const featInput = document.getElementById('project-featured-image');
            if (featInput && featInput.files && featInput.files[0]) {
                const originalFile = featInput.files[0];
                if (originalFile.type.startsWith('image/')) {
                    const compressed = await compressImageFile(originalFile);
                    formData.set('featured_image', compressed);
                }
            } else if (id) {
                // If editing and no new featured image chosen, omit empty field so current image is preserved
                formData.delete('featured_image');
            }

            // Always ensure no gallery_images are sent from the project form (handled exclusively via Drawings modal)
            formData.delete('gallery_images');
            
            const url = id ? `/api/projects/${id}` : '/api/projects';
            const res = await fetch(url, {
                method: 'POST',
                body: formData
            });

            if (res.status === 401) {
                alert('Your admin session has expired. Please log in again.');
                window.location.href = '/admin/login';
                return;
            }

            const data = await res.json();
            if (res.ok) {
                const wasAdd = !id;
                const newId = data.id;
                resetProjectModal();
                closeModal('project-modal');
                fetchProjects();
                
                // If user just created a new project, offer to open Gallery Manager to add drawings right away
                if (wasAdd && newId) {
                    setTimeout(() => {
                        if (confirm('Project created successfully! Would you like to upload drawings to this project now?')) {
                            openGalleryManager(newId);
                        }
                    }, 250);
                }
            } else {
                alert(data.error || 'An error occurred.');
            }
        } catch (err) {
            console.error(err);
            alert('An error occurred while saving project: ' + (err.message || 'Network error'));
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnHtml;
                initIcons();
            }
        }
    });

    document.getElementById('btn-add-project').addEventListener('click', () => {
        resetProjectModal();
        document.getElementById('project-featured-image').required = true;
        document.getElementById('project-modal-title').textContent = 'Add Project';
        const helpEl = document.getElementById('project-featured-help');
        if (helpEl) helpEl.textContent = 'Upload the featured project cover image (required).';
        
        // Ensure categories are loaded
        fetchCategories().then(() => {
            openModal('project-modal');
            initIcons();
        });
    });

    window.editProject = async (id) => {
        try {
            // First cleanly reset any previous form or file state
            resetProjectModal();

            // First load categories
            await fetchCategories();
            
            // Fetch project details with cache-buster
            const res = await fetch(`/api/projects/${id}?t=${Date.now()}`);
            const p = await res.json();
            
            if (res.ok) {
                document.getElementById('project-id').value = p.id;
                document.getElementById('project-title').value = p.title || '';
                document.getElementById('project-category').value = p.category_id || '';
                document.getElementById('project-capacity').value = p.capacity || '';
                document.getElementById('project-location').value = p.location || '';
                document.getElementById('project-client').value = p.client_name || '';
                document.getElementById('project-date').value = p.completion_date || '';
                document.getElementById('project-status').value = p.status || 'published';
                document.getElementById('project-services').value = p.services_delivered || '';
                document.getElementById('project-description').value = p.description || '';
                
                // Clear file input & make optional for edit
                document.getElementById('project-featured-image').value = '';
                document.getElementById('project-featured-image').required = false;
                
                const helpEl = document.getElementById('project-featured-help');
                if (helpEl) helpEl.textContent = 'Leave empty to keep current image, or select a new file to replace it.';

                // Show current featured image preview with cache-buster
                if (p.featured_image) {
                    const previewUrl = `${p.featured_image}${p.featured_image.includes('?') ? '&' : '?'}t=${Date.now()}`;
                    document.getElementById('project-featured-preview').innerHTML = `<img src="${previewUrl}" alt="Featured preview">`;
                } else {
                    document.getElementById('project-featured-preview').innerHTML = `<i data-lucide="image" style="width: 24px; height: 24px; color: var(--admin-text-light);"></i>`;
                }

                // Show Gallery Manager shortcut inside Edit tab
                const galleryInfo = document.getElementById('project-edit-gallery-info');
                const galBtn = document.getElementById('btn-open-gallery-from-edit');
                const galBtnText = document.getElementById('edit-modal-gallery-btn-text');
                if (galleryInfo && galBtn) {
                    galleryInfo.style.display = 'block';
                    const drawingsCount = (p.gallery && p.gallery.length) || 0;
                    if (galBtnText) galBtnText.textContent = `Manage Drawings (${drawingsCount})`;
                    galBtn.onclick = () => {
                        closeModal('project-modal');
                        openGalleryManager(p.id);
                    };
                }
                
                document.getElementById('project-modal-title').textContent = 'Edit Project';
                openModal('project-modal');
                initIcons();
            } else {
                alert(p.error || 'Failed to load project details.');
            }
        } catch (err) {
            console.error(err);
            alert('Error loading project: ' + (err.message || 'Network error'));
        }
    };

    window.deleteProject = async (id) => {
        if (confirm('Are you sure you want to delete this project? All associated gallery drawings will be permanently deleted.')) {
            try {
                const res = await fetch(`/api/projects/${id}`, { method: 'DELETE' });
                if (res.ok) fetchProjects();
            } catch (err) {
                console.error(err);
            }
        }
    };


    // --- PROJECT GALLERY MANAGER LOGIC (Multi-Add, Multi-Select, Bulk-Delete) ---
    const updateBulkDeleteVisibility = () => {
        const list = document.getElementById('gallery-manager-list');
        const selectedCheckboxes = list ? list.querySelectorAll('.gallery-item-select:checked') : [];
        const count = selectedCheckboxes.length;
        const bulkDeleteBtn = document.getElementById('btn-bulk-delete-gallery');
        const countSpan = document.getElementById('gallery-selected-count');
        const selectAllCheckbox = document.getElementById('gallery-select-all');
        const selectAllText = document.getElementById('gallery-select-all-text');
        const allCheckboxes = list ? list.querySelectorAll('.gallery-item-select') : [];

        if (countSpan) countSpan.textContent = count;
        if (bulkDeleteBtn) {
            if (count > 0) {
                bulkDeleteBtn.style.setProperty('display', 'inline-flex', 'important');
            } else {
                bulkDeleteBtn.style.setProperty('display', 'none', 'important');
            }
        }
        if (selectAllCheckbox && allCheckboxes.length > 0) {
            selectAllCheckbox.checked = count === allCheckboxes.length;
            selectAllCheckbox.indeterminate = count > 0 && count < allCheckboxes.length;
            if (selectAllText) {
                selectAllText.textContent = count === allCheckboxes.length ? 'Deselect All' : 'Select All';
            }
        } else if (selectAllCheckbox) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
            if (selectAllText) selectAllText.textContent = 'Select All';
        }
    };

    const loadGalleryImages = async (projId) => {
        try {
            const list = document.getElementById('gallery-manager-list');
            const emptyText = document.getElementById('gallery-empty-text');
            const totalCount = document.getElementById('gallery-total-count');
            const subtitle = document.getElementById('gallery-modal-subtitle');
            
            if (list) list.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding: 2.5rem 1rem; color:var(--admin-text-light);"><i data-lucide="loader-2" class="spin" style="width:26px;height:26px;margin-bottom:8px;display:inline-block;"></i><div>Loading project drawings...</div></div>';
            initIcons();

            const res = await fetch(`/api/projects/${projId}?t=${Date.now()}`);
            const data = await res.json();
            
            if (subtitle && data.title) {
                subtitle.textContent = `Drawings & renderings for "${data.title}"`;
            }

            const drawings = data.gallery || [];
            if (totalCount) totalCount.textContent = drawings.length;

            if (list) list.innerHTML = '';

            if (drawings.length === 0) {
                if (emptyText) emptyText.style.display = 'block';
            } else {
                if (emptyText) emptyText.style.display = 'none';
                
                drawings.forEach(img => {
                    const div = document.createElement('div');
                    div.classList.add('gallery-preview-item');
                    div.dataset.imgId = img.id;
                    const imgSrc = `${img.image_path}${img.image_path.includes('?') ? '&' : '?'}t=${Date.now()}`;
                    div.innerHTML = `
                        <div class="img-wrapper" title="Click drawing to select/deselect">
                            <input type="checkbox" class="gallery-item-select" data-img-id="${img.id}">
                            <img src="${imgSrc}" alt="Gallery drawing" loading="lazy">
                            <button type="button" class="gallery-preview-item-delete" title="Delete drawing" onclick="event.stopPropagation(); deleteGalleryImage(${img.id}, ${projId})">&times;</button>
                        </div>
                        <div class="gallery-item-caption-wrap">
                            <input type="text" class="gallery-item-caption-input" value="${img.caption || ''}" placeholder="Caption (e.g. SLD, 3D)..." 
                                   onclick="event.stopPropagation()"
                                   onblur="updateGalleryCaption(${img.id}, this.value)">
                        </div>
                    `;

                    // Checkbox toggle logic
                    const chk = div.querySelector('.gallery-item-select');
                    chk.addEventListener('change', (e) => {
                        e.stopPropagation();
                        div.classList.toggle('selected', chk.checked);
                        updateBulkDeleteVisibility();
                    });

                    // Clicking anywhere on the img-wrapper toggles selection effortlessly
                    const imgWrap = div.querySelector('.img-wrapper');
                    imgWrap.addEventListener('click', (e) => {
                        if (e.target.closest('.gallery-preview-item-delete')) return;
                        if (e.target.classList.contains('gallery-item-select')) return;
                        chk.checked = !chk.checked;
                        div.classList.toggle('selected', chk.checked);
                        updateBulkDeleteVisibility();
                    });

                    list.appendChild(div);
                });
            }
            updateBulkDeleteVisibility();
            initIcons();
        } catch (err) {
            console.error(err);
        }
    };

    window.openGalleryManager = (projId) => {
        document.getElementById('gallery-project-id').value = projId;
        const galFiles = document.getElementById('gallery-manager-files');
        if (galFiles) galFiles.value = '';
        const selectAll = document.getElementById('gallery-select-all');
        if (selectAll) {
            selectAll.checked = false;
            selectAll.indeterminate = false;
        }
        const selectAllText = document.getElementById('gallery-select-all-text');
        if (selectAllText) selectAllText.textContent = 'Select All';

        updateBulkDeleteVisibility();
        loadGalleryImages(projId);
        openModal('gallery-manager-modal');
        initIcons();
    };

    // Select All toggle handler (bind to both checkbox and wrapper label)
    const selectAllCheckbox = document.getElementById('gallery-select-all');
    const selectAllLabel = document.getElementById('gallery-select-all-label');

    const handleSelectAllToggle = () => {
        if (!selectAllCheckbox) return;
        const isChecked = selectAllCheckbox.checked;
        const list = document.getElementById('gallery-manager-list');
        const items = list ? list.querySelectorAll('.gallery-preview-item') : [];
        items.forEach(item => {
            const chk = item.querySelector('.gallery-item-select');
            if (chk) chk.checked = isChecked;
            item.classList.toggle('selected', isChecked);
        });
        updateBulkDeleteVisibility();
    };

    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', handleSelectAllToggle);
    }
    if (selectAllLabel) {
        selectAllLabel.addEventListener('click', (e) => {
            if (e.target !== selectAllCheckbox) {
                selectAllCheckbox.checked = !selectAllCheckbox.checked;
                handleSelectAllToggle();
            }
        });
    }

    // Bulk Delete Selected Drawings
    const bulkDeleteBtn = document.getElementById('btn-bulk-delete-gallery');
    if (bulkDeleteBtn) {
        bulkDeleteBtn.addEventListener('click', async () => {
            const projId = document.getElementById('gallery-project-id').value;
            const selectedCheckboxes = document.querySelectorAll('.gallery-item-select:checked');
            const ids = Array.from(selectedCheckboxes).map(chk => parseInt(chk.dataset.imgId, 10)).filter(id => !isNaN(id));

            if (ids.length === 0) {
                alert('No drawings selected. Click on drawing images or use "Select All" to select drawings to delete.');
                return;
            }

            if (!confirm(`Are you sure you want to permanently delete the ${ids.length} selected drawing(s)?`)) {
                return;
            }

            const origHtml = bulkDeleteBtn.innerHTML;
            bulkDeleteBtn.disabled = true;
            bulkDeleteBtn.innerHTML = '<i data-lucide="loader-2" class="spin" style="width:14px;height:14px;vertical-align:middle;margin-right:4px;"></i> Deleting...';
            initIcons();

            try {
                const res = await fetch('/api/projects/gallery/bulk-delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ image_ids: ids })
                });

                if (res.ok) {
                    const data = await res.json();
                    loadGalleryImages(projId);
                    fetchProjects();
                } else {
                    const errData = await res.json().catch(() => ({}));
                    alert(errData.error || 'Failed to delete selected drawings.');
                }
            } catch (err) {
                console.error(err);
                alert('Error during bulk deletion: ' + (err.message || 'Network error'));
            } finally {
                bulkDeleteBtn.disabled = false;
                bulkDeleteBtn.innerHTML = origHtml;
                initIcons();
            }
        });
    }

    // Upload more gallery drawings with dedicated endpoint & loading state
    document.getElementById('btn-upload-more-gallery').addEventListener('click', async () => {
        const projId = document.getElementById('gallery-project-id').value;
        const fileInput = document.getElementById('gallery-manager-files');
        const files = fileInput.files;
        
        if (!projId) {
            alert('No project selected.');
            return;
        }

        if (!files || files.length === 0) {
            alert('Please select files to upload.');
            return;
        }
        
        const uploadBtn = document.getElementById('btn-upload-more-gallery');
        const origText = uploadBtn ? uploadBtn.innerHTML : 'Upload';
        if (uploadBtn) {
            uploadBtn.disabled = true;
            uploadBtn.innerHTML = '<i data-lucide="loader-2" class="spin" style="width:14px;height:14px;vertical-align:middle;margin-right:6px;"></i> Uploading...';
            initIcons();
        }

        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('gallery_images', files[i]);
        }
        
        try {
            const res = await fetch(`/api/projects/${projId}/gallery`, {
                method: 'POST',
                body: formData
            });
            if (res.ok) {
                fileInput.value = '';
                loadGalleryImages(projId);
                fetchProjects(); // Update project table gallery count
            } else {
                const errData = await res.json().catch(() => ({}));
                alert(errData.error || 'Upload failed.');
            }
        } catch (err) {
            console.error(err);
            alert('Error uploading gallery drawings: ' + (err.message || 'Network error'));
        } finally {
            if (uploadBtn) {
                uploadBtn.disabled = false;
                uploadBtn.innerHTML = origText;
                initIcons();
            }
        }
    });

    window.deleteGalleryImage = async (imgId, projId) => {
        if (confirm('Delete this gallery drawing?')) {
            try {
                const res = await fetch(`/api/projects/gallery/${imgId}`, { method: 'DELETE' });
                if (res.ok) {
                    loadGalleryImages(projId);
                    fetchProjects(); // Update gallery count in main table
                }
            } catch (err) {
                console.error(err);
            }
        }
    };

    window.updateGalleryCaption = async (imgId, value) => {
        try {
            await fetch(`/api/projects/gallery/${imgId}/caption`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ caption: value })
            });
        } catch (err) {
            console.error(err);
        }
    };


    // --- TESTIMONIALS LOGIC ---
    const fetchTestimonials = async () => {
        try {
            const res = await fetch('/api/testimonials');
            const data = await res.json();
            
            const tbody = document.getElementById('testimonials-table-body');
            tbody.innerHTML = '';
            
            data.forEach(t => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><strong>${t.client_name}</strong></td>
                    <td>${t.client_role}</td>
                    <td>${t.company_name}</td>
                    <td style="color:#FBBF24;">${'★'.repeat(t.rating)}</td>
                    <td><span style="font-size:0.82rem; color:var(--admin-text-light);">${t.feedback.substring(0, 50)}...</span></td>
                    <td>
                        <div class="btn-action-group">
                            <button class="btn-action edit" onclick="editTestimonial(${t.id})">
                                <i data-lucide="edit-3" style="width:14px; height:14px;"></i>
                            </button>
                            <button class="btn-action delete" onclick="deleteTestimonial(${t.id})">
                                <i data-lucide="trash-2" style="width:14px; height:14px;"></i>
                            </button>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });
            initIcons();
        } catch (err) {
            console.error(err);
        }
    };

    document.getElementById('testimonial-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('testimonial-id').value;
        const client_name = document.getElementById('testimonial-name').value.trim();
        const client_role = document.getElementById('testimonial-role').value.trim();
        const rating = parseInt(document.getElementById('testimonial-rating').value);
        const company_name = document.getElementById('testimonial-company').value.trim();
        const feedback = document.getElementById('testimonial-feedback').value.trim();
        
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/testimonials/${id}` : '/api/testimonials';
        
        try {
            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ client_name, client_role, rating, company_name, feedback })
            });
            if (res.ok) {
                closeModal('testimonial-modal');
                fetchTestimonials();
            } else {
                alert('Failed to save testimonial.');
            }
        } catch (err) {
            console.error(err);
        }
    });

    document.getElementById('btn-add-testimonial').addEventListener('click', () => {
        document.getElementById('testimonial-form').reset();
        document.getElementById('testimonial-id').value = '';
        document.getElementById('testimonial-modal-title').textContent = 'Add Testimonial';
        openModal('testimonial-modal');
    });

    window.editTestimonial = async (id) => {
        try {
            const res = await fetch(`/api/testimonials/${id}`);
            const t = await res.json();
            
            if (res.ok) {
                document.getElementById('testimonial-id').value = t.id;
                document.getElementById('testimonial-name').value = t.client_name;
                document.getElementById('testimonial-role').value = t.client_role;
                document.getElementById('testimonial-rating').value = t.rating;
                document.getElementById('testimonial-company').value = t.company_name;
                document.getElementById('testimonial-feedback').value = t.feedback;
                
                document.getElementById('testimonial-modal-title').textContent = 'Edit Testimonial';
                openModal('testimonial-modal');
            }
        } catch (err) {
            console.error(err);
        }
    };

    window.deleteTestimonial = async (id) => {
        if (confirm('Delete this client testimonial?')) {
            try {
                const res = await fetch(`/api/testimonials/${id}`, { method: 'DELETE' });
                if (res.ok) fetchTestimonials();
            } catch (err) {
                console.error(err);
            }
        }
    };


    // --- BLOGS LOGIC ---
    const fetchBlogs = async () => {
        try {
            const res = await fetch('/api/blogs');
            const data = await res.json();
            
            const tbody = document.getElementById('blogs-table-body');
            tbody.innerHTML = '';
            
            data.forEach(b => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><img src="${b.featured_image}" style="width:50px; height:35px; object-fit:cover; border-radius:4px;"></td>
                    <td><strong>${b.title}</strong></td>
                    <td><span class="badge badge-info">${b.category}</span></td>
                    <td><code>/blog/${b.slug}</code></td>
                    <td>${b.created_at.split(' ')[0]}</td>
                    <td>
                        <span class="badge ${b.status === 'published' ? 'badge-success' : 'badge-warning'}">${b.status}</span>
                    </td>
                    <td>
                        <div class="btn-action-group">
                            <button class="btn-action edit" onclick="editBlog(${b.id})">
                                <i data-lucide="edit-3" style="width:14px; height:14px;"></i>
                            </button>
                            <button class="btn-action delete" onclick="deleteBlog(${b.id})">
                                <i data-lucide="trash-2" style="width:14px; height:14px;"></i>
                            </button>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });
            initIcons();
        } catch (err) {
            console.error(err);
        }
    };

    document.getElementById('blog-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalBtnHtml = submitBtn ? submitBtn.innerHTML : 'Save Article';

        try {
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i data-lucide="loader-2" class="spin" style="width:14px;height:14px;vertical-align:middle;margin-right:6px;"></i> Optimizing & Saving...';
                initIcons();
            }

            const id = document.getElementById('blog-id').value;
            const formData = new FormData(e.target);

            // Auto-compress blog featured image
            const featInput = document.getElementById('blog-featured-image');
            if (featInput && featInput.files && featInput.files[0]) {
                const originalFile = featInput.files[0];
                if (originalFile.type.startsWith('image/')) {
                    const compressed = await compressImageFile(originalFile);
                    formData.set('featured_image', compressed);
                }
            }
            
            const url = id ? `/api/blogs/${id}` : '/api/blogs';
            const res = await fetch(url, {
                method: 'POST', // Use POST for both insert and edit to support FormData upload seamlessly
                body: formData
            });

            if (res.status === 401) {
                alert('Your admin session has expired. Please log in again.');
                window.location.href = '/admin/login';
                return;
            }

            const data = await res.json();
            if (res.ok) {
                closeModal('blog-modal');
                fetchBlogs();
            } else {
                alert(data.error || 'An error occurred.');
            }
        } catch (err) {
            console.error(err);
            alert('An error occurred while saving article: ' + (err.message || 'Network error'));
        } finally {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerHTML = originalBtnHtml;
                initIcons();
            }
        }
    });

    document.getElementById('btn-add-blog').addEventListener('click', () => {
        document.getElementById('blog-form').reset();
        document.getElementById('blog-id').value = '';
        document.getElementById('blog-featured-preview').innerHTML = `<i data-lucide="image" style="width: 24px; height: 24px; color: var(--admin-text-light);"></i>`;
        document.getElementById('blog-featured-image').required = true;
        document.getElementById('blog-modal-title').textContent = 'Write Article';
        openModal('blog-modal');
    });

    window.editBlog = async (id) => {
        try {
            const res = await fetch(`/api/blogs/${id}`);
            const b = await res.json();
            
            if (res.ok) {
                document.getElementById('blog-id').value = b.id;
                document.getElementById('blog-title').value = b.title;
                document.getElementById('blog-category').value = b.category;
                document.getElementById('blog-slug').value = b.slug;
                document.getElementById('blog-excerpt').value = b.excerpt;
                document.getElementById('blog-content').value = b.content;
                document.getElementById('blog-status').value = b.status;
                
                document.getElementById('blog-featured-preview').innerHTML = `<img src="${b.featured_image}" alt="Blog featured preview">`;
                document.getElementById('blog-featured-image').required = false; // Not required for editing
                
                document.getElementById('blog-modal-title').textContent = 'Edit Article';
                openModal('blog-modal');
            }
        } catch (err) {
            console.error(err);
        }
    };

    window.deleteBlog = async (id) => {
        if (confirm('Delete this blog article permanently?')) {
            try {
                const res = await fetch(`/api/blogs/${id}`, { method: 'DELETE' });
                if (res.ok) fetchBlogs();
            } catch (err) {
                console.error(err);
            }
        }
    };

    // Auto-generate blog slug
    document.getElementById('blog-title').addEventListener('input', (e) => {
        const titleVal = e.target.value;
        document.getElementById('blog-slug').value = titleVal.toLowerCase()
            .replace(/[^a-z0-9 -]/g, '')
            .replace(/\s+/g, '-')
            .replace(/-+/g, '-');
    });


    // --- CONTACT LEADS LOGIC ---
    const fetchLeads = async () => {
        try {
            const res = await fetch('/api/inquiries');
            const data = await res.json();
            
            const tbody = document.getElementById('leads-table-body');
            tbody.innerHTML = '';
            
            data.forEach(l => {
                const dateStr = l.created_at.split(' ')[0];
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${dateStr}</td>
                    <td><strong>${l.name}</strong></td>
                    <td>${l.company_name || '-'}</td>
                    <td><a href="mailto:${l.email}">${l.email}</a></td>
                    <td>${l.phone || '-'}</td>
                    <td><span class="badge badge-info" style="font-size:0.75rem;">${l.project_type}</span></td>
                    <td>
                        <span style="font-size:0.82rem; color:var(--admin-text-light); display:block; max-width:250px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${l.message}">
                            ${l.message}
                        </span>
                    </td>
                    <td>
                        <span class="badge ${l.status === 'unread' ? 'badge-danger' : 'badge-success'}">${l.status}</span>
                    </td>
                    <td>
                        <button class="btn-admin btn-admin-secondary" onclick="toggleLeadStatus(${l.id}, '${l.status}')" style="font-size:0.75rem; padding:0.25rem 0.5rem;">
                            Mark as ${l.status === 'unread' ? 'Contacted' : 'Unread'}
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
            initIcons();
        } catch (err) {
            console.error(err);
        }
    };

    window.toggleLeadStatus = async (id, currentStatus) => {
        const nextStatus = currentStatus === 'unread' ? 'contacted' : 'unread';
        try {
            const res = await fetch(`/api/inquiries/${id}/contacted`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: nextStatus })
            });
            if (res.ok) fetchLeads();
        } catch (err) {
            console.error(err);
        }
    };


    // ===================================
    // 8. USERS MANAGEMENT
    // ===================================
    const fetchUsers = async () => {
        const table = document.getElementById('users-table');
        if (!table) return;
        const tbody = table.querySelector('tbody');
        try {
            const res = await fetch('/api/users');
            if (res.status === 403) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--admin-text-light);">Access denied.</td></tr>';
                return;
            }
            const users = await res.json();
            tbody.innerHTML = '';
            users.forEach(u => {
                const tr = document.createElement('tr');
                const roleLabel = u.role === 'super_admin' ? 'Super Admin' : 'Admin';
                const statusBadge = u.is_active ? '<span class="badge badge-success">Active</span>' : '<span class="badge badge-danger">Disabled</span>';
                tr.innerHTML = `
                    <td><a href="mailto:${u.email}">${u.email}</a></td>
                    <td>${u.name || '-'}</td>
                    <td><span class="badge badge-info" style="font-size:0.75rem;">${roleLabel}</span></td>
                    <td>${statusBadge}</td>
                    <td>
                        <div style="display:flex;gap:6px;">
                            <button class="btn-admin btn-admin-secondary" onclick="editUser(${u.id})" style="font-size:0.75rem;padding:0.25rem 0.5rem;">
                                <i data-lucide="edit-3" style="width:13px;height:13px;"></i> Edit
                            </button>
                            <button class="btn-admin btn-admin-danger" onclick="deleteUser(${u.id}, '${u.email}')" style="font-size:0.75rem;padding:0.25rem 0.5rem;">
                                <i data-lucide="trash-2" style="width:13px;height:13px;"></i>
                            </button>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });
            initIcons();
        } catch (err) {
            console.error(err);
        }
    };

    window.openUserModal = () => {
        const modal = document.getElementById('user-modal');
        if (!modal) return;
        document.getElementById('user-modal-title').textContent = 'Add New User';
        document.getElementById('user-id').value = '';
        document.getElementById('user-email').value = '';
        document.getElementById('user-email').disabled = false;
        document.getElementById('user-name').value = '';
        document.getElementById('user-password').value = '';
        document.getElementById('user-password').required = true;
        document.getElementById('user-password').placeholder = 'Min 6 characters';
        document.getElementById('user-role').value = 'admin';
        document.getElementById('user-active').value = '1';
        openModal('user-modal');
    };

    window.editUser = async (id) => {
        try {
            const res = await fetch('/api/users');
            const users = await res.json();
            const user = users.find(u => u.id === id);
            if (!user) return alert('User not found');

            document.getElementById('user-modal-title').textContent = 'Edit User';
            document.getElementById('user-id').value = user.id;
            document.getElementById('user-email').value = user.email;
            document.getElementById('user-email').disabled = true;
            document.getElementById('user-name').value = user.name || '';
            document.getElementById('user-password').value = '';
            document.getElementById('user-password').required = false;
            document.getElementById('user-password').placeholder = 'Leave blank to keep current';
            document.getElementById('user-role').value = user.role;
            document.getElementById('user-active').value = String(user.is_active);
            openModal('user-modal');
        } catch (err) {
            console.error(err);
        }
    };

    window.deleteUser = async (id, email) => {
        if (!confirm(`Are you sure you want to remove ${email}?`)) return;
        try {
            const res = await fetch(`/api/users/${id}`, { method: 'DELETE' });
            const data = await res.json();
            if (res.ok) {
                fetchUsers();
            } else {
                alert(data.error || 'Failed to delete user.');
            }
        } catch (err) {
            console.error(err);
        }
    };

    // User form submit
    const userForm = document.getElementById('user-form');
    if (userForm) {
        userForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const id = document.getElementById('user-id').value;
            const email = document.getElementById('user-email').value.trim();
            const name = document.getElementById('user-name').value.trim();
            const password = document.getElementById('user-password').value.trim();
            const role = document.getElementById('user-role').value;
            const is_active = parseInt(document.getElementById('user-active').value);

            if (id) {
                // Edit user
                const body = { name, role, is_active };
                if (password) body.password = password;
                try {
                    const res = await fetch(`/api/users/${id}`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(body)
                    });
                    const data = await res.json();
                    if (res.ok) {
                        closeModal('user-modal');
                        fetchUsers();
                    } else {
                        alert(data.error || 'Failed to update user.');
                    }
                } catch (err) {
                    console.error(err);
                }
            } else {
                // Create user
                if (!email || !password) return alert('Email and password are required.');
                try {
                    const res = await fetch('/api/users', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ email, name, password, role })
                    });
                    const data = await res.json();
                    if (res.ok) {
                        closeModal('user-modal');
                        fetchUsers();
                    } else {
                        alert(data.error || 'Failed to create user.');
                    }
                } catch (err) {
                    console.error(err);
                }
            }
        });
    }

    // Change password form
    const changePwForm = document.getElementById('change-password-form');
    if (changePwForm) {
        changePwForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const currentPassword = document.getElementById('current-password').value.trim();
            const newPassword = document.getElementById('new-password').value.trim();

            if (!currentPassword || !newPassword) return alert('Both fields are required.');
            if (newPassword.length < 6) return alert('New password must be at least 6 characters.');

            try {
                const res = await fetch('/api/users/change-password', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
                });
                const data = await res.json();
                if (res.ok) {
                    alert('Password changed successfully!');
                    document.getElementById('current-password').value = '';
                    document.getElementById('new-password').value = '';
                } else {
                    alert(data.error || 'Failed to change password.');
                }
            } catch (err) {
                console.error(err);
            }
        });
    }

    // ==========================================
    // 10. CLIENT LOGOS MANAGEMENT
    // ==========================================
    const fetchClientLogos = async () => {
        try {
            const res = await fetch('/api/client-logos');
            const data = await res.json();
            const tbody = document.getElementById('client-logos-table-body');
            if (tbody) {
                tbody.innerHTML = '';
                if (!data || data.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; color:var(--admin-text-light); padding:2rem;">No client logos found. Click "Add Client Logo" to add your first partner logo.</td></tr>';
                } else {
                    data.forEach(logo => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td>
                                <div style="width:96px; height:44px; background:#F8FAFC; border:1px solid var(--admin-border); border-radius:6px; display:flex; align-items:center; justify-content:center; padding:4px;">
                                    <img src="${logo.image}" alt="${logo.name}" style="max-width:100%; max-height:36px; object-fit:contain;">
                                </div>
                            </td>
                            <td><strong>${logo.name}</strong></td>
                            <td>${logo.website_url ? `<a href="${logo.website_url}" target="_blank" style="color:var(--accent);">${logo.website_url}</a>` : '<span style="color:var(--admin-text-light);">-</span>'}</td>
                            <td><span class="badge badge-info">${logo.display_order || 0}</span></td>
                            <td><span class="badge ${logo.is_published ? 'badge-success' : 'badge-warning'}">${logo.is_published ? 'Published' : 'Hidden'}</span></td>
                            <td>
                                <div class="btn-action-group">
                                    <button class="btn-action edit" onclick="editClientLogo(${logo.id})" title="Edit">
                                        <i data-lucide="edit-3" style="width:14px; height:14px;"></i>
                                    </button>
                                    <button class="btn-action delete" onclick="deleteClientLogo(${logo.id})" title="Delete">
                                        <i data-lucide="trash-2" style="width:14px; height:14px;"></i>
                                    </button>
                                </div>
                            </td>
                        `;
                        tbody.appendChild(tr);
                    });
                }
                initIcons();
            }
        } catch (err) {
            console.error('Error fetching client logos:', err);
        }
    };

    window.editClientLogo = async (id) => {
        try {
            const res = await fetch(`/api/client-logos/${id}`);
            const logo = await res.json();
            if (!res.ok) return alert(logo.error || 'Failed to fetch logo');

            document.getElementById('client-logo-form').reset();
            document.getElementById('client-logo-id').value = logo.id;
            document.getElementById('client-logo-name').value = logo.name;
            document.getElementById('client-logo-url').value = logo.website_url || '';
            document.getElementById('client-logo-status').value = String(logo.is_published);
            document.getElementById('client-logo-preset').value = '';
            
            const preview = document.getElementById('client-logo-preview');
            if (preview && logo.image) {
                preview.innerHTML = `<div style="font-size:0.75rem; color:var(--admin-text-light); margin-bottom:4px;">Current Logo:</div><img src="${logo.image}" style="max-width:100%; max-height:45px; object-fit:contain;">`;
                preview.style.display = 'block';
            }
            document.getElementById('client-logo-modal-title').textContent = `Edit Logo: ${logo.name}`;
            openModal('client-logo-modal');
            initIcons();
        } catch (err) {
            console.error(err);
        }
    };

    window.deleteClientLogo = async (id) => {
        if (confirm('Delete this client logo from the auto-scroll marquee?')) {
            try {
                const res = await fetch(`/api/client-logos/${id}`, { method: 'DELETE' });
                const data = await res.json();
                if (res.ok) {
                    fetchClientLogos();
                } else {
                    alert(data.error || 'Failed to delete client logo.');
                }
            } catch (err) {
                console.error(err);
            }
        }
    };

    const btnAddClientLogo = document.getElementById('btn-add-client-logo');
    if (btnAddClientLogo) {
        btnAddClientLogo.addEventListener('click', () => {
            document.getElementById('client-logo-form').reset();
            document.getElementById('client-logo-id').value = '';
            document.getElementById('client-logo-preset').value = '';
            const preview = document.getElementById('client-logo-preview');
            if (preview) {
                preview.innerHTML = '';
                preview.style.display = 'none';
            }
            document.getElementById('client-logo-modal-title').textContent = 'Add Client Logo';
            openModal('client-logo-modal');
        });
    }

    const setLogoPreset = (btnId, imgPath, defaultName) => {
        const btn = document.getElementById(btnId);
        if (btn) {
            btn.addEventListener('click', () => {
                const fileInput = document.getElementById('client-logo-file');
                if (fileInput) fileInput.value = '';
                document.getElementById('client-logo-preset').value = imgPath;
                if (!document.getElementById('client-logo-name').value) {
                    document.getElementById('client-logo-name').value = defaultName;
                }
                const preview = document.getElementById('client-logo-preview');
                if (preview) {
                    preview.innerHTML = `<div style="font-size:0.75rem; color:var(--admin-text-light); margin-bottom:4px;">Preset Selected:</div><img src="${imgPath}" style="max-width:100%; max-height:45px; object-fit:contain;">`;
                    preview.style.display = 'block';
                }
            });
        }
    };

    setLogoPreset('btn-preset-logo-apex', '/uploads/client_apex_solar.svg', 'Apex Solar EPC');
    setLogoPreset('btn-preset-logo-sunpeak', '/uploads/client_sunpeak.svg', 'SunPeak Energy');
    setLogoPreset('btn-preset-logo-nexus', '/uploads/client_nexus_power.svg', 'Nexus Power EPC');
    setLogoPreset('btn-preset-logo-solaria', '/uploads/client_solaria.svg', 'Solaria Global');
    setLogoPreset('btn-preset-logo-voltix', '/uploads/client_voltix.svg', 'Voltix Renewables');
    setLogoPreset('btn-preset-logo-terrawatt', '/uploads/client_terrawatt.svg', 'TerraWatt Engineering');

    const clientLogoFileInput = document.getElementById('client-logo-file');
    if (clientLogoFileInput) {
        clientLogoFileInput.addEventListener('change', () => {
            const file = clientLogoFileInput.files[0];
            if (file) {
                document.getElementById('client-logo-preset').value = '';
                const fileUrl = URL.createObjectURL(file);
                const preview = document.getElementById('client-logo-preview');
                if (preview) {
                    preview.innerHTML = `<div style="font-size:0.75rem; color:var(--admin-text-light); margin-bottom:4px;">Uploaded Preview:</div><img src="${fileUrl}" style="max-width:100%; max-height:45px; object-fit:contain;">`;
                    preview.style.display = 'block';
                }
            }
        });
    }

    const clientLogoForm = document.getElementById('client-logo-form');
    if (clientLogoForm) {
        clientLogoForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = clientLogoForm.querySelector('button[type="submit"]');
            const originalBtnHtml = submitBtn ? submitBtn.innerHTML : 'Save Partner Logo';

            try {
                if (submitBtn) {
                    submitBtn.disabled = true;
                    submitBtn.innerHTML = '<i data-lucide="loader-2" class="spin" style="width:14px;height:14px;vertical-align:middle;margin-right:6px;"></i> Optimizing & Saving...';
                    initIcons();
                }

                const id = document.getElementById('client-logo-id').value;
                const formData = new FormData(clientLogoForm);

                const fileInput = document.getElementById('client-logo-file');
                if (fileInput && fileInput.files && fileInput.files[0]) {
                    const originalFile = fileInput.files[0];
                    if (originalFile.type.startsWith('image/') && originalFile.type !== 'image/svg+xml') {
                        const compressed = await compressImageFile(originalFile, 800, 400, 0.9);
                        formData.set('image', compressed);
                    }
                }

                const url = id ? `/api/client-logos/${id}` : '/api/client-logos';
                const res = await fetch(url, {
                    method: 'POST',
                    body: formData
                });

                if (res.status === 401) {
                    alert('Your admin session has expired. Please log in again.');
                    window.location.href = '/admin/login';
                    return;
                }

                const result = await res.json();
                if (res.ok) {
                    closeModal('client-logo-modal');
                    fetchClientLogos();
                } else {
                    alert(result.error || 'Failed to save client logo.');
                }
            } catch (err) {
                console.error(err);
                alert('Network or server error while saving client logo: ' + (err.message || 'Error'));
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnHtml;
                    initIcons();
                }
            }
        });
    }

    // ==========================================
    // 10. HOME PAGE SETTINGS (HERO MEDIA & WHO WE ARE)
    // ==========================================
    let currentHeroMedia = '';
    let currentHomeImage = '';

    const showHeroAlert = (message, type = 'success') => {
        const box = document.getElementById('hero-media-alert-box');
        if (!box) return;
        box.textContent = message;
        if (type === 'success') {
            box.style.background = '#dcfce7';
            box.style.color = '#166534';
            box.style.border = '1px solid #bbf7d0';
        } else {
            box.style.background = '#fee2e2';
            box.style.color = '#991b1b';
            box.style.border = '1px solid #fecaca';
        }
        box.style.display = 'block';
        setTimeout(() => {
            if (box) box.style.display = 'none';
        }, 5500);
    };

    const isVideoUrl = (url) => {
        if (!url) return false;
        const clean = url.split('?')[0].toLowerCase();
        return clean.endsWith('.mp4') || clean.endsWith('.webm') || clean.endsWith('.mov') || clean.endsWith('.ogg') || clean.endsWith('.m4v');
    };

    const updateHeroMediaPreview = (src, isBlobVideo = null) => {
        const video = document.getElementById('hero-preview-video');
        const img = document.getElementById('hero-preview-img');
        const emptyNotice = document.getElementById('hero-media-empty-notice');
        const badge = document.getElementById('hero-media-status-badge');
        const pathDisplay = document.getElementById('hero-media-path-display');

        if (src && src.trim() !== '') {
            if (emptyNotice) emptyNotice.style.display = 'none';
            const isVid = isBlobVideo !== null ? isBlobVideo : isVideoUrl(src);

            if (isVid) {
                if (video) {
                    video.src = src;
                    video.style.display = 'block';
                    video.load();
                }
                if (img) img.style.display = 'none';
                if (badge) {
                    badge.textContent = 'Active Video';
                    badge.className = 'badge-status badge-published';
                }
            } else {
                if (img) {
                    img.src = src;
                    img.style.display = 'block';
                }
                if (video) {
                    video.pause();
                    video.src = '';
                    video.style.display = 'none';
                }
                if (badge) {
                    badge.textContent = 'Active Image';
                    badge.className = 'badge-status badge-published';
                }
            }
            if (pathDisplay) pathDisplay.textContent = 'Path: ' + src;
        } else {
            if (video) {
                video.pause();
                video.src = '';
                video.style.display = 'none';
            }
            if (img) {
                img.src = '';
                img.style.display = 'none';
            }
            if (emptyNotice) emptyNotice.style.display = 'flex';
            if (badge) {
                badge.textContent = 'No Media (Dark Theme)';
                badge.className = 'badge-status badge-draft';
            }
            if (pathDisplay) pathDisplay.textContent = 'No background media set (solid dark solar theme displayed)';
        }
        initIcons();
    };

    const showHomeAlert = (message, type = 'success') => {
        const box = document.getElementById('home-img-alert-box');
        if (!box) return;
        box.textContent = message;
        if (type === 'success') {
            box.style.background = '#dcfce7';
            box.style.color = '#166534';
            box.style.border = '1px solid #bbf7d0';
        } else {
            box.style.background = '#fee2e2';
            box.style.color = '#991b1b';
            box.style.border = '1px solid #fecaca';
        }
        box.style.display = 'block';
        setTimeout(() => {
            if (box) box.style.display = 'none';
        }, 4500);
    };

    const updateHomeImagePreview = (src) => {
        const img = document.getElementById('home-who-preview-img');
        const emptyNotice = document.getElementById('home-img-empty-notice');
        const badge = document.getElementById('home-img-status-badge');
        const pathDisplay = document.getElementById('home-img-path-display');

        if (src && src.trim() !== '') {
            if (img) {
                img.src = src;
                img.style.display = 'block';
            }
            if (emptyNotice) emptyNotice.style.display = 'none';
            if (badge) {
                badge.textContent = 'Active';
                badge.className = 'badge-status badge-published';
            }
            if (pathDisplay) pathDisplay.textContent = 'Path: ' + src;
        } else {
            if (img) {
                img.src = '';
                img.style.display = 'none';
            }
            if (emptyNotice) {
                emptyNotice.style.display = 'flex';
            }
            if (badge) {
                badge.textContent = 'No Image (Full-Width Text)';
                badge.className = 'badge-status badge-draft';
            }
            if (pathDisplay) pathDisplay.textContent = 'No image set (text will span full width on Home page)';
        }
        initIcons();
    };

    const fetchHomeSettings = async () => {
        try {
            const res = await fetch('/api/admin/home-settings');
            if (res.ok) {
                const data = await res.json();
                
                // 1. Hero background media
                currentHeroMedia = data.hero_bg_media || '';
                updateHeroMediaPreview(currentHeroMedia);
                document.querySelectorAll('.hero-preset-btn').forEach(btn => {
                    if (btn.getAttribute('data-preset') === currentHeroMedia) {
                        btn.classList.add('active-preset');
                    } else {
                        btn.classList.remove('active-preset');
                    }
                });

                // 2. Who We Are image
                currentHomeImage = data.who_we_are_image || '';
                updateHomeImagePreview(currentHomeImage);
                document.querySelectorAll('.home-preset-btn').forEach(btn => {
                    if (btn.getAttribute('data-preset') === currentHomeImage) {
                        btn.classList.add('active-preset');
                    } else {
                        btn.classList.remove('active-preset');
                    }
                });
            }
        } catch (err) {
            console.error('Error fetching home settings:', err);
        }
    };

    // --- Hero Preset button clicks ---
    document.querySelectorAll('.hero-preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const presetUrl = btn.getAttribute('data-preset');
            const presetInput = document.getElementById('hero-preset-input');
            const removeInput = document.getElementById('hero-remove-input');
            if (presetInput) presetInput.value = presetUrl;
            if (removeInput) removeInput.value = '0';
            const fileInput = document.getElementById('hero-media-file-input');
            if (fileInput) fileInput.value = '';

            document.querySelectorAll('.hero-preset-btn').forEach(b => b.classList.remove('active-preset'));
            btn.classList.add('active-preset');

            updateHeroMediaPreview(presetUrl);
            const badge = document.getElementById('hero-media-status-badge');
            if (badge) {
                badge.textContent = 'Preset Selected (Click Save)';
                badge.className = 'badge-status badge-draft';
            }
        });
    });

    // --- Hero File input preview ---
    const heroFileInput = document.getElementById('hero-media-file-input');
    if (heroFileInput) {
        heroFileInput.addEventListener('change', (e) => {
            const file = e.target.files && e.target.files[0];
            if (file) {
                const presetInput = document.getElementById('hero-preset-input');
                const removeInput = document.getElementById('hero-remove-input');
                if (presetInput) presetInput.value = '';
                if (removeInput) removeInput.value = '0';
                document.querySelectorAll('.hero-preset-btn').forEach(b => b.classList.remove('active-preset'));
                
                const isVideo = file.type.startsWith('video/') || /\.(mp4|webm|mov|ogg|m4v)$/i.test(file.name);
                const objectUrl = URL.createObjectURL(file);
                updateHeroMediaPreview(objectUrl, isVideo);

                const pathDisplay = document.getElementById('hero-media-path-display');
                if (pathDisplay) {
                    const sizeMb = (file.size / (1024 * 1024)).toFixed(2);
                    pathDisplay.textContent = `Selected: ${file.name} (${sizeMb} MB) - Ready to compress & upload`;
                }
                const badge = document.getElementById('hero-media-status-badge');
                if (badge) {
                    badge.textContent = (isVideo ? 'Video Ready' : 'Image Ready') + ' (Click Save)';
                    badge.className = 'badge-status badge-draft';
                }
            }
        });
    }

    // --- Hero Form submit ---
    const heroForm = document.getElementById('form-hero-media-settings');
    if (heroForm) {
        heroForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = document.getElementById('btn-save-hero-media');
            const originalBtnHtml = submitBtn ? submitBtn.innerHTML : '';
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i data-lucide="loader-2" class="spin" style="width:16px;height:16px;vertical-align:middle;margin-right:6px;"></i> Compressing & Uploading...';
                initIcons();
            }

            try {
                const formData = new FormData(heroForm);
                const res = await fetch('/api/admin/home-settings', {
                    method: 'POST',
                    body: formData
                });

                if (res.status === 401) {
                    alert('Your admin session has expired. Please log in again.');
                    window.location.href = '/admin/login';
                    return;
                }

                const result = await res.json();
                if (res.ok) {
                    currentHeroMedia = result.hero_bg_media || '';
                    updateHeroMediaPreview(currentHeroMedia);
                    showHeroAlert(result.message || 'Hero background media updated successfully!', 'success');
                    if (heroFileInput) heroFileInput.value = '';
                    const presetInput = document.getElementById('hero-preset-input');
                    if (presetInput) presetInput.value = '';
                    const removeInput = document.getElementById('hero-remove-input');
                    if (removeInput) removeInput.value = '0';
                    fetchHomeSettings();
                } else {
                    alert(result.error || 'Failed to update hero background media.');
                }
            } catch (err) {
                console.error(err);
                alert('An error occurred while saving: ' + (err.message || 'Network error'));
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnHtml;
                    initIcons();
                }
            }
        });
    }

    // --- Hero Reset to Default button ---
    const btnResetDefaultHero = document.getElementById('btn-reset-default-hero-media');
    if (btnResetDefaultHero) {
        btnResetDefaultHero.addEventListener('click', async () => {
            if (!confirm('Reset the Hero background media to the default Solar Drone Video?')) {
                return;
            }
            try {
                const formData = new FormData();
                formData.append('target', 'hero_bg');
                formData.append('preset_hero_media', '/uploads/hero_video.mp4');
                const res = await fetch('/api/admin/home-settings', {
                    method: 'POST',
                    body: formData
                });
                const result = await res.json();
                if (res.ok) {
                    currentHeroMedia = result.hero_bg_media;
                    updateHeroMediaPreview(currentHeroMedia);
                    showHeroAlert('Reset to default hero video successfully!', 'success');
                    fetchHomeSettings();
                } else {
                    alert(result.error || 'Failed to reset.');
                }
            } catch (err) {
                alert('Error resetting hero video: ' + err.message);
            }
        });
    }

    // --- Hero Remove Media button ---
    const btnRemoveHero = document.getElementById('btn-remove-hero-media');
    if (btnRemoveHero) {
        btnRemoveHero.addEventListener('click', async () => {
            if (!confirm('Are you sure you want to remove the Hero background media? The homepage hero will display the solid dark solar gradient.')) {
                return;
            }
            try {
                const formData = new FormData();
                formData.append('target', 'hero_bg');
                formData.append('remove_hero_media', '1');
                const res = await fetch('/api/admin/home-settings', {
                    method: 'POST',
                    body: formData
                });
                const result = await res.json();
                if (res.ok) {
                    currentHeroMedia = '';
                    updateHeroMediaPreview('');
                    showHeroAlert('Hero background media removed successfully.', 'success');
                    document.querySelectorAll('.hero-preset-btn').forEach(b => b.classList.remove('active-preset'));
                    if (heroFileInput) heroFileInput.value = '';
                    const presetInput = document.getElementById('hero-preset-input');
                    if (presetInput) presetInput.value = '';
                    const removeInput = document.getElementById('hero-remove-input');
                    if (removeInput) removeInput.value = '0';
                } else {
                    alert(result.error || 'Failed to remove media.');
                }
            } catch (err) {
                alert('Error removing hero media: ' + err.message);
            }
        });
    }

    // Preset button clicks for Who We Are
    document.querySelectorAll('.home-preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const presetUrl = btn.getAttribute('data-preset');
            const presetInput = document.getElementById('home-preset-input');
            const removeInput = document.getElementById('home-remove-input');
            if (presetInput) presetInput.value = presetUrl;
            if (removeInput) removeInput.value = '0';
            const fileInput = document.getElementById('home-img-file-input');
            if (fileInput) fileInput.value = '';

            document.querySelectorAll('.home-preset-btn').forEach(b => b.classList.remove('active-preset'));
            btn.classList.add('active-preset');

            updateHomeImagePreview(presetUrl);
            const badge = document.getElementById('home-img-status-badge');
            if (badge) {
                badge.textContent = 'Preset Selected (Click Save)';
                badge.className = 'badge-status badge-draft';
            }
        });
    });

    // File input change preview for Who We Are
    const homeFileInput = document.getElementById('home-img-file-input');
    if (homeFileInput) {
        homeFileInput.addEventListener('change', (e) => {
            const file = e.target.files && e.target.files[0];
            if (file) {
                const presetInput = document.getElementById('home-preset-input');
                const removeInput = document.getElementById('home-remove-input');
                if (presetInput) presetInput.value = '';
                if (removeInput) removeInput.value = '0';
                document.querySelectorAll('.home-preset-btn').forEach(b => b.classList.remove('active-preset'));
                
                const objectUrl = URL.createObjectURL(file);
                updateHomeImagePreview(objectUrl);
                const pathDisplay = document.getElementById('home-img-path-display');
                if (pathDisplay) pathDisplay.textContent = 'Selected: ' + file.name + ' (' + (file.size / 1024).toFixed(1) + ' KB)';
                const badge = document.getElementById('home-img-status-badge');
                if (badge) {
                    badge.textContent = 'File Ready (Click Save)';
                    badge.className = 'badge-status badge-draft';
                }
            }
        });
    }

    // Save / Update form submit for Who We Are
    const homeForm = document.getElementById('form-home-image-settings');
    if (homeForm) {
        homeForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitBtn = document.getElementById('btn-save-home-image');
            const originalBtnHtml = submitBtn ? submitBtn.innerHTML : '';
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i data-lucide="loader-2" class="spin" style="width:16px;height:16px;vertical-align:middle;margin-right:6px;"></i> Updating...';
                initIcons();
            }

            try {
                const formData = new FormData(homeForm);
                const res = await fetch('/api/admin/home-settings', {
                    method: 'POST',
                    body: formData
                });

                if (res.status === 401) {
                    alert('Your admin session has expired. Please log in again.');
                    window.location.href = '/admin/login';
                    return;
                }

                const result = await res.json();
                if (res.ok) {
                    currentHomeImage = result.who_we_are_image || '';
                    updateHomeImagePreview(currentHomeImage);
                    showHomeAlert(result.message || 'Featured image updated successfully!', 'success');
                    const fileInput = document.getElementById('home-img-file-input');
                    if (fileInput) fileInput.value = '';
                    const presetInput = document.getElementById('home-preset-input');
                    if (presetInput) presetInput.value = '';
                    const removeInput = document.getElementById('home-remove-input');
                    if (removeInput) removeInput.value = '0';
                    fetchHomeSettings();
                } else {
                    alert(result.error || 'Failed to update image.');
                }
            } catch (err) {
                console.error(err);
                alert('An error occurred while saving: ' + (err.message || 'Network error'));
            } finally {
                if (submitBtn) {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalBtnHtml;
                    initIcons();
                }
            }
        });
    }

    // Reset to Default button for Who We Are
    const btnResetDefault = document.getElementById('btn-reset-default-home-image');
    if (btnResetDefault) {
        btnResetDefault.addEventListener('click', async () => {
            if (!confirm('Reset the Who We Are section image to the default Commercial Solar featured image?')) {
                return;
            }
            try {
                const formData = new FormData();
                formData.append('preset_image', '/uploads/commercial_solar_featured.png');
                const res = await fetch('/api/admin/home-settings', {
                    method: 'POST',
                    body: formData
                });
                const result = await res.json();
                if (res.ok) {
                    currentHomeImage = result.who_we_are_image;
                    updateHomeImagePreview(currentHomeImage);
                    showHomeAlert('Reset to default image successfully!', 'success');
                    fetchHomeSettings();
                } else {
                    alert(result.error || 'Failed to reset.');
                }
            } catch (err) {
                alert('Error resetting image: ' + err.message);
            }
        });
    }

    // Remove Image button for Who We Are
    const btnRemoveHomeImg = document.getElementById('btn-remove-home-image');
    if (btnRemoveHomeImg) {
        btnRemoveHomeImg.addEventListener('click', async () => {
            if (!confirm('Are you sure you want to remove the image from the "Who We Are" section? The section text will span full-width without an image.')) {
                return;
            }
            try {
                const formData = new FormData();
                formData.append('remove_image', '1');
                const res = await fetch('/api/admin/home-settings', {
                    method: 'POST',
                    body: formData
                });
                const result = await res.json();
                if (res.ok) {
                    currentHomeImage = '';
                    updateHomeImagePreview('');
                    showHomeAlert('Image removed from Who We Are section.', 'success');
                    document.querySelectorAll('.home-preset-btn').forEach(b => b.classList.remove('active-preset'));
                    const fileInput = document.getElementById('home-img-file-input');
                    if (fileInput) fileInput.value = '';
                    const presetInput = document.getElementById('home-preset-input');
                    if (presetInput) presetInput.value = '';
                    const removeInput = document.getElementById('home-remove-input');
                    if (removeInput) removeInput.value = '0';
                } else {
                    alert(result.error || 'Failed to remove image.');
                }
            } catch (err) {
                alert('Error removing image: ' + err.message);
            }
        });
    }

    // --- INITIAL DATA LOAD ---
    // Default load is projects
    fetchProjects();
});



