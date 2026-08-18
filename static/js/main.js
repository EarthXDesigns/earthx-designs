// EarthX Designs - Public Frontend Scripting

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Lucide Icons
    if (typeof lucide !== 'undefined') {
        lucide.createIcons();
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
});
