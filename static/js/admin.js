// EarthX Designs - CMS Admin Panel Logic

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Icons
    const initIcons = () => {
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    };
    initIcons();

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
            case 'categories-tab':
                fetchCategories();
                break;
            case 'services-tab':
                fetchServiceCategories();
                fetchServices();
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
    document.getElementById('category-name').addEventListener('input', (e) => {
        const nameVal = e.target.value;
        document.getElementById('category-slug').value = nameVal.toLowerCase()
            .replace(/[^a-z0-9 -]/g, '')
            .replace(/\s+/g, '-')
            .replace(/-+/g, '-');
    });


    // --- PROJECTS LOGIC ---
    const fetchProjects = async () => {
        try {
            const res = await fetch('/api/projects');
            const data = await res.json();
            
            const tbody = document.getElementById('projects-table-body');
            tbody.innerHTML = '';
            
            let pubCount = 0;
            data.forEach(p => {
                if (p.status === 'published') pubCount++;
                
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><img src="${p.featured_image}" style="width:50px; height:35px; object-fit:cover; border-radius:4px;"></td>
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

    // Project form submit (Supports multipart uploads)
    document.getElementById('project-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('project-id').value;
        const formData = new FormData(e.target);
        
        const url = id ? `/api/projects/${id}` : '/api/projects';
        
        try {
            const res = await fetch(url, {
                method: 'POST', // Use POST for both insert and edit to support FormData upload seamlessly
                body: formData
            });
            const data = await res.json();
            
            if (res.ok) {
                closeModal('project-modal');
                fetchProjects();
            } else {
                alert(data.error || 'An error occurred.');
            }
        } catch (err) {
            console.error(err);
        }
    });

    document.getElementById('btn-add-project').addEventListener('click', () => {
        document.getElementById('project-form').reset();
        document.getElementById('project-id').value = '';
        document.getElementById('project-featured-preview').innerHTML = `<i data-lucide="image" style="width: 24px; height: 24px; color: var(--admin-text-light);"></i>`;
        document.getElementById('project-featured-image').required = true;
        document.getElementById('project-modal-title').textContent = 'Add Project';
        
        // Ensure categories are loaded
        fetchCategories().then(() => {
            openModal('project-modal');
        });
    });

    window.editProject = async (id) => {
        try {
            // First load categories
            await fetchCategories();
            
            // Fetch project details
            const res = await fetch(`/api/projects/${id}`);
            const p = await res.json();
            
            if (res.ok) {
                document.getElementById('project-id').value = p.id;
                document.getElementById('project-title').value = p.title;
                document.getElementById('project-category').value = p.category_id || '';
                document.getElementById('project-capacity').value = p.capacity;
                document.getElementById('project-location').value = p.location;
                document.getElementById('project-client').value = p.client_name || '';
                document.getElementById('project-date').value = p.completion_date;
                document.getElementById('project-status').value = p.status;
                document.getElementById('project-services').value = p.services_delivered;
                document.getElementById('project-description').value = p.description;
                
                // Show current featured image
                document.getElementById('project-featured-preview').innerHTML = `<img src="${p.featured_image}" alt="Featured preview">`;
                document.getElementById('project-featured-image').required = false; // Not required for editing
                
                document.getElementById('project-modal-title').textContent = 'Edit Project';
                openModal('project-modal');
            }
        } catch (err) {
            console.error(err);
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


    // --- PROJECT GALLERY MANAGER LOGIC ---
    const loadGalleryImages = async (projId) => {
        try {
            const res = await fetch(`/api/projects/${projId}`);
            const data = await res.json();
            
            const list = document.getElementById('gallery-manager-list');
            const emptyText = document.getElementById('gallery-empty-text');
            list.innerHTML = '';
            
            if (!data.gallery || data.gallery.length === 0) {
                emptyText.style.display = 'block';
            } else {
                emptyText.style.display = 'none';
                
                data.gallery.forEach(img => {
                    const div = document.createElement('div');
                    div.classList.add('gallery-preview-item');
                    div.innerHTML = `
                        <img src="${img.image_path}" alt="Gallery item">
                        <button class="gallery-preview-item-delete" onclick="deleteGalleryImage(${img.id}, ${projId})">&times;</button>
                        <input type="text" value="${img.caption || ''}" placeholder="Caption..." 
                               onblur="updateGalleryCaption(${img.id}, this.value)" 
                               style="width: 100%; font-size: 0.72rem; padding: 2px 4px; border: 1px solid var(--admin-border); margin-top: 4px; outline:none; border-radius:3px;">
                    `;
                    list.appendChild(div);
                });
            }
        } catch (err) {
            console.error(err);
        }
    };

    window.openGalleryManager = (projId) => {
        document.getElementById('gallery-project-id').value = projId;
        document.getElementById('gallery-manager-files').value = '';
        loadGalleryImages(projId);
        openModal('gallery-manager-modal');
    };

    // Upload more gallery drawings
    document.getElementById('btn-upload-more-gallery').addEventListener('click', async () => {
        const projId = document.getElementById('gallery-project-id').value;
        const fileInput = document.getElementById('gallery-manager-files');
        const files = fileInput.files;
        
        if (files.length === 0) {
            alert('Please select files to upload.');
            return;
        }
        
        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('gallery_images', files[i]);
        }
        
        try {
            const res = await fetch(`/api/projects/${projId}/gallery` || `/api/projects/${projId}`, {
                method: 'POST',
                body: formData
            });
            if (res.ok) {
                fileInput.value = '';
                loadGalleryImages(projId);
                fetchProjects(); // Update project table gallery count
            } else {
                alert('Upload failed.');
            }
        } catch (err) {
            console.error(err);
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
        const id = document.getElementById('blog-id').value;
        const formData = new FormData(e.target);
        
        const url = id ? `/api/blogs/${id}` : '/api/blogs';
        
        try {
            const res = await fetch(url, {
                method: 'POST', // Use POST for both insert and edit to support FormData upload seamlessly
                body: formData
            });
            const data = await res.json();
            
            if (res.ok) {
                closeModal('blog-modal');
                fetchBlogs();
            } else {
                alert(data.error || 'An error occurred.');
            }
        } catch (err) {
            console.error(err);
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


    // --- INITIAL DATA LOAD ---
    // Default load is projects
    fetchProjects();
});


    // --- SERVICE CATEGORIES LOGIC ---
    const fetchServiceCategories = async () => {
        try {
            const res = await fetch('/api/service-categories');
            const data = await res.json();
            
            const tbody = document.getElementById('service-categories-table-body');
            tbody.innerHTML = '';
            
            data.forEach(c => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${c.id}</td>
                    <td><strong>${c.name}</strong></td>
                    <td><code>/services/${c.slug}</code></td>
                    <td>
                        <div class="btn-action-group">
                            <button class="btn-action edit" onclick="editServiceCategory(${c.id})">
                                <i data-lucide="edit-3" style="width:14px; height:14px;"></i>
                            </button>
                            <button class="btn-action delete" onclick="deleteServiceCategory(${c.id})">
                                <i data-lucide="trash-2" style="width:14px; height:14px;"></i>
                            </button>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });
            initIcons();
            
            // Populate category select list in service modal
            const select = document.getElementById('service-category-select');
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
            console.error('Error fetching service categories:', err);
        }
    };

    document.getElementById('service-category-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('service-category-id').value;
        
        const data = {
            name: document.getElementById('service-category-name').value,
            slug: document.getElementById('service-category-slug').value,
            hero_heading: document.getElementById('service-category-hero-heading').value,
            hero_subtitle: document.getElementById('service-category-hero-subtitle').value,
            full_description: document.getElementById('service-category-full-description').value
        };
        
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/service-categories/${id}` : '/api/service-categories';
        
        try {
            const res = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            if (res.ok) {
                closeModal('service-category-modal');
                fetchServiceCategories();
            } else {
                const error = await res.json();
                alert(error.error || 'An error occurred.');
            }
        } catch (err) {
            console.error(err);
        }
    });

    document.getElementById('btn-add-service-category').addEventListener('click', () => {
        document.getElementById('service-category-form').reset();
        document.getElementById('service-category-id').value = '';
        document.getElementById('service-category-modal-title').textContent = 'Add Service Category';
        openModal('service-category-modal');
    });

    window.editServiceCategory = async (id) => {
        try {
            const res = await fetch('/api/service-categories');
            const categories = await res.json();
            const cat = categories.find(c => c.id === id);
            
            if (cat) {
                document.getElementById('service-category-id').value = cat.id;
                document.getElementById('service-category-name').value = cat.name;
                document.getElementById('service-category-slug').value = cat.slug;
                document.getElementById('service-category-hero-heading').value = cat.hero_heading || '';
                document.getElementById('service-category-hero-subtitle').value = cat.hero_subtitle || '';
                document.getElementById('service-category-full-description').value = cat.full_description || '';
                
                document.getElementById('service-category-modal-title').textContent = 'Edit Service Category';
                openModal('service-category-modal');
            }
        } catch (err) {
            console.error(err);
        }
    };

    window.deleteServiceCategory = async (id) => {
        if (!confirm('Are you sure you want to delete this service category? This will also un-publish related services.')) return;
        try {
            const res = await fetch(`/api/service-categories/${id}`, { method: 'DELETE' });
            if (res.ok) fetchServiceCategories();
        } catch (err) {
            console.error(err);
        }
    };

    // --- SERVICES LOGIC ---
    const fetchServices = async () => {
        try {
            const res = await fetch('/api/services');
            const data = await res.json();
            
            const tbody = document.getElementById('services-table-body');
            tbody.innerHTML = '';
            
            data.forEach(s => {
                const tr = document.createElement('tr');
                const statusHtml = s.is_published ? 
                    '<span class="badge" style="background-color:rgba(16,185,129,0.1); color:#10B981;">Published</span>' : 
                    '<span class="badge" style="background-color:var(--bg-light); color:var(--text-muted);">Draft</span>';
                
                tr.innerHTML = `
                    <td><i data-lucide="${s.icon || 'box'}" style="width:20px; height:20px; color:var(--primary);"></i></td>
                    <td><strong>${s.name}</strong></td>
                    <td>${s.category_name || s.category_id}</td>
                    <td>${statusHtml}</td>
                    <td>
                        <div class="btn-action-group">
                            <button class="btn-action edit" onclick="editService(${s.id})">
                                <i data-lucide="edit-3" style="width:14px; height:14px;"></i>
                            </button>
                            <button class="btn-action delete" onclick="deleteService(${s.id})">
                                <i data-lucide="trash-2" style="width:14px; height:14px;"></i>
                            </button>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });
            initIcons();
        } catch (err) {
            console.error('Error fetching services:', err);
        }
    };

    document.getElementById('service-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const id = document.getElementById('service-id').value;
        const formData = new FormData(e.target);
        
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/services/${id}` : '/api/services';
        
        try {
            const res = await fetch(url, {
                method: method,
                body: formData
            });
            
            if (res.ok) {
                closeModal('service-modal');
                fetchServices();
            } else {
                const error = await res.json();
                alert(error.error || 'An error occurred.');
            }
        } catch (err) {
            console.error(err);
        }
    });

    document.getElementById('btn-add-service').addEventListener('click', () => {
        document.getElementById('service-form').reset();
        document.getElementById('service-id').value = '';
        document.getElementById('service-modal-title').textContent = 'Add Service';
        openModal('service-modal');
    });

    window.editService = async (id) => {
        try {
            const res = await fetch('/api/services');
            const services = await res.json();
            const s = services.find(item => item.id === id);
            
            if (s) {
                document.getElementById('service-id').value = s.id;
                document.getElementById('service-name').value = s.name;
                document.getElementById('service-category-select').value = s.category_id;
                document.getElementById('service-slug').value = s.slug;
                document.getElementById('service-icon').value = s.icon;
                document.getElementById('service-short-description').value = s.short_description;
                document.getElementById('service-full-description').value = s.full_description || '';
                document.getElementById('service-is-published').value = s.is_published;
                
                document.getElementById('service-modal-title').textContent = 'Edit Service';
                openModal('service-modal');
            }
        } catch (err) {
            console.error(err);
        }
    };

    window.deleteService = async (id) => {
        if (!confirm('Are you sure you want to delete this service?')) return;
        try {
            const res = await fetch(`/api/services/${id}`, { method: 'DELETE' });
            if (res.ok) fetchServices();
        } catch (err) {
            console.error(err);
        }
    };
