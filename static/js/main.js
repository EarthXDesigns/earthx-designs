// EarthX Designs - "Fabrica" Studio Interaction Script

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Lucide Icons
    const initIcons = () => {
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    };
    initIcons();
    window.addEventListener('load', initIcons);

    // 2. Hero Background Video Immediate Playback
    const heroVideo = document.querySelector('.hero-video-bg');
    if (heroVideo && heroVideo.tagName === 'VIDEO') {
        heroVideo.muted = true;
        const playPromise = heroVideo.play();
        if (playPromise !== undefined) {
            playPromise.catch(() => {});
        }
    }

    // 3. Navbar Scroll Class Toggle
    const navbar = document.getElementById('navbar');
    if (navbar) {
        const handleScroll = () => {
            if (window.scrollY > 20) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        };
        handleScroll();
        window.addEventListener('scroll', handleScroll, { passive: true });
    }

    // 4. Mobile Navigation Drawer Controller (Preserves all selectors for tests)
    const navToggle = document.getElementById('nav-toggle');
    const mobileNavDrawer = document.getElementById('mobile-nav-drawer');
    const navBackdrop = document.getElementById('nav-backdrop');
    const mobileNavClose = document.getElementById('mobile-nav-close');
    const servicesMenuTrigger = document.getElementById('services-menu-trigger');
    const mobileServicesDropdown = document.getElementById('mobile-services-dropdown');

    const closeNavMenu = () => {
        if (navToggle) navToggle.classList.remove('active');
        if (mobileNavDrawer) mobileNavDrawer.classList.remove('active');
        if (navBackdrop) navBackdrop.classList.remove('active');
        document.body.classList.remove('nav-open');
        if (mobileServicesDropdown) {
            mobileServicesDropdown.classList.remove('expanded');
        }
        if (servicesMenuTrigger) {
            servicesMenuTrigger.setAttribute('aria-expanded', 'false');
        }
    };

    if (navToggle && mobileNavDrawer) {
        navToggle.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = mobileNavDrawer.classList.toggle('active');
            navToggle.classList.toggle('active', isOpen);
            if (navBackdrop) navBackdrop.classList.toggle('active', isOpen);
            document.body.classList.toggle('nav-open', isOpen);
        });

        if (mobileNavClose) {
            mobileNavClose.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                closeNavMenu();
            });
        }

        if (servicesMenuTrigger && mobileServicesDropdown) {
            servicesMenuTrigger.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const isExpanded = mobileServicesDropdown.classList.toggle('expanded');
                servicesMenuTrigger.setAttribute('aria-expanded', isExpanded ? 'true' : 'false');
            });
        }

        if (navBackdrop) {
            navBackdrop.addEventListener('click', closeNavMenu);
        }

        document.addEventListener('click', (e) => {
            if (mobileNavDrawer.classList.contains('active') && !navToggle.contains(e.target) && !mobileNavDrawer.contains(e.target)) {
                closeNavMenu();
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && mobileNavDrawer.classList.contains('active')) {
                closeNavMenu();
            }
        });

        const links = mobileNavDrawer.querySelectorAll('a');
        links.forEach(link => {
            link.addEventListener('click', closeNavMenu);
        });
    }

    // 5. Portfolio Matrix Filter Chips Controller
    const filterContainer = document.getElementById('portfolio-filter-chips');
    if (filterContainer) {
        const filterBtns = filterContainer.querySelectorAll('.filter-chip');
        const projectCards = document.querySelectorAll('.viewport-project-card');

        filterBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                filterBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                const filter = btn.getAttribute('data-filter');
                projectCards.forEach(card => {
                    const cat = card.getAttribute('data-category') || '';
                    if (filter === 'all') {
                        card.style.display = 'flex';
                    } else if (filter === 'ground' && (cat.includes('ground') || cat.includes('utility'))) {
                        card.style.display = 'flex';
                    } else if (filter === '3d' && (cat.includes('3d') || cat.includes('render') || cat.includes('visualization'))) {
                        card.style.display = 'flex';
                    } else if (filter === 'rooftop' && (cat.includes('roof') || cat.includes('commercial') || cat.includes('residential'))) {
                        card.style.display = 'flex';
                    } else if (filter === 'sld' && (cat.includes('sld') || cat.includes('schematic') || cat.includes('electrical'))) {
                        card.style.display = 'flex';
                    } else {
                        card.style.display = 'none';
                    }
                });
            });
        });
    }

    // 6. High-Conversion Intake Engine Funnel (Form Controller)
    const intakeForm = document.getElementById('intake-rfp-form') || document.getElementById('contact-inquiry-form');
    if (intakeForm) {
        // Step 1: Scale Chips Selection
        const scaleChips = document.querySelectorAll('#scale-chips .chip-btn');
        const projectTypeInput = document.getElementById('form-project-type') || document.getElementById('project_type');
        let selectedScale = '<5 MW C&I';

        scaleChips.forEach(chip => {
            chip.addEventListener('click', () => {
                scaleChips.forEach(c => c.classList.remove('active'));
                chip.classList.add('active');
                selectedScale = chip.getAttribute('data-scale');
                if (projectTypeInput) {
                    projectTypeInput.value = selectedScale;
                }
            });
        });

        // Step 2: Multi-select Checkbox Pills
        const multiPills = document.querySelectorAll('#deliverable-pills .multi-pill');
        multiPills.forEach(pill => {
            const checkbox = pill.querySelector('input[type="checkbox"]');
            pill.addEventListener('click', (e) => {
                if (e.target !== checkbox) {
                    checkbox.checked = !checkbox.checked;
                }
                pill.classList.toggle('active', checkbox.checked);
            });
        });

        // Step 3: Direct File Upload Drag & Drop
        const dropzone = document.getElementById('intake-dropzone');
        const fileInput = document.getElementById('site-file-input');
        const fileNotice = document.getElementById('file-chosen-notice');

        if (dropzone && fileInput) {
            ['dragenter', 'dragover'].forEach(eventName => {
                dropzone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    dropzone.classList.add('dragover');
                });
            });

            ['dragleave', 'drop'].forEach(eventName => {
                dropzone.addEventListener(eventName, (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    dropzone.classList.remove('dragover');
                });
            });

            dropzone.addEventListener('drop', (e) => {
                const dt = e.dataTransfer;
                const files = dt.files;
                if (files.length > 0) {
                    fileInput.files = files;
                    updateFileNotice(files[0].name);
                }
            });

            fileInput.addEventListener('change', () => {
                if (fileInput.files.length > 0) {
                    updateFileNotice(fileInput.files[0].name);
                }
            });

            function updateFileNotice(fileName) {
                if (fileNotice) {
                    fileNotice.innerHTML = `✓ Staged for scoping: <strong>${fileName}</strong>`;
                }
            }
        }

        // Form Submit Handler: Enrich message body with structured RFP parameters
        intakeForm.addEventListener('submit', () => {
            const messageEl = intakeForm.querySelector('#intake-message') || intakeForm.querySelector('#message');
            const ndaToggle = document.getElementById('nda-toggle-checkbox');
            
            // Gather selected deliverables
            const checkedDeliverables = [];
            intakeForm.querySelectorAll('#deliverable-pills input[type="checkbox"]:checked').forEach(cb => {
                checkedDeliverables.push(cb.value);
            });

            const stagedFile = fileInput && fileInput.files.length > 0 ? fileInput.files[0].name : 'None attached';
            const ndaStatus = ndaToggle && ndaToggle.checked ? 'YES (Mutual NDA Requested)' : 'Standard';

            if (messageEl) {
                const originalText = messageEl.value.trim();
                const rfpMetadata = `
[RFP CONFIGURATION]
- Project Scale: ${selectedScale}
- Deliverables Required: ${checkedDeliverables.join(', ') || 'Not specified'}
- Mutual NDA Requested: ${ndaStatus}
- Staged Site File: ${stagedFile}
----------------------------------------
CLIENT SCOPE DETAILS:
`;
                // Only prepend if not already prepended
                if (!originalText.includes('[RFP CONFIGURATION]')) {
                    messageEl.value = rfpMetadata + originalText;
                }
            }
        });
    }

    // 7. Live Time Zone Indicator (UTC+5:30 IST)
    const timeIndicator = document.getElementById('live-time-indicator');
    if (timeIndicator) {
        const updateISTTime = () => {
            const now = new Date();
            // Calculate IST time (UTC + 5:30)
            const utcTime = now.getTime() + (now.getTimezoneOffset() * 60000);
            const istTime = new Date(utcTime + (3600000 * 5.5));
            const hours = String(istTime.getHours()).padStart(2, '0');
            const minutes = String(istTime.getMinutes()).padStart(2, '0');
            timeIndicator.textContent = `UTC+5:30 [IST ${hours}:${minutes}] DESK ACTIVE`;
        };
        updateISTTime();
        setInterval(updateISTTime, 30000);
    }

    // 8. Exclusive Accordion Rows (Fabrica Services Engine)
    const accordionRows = document.querySelectorAll('.fabrica-accordion-row');
    if (accordionRows.length > 0) {
        accordionRows.forEach(row => {
            row.addEventListener('toggle', () => {
                if (row.open) {
                    accordionRows.forEach(otherRow => {
                        if (otherRow !== row && otherRow.open) {
                            otherRow.removeAttribute('open');
                        }
                    });
                }
            });
        });
    }

    // 9. Speculative Link Prefetching for Ultra-Fast Page Navigation
    const prefetchCache = new Set();
    const prefetchUrl = (url) => {
        if (!url || url.startsWith('#') || url.startsWith('javascript') || url.startsWith('/admin') || url.startsWith('/api') || prefetchCache.has(url)) return;
        prefetchCache.add(url);
        const linkElem = document.createElement('link');
        linkElem.rel = 'prefetch';
        linkElem.href = url;
        document.head.appendChild(linkElem);
    };

    const linkHoverTimers = new Map();
    document.querySelectorAll('a[href^="/"]').forEach(a => {
        const href = a.getAttribute('href');
        if (!href || href.startsWith('/admin') || href.startsWith('/api')) return;

        a.addEventListener('mouseenter', () => {
            const timer = setTimeout(() => {
                prefetchUrl(href);
            }, 180);
            linkHoverTimers.set(a, timer);
        }, { passive: true });

        a.addEventListener('mouseleave', () => {
            const timer = linkHoverTimers.get(a);
            if (timer) {
                clearTimeout(timer);
                linkHoverTimers.delete(a);
            }
        }, { passive: true });

        a.addEventListener('touchstart', () => prefetchUrl(href), { passive: true });
    });
});
