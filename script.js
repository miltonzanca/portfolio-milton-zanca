// A página principal sempre começa no topo. Links com âncora continuam funcionando.
if ('scrollRestoration' in window.history) {
  window.history.scrollRestoration = 'manual';
}

function resetInitialScroll() {
  if (window.location.hash) return;

  const previousBehavior = document.documentElement.style.scrollBehavior;
  document.documentElement.style.scrollBehavior = 'auto';
  window.scrollTo(0, 0);

  window.setTimeout(() => {
    window.scrollTo(0, 0);
    document.documentElement.style.scrollBehavior = previousBehavior;
  }, 0);
}

window.addEventListener('DOMContentLoaded', resetInitialScroll);
window.addEventListener('pageshow', resetInitialScroll);

document.getElementById('year').textContent = new Date().getFullYear();

const glow = document.querySelector('.cursor-glow');
if (glow) {
  window.addEventListener('pointermove', (event) => {
    glow.style.transform = `translate(${event.clientX - 180}px, ${event.clientY - 180}px)`;
  });
}

const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) entry.target.classList.add('is-visible');
  });
}, { threshold: 0.12 });

document.querySelectorAll('.project-card, .approach li').forEach((item) => observer.observe(item));

const dashboardPreviews = document.querySelectorAll('[data-dashboard-preview]');

function fitDashboardPreviews() {
  dashboardPreviews.forEach((preview) => {
    const frame = preview.querySelector('iframe');
    if (!frame) return;

    const sourceWidth = Number(preview.dataset.sourceWidth);
    const maximumScale = Number(preview.dataset.maxScale);
    if (!sourceWidth || !maximumScale) return;

    const scale = Math.min(maximumScale, preview.clientWidth / sourceWidth);
    const renderedWidth = sourceWidth * scale;

    frame.style.width = `${sourceWidth}px`;
    frame.style.height = `${preview.clientHeight / scale}px`;
    frame.style.transform = `scale(${scale})`;
    frame.style.left = `${Math.max(0, (preview.clientWidth - renderedWidth) / 2)}px`;
  });
}

fitDashboardPreviews();

if ('ResizeObserver' in window) {
  const dashboardPreviewObserver = new ResizeObserver(fitDashboardPreviews);
  dashboardPreviews.forEach((preview) => dashboardPreviewObserver.observe(preview));
} else {
  window.addEventListener('resize', fitDashboardPreviews);
}
