# 重构源码核查：2026-10-19

用户再次拒绝本轮浅绿收藏原型，并要求检查代码，指出反复看图没有改善结果。
这份记录检查当前源码和参考项目的明确提交，不把截图、测试通过或依赖已安装
当作设计已达到要求的证据。未逐条审计用户提到的近百轮改动。

## 核查范围与版本

- Facetmark：`035ba99`；实际应用入口、样式链、按钮适配与交互动效，以及本轮独立原型。
- [HeroUI v3，ce90ea3](https://github.com/heroui-inc/heroui/tree/ce90ea3ab49d58f6c428f71bfd6fe8ae2a87b960)：
  2026-10-17 提交，`packages/react/package.json` 为 3.2.6，与 Facetmark 声明版本一致。
  核查 Button 实现、button.css、主题变量。
- [FlClash，8d4f974](https://github.com/chen08209/FlClash/tree/8d4f9744948751f1273fe871e1d05276fac09b0e)：
  2026-10-17 提交，核查字体回退、排版尺度、主题状态、dashboard 布局与材质文件。
- [GithubStarsManager，60e51be](https://github.com/AmintaCCCP/GithubStarsManager/tree/60e51be137e068e9ad3ce5c2b726d4ae73a6826e)：
  2026-10-18 提交，核查 Button、RepositoryCard、RepositoryList 与主题 CSS；未审计整个项目。

这些提交来自本次读取各仓库默认分支后取得的 SHA，源码通过对应 Git blob 获取。
此前读取的本地参考截图没有核对到这些版本，不能视为当前源码的呈现。

## 1. 使用 HeroUI 并不等于采用了它的控件表现

`frontend/src/styles.css:6` 将 HeroUI 按钮 CSS 放入 `components` layer；
同文件 106–110 行却有未分层的 `button { color: inherit; border: 0; background: none; }`。
按 CSS 层叠规则，未分层的普通声明优先于命名层内普通声明，因此这段规则接管了
库按钮的背景、文字与边框，也覆盖其 hover/pressed 背景。791 行起的 `.primary`、
`.secondary` 再画项目自己的外观。

本地 `styles.css:113` 固定 `.fm-button.button` 的圆角为 9999px；
`workbench.css:351` 又对应用中的 button、summary、input、select 统一设 9999px。
这不是 HeroUI 强制所有控件成为胶囊。仅调整库主题的半径也不能解除本地覆盖。

上游对应实现：

- [button.tsx](https://github.com/heroui-inc/heroui/blob/ce90ea3ab49d58f6c428f71bfd6fe8ae2a87b960/packages/react/src/components/button/button.tsx#L54)：React Aria ButtonPrimitive 承担交互状态。
- [button.css](https://github.com/heroui-inc/heroui/blob/ce90ea3ab49d58f6c428f71bfd6fe8ae2a87b960/packages/styles/components/button.css#L29)：焦点、pressed、hover 及不同尺寸的按压缩放分别有规则。

按压 transform 仍可由库提供，不能说所有 HeroUI 效果都被清除。本地还在
`ui/controls.tsx:23` 起适配 press、keydown、keyup 与 DOM click。这是额外的行为
责任，静态代码不能证明它一定重复点击，也不能仅凭库名证明它正确。

## 2. 样式和动效仍有多个所有者

`frontend/src/main.tsx:4` 起依次加载 styles、collection-tools、support、reader-shell、
workbench 五份 CSS。以 `.page-scroll` 为例，同一属性在三个文件定义：

| 来源 | padding | 圆角 / 阴影 |
|---|---|---|
| styles.css:1248 | `44px clamp(24px, 5vw, 72px) 64px` | — |
| support.css:4 | `24px 36px 40px` | 20px / sheet-shadow |
| workbench.css:160 | `32px 40px 40px` | 28px / card-shadow |

后加载规则决定最终表现；修改前面的同名规则可能没有预期作用。多个文件本身
不是错误，重复接管同一组件属性才是这里需要处理的问题。

`InteractionMotion.tsx:149` 起使用 document 级 pointerdown/keydown 捕获，为
`button, summary, .result-title` 创建 portal 涟漪；`App.tsx:670` 挂载它。
控件自己的库状态、局部动画与全局绘制因此需要协调。源码能证明存在这种耦合，
不能在没有复现的情况下声称某个具体动画 bug 正由它造成。

## 3. 本轮原型重新犯了已约定要避免的问题

原型的 `workbench.css:1931` 将手机分类块高度设为 84px，2299 行又改为 94px；
1900 行设置工作区底部 20px，2293 行再覆盖成 100px。末尾追加覆盖仍然出现。
这违反了本项目已经写明的“替换时移除旧规则、明确组件归属”，属于执行失误。

`workbench.css:1118` 对紧凑视图的 `.card-metadata` 使用 `display:none`，而
`workbench.js:71` 正把摘要状态和标签放在其中。切换布局就丢失了结构化状态提示。
这是代码可定位的信息损失，30 项原型检查没有覆盖这一断言。

`workbench.js:248` 的阅读目录阻止原生锚点行为，只滚动并切换样式，没有把焦点
交给目标章节或同步当前章节语义。这也没有被现有的打开/关闭焦点测试覆盖。

这些问题记录用于后续替换的回归边界；被拒绝的原型不应为了修它们继续扩展。

## 4. 参考项目实际提供的是成套实现机制

### FlClash

- [typography.dart](https://github.com/chen08209/FlClash/blob/8d4f9744948751f1273fe871e1d05276fac09b0e/lib/ui/typography.dart#L6)
  定义排版角色，包含字号、行高、普通/强调字重，并映射到 ThemeData，而非各区域临时决定小字尺寸。
- [font.dart](https://github.com/chen08209/FlClash/blob/8d4f9744948751f1273fe871e1d05276fac09b0e/lib/ui/font.dart#L7)
  根据平台和汉字区域选择回退字体；不能从 macOS 截图推断 Windows 字体表现。
- [dashboard.dart](https://github.com/chen08209/FlClash/blob/8d4f9744948751f1273fe871e1d05276fac09b0e/lib/views/dashboard/dashboard.dart#L47)
  将文本缩放、剩余可用宽高和 density 纳入布局；短窗口有对应内容组织，不只减少列数。
- [style.dart](https://github.com/chen08209/FlClash/blob/8d4f9744948751f1273fe871e1d05276fac09b0e/lib/views/dashboard/style.dart#L23)
  使用 page/card/block/inset 层级，深浅色阴影分开，控件与大卡片有不同形状尺度。

### GithubStarsManager

- [ui/button.tsx](https://github.com/AmintaCCCP/GithubStarsManager/blob/60e51be137e068e9ad3ce5c2b726d4ae73a6826e/src/components/ui/button.tsx#L13)
  用共享 variant 和原生 button/Slot 组织控件。
- [index.css](https://github.com/AmintaCCCP/GithubStarsManager/blob/60e51be137e068e9ad3ce5c2b726d4ae73a6826e/src/index.css#L523)
  明确字体栈、前景/背景、浮层、状态色与层次变量；这不意味着需要复制其配色。
- [RepositoryCard.tsx](https://github.com/AmintaCCCP/GithubStarsManager/blob/60e51be137e068e9ad3ce5c2b726d4ae73a6826e/src/components/RepositoryCard.tsx#L1062)
  为列表视图安排独立状态区域，分析状态与摘要显示分开。本轮原型却直接隐藏整块 metadata。

可学习的是这些实现关系，不能把几个圆角、配色和卡片位置等同于学会参考项目。

## 5. 原型、正式应用和验证范围没有合并

`frontend/design/workbench/index.html:8` 加载独立 CSS/JS，不使用现有 React 组件。
`frontend/src/main.tsx` 仍渲染 App。`git diff 0618f24..035ba99 -- frontend/src` 为空。
这是本轮视觉原型的实际范围，不能声称正式界面完成重构。

`scripts/design_preview.py:17` 只指向该原型，81 行检查六条合成收藏。30 项检查证明
列明的原型行为和资源隔离，不覆盖实际服务分页、模型流程、任务恢复或安装应用。

这两次原型云端产物记录了各自提交与文件哈希；其中 `672f7eb` 的图片、录像、
检查记录和源文件已核对到对应 git blob。因此它们有版本依据，但仍被用户拒绝。
“版本正确”和“设计合适”是两件分别需要证据的事。

## 后续实施约束

本轮浅绿原型已拒绝。当前阶段停止视觉改动，以本核查结果约束下一次实际重构：

1. 先明确现有组件与功能边界、样式属性与动画的唯一所有者，再改布局。
2. 对参考的具体组件读取同一提交下的实现，记录采用的机制及不适用的部分。
3. 在真实组件路径里替换；用同一组件和合成数据预览，避免另写不能回迁的界面。
4. 每替换组件同时删除它的旧覆盖；避免全控件半径与 document 级外观补丁。
5. 核对状态、字号、主题、窄屏与键盘实现后，再用源码对应的云端运行检查呈现。
6. 截图用于验证已实现的结果；技术通过不替代用户的视觉判断。
