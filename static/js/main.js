// EarthX Designs - Public Frontend Scripting

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Lucide Icons
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
    }

    // 2. Header & Navbar Scroll Behavior
    const siteHeader = document.getElementById('site-header');
    const navbar = document.getElementById('navbar');
    
    const handleScroll = () => {
        const isScrolled = window.scrollY > 25;
        if (siteHeader) {
            siteHeader.classList.toggle('scrolled', isScrolled);
        }
        if (navbar) {
            navbar.classList.toggle('scrolled', isScrolled);
        }
    };
    handleScroll();
    window.addEventListener('scroll', handleScroll, { passive: true });

    // 2b. Modern Scroll Reveal Observer
    const revealElements = document.querySelectorAll('.reveal-on-scroll');
    if ('IntersectionObserver' in window && revealElements.length > 0) {
        const revealObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('revealed');
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.12,
            rootMargin: '0px 0px -40px 0px'
        });

        revealElements.forEach(el => revealObserver.observe(el));
    } else {
        // Fallback for older browsers
        revealElements.forEach(el => el.classList.add('revealed'));
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
});
