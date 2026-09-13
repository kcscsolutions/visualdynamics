/* arithmatex (generic) wraps math in \( \) and \[ \]; this tells
   MathJax to read exactly those, and re-typesets after the instant
   navigation swaps a page in without a reload. */
window.MathJax = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
    processEscapes: true
  },
  options: {
    ignoreHtmlClass: ".*|",
    processHtmlClass: "arithmatex"
  }
};
document$.subscribe(() => {
  if (window.MathJax && MathJax.typesetPromise) MathJax.typesetPromise();
});
