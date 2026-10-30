const workFilters = [...document.querySelectorAll<HTMLButtonElement>('[data-work-filter]')];
const workEmpty = document.querySelector<HTMLElement>('[data-work-empty]');

workFilters.forEach(button => button.addEventListener('click', () => {
  workFilters.forEach(filter => filter.setAttribute('aria-pressed', String(filter === button)));
  if (workEmpty) workEmpty.textContent = button.dataset.emptyLabel ?? '';
}));
