/** An explicit section choice belongs to the reader, not to either control. */
export const SECTION_SELECTED = "facetmark:reader-section-selected";

export function selectReaderSection(container: HTMLElement, id: string) {
  container.dispatchEvent(new CustomEvent<string>(SECTION_SELECTED, { detail: id }));
}

export function scrollToReaderSection(container: HTMLElement, heading: HTMLElement, behavior: ScrollBehavior) {
  const top = heading.id === "reader-start" ? 0 : heading.getBoundingClientRect().top - container.getBoundingClientRect().top
    - container.clientTop + container.scrollTop - 28;
  container.scrollTo({ top: Math.max(0, Math.min(top, container.scrollHeight - container.clientHeight)), behavior });
}
