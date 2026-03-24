/**
 * Trapp Family Farm – vanilla JS slideshow for .slideshow-artifact
 * Auto-advances; dots and prev/next for control. No dependencies.
 */
(function () {
  'use strict';

  var INTERVAL_MS = 5000;

  function findSlideshows() {
    return document.querySelectorAll('.slideshow-artifact');
  }

  function getSlides(container) {
    var track = container.querySelector('.slideshow-track');
    if (!track) return [];
    return Array.prototype.slice.call(track.querySelectorAll('.slide'));
  }

  function goTo(slideshow, index) {
    var slides = getSlides(slideshow);
    if (!slides.length) return;
    var n = slides.length;
    index = ((index % n) + n) % n;
    slideshow.dataset.current = index;

    slides.forEach(function (slide, i) {
      slide.classList.toggle('is-active', i === index);
      slide.setAttribute('aria-hidden', i !== index);
    });

    var dots = slideshow.querySelectorAll('.slideshow-dot');
    dots.forEach(function (dot, i) {
      dot.classList.toggle('is-active', i === index);
      dot.setAttribute('aria-current', i === index ? 'true' : 'false');
    });
  }

  function next(slideshow) {
    var slides = getSlides(slideshow);
    if (!slides.length) return;
    var current = parseInt(slideshow.dataset.current || '0', 10);
    goTo(slideshow, current + 1);
    resetTimer(slideshow);
  }

  function prev(slideshow) {
    var slides = getSlides(slideshow);
    if (!slides.length) return;
    var current = parseInt(slideshow.dataset.current || '0', 10);
    goTo(slideshow, current - 1);
    resetTimer(slideshow);
  }

  var timers = {};
  function startTimer(slideshow) {
    stopTimer(slideshow);
    timers[slideshow] = setInterval(function () { next(slideshow); }, INTERVAL_MS);
  }
  function stopTimer(slideshow) {
    if (timers[slideshow]) clearInterval(timers[slideshow]);
    timers[slideshow] = null;
  }
  function resetTimer(slideshow) {
    startTimer(slideshow);
  }

  function buildDots(slideshow, count) {
    var nav = slideshow.querySelector('.slideshow-nav');
    if (!nav || nav.querySelector('.slideshow-dots')) return;
    var dotsEl = document.createElement('div');
    dotsEl.className = 'slideshow-dots';
    dotsEl.setAttribute('role', 'tablist');
    dotsEl.setAttribute('aria-label', 'Slide navigation');
    for (var i = 0; i < count; i++) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'slideshow-dot' + (i === 0 ? ' is-active' : '');
      btn.setAttribute('aria-label', 'Go to slide ' + (i + 1));
      btn.setAttribute('aria-current', i === 0 ? 'true' : 'false');
      btn.setAttribute('role', 'tab');
      (function (idx) {
        btn.addEventListener('click', function () {
          goTo(slideshow, idx);
          resetTimer(slideshow);
        });
      })(i);
      dotsEl.appendChild(btn);
    }
    nav.insertBefore(dotsEl, nav.firstChild);
  }

  function initSlideshow(slideshow) {
    var slides = getSlides(slideshow);
    if (!slides.length) return;

    slideshow.dataset.current = '0';
    slides.forEach(function (slide, i) {
      slide.classList.toggle('is-active', i === 0);
      slide.setAttribute('aria-hidden', i !== 0);
    });

    var nav = slideshow.querySelector('.slideshow-nav');
    if (nav) {
      buildDots(slideshow, slides.length);
      var prevBtn = nav.querySelector('.slideshow-prev');
      var nextBtn = nav.querySelector('.slideshow-next');
      if (prevBtn) prevBtn.addEventListener('click', function () { prev(slideshow); });
      if (nextBtn) nextBtn.addEventListener('click', function () { next(slideshow); });
    }

    slideshow.addEventListener('mouseenter', function () { stopTimer(slideshow); });
    slideshow.addEventListener('mouseleave', function () { startTimer(slideshow); });
    startTimer(slideshow);
  }

  function init() {
    findSlideshows().forEach(initSlideshow);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
