import { useState } from "react";
import { createRoot } from "react-dom/client";
import { FolderGlyph, type FolderGlyphTone } from "../src/FolderGlyph";
import "./folders.css";

const folders: { name: string; tone: FolderGlyphTone }[] = [
  { name: "设计灵感", tone: "amber" }, { name: "开发资料", tone: "sky" },
  { name: "阅读笔记", tone: "lilac" }, { name: "日常收藏", tone: "sage" },
];
function Preview() {
  const [selected, setSelected] = useState("");
  return <main>
    <header><strong>Facetmark</strong><span>文件夹动效 · 组件预览</span></header>
    <h1>让收藏，触手可及。</h1>
    <p>移近时轻轻展开，选中后停留。试着在文件夹之间切换。</p>
    <section aria-label="文件夹动画预览">
      {folders.map(folder => <button key={folder.tone} type="button" aria-pressed={selected === folder.tone}
        onClick={() => setSelected(folder.tone)}>
        <FolderGlyph tone={folder.tone} active={selected === folder.tone}/>
        <span>{folder.name}</span><i aria-hidden="true"/>
      </button>)}
    </section>
    <footer><span>悬停展开</span><span>点击选中</span><span>键盘 Tab / Enter</span></footer>
    <small>仅展示保留的文件夹组件，整体界面另行重设计。</small>
  </main>;
}
createRoot(document.getElementById("root")!).render(<Preview/>);
