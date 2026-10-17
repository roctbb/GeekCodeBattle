(() => {
  let theme = 'system';
  try { theme = localStorage.getItem('codebattle:theme') || 'system'; } catch {}
  if (theme !== 'light' && theme !== 'dark') theme = typeof matchMedia === 'function' && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  document.documentElement.dataset.theme = theme;
  document.documentElement.dataset.bsTheme = theme;
  document.documentElement.style.colorScheme = theme;
})();
