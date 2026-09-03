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

    // 3. Mobile Navigation Toggle Menu
    const navToggle = document.getElementById('nav-toggle');
    const navLinks = document.getElementById('nav-links');
    if (navToggle && navLinks) {
        navToggle.addEventListener('click', () => {
            navToggle.classList.toggle('active');
            navLinks.classList.toggle('active');
        });
        
        // Close menu when clicking outside or on links
        document.addEventListener('click', (e) => {
            if (!navToggle.contains(e.target) && !navLinks.contains(e.target)) {
                navToggle.classList.remove('active');
                navLinks.classList.remove('active');
            }
        });
        
        const links = navLinks.querySelectorAll('a:not(.dropdown-toggle)');
        links.forEach(link => {
            link.addEventListener('click', () => {
                navToggle.classList.remove('active');
                navLinks.classList.remove('active');
            });
        });

        const dropdownToggles = document.querySelectorAll('.dropdown-toggle');
        dropdownToggles.forEach(toggle => {
            toggle.addEventListener('click', (e) => {
                if (window.innerWidth <= 768) {
                    e.preventDefault();
                    const parent = toggle.closest('.nav-dropdown');
                    parent.classList.toggle('expanded');
                    
                    const isExpanded = parent.classList.contains('expanded');
                    toggle.setAttribute('aria-expanded', isExpanded);
                }
            });
        });
    }

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
