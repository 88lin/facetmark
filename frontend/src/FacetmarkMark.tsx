import mark from "../../desktop/splash/mark.svg";

/** The native splash and workbench share the desktop icon's folded-F identity. */
export function FacetmarkMark() {
  return <span className="brand-mark" aria-hidden="true">
    <img src={mark} alt="" draggable={false}/>
  </span>;
}
