// EarthX Designs - Public Frontend Scripting

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Lucide Icons
    const initIcons = () => {
        if (typeof lucide !== 'undefined') {
            lucide.createIcons();
        }
    };
    initIcons();
    window.addEventListener('load', initIcons);

    // Hero Background Video Immediate Playback
    const heroVideo = document.querySelector('.hero-video-bg');
    if (heroVideo) {
        heroVideo.muted = true;
        const playPromise = heroVideo.play();
        if (playPromise !== undefined) {
            playPromise.catch(() => {});
        }
    }

    // 2. Navbar Scroll Behavior
    const navbar = document.getElementById('navbar');
    if (navbar) {
        const handleScroll = () => {
            if (window.scrollY > 20) {
                navbar.classList.add('scrolled');
            } else {
                navbar.classList.remove('scrolled');
            }
        };
        // Initial check and scroll event
        handleScroll();
        window.addEventListener('scroll', handleScroll);
    }

    // 3. Mobile Navigation Toggle Menu & Submenu Controller (Mobile Only)
    const navToggle = document.getElementById('nav-toggle');
    const mobileNavDrawer = document.getElementById('mobile-nav-drawer');
    const navBackdrop = document.getElementById('nav-backdrop');
    const mobileNavClose = document.getElementById('mobile-nav-close');
    const submenuBackBtn = document.getElementById('submenu-back-btn');
    const submenuCloseBtn = document.getElementById('submenu-close-btn');
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

        // Dedicated Mobile Nav Close Button
        if (mobileNavClose) {
            mobileNavClose.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                closeNavMenu();
            });
        }

        // Submenu Back Button (Returns from sliding submenu panel back to main mobile drawer)
        if (submenuBackBtn && mobileServicesDropdown) {
            submenuBackBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                mobileServicesDropdown.classList.remove('expanded');
                if (servicesMenuTrigger) servicesMenuTrigger.setAttribute('aria-expanded', 'false');
            });
        }

        // Submenu Close Button (Closes entire mobile navigation immediately)
        if (submenuCloseBtn) {
            submenuCloseBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                closeNavMenu();
            });
        }

        // Services Menu Trigger on Mobile (Toggles sliding sub-panel)
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
        
        // Close menu when clicking outside mobile drawer
        document.addEventListener('click', (e) => {
            if (mobileNavDrawer.classList.contains('active') && !navToggle.contains(e.target) && !mobileNavDrawer.contains(e.target)) {
                closeNavMenu();
            }
        });

        // Close on ESC key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && mobileNavDrawer.classList.contains('active')) {
                if (mobileServicesDropdown && mobileServicesDropdown.classList.contains('expanded')) {
                    mobileServicesDropdown.classList.remove('expanded');
                    if (servicesMenuTrigger) servicesMenuTrigger.setAttribute('aria-expanded', 'false');
                } else {
                    closeNavMenu();
                }
            }
        });
        
        // Navigation links inside mobile drawer close the drawer upon click
        const links = mobileNavDrawer.querySelectorAll('a');
        links.forEach(link => {
            link.addEventListener('click', closeNavMenu);
        });
    }

    // Optimized speculative prefetching with hover debouncing to prevent server congestion
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
            // Wait 180ms of steady hover before prefetching to avoid storming the server during rapid mouse sweeps across dropdown items
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

    // 4. Testimonials Slideshow/Carousel
    const track = document.querySelector('.testimonial-track');
    if (track) {
        const slides = Array.from(track.children);
        const dotsContainer = document.querySelector('.carousel-dots');
        let currentIdx = 0;
        let slideInterval;

        // Create navigation dots
        slides.forEach((_, idx) => {
            const dot = document.createElement('div');
            dot.classList.add('dot');
            if (idx === 0) dot.classList.add('active');
            dot.addEventListener('click', () => {
                goToSlide(idx);
                resetAutoplay();
            });
            dotsContainer.appendChild(dot);
        });

        const dots = Array.from(dotsContainer.children);

        const goToSlide = (idx) => {
            currentIdx = idx;
            track.style.transform = `translateX(-${idx * 100}%)`;
            dots.forEach(d => d.classList.remove('active'));
            dots[idx].classList.add('active');
        };

        const nextSlide = () => {
            currentIdx = (currentIdx + 1) % slides.length;
            goToSlide(currentIdx);
        };

        const startAutoplay = () => {
            slideInterval = setInterval(nextSlide, 6000);
        };

        const resetAutoplay = () => {
            clearInterval(slideInterval);
            startAutoplay();
        };

        // Initialize autoplay
        startAutoplay();

        // Support swipe/drag on mobile
        let startX = 0;
        let isDragging = false;

        track.addEventListener('touchstart', (e) => {
            startX = e.touches[0].clientX;
            isDragging = true;
            clearInterval(slideInterval);
        }, { passive: true });

        track.addEventListener('touchend', (e) => {
            if (!isDragging) return;
            const diffX = e.changedTouches[0].clientX - startX;
            if (Math.abs(diffX) > 50) {
                if (diffX > 0) {
                    // swipe right (prev)
                    const prevIdx = (currentIdx - 1 + slides.length) % slides.length;
                    goToSlide(prevIdx);
                } else {
                    // swipe left (next)
                    const nextIdx = (currentIdx + 1) % slides.length;
                    goToSlide(nextIdx);
                }
            }
            isDragging = false;
            startAutoplay();
        }, { passive: true });
    }

    // 5. Scroll-Reveal Observer with Smooth Staggering
    const revealTargets = document.querySelectorAll('.reveal-on-scroll, .section-header, .service-card, .project-card, .feature-box, .why-card');
    if ('IntersectionObserver' in window && revealTargets.length > 0) {
        const revealObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealed');
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.08,
            rootMargin: '0px 0px -30px 0px'
        });

        revealTargets.forEach(el => {
            el.classList.add('reveal-on-scroll');
            const parent = el.parentElement;
            if (parent) {
                const siblings = Array.from(parent.children);
                const siblingIdx = siblings.indexOf(el);
                if (siblingIdx > 0 && siblingIdx <= 4) {
                    el.classList.add(`delay-${Math.min(siblingIdx, 4)}`);
                }
            }
            revealObserver.observe(el);
        });
    } else {
        revealTargets.forEach(el => el.classList.add('revealed'));
    }

    // 6. Smooth Number Counter for Stats on Scroll
    const statNumbers = document.querySelectorAll('.stat-number');
    if (statNumbers.length > 0 && 'IntersectionObserver' in window) {
        const statsObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const el = entry.target;
                    const text = el.textContent.trim();
                    const match = text.match(/^(\d+)(.*)$/);
                    if (match) {
                        const targetNum = parseInt(match[1], 10);
                        const suffix = match[2] || '';
                        const duration = 1200;
                        const startTime = performance.now();
                        
                        const updateNumber = (currentTime) => {
                            const elapsed = currentTime - startTime;
                            const progress = Math.min(elapsed / duration, 1);
                            const easeOutCubic = 1 - Math.pow(1 - progress, 3);
                            const currentVal = Math.floor(easeOutCubic * targetNum);
                            el.textContent = currentVal + suffix;
                            
                            if (progress < 1) {
                                requestAnimationFrame(updateNumber);
                            } else {
                                el.textContent = text;
                            }
                        };
                        requestAnimationFrame(updateNumber);
                    }
                    observer.unobserve(el);
                }
            });
        }, { threshold: 0.3 });

        statNumbers.forEach(s => statsObserver.observe(s));
    }
});
