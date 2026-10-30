const search = document.querySelector<HTMLInputElement>('#article-search');
const typeButtons = [...document.querySelectorAll<HTMLButtonElement>('[data-type]')];
const empty = document.querySelector<HTMLElement>('[data-library-empty]');
const noMatches = document.querySelector<HTMLElement>('[data-filter-empty]');
const clear = document.querySelector<HTMLButtonElement>('.clear-filters');
const topicButtons = [...document.querySelectorAll<HTMLButtonElement>('[data-topic]')];
const articles = [...document.querySelectorAll<HTMLElement>('.article-entry')];
const emptySection = document.querySelector<HTMLElement>('.writing-empty');
let type = 'all';
let topic = '';
const typeNavigation = document.querySelector<HTMLElement>('.writing-types');
function positionIndicator() {
  const selected = typeButtons.find(button => button.dataset.type === type);
  if (selected && typeNavigation) {
    typeNavigation.style.setProperty('--filter-left', `${selected.offsetLeft}px`);
    typeNavigation.style.setProperty('--filter-width', `${selected.offsetWidth}px`);
  }
}

function update() {
  const query = search?.value.trim().toLocaleLowerCase() ?? '';
  const filtered = type !== 'all' || Boolean(query) || Boolean(topic);
  let visible = 0;
  articles.forEach(article => {
    const matches = (type === 'all' || article.dataset.kind === type)
      && (!topic || JSON.parse(article.dataset.topics!).includes(topic))
      && (!query || article.dataset.search?.toLocaleLowerCase().includes(query));
    article.hidden = !matches;
    if (matches) visible++;
  });
  if (emptySection) emptySection.hidden = visible > 0;
  if (empty) empty.hidden = filtered || articles.length > 0;
  if (noMatches) noMatches.hidden = !filtered || visible > 0;
  if (clear) clear.hidden = !filtered;
  typeButtons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.type === type)));
  topicButtons.forEach(button => button.setAttribute('aria-pressed', String(button.dataset.topic === topic)));
  positionIndicator();
}
typeButtons.forEach(button => button.addEventListener('click', () => { type = button.dataset.type!; update(); }));
search?.addEventListener('input', update);
search?.form?.addEventListener('submit', event => event.preventDefault());
topicButtons.forEach(button => button.addEventListener('click', () => { topic = topic === button.dataset.topic ? '' : button.dataset.topic!; update(); }));
clear?.addEventListener('click', () => { type = 'all'; topic = ''; if (search) search.value = ''; update(); search?.focus(); });
addEventListener('resize', positionIndicator);
document.fonts.ready.then(positionIndicator);
positionIndicator();

const searchToggle = document.querySelector<HTMLButtonElement>('[data-search-toggle]');
const searchPanel = document.querySelector<HTMLElement>('#writing-search-panel');
searchToggle?.addEventListener('click', () => {
  if (!searchPanel) return;
  searchPanel.hidden = !searchPanel.hidden;
  searchToggle.setAttribute('aria-expanded', String(!searchPanel.hidden));
  if (!searchPanel.hidden) search?.focus();
});
