/** Localize the renderer's generated footnote labels with the edition language. */
export default function readingFootnotes() {
  return (tree, file) => {
    const chinese = file.data.astro?.frontmatter?.lang === 'zh';
    function visit(node) {
      if (node.type === 'element' && node.properties?.id === 'footnote-label') {
        node.children = [{ type:'text', value:chinese ? '注释' : 'Notes' }];
      }
      if (node.type === 'element' && Object.hasOwn(node.properties ?? {}, 'dataFootnoteBackref')) {
        node.properties.ariaLabel = chinese ? '返回正文引用' : 'Back to text reference';
      }
      node.children?.forEach(visit);
    }
    visit(tree);
  };
}
