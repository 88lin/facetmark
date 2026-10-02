"""facetmark 官网中文文案。

这里出现的每一个数字，都来自仓库 ``docs/`` 下的某一份实测记录，或者来自本仓库某条命令的
真实输出。没有为了好看而四舍五入，也没有估算。没有协议撑着的说法，不会出现在站上。
"""

REPO = "https://github.com/88lin/facetmark"

ZH = {
    "code": "zh",
    "html_lang": "zh-CN",
    "other_code": "en",
    "other_label": "EN",
    "other_title": "Switch to English",
    "skip": "\u8df3\u5230\u6b63\u6587",
    "copy": {"label": "\u590d\u5236", "done": "\u5df2\u590d\u5236", "seealso": "\u53e6\u89c1"},
    "nav": {
        "home": "\u9996\u9875",
        "quickstart": "\u4e0a\u624b",
        "guide": "\u4f7f\u7528\u6307\u5357",
        "measured": "\u5b9e\u6d4b\u8bb0\u5f55",
        "gh": "GitHub",
    },
    "term_labels": {
        "hits": "\u6761\u7ed3\u679c",
        "found": "\u76ee\u6807\u5728\u7b2c",
        "missed": "\u76ee\u6807\u4e0d\u5728\u524d 5",
        "content": "\u5185\u5bb9\u578b\u67e5\u8be2 \u2014\u2014 \u4f60\u8bb0\u5f97\u91cc\u9762\u7684\u8bcd",
        "vague": "\u6a21\u7cca\u578b\u67e5\u8be2 \u2014\u2014 \u4f60\u53ea\u8bb0\u5f97\u610f\u601d",
        "episodic": "\u60c5\u666f\u578b\u67e5\u8be2 \u2014\u2014 \u4f60\u8bb0\u5f97\u662f\u4ec0\u4e48\u65f6\u5019",
    },
    "meta": {
        "index": (
            "facetmark · 只记得一点，也能找到那一篇。",
            "把浏览器里的书签变成可搜索的个人资料库。用关键词、内容描述或保存时间找回页面，再顺着来源继续阅读。数据保存在你运行 facetmark 的电脑或服务器上。",
        ),
        "quickstart": (
            "facetmark · 快速上手",
            "从导入书签到完成第一次搜索。每一步都有检查方法；本机使用和服务器管理分别说明。",
        ),
        "guide": (
            "facetmark · 命令与接口参考",
            "按任务查找导入、检索语法、分页、HTTP API、扩展和配置项。首次使用建议先完成快速上手，再回到这里查具体参数。",
        ),
        "measured": (
            "facetmark · 评测方法与结果",
            "记录检索默认值背后的实验、反例和未覆盖的场景。每项结果应结合数据集、协议和样本限制阅读；这些数字不代表所有书签库的表现。",
        ),
    },
    "foot": {
        "cols": [
            (
                "\u4ece\u8fd9\u91cc\u5f00\u59cb",
                [
                    ("\u5feb\u901f\u4e0a\u624b", "quickstart.zh.html"),
                    ("\u5b89\u88c5", "guide.zh.html#install"),
                    ("\u628a\u4e66\u7b7e\u5bfc\u8fdb\u6765", "guide.zh.html#import"),
                    ("\u6a21\u578b\u63a5\u5165", "guide.zh.html#models"),
                    ("\u5efa\u7d22\u5f15", "guide.zh.html#index"),
                    ("\u8bbe\u7f6e", "config.zh.html"),
                    ("\u6392\u9519", "guide.zh.html#trouble"),
                ],
            ),
            (
                "\u63a5\u53e3",
                [
                    ("\u7f51\u9875\u754c\u9762", "webui.zh.html"),
                    ("\u672c\u5730\u9875\u9762", "guide.zh.html#webui"),
                    ("\u547d\u4ee4\u884c", "guide.zh.html#commands"),
                    ("HTTP API", "guide.zh.html#serve"),
                    ("MCP \u670d\u52a1\u5668", "guide.zh.html#mcp"),
                    ("\u6d4f\u89c8\u5668\u6269\u5c55", "guide.zh.html#extension"),
                    ("\u8fde\u63a5\u5176\u4ed6\u5de5\u5177", "integrations.zh.html"),
                    ("karakeep \u63d2\u4ef6", "guide.zh.html#karakeep"),
                ],
            ),
            (
                "\u8bc1\u636e",
                [
                    ("\u5168\u90e8\u5b9e\u6d4b", "measured.zh.html"),
                    ("\u56db\u8def\u878d\u5408", "measured.zh.html#w1"),
                    ("\u60c5\u666f\u95e8", "measured.zh.html#gate"),
                    ("\u8870\u51cf\u5c42\u6d4b\u4e86\u4e24\u6b21", "measured.zh.html#decay"),
                    ("\u8fd9\u4e9b\u90fd\u6ca1\u6d4b\u5230\u4ec0\u4e48", "measured.zh.html#gaps"),
                ],
            ),
            (
                "\u9879\u76ee",
                [
                    ("\u6e90\u7801", REPO),
                    ("\u53d1\u884c\u7248", REPO + "/releases"),
                    ("Issues", REPO + "/issues"),
                    ("MIT \u8bb8\u53ef\u8bc1", REPO + "/blob/main/LICENSE"),
                ],
            ),
        ],
        "bar": [
            "facetmark v@@VERSION@@ \u00b7 MIT",
            "Python 3.10+ \u00b7 \u4e00\u4e2a SQLite \u6587\u4ef6",
            "\u8fd9\u4e2a\u7ad9\u4e0a\u6ca1\u6709\u4e00\u4e2a\u6570\u5b57\u662f\u6ca1\u6709\u534f"
            "\u8bae\u6491\u7740\u7684\u3002",
        ],
    },
}

ZH["index"] = {
    "kicker": "\u672c\u5730\u4f18\u5148\u7684\u4e66\u7b7e\u68c0\u7d22",
    "h1": "只记得一点，<br><em>也能找到那一篇。</em>",
    "lede": (
        "把浏览器里的书签变成可搜索的个人资料库。用关键词、内容描述或保存时间找回页面，再顺着来源继续阅读。数据保存在你运行 facetmark 的电脑或服务器上。"
    ),
    "cta": [("开始使用", "quickstart.zh.html", True), ("了解应用界面", "webui.zh.html", False)],
    "chips": [("运行环境", "Python 3.10+"), ("存储", "SQLite"), ("开源许可", "MIT")],
    "term_title": "facetmark demo --size 60",
    "term_note": (
        "\u8fd9\u662f <code>facetmark demo</code> \u7684\u771f\u5b9e\u8f93\u51fa\uff0c\u5b83"
        "\u4f1a\u79bb\u7ebf\u9020\u4e00\u4e2a 60 \u9875\u7684\u5408\u6210\u4e66\u7b7e\u5e93\u3002"
        "provider \u662f <code>mock</code>\uff0c\u6240\u4ee5\u8fd9\u662f\u4e00\u6b21\u7ba1\u8def"
        "\u4f53\u68c0\uff0c<b>\u4e0d\u662f\u8d28\u91cf\u5ea6\u91cf</b> \u2014\u2014 mock \u662f"
        "\u628a\u6587\u672c\u54c8\u5e0c\u6210\u5411\u91cf\u7684\u3002\u5206\u6570\u5217\u770b"
        "\u4e0a\u53bb\u6ca1\u6392\u5e8f\uff0c\u662f\u56e0\u4e3a\u540d\u6b21\u6765\u81ea\u91cd"
        "\u6392\u9636\u6bb5\uff0c\u800c\u5206\u6570\u662f\u878d\u5408\u5206\uff0c\u91cd\u6392"
        "\u6545\u610f\u4e0d\u53bb\u8986\u76d6\u5b83\u3002"
    ),
    "prob_label": "\u5b83\u8981\u89e3\u51b3\u7684\u95ee\u9898",
    "prob_h2": "从你还记得的那一点开始",
    "prob_lede": (
        "不必先整理好每个文件夹。先试试关键词；配置向量模型后，也可以用自己的话描述内容。保存时间和关联页面帮助你继续缩小范围。"
    ),
    "prob_cards": [
        (
            "内容型",
            "记得几个词",
            "搜索标题、网址和文件夹中的词语，也支持中文子串。",
            "“sqlite 向量索引”",
            "0.959",
            "Recall@5",
            "good",
        ),
        (
            "模糊型",
            "记得内容的意思",
            "配置向量模型后，用内容描述寻找相关页面。结果取决于已索引内容和所用模型。",
            "“让应用在断网时也能搜索”",
            "0.706",
            "Recall@5",
            "",
        ),
        (
            "情景型",
            "记得收藏的时间",
            "按保存日期筛选，再查看同一浏览批次里的其他书签。",
            "“上个月收藏的数据库文章”",
            "0.279",
            "Recall@5",
            "bad",
        ),
    ],
    "prob_note": ('检索能力和限制都有记录。<a href="measured.zh.html">阅读评测方法与结果</a>。'),
    "fac_label": "\u5b83\u662f\u600e\u4e48\u5de5\u4f5c\u7684",
    "fac_h2": "搜索依据，看得见",
    "fac_lede": (
        "内容向量、生成的提问、关键词和子串，是不同的检索信号。有向量模型时，默认使用内容向量、图谱扩展和时间衰减；其他组合可在搜索选项中比较。没有模型时，仍可使用词面搜索。"
    ),
    "fac_head": [
        "\u9762",
        "\u7d22\u5f15\u7684\u662f\u4ec0\u4e48",
        "\u56de\u7b54\u4ec0\u4e48\u6837\u7684\u95ee\u9898",
        "\u9ed8\u8ba4",
    ],
    "fac_rows": [
        (
            '<b>\u8bcd\u9762</b><br><span class="tiny">\u4e24\u4e2a FTS5 \u7d22\u5f15</span>',
            "\u6807\u9898\u3001URL\u3001\u6b63\u6587\u7684\u5b57\u7b26\u4e09\u5143\u7ec4\u548c"
            "\u8bcd\u6bb5\u3002",
            "\u7cbe\u786e\u5b57\u7b26\u4e32\u3001ID\u3001\u4ee3\u7801\u3001\u62a5\u9519\u4fe1"
            "\u606f\uff0c\u4ee5\u53ca\u6ca1\u6709\u7a7a\u683c\u53ef\u5206\u7684\u4e2d\u6587\u3002",
            '<span class="badge warn">\u5173</span><br>'
            '<span class="tiny">\u878d\u5408\u65f6\u8f93\u4e86 5.4pp</span>',
        ),
        (
            '<b>\u5185\u5bb9\u9762</b><br><span class="tiny">\u7a20\u5bc6\u5411\u91cf</span>',
            "\u9875\u9762\u6b63\u6587\u62bd\u53d6\u540e\u7684\u5d4c\u5165\uff0c\u4e0d\u662f"
            "\u6807\u9898\u7684\u3002",
            "\u6362\u8bf4\u6cd5\u3002\u8bcd\u5fd8\u4e86\u3001\u610f\u601d\u8fd8\u5728\u7684"
            "\u90a3\u79cd\u3002",
            '<span class="badge pass">\u5f00</span><br>'
            '<span class="tiny">W1 \u8d62\u5bb6\uff0c0.643</span>',
        ),
        (
            '<b>\u610f\u56fe\u9762</b><br><span class="tiny">\u751f\u6210\u7684\u67e5\u8be2</span>',
            "\u6a21\u578b\u4e3a\u8fd9\u4e2a\u9875\u9762\u5199\u7684\u5019\u9009\u95ee\u6cd5"
            "\uff0c\u518d\u7528\u300c\u80fd\u4e0d\u80fd\u628a\u8fd9\u9875\u635e\u56de\u6765"
            "\u300d\u8fc7\u6ee4\u4e00\u904d\u3002",
            "\u4f60\u4ee5\u540e\u4f1a\u600e\u4e48\u5f00\u53e3\u627e\u5b83\u3002",
            '<span class="badge warn">\u5173</span><br>'
            '<span class="tiny">\u53ea\u6709 38% \u7684\u610f\u56fe\u7ad9\u5f97\u4f4f</span>',
        ),
        (
            '<b>\u4e0a\u4e0b\u6587\u9762</b><br><span class="tiny">\u4f1a\u8bdd\u4e0e\u56fe</span>',
            "\u4fdd\u5b58\u4f1a\u8bdd\u805a\u7c7b\u3001\u57df\u540d\u7ed3\u6784\uff0c\u4ee5"
            "\u53ca\u5168\u5e93\u7684\u94fe\u63a5\u56fe\u3002",
            "\u300c\u6211\u5b58\u90a3\u4e2a\u7684\u65f6\u5019\u8fd8\u987a\u624b\u5b58\u4e86"
            "\u54ea\u4e9b\uff1f\u300d",
            '<span class="badge pass">\u56fe\u6269\u5c55\u5f00</span> '
            '<span class="badge fail">\u60c5\u666f\u95e8\u5173</span><br>'
            '<span class="tiny">+2.09pp / \u221218.83pp</span>',
        ),
    ],
    "fac_note": (
        '\u8fd9\u56db\u4e2a\u7ed3\u8bba\u6bcf\u4e00\u4e2a\u90fd\u5bf9\u5e94<a href="'
        'measured.zh.html">\u5b9e\u6d4b\u9875</a>\u4e0a\u4e00\u4efd\u534f\u8bae\u3001\u4e00'
        "\u5957\u67e5\u8be2\u96c6\u548c\u4e00\u4e2a\u7f6e\u4fe1\u533a\u95f4\u3002"
    ),
    "pipe_label": "\u7ba1\u7ebf",
    "pipe_h2": "\u4ece\u4e00\u53e5\u67e5\u8be2\u5230\u4e00\u4efd\u6392\u540d",
    "pipe_lede": (
        "\u6709\u989c\u8272\u7684\u9636\u6bb5\u662f\u51fa\u5382\u9ed8\u8ba4\u771f\u7684\u4f1a\u8dd1\u7684\u3002\u7070"
        "\u8272\u7684\u662f\u5199\u4e86\u3001\u6d4b\u4e86\u3001\u7136\u540e\u5173\u6389\u7684\u3002"
        "\u6bcf\u4e00\u4e2a\u7d22\u5f15\u9636\u6bb5\u90fd\u662f\u5e42\u7b49\u7684\u5e76\u4e14"
        "\u5e26\u6307\u7eb9\uff0c\u6240\u4ee5 <code>facetmark index</code> \u53ea\u4f1a\u91cd"
        "\u505a\u8f93\u5165\u53d8\u4e86\u7684\u90a3\u90e8\u5206\u3002"
    ),
    "pipe_scroll": "\u56fe\u53ef\u4ee5\u5de6\u53f3\u6ed1 \u2192",
    "pipe_after": [
        (
            "\u5efa\u7d22\u5f15",
            "<code>bookmark</code> \u2192 <code>fetch</code> \u2192 "
            "<code>content</code> \u2192 <code>enrich</code>\uff08\u6458\u8981\u3001\u4e3b"
            "\u9898\u3001\u5b9e\u4f53\u3001\u8981\u70b9\uff09\u2192 <code>embed</code> \u2192 "
            "<code>intents</code> \u2192 \u8fc7\u6ee4 \u2192 <code>sessions</code> \u2192 "
            "<code>edges</code>\u3002",
        ),
        (
            "\u6307\u7eb9",
            "\u5bcc\u5316\u6309\u6b63\u6587\u54c8\u5e0c\u8ba1\u7b97\uff1b\u5d4c\u5165\u6309"
            "<em>\u91cd\u5efa\u540e\u7684\u5d4c\u5165\u6587\u672c</em>\u8ba1\u7b97 \u2014\u2014 \u6240\u4ee5\u4e00\u4e2a\u548c\u81ea\u5df1\u6587\u672c\u5bf9\u4e0d\u4e0a\u7684"
            "\u5411\u91cf\u4f1a\u88ab\u53d1\u73b0\uff0c\u800c\u4e0d\u662f\u88ab\u76f8\u4fe1"
            "\u3002<code>--force</code> \u4e24\u4e2a\u90fd\u4e0d\u770b\u3002",
        ),
        (
            "\u56fe\u6269\u5c55",
            "\u4ece\u878d\u5408\u7ed3\u679c\u5f80\u5916\u8d70\u4e00\u8df3\uff0c\u4f5c\u4e3a"
            "<em>\u5355\u72ec\u4e00\u7ec4</em>\u8fd4\u56de\uff0c\u4e0d\u6df7\u8fdb\u6392\u540d"
            "\u91cc\u3002\u5b9e\u6d4b +2.09pp\uff0c10 \u80dc 0 \u8d1f\uff0c9 ms\u3002",
        ),
    ],
    # --- the local page
    "app_label": "\u4f60\u8981\u6253\u5f00\u7684\u90a3\u4e2a\u9875\u9762",
    "app_h2": "一个界面，接着读下去",
    "app_lede": (
        "搜索结果可以展开查看摘要与来源；综述把相关资料整理成带引用的回答；书签库展示正文和索引的覆盖情况。桌面与手机使用同一套界面。"
    ),
    "app_shot": (
        "assets/app-search-zh.png",
        "facetmark 搜索界面：结果、摘要与匹配来源。图中为合成示例书签。",
        "搜索、查看来源、继续阅读 · 示例书签库",
    ),
    "app_shot_dark": (
        "assets/app-search-zh-dark.png",
        "\u540c\u4e00\u4e2a\u641c\u7d22\u9875\u7684\u6df1\u8272\u6a21\u5f0f",
    ),
    "app_points": [
        (
            "它说一门过滤语言",
            "<code>domain:github.com</code>、<code>tag:work</code>、"
            "<code>added:&lt;7d</code>、<code>-pinterest</code>、"
            "<code>sort:date</code>——都在同一个输入框里，字段名<em>和</em>"
            "你库里真实存在的值都会补全。只有过滤器的查询是一次浏览："
            "完全不调用模型。",
        ),
        (
            "\u5b83\u81ea\u5df1\u914d\u5bf9",
            "\u4ee4\u724c\u6765\u81ea\u4e00\u6761\u53ea\u5728<em>\u8c03\u7528\u65b9</em>\u548c<em>\u8bf7\u6c42\u91cc\u5199\u7684\u5730\u5740</em>\u4e24\u8005\u90fd\u662f\u56de"
            "\u73af\u5730\u5740\u65f6\u624d\u56de\u7b54\u7684\u8def\u7531\uff0c\u6240\u4ee5\u5728\u4f60\u81ea\u5df1\u673a\u5668\u4e0a\u6ca1\u6709\u4ec0\u4e48\u8981\u590d\u5236\u7684\u3002\u6362\u4e2a\u5730"
            "\u65b9\uff0c\u9875\u9762\u4f1a\u8ba9\u4f60\u7c98\u8d34\u4e00\u6b21\u3002",
        ),
        (
            "\u7f3a\u4ec0\u4e48\u5b83\u4f1a\u8bf4",
            "\u7a7a\u7684\u4e66\u7b7e\u5e93\u4f1a\u628a\u5bfc\u5165\u547d\u4ee4\u6253\u51fa\u6765\u3002\u6709\u4e66\u7b7e\u4f46\u6ca1\u6709\u5411\u91cf\uff0c\u5c31\u6253 "
            "<code>facetmark index</code>\u3002\u641c\u4e0d\u5230\u4e1c\u897f\u800c\u6293\u53d6\u961f\u5217\u8fd8\u6392\u7740\uff0c\u5b83\u4f1a\u76f4"
            "\u63a5\u544a\u8bc9\u4f60\uff0c\u800c\u4e0d\u662f\u7529\u7ed9\u4f60\u4e00\u4e2a\u7a7a\u5217\u8868\u8ba9\u4f60\u731c\u3002",
        ),
        (
            "\u4e2d\u6587\u548c English",
            "\u9876\u680f\u4e00\u4e2a\u5f00\u5173\uff0c\u4e0b\u6b21\u6765\u8fd8\u8bb0\u5f97\u3002\u6d45\u8272\u3001\u6df1\u8272\uff0c\u6216\u8005\u8ddf\u968f\u7cfb\u7edf\u3002<kbd>/</kbd> "
            "\u805a\u7126\u641c\u7d22\u6846\uff0c\u4e0a\u4e0b\u952e\u8d70\u7ed3\u679c\uff0c<kbd>Esc</kbd> \u6e05\u7a7a\u3002",
        ),
    ],
    "app_cta": "\u4ece\u96f6\u5f00\u59cb\u4e0a\u624b \u2192",
    # --- extension
    "shot_label": "\u5728\u6d4f\u89c8\u5668\u91cc",
    "shot_h2": "\u4e00\u4e2a\u53ea\u548c localhost \u8bf4\u8bdd\u7684\u6269\u5c55",
    "shot_lede": (
        "Manifest V3\u3002\u4e3b\u673a\u6743\u9650\u53ea\u6709 "
        "<code>http://127.0.0.1:8787/*</code> \u548c "
        "<code>http://localhost:8787/*</code>\u3002\u5b83\u53ea\u8bbf\u95ee\u4f60\u81ea\u5df1"
        "\u7684\u673a\u5668\uff0c\u7528\u4e00\u4e2a\u914d\u5bf9\u4ee4\u724c\u63e1\u624b\uff0c"
        "\u5e76\u4e14\u4ece\u4e0d\u5199\u4f60\u6d4f\u89c8\u5668\u7684\u4e66\u7b7e\u5e93\u3002"
    ),
    "shots": [
        (
            "assets/popup-mock.png",
            "facetmark \u5f39\u7a97\u641c\u7d22\u7ed3\u679c",
            "<b>\u5f39\u7a97\u3002</b>\u6bcf\u6761\u7ed3\u679c\u90fd\u5e26\u7740\u547d\u4e2d"
            "\u5b83\u7684\u9762\uff0c\u800c\u540c\u4e00\u6b21\u4fdd\u5b58\u4f1a\u8bdd\u91cc"
            "\u7684\u9875\u9762\u4f1a\u5355\u72ec\u6210\u4e00\u7ec4\uff0c\u4e0d\u6df7\u8fdb"
            "\u6392\u540d\u3002\u8fd9\u4e2a\u753b\u6846\u8ddf\u7740\u4f60\u6b63\u5728\u770b"
            "\u7684\u8fd9\u4e2a\u9875\u9762\u5207\u4e3b\u9898\u3002",
        ),
        (
            "assets/options.png",
            "facetmark \u8bbe\u7f6e\u9875",
            "<b>\u8bbe\u7f6e\u9875\u3002</b>\u7aef\u70b9\u3001\u914d\u5bf9\u4ee4\u724c\u3001"
            "\u4e00\u4e2a\u53ef\u9009\u7684\u7b2c\u4e8c\u901a\u9053\uff0c\u4e00\u4e2a\u6682"
            "\u505c\u5f00\u5173\u3002\u56db\u4e2a\u5b57\u6bb5\uff0c\u6ca1\u6709\u8d26\u53f7"
            "\u3002",
        ),
    ],
    "shot_dark": (
        "assets/popup-mock-dark.png",
        "\u6df1\u8272\u6a21\u5f0f\u4e0b\u7684\u540c\u4e00\u4e2a\u5f39\u7a97",
    ),
    "shot_dark_opts": (
        "assets/options-dark.png",
        "\u6df1\u8272\u6a21\u5f0f\u4e0b\u7684\u540c\u4e00\u4e2a\u8bbe\u7f6e\u9875",
    ),
    "shot_legend": (
        "\u7ed3\u679c\u884c\u4e0a\u7684\u6bcf\u4e2a\u6807\u8bb0\u662f\u4ec0\u4e48\u610f\u601d",
        [
            (
                "chip",
                "about",
                "\u547d\u4e2d\u4e86<b>\u5185\u5bb9</b>\u9762\uff1a\u6b63\u6587\u7684"
                "\u5411\u91cf\u3002\u552f\u4e00\u4e00\u4e2a\u9ed8\u8ba4\u5f00\u7740"
                "\u7684\u9762\u3002",
            ),
            (
                "chip",
                "asked as",
                "\u547d\u4e2d\u4e86<b>\u610f\u56fe</b>\u9762\uff1a\u4e3a\u8fd9\u4e2a"
                "\u9875\u9762\u751f\u6210\u7684\u95ee\u53e5\u7684\u5411\u91cf\u3002"
                "\u9ed8\u8ba4\u5173\u95ed\u3002",
            ),
            (
                "chip",
                "words",
                "\u547d\u4e2d\u4e86<b>\u8bcd\u9762 \u00b7 \u5206\u8bcd</b>\u9762\uff1a"
                "FTS5\uff0c\u6309\u8bcd\u5207\u3002\u9ed8\u8ba4\u5173\u95ed\u3002",
            ),
            (
                "chip",
                "substring",
                "\u547d\u4e2d\u4e86<b>\u8bcd\u9762 \u00b7 \u4e09\u5143\u7ec4</b>\u9762"
                "\uff1aFTS5\uff0c\u6309\u5b57\u7b26\u5207\u3002\u9ed8\u8ba4\u5173\u95ed"
                "\u3002",
            ),
            (
                "cold",
                "cold",
                "\u94fe\u63a5\u770b\u8d77\u6765\u5df2\u7ecf\u6b7b\u4e86\uff0c\u8fd9"
                "\u4e00\u884c\u53ea\u964d\u6743\uff0c\u4e0d\u5220\u3002\u4e3a\u4ec0"
                "\u4e48\uff0c\u95ee <code>facetmark health</code>\u3002",
            ),
            (
                "group",
                "saved around these",
                "\u5355\u72ec\u7684\u7b2c\u4e8c\u7ec4\uff0c\u6cbf\u4f1a\u8bdd\u8fb9"
                "\u548c\u8bed\u4e49\u8fb9\u8d70\u4e00\u8df3\u5f97\u5230\u3002\u6c38"
                "\u8fdc\u4e0d\u6df7\u8fdb\u4e0a\u9762\u7684\u6392\u540d\u3002",
            ),
        ],
    ),
    "shot_note": (
        "\u8fd9\u4e9b\u662f\u7528 mock \u6570\u636e\u6e32\u67d3\u7684\u754c\u9762\u9884"
        "\u89c8\uff0c\u4e0d\u662f\u771f\u5b9e\u5e93\u7684\u622a\u56fe \u2014\u2014 \u771f\u7684"
        "\u622a\u4e00\u5f20\uff0c\u7b49\u4e8e\u628a\u67d0\u4e2a\u4eba\u7684\u6d4f\u89c8\u5386"
        "\u53f2\u8d34\u5230\u516c\u5f00\u7f51\u9875\u4e0a\u3002"
    ),
    "meas_label": "\u8bc1\u636e",
    "meas_h2": "\u56db\u4e2a\u529f\u80fd\u88ab\u5b9e\u6d4b\uff0c\u56db\u4e2a\u90fd\u8f93\u4e86\u3002\u5b83\u4eec\u73b0\u5728\u662f\u5173\u7684\u3002",
    "meas_lede": (
        "\u8fd9\u4e2a\u9879\u76ee\u6709\u610f\u601d\u7684\u90e8\u5206\u4e0d\u662f\u90a3\u4e9b"
        "\u6210\u529f\u7684\u529f\u80fd\uff0c\u800c\u662f\u90a3\u4e9b\u5199\u5b8c\u4e86\u3001"
        "\u9884\u6ce8\u518c\u4e86\u3001\u6d4b\u5b8c\u4e86\u3001\u7136\u540e\u88ab\u5173\u6389"
        "\u7684 \u2014\u2014 \u5305\u62ec\u4e00\u4e2a\u5df2\u7ecf\u53d1\u51fa\u53bb\u7684\u3002"
    ),
    "meas_stats": [
        (
            "0.643",
            "479 \u6761\u771f\u5b9e\u67e5\u8be2\u3001\u5355\u4e00\u4e2a\u9762\u7684 Recall@5",
            "good",
        ),
        ("\u22125.4pp", "\u56db\u4e2a\u9762\u5168\u6253\u5f00\u7684\u4ee3\u4ef7", "bad"),
        (
            "\u221218.83pp",
            "\u5df2\u7ecf\u53d1\u51fa\u53bb\u7684\u60c5\u666f\u95e8\u7684\u4ee3\u4ef7",
            "bad",
        ),
    ],
    "meas_bars_title": "W1 \u00b7 \u5404\u6863 Recall@5\uff0c479 \u6761\u67e5\u8be2\uff0c\u4e00\u4e2a\u771f\u5b9e\u5e93",
    "meas_bars": [
        ("<b>A</b> \u53ea\u7528\u5185\u5bb9\u5411\u91cf", "0.643", 64.3, True),
        ("<b>B</b> \uff0b\u4e24\u4e2a\u8bcd\u9762", "0.589", 58.9, False),
        ("<b>C</b> \u56db\u4e2a\u9762\u5168\u4e0a", "0.635", 63.5, False),
        ("<b>D</b> \uff0b\u4e0a\u4e0b\u6587\uff0b\u56fe", "0.639", 63.9, False),
    ],
    "meas_body": (
        "<p>\u4e09\u6761\u6807\u51c6\u5728\u8dd1\u4e4b\u524d\u5c31\u5199\u597d\u4e86\u3002"
        "\u4e09\u6761\u5168\u6ca1\u8fbe\u5230\u3002\u878d\u5408\u4ed8\u51fa\u4e86 5.4 \u4e2a"
        "\u767e\u5206\u70b9\u7684 Recall@5\uff0c\u5e76\u4e14\u628a\u67e5\u8be2\u53d8\u6162"
        "\u4e86 3.5 \u500d \u2014\u2014 p50 \u4ece 148 ms \u5230 526 ms\u3002\u56db\u9762"
        "\u878d\u5408\u7684\u9ed8\u8ba4\u5f53\u5929\u5c31\u64a4\u4e86\u3002</p>"
        "<p>\u90a3\u4e00\u8f6e\u91cc\u6d3b\u4e0b\u6765\u4e24\u4e2a\uff0c\u73b0\u5728\u90fd"
        "\u5728\u8dd1\uff1a\u56fe\u6269\u5c55\u4f5c\u4e3a\u5355\u72ec\u4e00\u7ec4\u8fd4\u56de"
        "\uff08+2.09pp\uff0c10 \u80dc 0 \u8d1f\uff0cp=0.0019\uff09\uff0c\u4ee5\u53ca\u91cd"
        "\u6392\u5bf9 Recall@1 \u7684\u63d0\u5347\uff08+4.80pp\uff0cCI95 [+1.46, +8.35]"
        "\uff09\u3002</p>"
        "<p>\u7136\u540e\u662f\u60c5\u666f\u95e8\u3002\u5b83\u5728\u81ea\u5df1\u7684 holdout "
        "\u4e0a\u8d62\u4e86\uff08+3.09pp\uff0c19 \u80dc 0 \u8d1f\uff0cp=3.8e\u22126\uff09"
        "\u5e76\u4e14\u53d1\u4e86\u51fa\u53bb\u3002\u4e4b\u540e\u53e6\u5efa\u7684 361 \u6761"
        "\u63a2\u9488\u96c6\u95ee\u4e86\u53e6\u4e00\u4e2a\u95ee\u9898 \u2014\u2014 \u5b83\u5728"
        "<em>\u4e0d\u8be5</em>\u89e6\u53d1\u7684\u67e5\u8be2\u4e0a\u89e6\u53d1\u4e86\u4f1a"
        "\u600e\u6837\uff1f\u7b54\u6848\u662f <b>\u221218.83pp</b>\uff0c3 \u80dc 71 \u8d1f"
        "\u3002\u9ed8\u8ba4\u56de\u6eda\u4e86\u3002</p>"
    ),
    "meas_cta": "\u770b\u5b8c\u6574\u7684\u4e5d\u4e2a\u7ed3\u679c \u2192",
    "qs_label": "\u5feb\u901f\u5f00\u59cb",
    "qs_h2": "先跑通，再逐步完善你的库",
    "qs_lede": (
        "在 Python 3.10+ 环境中安装，导入书签，然后打开应用。完整教程会带你选择模型、建立索引，并区分本机使用与服务器访问。"
    ),
    "qs_code": (
        "python -m pip install facetmark\nfacetmark import\nfacetmark index --no-fetch\nfacetmark serve"
    ),
    "qs_steps": [
        "<b>本机使用。</b>在有浏览器书签的电脑上运行命令。",
        "<b>服务器部署。</b>先导出书签文件，再传到服务器导入。",
        "<b>先验证流程。</b><code>--no-fetch</code> 跳过网页下载；已有的正文仍可使用。",
        "<b>补全内容。</b>配置模型后运行 <code>facetmark index</code>。",
        '<a href="quickstart.zh.html">按完整教程操作 →</a>',
    ],
    "qs_offline": (
        "只想先体验？运行 <code>facetmark demo</code>。它使用离线生成的示例书签，不需要 API Key。"
    ),
    "if_label": "\u63a5\u53e3",
    "if_h2": "\u516d\u79cd\u7528\u6cd5\uff0c\u540c\u4e00\u4e2a\u7d22\u5f15",
    "if_cards": [
        (
            "web",
            "\u672c\u5730\u9875\u9762",
            "<code>facetmark serve</code> \u4f1a\u5728 <code>/app</code> \u4e0a\u5f00\u4e00\u4e2a\u641c\u7d22"
            "\u9875\u3002\u641c\u7d22\u52a0\u4e66\u7b7e\u5e93\u6982\u89c8\uff0c\u4e2d\u82f1\u6587\u3001\u6df1\u6d45\u8272\u90fd\u80fd\u5207\u3002\u8fd9\u662f\u552f\u4e00\u4e00\u4e2a\u9664\u4e86 "
            "facetmark \u672c\u8eab\u4ec0\u4e48\u90fd\u4e0d\u7528\u88c5\u7684\u5165\u53e3\u3002",
            "guide.zh.html#webui",
            "\u9875\u9762\u4e0a\u6709\u4ec0\u4e48",
        ),
        (
            "cli",
            "\u547d\u4ee4\u884c",
            "21 \u6761\u547d\u4ee4\u3002<code>search</code> \u6709 "
            "<code>--explain</code> \u53ef\u4ee5\u6253\u5370\u547d\u4e2d\u7684\u662f\u54ea"
            "\u4e2a\u9762\uff0c<code>--config</code> \u53ef\u4ee5\u6309\u540d\u5b57\u8dd1"
            "\u4efb\u4f55\u4e00\u4e2a\u6d88\u878d\u6863\u3002",
            "guide.zh.html#commands",
            "\u547d\u4ee4\u53c2\u8003",
        ),
        (
            "http",
            "HTTP API",
            "<code>facetmark serve</code> \u76d1\u542c 127.0.0.1:8787\u300229 \u6761\u8def"
            "\u7531\uff0c\u5176\u4e2d\u56db\u6761\u516c\u5f00 \u2014\u2014 \u6839\u8def\u5f84\u3001\u5065\u5eb7\u68c0\u67e5\uff0c\u4ee5\u53ca\u672c\u5730\u9875\u9762\u52a0\u8f7d\u81ea"
            "\u5df1\u9700\u8981\u7684\u90a3\u4e24\u6761\uff1b\u51e1\u662f\u78b0\u5230\u4e66\u7b7e\u5e93\u7684\u90fd\u8981\u914d\u5bf9\u4ee4\u724c\u3002",
            "guide.zh.html#serve",
            "\u8def\u7531\u4e0e\u9274\u6743",
        ),
        (
            "mcp",
            "MCP \u670d\u52a1\u5668",
            "<code>facetmark mcp</code> \u5728 stdio \u4e0a\u8bf4 MCP\u30029 \u4e2a\u5de5"
            "\u5177\u30013 \u4e2a\u8d44\u6e90\uff0cClaude Desktop \u53ef\u4ee5\u76f4\u63a5"
            "\u641c\u4f60\u7684\u5e93\u3001\u8bfb\u4e00\u6b21\u4fdd\u5b58\u4f1a\u8bdd\u3002",
            "guide.zh.html#mcp",
            "\u5ba2\u6237\u7aef\u914d\u7f6e",
        ),
        (
            "ext",
            "\u6d4f\u89c8\u5668\u6269\u5c55",
            "MV3\u3002\u5730\u5740\u680f\u5173\u952e\u5b57 <code>fm</code>\u3001"
            "<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd>\u3001\u4e00\u952e\u4fdd\u5b58"
            "\u5e76\u8fdb\u672c\u5730\u7d22\u5f15\u961f\u5217\u3002",
            "guide.zh.html#extension",
            "\u5b89\u88c5\u4e0e\u914d\u5bf9",
        ),
        (
            "kk",
            "karakeep \u63d2\u4ef6",
            "\u4e00\u4e2a\u641c\u7d22\u63d0\u4f9b\u8005\u63d2\u4ef6\uff0c\u628a facetmark "
            "\u63a5\u5230 karakeep \u81ea\u5df1\u7684\u641c\u7d22\u6846\u540e\u9762\u3002"
            "\u534f\u8bae\u683c\u5f0f\u7531\u4e00\u4e2a\u56de\u653e\u6d4b\u8bd5\u9489\u6b7b"
            "\u3002",
            "guide.zh.html#karakeep",
            "\u600e\u4e48\u63a5",
        ),
    ],
    "faq_label": "\u5e38\u89c1\u95ee\u9898",
    "faq_h2": "\u771f\u7684\u6709\u4eba\u95ee\u7684\u90a3\u516d\u4e2a",
    "faq": [
        (
            "我的数据会发到哪里？",
            "<p>书签库保存在运行服务的机器上。网页抓取会访问收藏的网站；使用在线模型时，相关文本与查询会发送到你配置的服务商。服务器部署时，导入文件会传到该服务器。</p><p>本地向量模型可在模型文件下载后本机计算。是否调用在线对话模型取决于你的配置；facetmark "
            "不提供托管账户或集中存储服务。</p>",
        ),
        (
            "会动我浏览器里的书签吗？",
            "<p>不会。导入是单向只读。导入器打开浏览器配置里的 <code>Bookmarks</code> 文件或者你导出的 "
            "HTML，读完就关。代码里没有任何一处往浏览器配置里写东西。</p><p>facetmark 这边也不删。衰减层只会把陈旧页面往后排，从来不删行。</p>",
        ),
        (
            "完全不用大模型能用吗？",
            "<p>能，会差，而且它会告诉你差在哪。不接模型，你保留两个词面、整套保存会话和域名图。你失去内容面 —— 就是测得最好的那个 —— "
            "和意图面。</p><p>折中方案：只跑一个本地嵌入模型支撑内容面，不接 chat 模型。你失去摘要和生成意图，保住换说法搜索。</p>",
        ),
        (
            "建索引需要多少时间和费用？",
            "<p>费用取决于页面数量、文本长度、所选模型和服务商定价。先用少量书签验证连接和结果，再处理完整书签库。</p><p>抓取速度还受网站响应、访问限制和按域名限速影响。后续运行会复用未变化的阶段；缺少正文和已生成向量是两种不同的状态。</p>",
        ),
        (
            "为什么默认只开一个面？",
            "<p>因为四面融合在 479 条真实查询上被测了，结果比单独用内容面<em>低</em> 5.4 个百分点的 Recall@5，延迟还高 3.5 倍。</p><p>机制也写下来了：平权重的 RRF "
            "下，两个弱面碰巧的一致（0.0279）能投赢一个强面的确定（0.0164）。四个面都还在，都还有测试。<code>--config C</code> 一下就全打开了，你可以自己看。</p>",
        ),
        (
            "适合用来做什么？",
            "<p>适合想自己管理书签数据、按内容找回旧资料，并愿意配置本机或服务器环境的人。它也提供 CLI、HTTP API 和 "
            "MCP，方便接入已有工具。</p><p>检索效果有明确边界：目前公开评测的查询由项目作者编写。请结合自己的书签验证，不把单一数据集的数字当作保证。</p>",
        ),
    ],
    "bnd_label": "\u8fb9\u754c",
    "bnd_h2": "\u8fd9\u4e2a\u4e1c\u897f\u62d2\u7edd\u505a\u7684\u4e8b",
    "bnd": [
        (
            "\u5bf9\u4f60\u7684\u6d4f\u89c8\u5668\u53ea\u8bfb",
            "\u5bfc\u5165\u4ece\u4e0d\u5199\u56de\u3002\u4f60\u7684\u6587\u4ef6\u5939\u6811"
            "\u8fd8\u662f\u4f60\u7684\u3002",
        ),
        (
            "\u4ec0\u4e48\u90fd\u4e0d\u5220",
            "\u51b7\u5c42\u53ea\u964d\u6743\u3002\u5b83\u4e0d\u5220\u884c\uff0c\u800c\u4e14 <code>facetmark health</code> \u4f1a\u544a\u8bc9\u4f60\u5b83\u8ba4\u4e3a\u54ea"
            "\u4e9b\u6b7b\u4e86\u3001\u4e3a\u4ec0\u4e48\u3002",
        ),
        (
            "\u672c\u5730\u4f18\u5148",
            "\u4e00\u4e2a SQLite \u6587\u4ef6\uff0c\u4efb\u4f55 SQLite \u5de5\u5177\u90fd"
            "\u80fd\u6253\u5f00\u3002\u5c31\u7b97\u4f60\u4e0d\u7528 facetmark \u4e86\uff0c"
            "\u6570\u636e\u4e5f\u8fd8\u8bfb\u5f97\u51fa\u6765\u3002",
        ),
        (
            "\u9ed8\u8ba4\u5c31\u5f88\u793c\u8c8c",
            "\u9075\u5b88 robots.txt\uff0c\u5355\u57df\u540d\u5e76\u53d1\u5c01\u9876 2\uff0c"
            "\u540c\u4e00\u4e3b\u673a\u4e24\u6b21\u8bf7\u6c42\u4e4b\u95f4\u6709\u6700\u5c0f"
            "\u95f4\u9694\uff0cUA \u91cc\u5199\u6e05\u695a\u81ea\u5df1\u662f\u8c01\u3002",
        ),
        (
            "\u6ca1\u6709\u534f\u8bae\u5c31\u4e0d\u62a5\u6570\u5b57",
            "\u6ca1\u6709\u4e00\u5957\u63d0\u524d\u51bb\u7ed3\u7684\u67e5\u8be2\u96c6\uff0c"
            "\u5c31\u4e0d\u6539\u9ed8\u8ba4\u503c\u3002",
        ),
    ],
    "end_h2": "让收藏重新派上用场",
    "end_p": ("从一小份书签开始。完成第一次搜索后，再按需要接入模型和其他工具。"),
    "end_cta": [
        ("阅读上手教程", "quickstart.zh.html", True),
        ("查看源码", "https://github.com/88lin/facetmark", False),
    ],
}

# ---------------------------------------------------------------- 指南 ----

ZH["quickstart"] = {
    "h1": "快速上手",
    "lede": ("从导入书签到完成第一次搜索。每一步都有检查方法；本机使用和服务器管理分别说明。"),
    "toc_title": "操作步骤",
    "sections": [
        (
            "install",
            "安装与检查",
            [
                (
                    "p",
                    "需要 Python 3.10 或更新版本，支持 Windows、macOS 和 Linux。以下命令在终端运行；macOS / Linux 如果没有 "
                    "<code>python</code>，请使用 <code>python3</code>。",
                ),
                (
                    "cb",
                    "shell",
                    "python --version\npython -m pip install facetmark\nfacetmark --version",
                ),
                (
                    "callout",
                    "",
                    "检查结果",
                    "<p>最后一条命令应输出版本号。如果提示找不到命令，试试 <code>python -m facetmark --version</code>；后续命令也可用这个模块入口。</p>",
                ),
            ],
        ),
        (
            "import",
            "导入一份书签",
            [
                ("p", "在自己的电脑上，可以自动读取 Chromium 系浏览器的书签。关闭浏览器后运行："),
                ("cb", "shell", "facetmark import"),
                (
                    "p",
                    "Firefox、Safari 或服务器部署：从浏览器导出书签 HTML，再把文件放到运行 facetmark 的机器上。路径包含空格时保留引号。",
                ),
                ("cb", "shell", 'facetmark import "bookmarks.html"\nfacetmark stats'),
                (
                    "callout",
                    "",
                    "检查结果",
                    "<p>导入会报告新增、更新与跳过数量，<code>stats</code> 中的书签总数应大于 0。它不会修改浏览器里的原始书签。找不到配置文件时，改用导出的 HTML。</p>",
                ),
            ],
        ),
        (
            "model",
            "选择搜索方式",
            [
                (
                    "p",
                    "暂时不配置模型也能按词搜索。需要“换个说法也能找到”时，再选择在线向量服务或本地向量模型。",
                ),
                ("h3", "在线模型"),
                (
                    "p",
                    "在运行命令的工作目录手动创建 <code>.env</code>。下面以 OpenAI 兼容接口为例；模型名称需与你的服务商一致。",
                ),
                (
                    "cb",
                    "dotenv",
                    "FACETMARK_BASE_URL=https://api.openai.com/v1\n"
                    "FACETMARK_API_KEY=sk-your-key\n"
                    "FACETMARK_CHAT_MODEL=gpt-4o-mini\n"
                    "FACETMARK_EMBED_MODEL=text-embedding-3-small\n"
                    "FACETMARK_EMBED_DIM=1536",
                ),
                (
                    "callout",
                    "",
                    "先确认能力与数据流向",
                    "<p>对话与向量是两种能力，支持对话不代表支持向量。在线模型会收到相关文本和查询。请先用“设置 → 测试连接”分别验证，再处理完整书签库。</p>",
                ),
                ("h3", "本地向量模型"),
                ("cb", "shell", 'python -m pip install "facetmark[local]"'),
                (
                    "p",
                    "在 <code>.env</code> 中使用以下配置。首次运行需要下载模型文件；准备好本地模型后，向量在运行服务的机器上计算。",
                ),
                (
                    "cb",
                    "dotenv",
                    "FACETMARK_EMBED_BACKEND=local\nFACETMARK_LOCAL_EMBED_PATH=BAAI/bge-m3\nFACETMARK_EMBED_DIM=1024",
                ),
                ("p", '<a href="config.zh.html">完整配置、优先级与服务商示例 →</a>'),
            ],
        ),
        (
            "index",
            "建立索引",
            [
                ("cb", "shell", "facetmark index\nfacetmark stats"),
                (
                    "p",
                    "索引会依次抓取网页、准备摘要与向量、整理浏览批次和关联。具体阶段取决于模型配置。抓取遵守网站限制，大型书签库可能需要较长时间。",
                ),
                (
                    "callout",
                    "",
                    "检查正文与向量两个指标",
                    "<p>在“书签库”查看正文覆盖和内容向量数量。向量数量不代表所有网页都抓到了正文；只有标题的书签也可能有衍生索引。</p>",
                ),
                (
                    "p",
                    "只想先验证流程，可运行 <code>facetmark index --no-fetch</code> 跳过网页下载。之后再次运行 <code>facetmark index</code> "
                    "补全内容；未变化的阶段会复用。",
                ),
            ],
        ),
        (
            "open",
            "打开应用并搜索",
            [
                ("cb", "shell", "facetmark serve"),
                (
                    "p",
                    "保持终端运行，在同一台电脑打开 <a "
                    'href="http://127.0.0.1:8787/app">http://127.0.0.1:8787/app</a>。端口以终端打印的地址为准。先用一个确定出现在书签标题里的词搜索，再尝试内容描述。',
                ),
                (
                    "shot",
                    "assets/app-search-zh.png",
                    "facetmark 搜索页，上面是排好序的结果，下面是当时前后一起存的那一组",
                    "<b>搜索。</b>第一屏是字面匹配，不花任何模型调用；排好序的答案到了就把它换掉。当时前后一起存的页面单独成一组，不会被打散混进排名里。这张图会跟着你正在读的这个页面切换深浅色。",
                    "assets/app-search-zh-dark.png",
                    "同一个搜索页的深色模式",
                ),
                ("p", '<a href="webui.zh.html">继续了解搜索、综述与书签库 →</a>'),
            ],
        ),
        (
            "server",
            "服务器访问与管理",
            [
                (
                    "p",
                    "命令必须在存放书签库的服务器上运行。远程电脑里的 <code>127.0.0.1</code> 指向远程电脑自身，并不指向服务器。公共域名上的应用需要配对令牌。",
                ),
                ("cb", "shell", "facetmark token"),
                (
                    "p",
                    "在服务器运行上面的命令，把令牌填入自己的应用配对框。它授予书签库访问权限，请勿公开。设置、导入和索引管理还要求本机连接；远程管理推荐使用 SSH 转发。",
                ),
                ("cb", "shell", "ssh -N -L 8788:127.0.0.1:8787 your-user@your-server"),
                (
                    "callout",
                    "",
                    "管理入口",
                    "<p>替换用户名与服务器地址，在你的电脑上保持 SSH 命令运行，然后打开 "
                    "<code>http://127.0.0.1:8788/app</code>。如果仍提示管理不可用，检查服务器是否配置了 "
                    "<code>FACETMARK_ADMIN_API=false</code>。</p>",
                ),
            ],
        ),
        (
            "read",
            "理解结果与来源",
            [
                (
                    "p",
                    "结果徽章说明匹配信号；详情中的“可回答的问题”由模型生成，不是搜索历史。生成摘要可能仅依据标题，界面会标明这种情况。",
                ),
                (
                    "ul",
                    [
                        "默认模式：有向量模型时使用内容向量、图谱扩展与时间衰减。",
                        "搜索选项：可比较其他检索组合，部分组合会增加模型调用。",
                        "关联结果：与排名结果分组展示，用于继续浏览相关页面。",
                        "综述：根据已存摘要或片段生成回答。引用帮助追溯来源，仍需核对原文。",
                    ],
                ),
            ],
        ),
        (
            "trouble",
            "常见问题与恢复",
            [
                (
                    "table",
                    ["现象", "下一步"],
                    [
                        [
                            "页面打不开",
                            "确认 serve 仍在运行。端口被占用时使用 <code>facetmark serve --port 8788</code>，并访问新端口。",
                        ],
                        [
                            "要求令牌 / 401",
                            "在运行服务的机器上执行 <code>facetmark token</code>，重新配对。",
                        ],
                        [
                            "设置不可用 / 403",
                            "使用本机地址或上面的 SSH 转发入口；令牌不会解除管理接口的本机限制。",
                        ],
                        [
                            "按词能搜，换说法搜不到",
                            "检查向量模型连接、维度与内容向量数量，配置正确后重新建索引。",
                        ],
                        [
                            "模型返回 404 / 429",
                            "404：核对服务商的完整 base URL 和模型名。429：降低并发并按服务商要求重试。",
                        ],
                    ],
                ),
                ("cb", "shell", "facetmark doctor\nfacetmark stats"),
                (
                    "p",
                    '仍有问题时，记录版本、操作和脱敏后的错误信息。<a href="guide.zh.html#trouble">查看完整排错参考</a>。',
                ),
            ],
        ),
    ],
}


ZH["guide"] = {
    "h1": "命令与接口参考",
    "lede": (
        "按任务查找导入、检索语法、分页、HTTP API、扩展和配置项。首次使用建议先完成快速上手，再回到这里查具体参数。"
    ),
    "toc_title": "\u672c\u9875\u76ee\u5f55",
    "sections": [
        (
            "install",
            "安装",
            [
                (
                    "p",
                    "Python 3.10 以上，Windows / macOS / Linux 都行。基础安装没有任何需要编译的机器学习依赖；向量检索来自 <code>sqlite-vec</code>，它是一个 "
                    "SQLite 扩展。",
                ),
                (
                    "cb",
                    "shell",
                    "pip install facetmark\n# 或者用 uv：\nuv pip install facetmark\n\nfacetmark version",
                ),
                ("h3", "带本地嵌入"),
                (
                    "p",
                    "只有你想在自己机器上算嵌入、而不走端点时才需要。它会拉 PyTorch 和 <code>sentence-transformers</code>，几百 MB。",
                ),
                ("cb", "shell", 'pip install "facetmark[local]"'),
                ("h3", "从源码装"),
                (
                    "cb",
                    "shell",
                    "git clone https://github.com/88lin/facetmark\n"
                    "cd facetmark\n"
                    "python -m venv .venv && . .venv/bin/activate\n"
                    'pip install -e ".[dev]"\n'
                    "\n"
                    "pytest -q                 # 1,700+ 个测试\n"
                    "ruff check src tests scripts",
                ),
                (
                    "callout",
                    "warn",
                    "不要格式化代码库",
                    "<p>它是手写排版的。CI 跑的是 <code>ruff check</code>，不是 <code>ruff format</code>；跑后者会生成一份没人想 review 的 "
                    "diff。</p>",
                ),
                ("h3", "数据存在哪"),
                (
                    "p",
                    "一个目录，按平台选，里面一个 SQLite 文件。用 <code>FACETMARK_DATA_DIR</code> 换目录，或者用 <code>--db</code> 给单条命令指一个文件。",
                ),
                (
                    "table",
                    ["平台", "默认数据目录"],
                    [
                        ["Windows", "<code>%LOCALAPPDATA%\\facetmark\\</code>"],
                        ["Linux / macOS", "<code>~/.local/share/facetmark/</code>"],
                        [
                            "设了 <code>XDG_DATA_HOME</code> 时",
                            "<code>$XDG_DATA_HOME/facetmark/</code>",
                        ],
                    ],
                ),
                (
                    "p",
                    "数据目录通常包含数据库、配对令牌及可选的配置文件。备份时分别保管数据库与密钥；路径以 <code>facetmark stats</code> 和 <code>facetmark config "
                    "path</code> 的输出为准。",
                ),
                ("h3", "没 key 没网也能先试"),
                (
                    "p",
                    "<code>facetmark demo</code> 会造一个合成库，用确定性的离线 provider 建索引，然后跑三条搜索。首页那个终端就是这么录的。",
                ),
                ("cb", "shell", "facetmark demo --size 60"),
            ],
        ),
        (
            "import",
            "把书签导进来",
            [
                ("p", "导入是单向只读的。facetmark 读浏览器配置或者导出文件，两者都不写。"),
                ("h3", "Chromium 系：不用导出"),
                (
                    "p",
                    "Chrome、Edge、Brave、Vivaldi、Chromium、Opera 和 Opera GX 都把书签放在一个 JSON 文件里，facetmark "
                    "能自己找到。浏览器开着也能安全读。",
                ),
                (
                    "cb",
                    "shell",
                    "facetmark browsers        # 它能看到哪些\nfacetmark import          # 只有一个时直接导",
                ),
                (
                    "p",
                    "装了多个配置时，它不猜 —— 导错人的书签比多敲一条命令糟糕得多。它会把候选列出来，你自己指：",
                ),
                ("cb", "shell", 'facetmark import "$HOME/.config/google-chrome/Default/Bookmarks"'),
                ("h3", "Firefox 和 Safari：先导出 HTML"),
                (
                    "table",
                    ["浏览器", "导出入口"],
                    [
                        ["Firefox", "书签 → 管理书签 → 导入和备份 → <b>将书签导出为 HTML</b>"],
                        ["Safari", "文件 → 导出 → <b>书签</b>"],
                        [
                            "Chrome / Edge（手动路线）",
                            "<code>chrome://bookmarks</code> → ⋮ → <b>导出书签</b>",
                        ],
                        [
                            "其他",
                            "任何 Netscape 格式的 <code>bookmarks.html</code> 都行。这是 1994 年的格式，到今天所有人还在写它。",
                        ],
                    ],
                ),
                ("cb", "shell", "facetmark import ~/Downloads/bookmarks.html"),
                ("h3", "导入会报什么"),
                (
                    "p",
                    "同一条命令同时处理 Netscape HTML 和 Chrome JSON，并且报它干了什么，而不是转一个圈。在一份真实的 1.7&nbsp;MB 导出上（96 个文件夹、四层嵌套）：解析 "
                    "1,710 条，写入 1,701 条，合并 9 条重复，1 条不可索引。",
                ),
                (
                    "table",
                    ["字段", "含义"],
                    [
                        ["<code>parsed</code>", "文件里找到的条目数。"],
                        [
                            "<code>inserted</code> / <code>updated</code>",
                            "新写入的，以及标题或文件夹变了的。",
                        ],
                        ["<code>merged_duplicates</code>", "同一个 URL 存了两次，取时间早的那个。"],
                        [
                            "<code>non_indexable</code>",
                            "<code>javascript:</code>、<code>place:</code>、<code>file:</code> 之类。",
                        ],
                        [
                            "<code>missing_dates</code>",
                            "没有保存时间的。照样导入，但进不了保存会话。",
                        ],
                        [
                            "<code>privacy_skipped</code>",
                            "被 <code>FACETMARK_PRIVACY_EXCLUDED_DOMAINS</code> 挡下的。",
                        ],
                        [
                            "<code>timestamp_unit</code>",
                            "源文件用的是哪种时间戳。Chrome 和 Netscape 不一样，这里告诉你识别出的是哪种。",
                        ],
                    ],
                ),
                (
                    "callout",
                    "info",
                    "先排除域名，再导入",
                    "<p>把 <code>FACETMARK_PRIVACY_EXCLUDED_DOMAINS</code> "
                    "设成逗号分隔的列表，这些主机就不会被写入、不会被抓、也不会被嵌入。比事后删行省事。</p>",
                ),
            ],
        ),
        (
            "models",
            "模型接入",
            [
                (
                    "p",
                    "在线模型共用一个 OpenAI 兼容的 <code>base_url</code> 和 "
                    "<code>api_key</code>。确认端点同时提供需要的对话与向量能力；兼容网关、自托管服务或本地向量后端可以补足服务商缺少的能力。",
                ),
                (
                    "p",
                    "对话模型生成摘要、主题、实体、要点和候选问题；向量模型把页面文本与查询转换为向量。没有正文时，部分衍生内容可能依据标题生成。",
                ),
                ("h3", "走端点"),
                (
                    "cb",
                    "shell",
                    "export FACETMARK_API_KEY=sk-...\n"
                    "export FACETMARK_BASE_URL=https://api.openai.com/v1\n"
                    "export FACETMARK_CHAT_MODEL=gpt-4o-mini\n"
                    "export FACETMARK_EMBED_MODEL=text-embedding-3-small\n"
                    "export FACETMARK_EMBED_DIM=1536",
                ),
                (
                    "callout",
                    "warn",
                    "base URL 必须以 /v1 结尾",
                    "<p>这是最常见的配置失败，没之一。少了 <code>/v1</code>，每一次调用都 404，包括第一次；而错误是从 provider 那边回来的，看起来像是密钥问题。</p>",
                ),
                (
                    "p",
                    "不想设环境变量，可以在运行目录放一个 <code>.env</code>。名字一样，前缀一样。",
                ),
                (
                    "cb",
                    "dotenv",
                    "FACETMARK_API_KEY=sk-...\n"
                    "FACETMARK_BASE_URL=https://api.deepseek.com/v1\n"
                    "FACETMARK_CHAT_MODEL=deepseek-chat",
                ),
                ("h3", "共享端点或免费端点"),
                (
                    "p",
                    "备用对话模型按配置顺序尝试。请先确认每个模型在当前账户和端点可用；不要用备用链掩盖错误的接口地址或权限。",
                ),
                ("cb", "shell", "export FACETMARK_CHAT_MODEL_FALLBACKS=deepseek-chat,qwen-plus"),
                (
                    "p",
                    "provider 会记录每一次调用到底是哪个模型答的。任何建立在降级链上的报告，都必须把这个混合比例公开。",
                ),
                ("h3", "本地嵌入，不要 key"),
                (
                    "p",
                    "本地向量使用 <code>sentence-transformers</code>。首次下载模型后可在服务所在机器计算；网页抓取仍会联网。若保留在线对话配置，摘要与综述仍可能调用该服务。",
                ),
                (
                    "cb",
                    "shell",
                    'pip install "facetmark[local]"\n'
                    "\n"
                    "export FACETMARK_EMBED_BACKEND=local\n"
                    "export FACETMARK_EMBED_MODEL=bge-m3\n"
                    "export FACETMARK_EMBED_DIM=1024\n"
                    "export FACETMARK_LOCAL_EMBED_PATH=/path/to/bge-m3   # 不设就下载\n"
                    "export FACETMARK_LOCAL_EMBED_MAX_SEQ=1024",
                ),
                (
                    "callout",
                    "info",
                    "为什么序列长度默认是 1024",
                    "<p>同一篇文档嵌入两次，必须落在同一个地方。bge-m3 在 1024 token 下，一个固定的 64 篇探针集上最小自余弦是 <b>0.999976</b>，64/64 全部自匹配。降到 "
                    "512 token，最小值掉到 <b>0.9769</b> —— 因为截断开始从同一段文本上剪掉不同的量。所以默认是 1024，而且调低它是一笔真的交易。</p>",
                ),
                (
                    "callout",
                    "bad",
                    "改维度等于作废所有向量",
                    "<p><code>FACETMARK_EMBED_DIM</code> 在第一次建索引时写进 <code>meta</code> "
                    "表。之后对不上就报错，而不是默默把不兼容的向量混在一起。换嵌入模型或换维度，请用 <code>facetmark index --force</code> 重算。</p>",
                ),
                ("h3", "一个模型都不接"),
                (
                    "p",
                    "照装照跑。你保留两个词面、保存会话、域名与链接图、链接健康。你失去内容面和意图面。<code>facetmark search --quick</code> "
                    "是明确的纯词面路径，一次模型调用都不发。",
                ),
            ],
        ),
        (
            "index",
            "建索引",
            [
                ("cb", "shell", "facetmark index"),
                (
                    "p",
                    "索引按阶段执行，并通过输入指纹复用已完成的工作。新增书签或正文、模型配置变化时，相应阶段需要更新；请查看实际任务输出。",
                ),
                (
                    "table",
                    ["阶段", "干什么", "要模型吗？"],
                    [
                        [
                            "<code>fetch</code>",
                            "抓页面，遵守 robots.txt 和单域名限速，抽取可读正文。",
                            "不要",
                        ],
                        [
                            "<code>enrich</code>",
                            "摘要、主题、实体、要点 —— 每页一次小的 chat 调用。",
                            "chat",
                        ],
                        ["<code>embed_content</code>", "把重建后的文本嵌入。", "嵌入"],
                        ["<code>intents</code>", "为每页生成候选查询。", "chat"],
                        [
                            "<code>filter_intents</code>",
                            "只留下能把这页搜回来的那些。典型情况下不到一半能活。",
                            "不要",
                        ],
                        ["<code>embed_intents</code>", "把存活下来的意图嵌入。", "嵌入"],
                        [
                            "<code>sessions</code>",
                            "按时间间隔把保存行为聚成一次次会话，间隔选哪个由「覆盖率 × 相对打乱对照的纯度提升」决定。",
                            "不要",
                        ],
                        ["<code>edges</code>", "建会话边、语义边、同域名边和替代边。", "不要"],
                    ],
                ),
                ("h3", "常用参数"),
                (
                    "table",
                    ["参数", "作用"],
                    [
                        [
                            "<code>--no-fetch</code>",
                            "完全不抓网，只索引标题。几秒钟而不是几小时，效果也弱很多。",
                        ],
                        [
                            "<code>--limit N</code>",
                            "每阶段只处理 N 条。适合先看一眼这一跑到底要多少钱。",
                        ],
                        ["<code>--force</code>", "不看指纹，已经做过的也重做。"],
                        [
                            "<code>--mock</code>",
                            "确定性离线 provider。不要 key、不联网、也没质量。",
                        ],
                        ["<code>--json</code>", "每个阶段的机器可读报告，含各阶段耗时。"],
                    ],
                ),
                ("h3", "指纹是怎么算的"),
                (
                    "ul",
                    [
                        "<b>富化</b>按正文哈希。正文没变，就不发第二次 chat 请求。",
                        "<b>嵌入</b>按<em>重建后的嵌入文本</em>，而不是按正文。所以富化变了、嵌入文本跟着变了，那个陈旧向量会被发现 —— karakeep 往返的损伤就是这么插出来的。",
                        "<b>会话和边</b>每次重建；它们便宜，而且依赖整个库。",
                    ],
                ),
                (
                    "p",
                    "<code>facetmark reindex</code> 把所有衍生产物丢掉，从书签本身重建。<code>facetmark migrate</code> 把旧库升到当前 "
                    "schema，默认先快照一份，除非你加 <code>--no-backup</code>。",
                ),
                ("h3", "这一跑的代价"),
                (
                    "p",
                    "费用由文本长度、模型和服务商定价决定，建议先处理小样本。耗时还受网页抓取和站点限流影响；默认单主机并发为 2，并保留请求间隔。",
                ),
                (
                    "p",
                    "给个量级感：刚才那个真实的 1,700 条书签库，用 <code>--no-fetch</code> 建索引，得到 322 个保存会话、9,132 条边、1,386 个域名、1,775 "
                    "个向量。",
                ),
            ],
        ),
        (
            "search",
            "搜索",
            [
                (
                    "cb",
                    "shell",
                    'facetmark search "那篇讲把向量存在 sqlite 里的"\n'
                    'facetmark search "sqlite-vec" -n 20 --explain\n'
                    'facetmark search "error EADDRINUSE" --quick',
                ),
                (
                    "table",
                    ["参数", "作用"],
                    [
                        ["<code>-n, --limit</code>", "返回多少条。默认 10。"],
                        ["<code>--quick</code>", "只走词面。不调模型、不联网、亚毫秒级。"],
                        [
                            "<code>--explain</code>",
                            "打印每条命中的是哪个面。搞清楚「它为什么排在这」最快的办法。",
                        ],
                        [
                            "<code>--config NAME</code>",
                            "跑指定的 profile 或消融档。默认 <code>full</code>。",
                        ],
                        ["<code>--json</code>", "机器可读，包含每个阶段的耗时。"],
                    ],
                ),
                ("h3", "profile 和消融档"),
                (
                    "p",
                    "<code>--config</code> 接受任何预注册档、任何出厂 profile，以及大约 20 个探索性消融档。档位的定义在 "
                    "<code>search/pipeline.py</code> 里。",
                ),
                (
                    "table",
                    ["名字", "面与阶段", "状态"],
                    [
                        [
                            "<code>A</code>",
                            "只用内容向量",
                            '<span class="badge pass">W1 赢家 · 0.643</span>',
                        ],
                        [
                            "<code>B</code>",
                            "内容 + 两个词面",
                            '<span class="badge fail">−5.4pp</span>',
                        ],
                        ["<code>C</code>", "四个面全上", "已实测"],
                        ["<code>D</code>", "四面 + 上下文 + 图", "已实测"],
                        ["<code>E</code>", "四面 + 上下文 + 图 + 重排", "已实测"],
                        [
                            "<code>full</code>",
                            "内容 + 图 + 衰减",
                            '<span class="badge info">真实 provider 下的默认</span>',
                        ],
                        [
                            "<code>fused</code>",
                            "四面 + 上下文 + 图 + 重排 + 衰减",
                            '<span class="badge info">mock provider 下的默认</span>',
                        ],
                    ],
                ),
                (
                    "callout",
                    "info",
                    "为什么 mock 下默认不一样",
                    "<p>mock 是把文本哈希成向量的，所以内容面 —— 在真实库上完胜的那个 —— 恰好就是在 mock "
                    "下返回噪声的那个。在那种部署下再把词面去掉，就什么能用的都不剩了。有真实嵌入的拿实测结论；其他人拿门控之前的行为，至少能按词搜。</p>",
                ),
                ("h3", "排名是怎么构成的"),
                (
                    "p",
                    "选中的每个面各返回最多 <code>CANDIDATES_PER_FACET</code> 条候选。RRF 按 <code>sum_f w_f / (k + rank_f)</code> "
                    "合并，<code>k = 60</code>。然后按顺序跑上下文、衰减、重排；一跳图扩展作为<em>单独一组</em>返回 —— "
                    "不混进排名，因为当初测的就是它作为“补充”的效果，不是“替代”。",
                ),
                (
                    "callout",
                    "warn",
                    "名次列和分数列不一致",
                    "<p>这是设计如此。重排会重排前 20 条，但故意保留每条上的融合分，所以重排过的列表看起来分数是乱的。如果它把分数覆盖了，你就再也看不到融合当时是怎么想的。</p>",
                ),
                ("h3", "看一次保存会话"),
                (
                    "cb",
                    "shell",
                    "facetmark sessions -n 20     # 最近的保存会话\n"
                    "facetmark show 412 --body    # 一条书签的 JSON\n"
                    "facetmark stats              # 索引规模与覆盖率",
                ),
            ],
        ),
        (
            "query",
            "查询语言",
            [
                (
                    "p",
                    "所有检索入口用的是同一套语法：网页搜索框、<code>facetmark search</code>、<code>/search</code> 与 <code>/quick</code>、MCP "
                    "工具、karakeep 插件。它是一门<em>过滤</em>语言，不是第二个排序器——过滤器只决定哪些页面有资格，从不改动幸存页面的分数。完整参考：<a "
                    'href="https://github.com/88lin/facetmark/blob/main/docs/query-language.md">docs/query-language.md</a>。',
                ),
                (
                    "cb",
                    "shell",
                    'facetmark search "postgres domain:github.com -title:tutorial"\n'
                    'facetmark search "kafka added:<7d"          # 这周存的\n'
                    "facetmark search 'title:encryption (signal|matrix)'\n"
                    'facetmark search "tag:work sort:date"       # 一次浏览，按时间倒序',
                ),
                (
                    "table",
                    ["字段", "匹配什么", "例子"],
                    [
                        [
                            '<code>domain:</code> <span class="tiny">别名 <code>site:</code></span>',
                            "站点，精确或通配",
                            "<code>domain:github.com</code>",
                        ],
                        [
                            "<code>host:</code>",
                            "完整主机名",
                            "<code>host:news.ycombinator.com</code>",
                        ],
                        ["<code>url:</code>", "地址的一部分", "<code>url:*/docs/*</code>"],
                        ["<code>title:</code>", "只在标题里", "<code>title:encryption</code>"],
                        [
                            "<code>text:</code>",
                            "抓下来的正文里",
                            '<code>text:"GDPR compliance"</code>',
                        ],
                        [
                            "<code>folder:</code>",
                            "来自哪个浏览器文件夹",
                            "<code>folder:study</code>",
                        ],
                        ["<code>tag:</code>", "你自己的标签，精确匹配", "<code>tag:work</code>"],
                        ["<code>topic:</code>", "富集写出来的主题", "<code>topic:postgres</code>"],
                        ["<code>lang:</code>", "检测到的页面语言", "<code>lang:zh</code>"],
                        ["<code>opened:</code>", "你打开过几次", "<code>opened:10..</code>"],
                    ],
                ),
                ("h3", "否定、短语、多选、通配"),
                (
                    "cb",
                    "shell",
                    "-facebook                    排除一个词\n"
                    "-domain:pinterest.com        排除整个站\n"
                    '"consumer group rebalancing"  精确短语\n'
                    "(security|privacy)           两个词任一\n"
                    "domain:(github.com|gitlab.com)   两个值任一\n"
                    "domain:*.github.io           * 是任意长度的一段字符",
                ),
                ("h3", "日期"),
                (
                    "p",
                    "写<em>时长</em>时比的是书签的年龄，所以 <code>added:&gt;90d</code> 是「存了 90 天以上」。写<em>绝对日期</em>时直接比时间戳，所以 "
                    "<code>added:&gt;=2026-04-01</code> 是「那天及之后存的」。两者方向相反，因为对各自的写法来说，这都是唯一自然的读法。",
                ),
                (
                    "table",
                    ["写法", "含义"],
                    [
                        ["<code>added:&lt;7d</code>", "最近一周存的"],
                        ["<code>added:&gt;90d</code>", "存了 90 天以上"],
                        ["<code>added:2026-04</code>", "那个月存的"],
                        ["<code>added:2026-04-01..2026-09-01</code>", "一个显式区间"],
                        [
                            "<code>before:2026-05-01</code> <code>after:30d</code>",
                            "<code>added:</code> 的别名；这两个上的时长按年龄读，所以 <code>after:30d</code> 是最近 30 天",
                        ],
                    ],
                ),
                ("h3", "排序，以及什么叫一次浏览"),
                (
                    "p",
                    "<code>sort:date</code> 最新在前，<code>sort:-date</code> 最旧在前；也支持 "
                    "<code>title</code>、<code>domain</code>、<code>url</code> 和 "
                    "<code>opened</code>。只有过滤器或排序指令、没有自由文本时，查询直接浏览书签，不调用模型。纯词面搜索和本地向量搜索也不产生在线向量费用。",
                ),
                (
                    "callout",
                    "info",
                    "不带语法的查询行为不变",
                    "<p>解析器只在一个 token「不可能是纯文本」时才把它当语法。<code>note: something</code> 不是过滤器，因为 <code>note</code> "
                    "不是字段；<code>state-of-the-art</code> 不是三个否定；<code>https://example.com/x</code> 是一个完整的词。而解析不了的值——比如 "
                    "<code>added:90d</code>，一个没有比较符的时长——会出现在响应的 <code>filters.ignored</code> 里，既不悄悄生效，也不悄悄丢掉。</p>",
                ),
                ("h3", "你自己的标签"),
                (
                    "p",
                    "Netscape 与 pinboard 导出带着 <code>TAGS</code> 属性，现在它被保留下来：存在书签上、随每条命中返回、并且可以用 <code>tag:work</code> "
                    "查询。匹配的是列表里完整的一个元素，所以 <code>tag:work</code> 不会扩到 <code>workshop</code>；要匹配多个用 "
                    "<code>tag:(work|rust)</code>。<code>POST /bookmark</code> 和 MCP 的 <code>save_bookmark</code> 也接受 "
                    "<code>tags</code>；重复导入同一个文件时标签取并集而不是覆盖。",
                ),
            ],
        ),
        (
            "serve",
            "起服务：HTTP API 与配对令牌",
            [
                ("cb", "shell", "facetmark serve        # 127.0.0.1:8787"),
                (
                    "callout",
                    "warn",
                    "只听回环地址不算鉴权",
                    "<p>除了 <code>/</code>、<code>/health</code>，以及本地页面加载自己用的 <code>/app</code> 和 "
                    "<code>/app/boot</code>，每条路由都要令牌，在 localhost 上也要 —— 因为你机器上任何一个进程都能访问 127.0.0.1。<code>--host</code> "
                    "不是回环地址时，<code>facetmark serve</code> 会告警：这个索引里是你整个浏览兴趣图谱。</p>",
                ),
                ("h3", "令牌"),
                (
                    "p",
                    "令牌首次运行时生成，保存在数据目录的 <code>pairing-token.txt</code>。请求可使用 <code>Authorization: Bearer "
                    "&lt;token&gt;</code> 或 <code>x-facetmark-token</code>。不要把令牌放入公开链接或日志。",
                ),
                (
                    "cb",
                    "shell",
                    "facetmark token             # 打印\nfacetmark token --rotate    # 作废旧的",
                ),
                (
                    "cb",
                    "shell",
                    "TOKEN=$(facetmark token)\n"
                    "\n"
                    "curl -s http://127.0.0.1:8787/health\n"
                    "\n"
                    "curl -s -X POST http://127.0.0.1:8787/search \\\n"
                    "  -H 'content-type: application/json' \\\n"
                    '  -H "x-facetmark-token: $TOKEN" \\\n'
                    '  -d \'{"q":"vectors inside sqlite","limit":5}\'',
                ),
                ("h3", "POST /search"),
                (
                    "table",
                    ["字段", "类型", "含义"],
                    [
                        ["<code>q</code>", "string", "查询。必填。"],
                        ["<code>limit</code>", "int", "返回条数。"],
                        [
                            "<code>config</code>",
                            "string",
                            'profile 或档位名。<code>""</code> 和 <code>"full"</code> 都走 <code>default_config</code>。',
                        ],
                        ["<code>assist</code>", "bool", "允许模型参与的理解阶段。"],
                        ["<code>expand</code>", "bool", "同时返回一跳图扩展那一组。"],
                    ],
                ),
                ("h3", "全部路由"),
                (
                    "table",
                    ["分组", "路由"],
                    [
                        ["公开", "<code>GET /</code> · <code>GET /health</code>"],
                        [
                            "本地页面 —— 同样公开",
                            "<code>GET /app</code> · <code>GET /app/static/*</code> · <code>GET /app/boot</code>",
                        ],
                        [
                            "搜索",
                            "<code>GET /stats</code> · <code>GET /quick</code> · <code>POST /search</code> · <code>POST "
                            "/suggest</code> · <code>POST /synthesize</code>",
                        ],
                        [
                            "记录",
                            "<code>GET /bookmark/{id}</code> · <code>GET /bookmark/{id}/related</code> · <code>POST "
                            "/bookmark</code> · <code>POST /open</code>",
                        ],
                        ["会话", "<code>GET /sessions</code> · <code>GET /session/{id}</code>"],
                        [
                            "索引队列",
                            "<code>GET /queue/next</code> · <code>POST /queue/complete</code> · <code>GET "
                            "/queue/stats</code>",
                        ],
                        [
                            "链接健康",
                            "<code>GET /link-health/summary</code> · <code>GET /link-health/{id}</code> · <code>POST "
                            "/link-health/check</code> · <code>GET /graveyard</code>",
                        ],
                        [
                            "karakeep 桥",
                            "<code>POST /karakeep/documents</code> · <code>POST /karakeep/documents/delete</code> · "
                            "<code>POST /karakeep/search</code> · <code>POST /karakeep/clear</code> · <code>GET "
                            "/karakeep/stats</code>",
                        ],
                    ],
                ),
                (
                    "callout",
                    "",
                    "管理接口",
                    "<p>管理接口还检查连接来源，仅允许回环连接，并可通过 <code>FACETMARK_ADMIN_API=false</code> 关闭。远程管理请使用 <a "
                    'href="quickstart.zh.html#server">SSH 转发步骤</a>。</p>',
                ),
            ],
        ),
        (
            "webui",
            "本地页面",
            [
                (
                    "p",
                    "<code>facetmark serve</code> 同时提供 <code>/app</code> 应用和 HTTP "
                    "API。页面包含搜索、综述、书签库、浏览批次与系统状态，设置从齿轮入口进入。",
                ),
                (
                    "cb",
                    "shell",
                    "facetmark serve\n"
                    "# facetmark @@VERSION@@  http://127.0.0.1:8787\n"
                    "# open the search page:     http://127.0.0.1:8787/app\n"
                    "# pairing token written to the data directory\n"
                    "#   (facetmark config show lists the effective data_dir)",
                ),
                (
                    "p",
                    "Python 包里的纯 HTML、CSS 和 ES 模块：没有 Node，没有打包器，也就没有会和服务端对不上的构建产物。页面和 API 由同一个进程发出，所以是同源的 —— "
                    "这也是它没法托管到别处去的原因：这个服务的 CORS 只对浏览器扩展的来源开放。",
                ),
                ("h3", "两个视图"),
                (
                    "table",
                    ["视图", "地址", "干什么用"],
                    [
                        [
                            "搜索",
                            "<code>/app#/search</code>",
                            "搜索框和排好序的列表。一敲字先出字面匹配的结果，完全不调模型；排好序的答案到了就替换掉，<b>加载更多</b>翻后面的。",
                        ],
                        [
                            "书签库",
                            "<code>/app#/library</code>",
                            "<code>facetmark stats</code> "
                            "打印的所有东西，按行列出来：书签数、多少条抓到了正文、多少条做了向量、会话、按类型分的边、抓取队列、链接健康，还有冷层清点。“我搜了但什么都没有” 这个问题就靠这个视图回答。",
                        ],
                    ],
                ),
                (
                    "callout",
                    "info",
                    "它故意不做的事",
                    "<p>它只读。没有删除，没有编辑，没有队列控制，也没有综述按钮。那些在命令行和 API 里有，在那儿犯错至少是主动犯的。页面唯一写的一次，是你点开某条结果时的 <code>POST "
                    "/open</code>，冷层就是靠它喂的。</p>",
                ),
                ("h3", "结果行上的标记是什么意思"),
                (
                    "p",
                    "和扩展弹窗用的是同一套词。在页面里，每个标记鼠标悬停都有一行解释；这张表是为了让你一次看全。",
                ),
                (
                    "table",
                    ["标记", "意思", "默认"],
                    [
                        [
                            '<span class="chip mk">内容相关</span>',
                            "命中了<b>内容</b>面 —— 页面自己正文的向量。",
                            '<span class="badge info">开</span>',
                        ],
                        [
                            '<span class="chip mk">提问方式</span>',
                            "命中了<b>意图</b>面 —— 给这个页面生成的问题的向量。",
                            "关",
                        ],
                        [
                            '<span class="chip mk">词语</span>',
                            "命中了<b>字面 · 分词</b>面 —— 对标题、文件夹、网址里完整词的 FTS5。",
                            "关",
                        ],
                        [
                            '<span class="chip mk">子串</span>',
                            "命中了<b>字面 · 三元组</b>面 —— 对字符的 FTS5，中文查询和只打了一半的词能命中，靠的就是它。",
                            "关",
                        ],
                        [
                            '<span class="badge warn mk">已冷却</span>',
                            "很久以前存的，一直没打开过，而且有更新的东西看起来把它取代了。排名压低，绝不删除。",
                            '<span class="badge info">开</span>',
                        ],
                        [
                            '<span class="gmk mk">当时前后一起存的</span>',
                            "第二组：从上面某条结果出发，在链接图上走一跳。绝不混进排名里。",
                            '<span class="badge info">开</span>',
                        ],
                    ],
                ),
                (
                    "p",
                    "第二组里每一行都带着走到它的那条边 —— "
                    "<em>同一次浏览</em>（同一次上网时存的）、<em>语义相近</em>、<em>已被取代</em>、<em>同一页面</em>、<em>同一站点</em>。这些名字背后的权重在<a "
                    'href="#env">配置表</a>里。',
                ),
                ("h3", "页面怎么拿到令牌"),
                (
                    "p",
                    "它去问 <code>GET "
                    "/app/boot</code>。这是唯一一条能把配对令牌交出去的路由，而且只在调用方和请求里写的地址两者都是回环地址时才交。在你自己机器上两条都成立，页面就自己配对好了，没有什么要复制的。",
                ),
                (
                    "callout",
                    "warn",
                    "第二个条件是干什么的",
                    "<p>公网上的一个页面可以把某个域名解析到 127.0.0.1，然后让<em>你的</em>浏览器去发这个请求 —— 调用方确实是回环地址。但它改不了 <code>Host</code> "
                    "头，那里面还写着攻击者的域名。查这一项，才是拦住一个网站读走你令牌的东西；这也是为什么它是一条单独的路由，而不是挂在现有路由上的一个开关。</p><p>在反向代理后面，或者用局域网地址访问时，这个检查会不通过 "
                    "—— 这是故意的：页面这时给你一个输入框，把 <code>facetmark token</code> 粘一次就行。它存在那个浏览器的本地存储里，不在页面里。</p>",
                ),
                ("h3", "键盘"),
                (
                    "table",
                    ["按键", "作用"],
                    [
                        ["<kbd>/</kbd>", "在页面任何地方聚焦到搜索框。"],
                        ["<kbd>Enter</kbd>", "搜索。"],
                        [
                            "<kbd>↑</kbd> <kbd>↓</kbd>",
                            "在结果之间移动。在搜索框里按 <kbd>↓</kbd> 进入列表。",
                        ],
                        ["<kbd>Esc</kbd>", "清空查询，回到搜索框。"],
                    ],
                ),
                ("h3", "语言和主题"),
                (
                    "p",
                    "中英文和主题偏好保存在当前浏览器的当前站点。官网与应用使用同名偏好键，但不同域名的浏览器存储不会自动同步。界面尊重系统的减少动态效果设置。",
                ),
            ],
        ),
        (
            "paging",
            "翻页：limit、offset 和 depth",
            [
                (
                    "p",
                    "每个搜索入口都收 <code>limit</code>、<code>offset</code> 和 "
                    "<code>depth</code>，而每个搜索响应报的是它<em>实际</em>给出的那个窗口，不是把你要的原样回显。",
                ),
                (
                    "cb",
                    "shell",
                    'facetmark search "kafka rebalance" -n 20\n'
                    'facetmark search "kafka rebalance" -n 20 -o 20 --depth 60',
                ),
                (
                    "p",
                    "只要还有下一页，CLI 就会把下一页的 <code>--offset</code> 和 <code>--depth</code> 打出来。走 HTTP 时，同样这三个字段放在 "
                    "<code>POST /search</code> 的请求体里：",
                ),
                (
                    "cb",
                    "json",
                    "{\n"
                    '  "hits": [ ],\n'
                    '  "limit": 20,          // 实际给的，已经夹过\n'
                    '  "offset": 20,\n'
                    '  "depth": 60,          // 这次排名跑的深度\n'
                    '  "total": 137,         // 已经排过的条数；封顶时是下界\n'
                    '  "has_more": true,\n'
                    '  "depth_capped": false\n'
                    "}",
                ),
                (
                    "table",
                    ["字段", "含义"],
                    [
                        [
                            "<code>limit</code>",
                            "这一页的条数。会夹到 <code>MAX_PAGE_SIZE</code>，默认 200。",
                        ],
                        [
                            "<code>offset</code>",
                            "跳过的条数。会夹在 <code>MAX_CANDIDATE_DEPTH</code> 以下。",
                        ],
                        [
                            "<code>depth</code>",
                            "融合之前每个面各读多深。不填就按窗口推算；把上一页报的值原样送回来，这一页就接着<em>同一次</em>排名往下走。",
                        ],
                        [
                            "<code>total</code>",
                            "融合这一步排过的文档数。是个下界，不是书签库的总数；<code>depth_capped</code> 为真时更是明确只当下界看。",
                        ],
                        [
                            "<code>has_more</code>",
                            "这个窗口后面还有东西。在出厂的单面默认档下是准的；开了好几个面时是上界 —— 多出来的那一条有可能是候选池里已经有的文档。",
                        ],
                        [
                            "<code>depth_capped</code>",
                            "后面<em>确实</em>还有，而且停下来的原因是撞到了深度上限，不是你的窗口 —— 这是“点下一页”和“把深度调大，或者把查询收窄”之间的区别。",
                        ],
                    ],
                ),
                ("h3", "为什么 depth 是个参数，而不是实现细节"),
                (
                    "p",
                    "页面大小决定一次展示多少条，检索深度决定候选池范围。下一页沿用响应中的 <code>depth</code>，可以在同一个候选池上继续读取，避免翻页时改变排名依据。",
                ),
                (
                    "callout",
                    "warn",
                    "钉住 depth，否则第二页会和第一页打架",
                    "<p>只有在<em>一个</em>面的时候，RRF 才在候选池变大时保持名次稳定。一个文档的分数，是它在“深度以内排到了它”的那些面上求和，所以更深的池子可能凭空给某个文档补上一项 —— "
                    "而这一项可能压过对手的整个分数。在一个面上排第 2、在另一个面上排第 40，合起来赢过只在一个面上排第 1 的（1/62 + 1/100 对 1/61），但在深度 30 "
                    "时后面那一项根本不存在。</p><p>所以开了好几个面时，为了翻到第 2 页而把深度加大，会让第 2 页对“第 1 页是什么”这件事和第 1 页产生分歧。解法不是加大它：把上一页报的 "
                    "<code>depth</code> 原样送回来，每一页就都是同一次排名的一个切片。本地页面和浏览器扩展都是这么做的。</p>",
                ),
                ("h3", "两个上限"),
                (
                    "p",
                    "<code>MAX_PAGE_SIZE</code>（200）限住一页。<code>MAX_CANDIDATE_DEPTH</code>（2000）限住它们背后的整个候选池，撞上它就是 "
                    "<code>depth_capped</code> 被置上的原因。两个都在同一个地方、在任何查询开跑之前夹好，所以一个超大的请求不花什么代价，回给你的就是实际给出的那个窗口。",
                ),
            ],
        ),
        (
            "extension",
            "浏览器扩展",
            [
                (
                    "p",
                    "Manifest V3，Chromium 系浏览器。它只和 <code>127.0.0.1:8787</code> 说话 —— 那就是它全部的必需主机权限。",
                ),
                (
                    "steps",
                    [
                        '从<a href="https://github.com/88lin/facetmark/releases">发行页</a>下载 '
                        "<code>facetmark-extension.zip</code> 并解压。",
                        "打开 <code>chrome://extensions</code>，开启<b>开发者模式</b>，选<b>加载已解压的扩展</b>，指向刚才那个目录。",
                        "在终端跑 <code>facetmark serve</code> 并保持运行。",
                        "跑 <code>facetmark token</code>，打开扩展的设置页，把令牌粘进去。",
                        "按 <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd>（macOS 是 "
                        "<kbd>Cmd</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd>）就能搜了。",
                    ],
                ),
                ("h3", "它能干什么"),
                (
                    "table",
                    ["功能", "说明"],
                    [
                        ["地址栏关键字", "地址栏输 <code>fm</code> 再敲空格，不用开弹窗就能搜。"],
                        [
                            "快捷键",
                            "<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd> / <kbd>Cmd</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd>。",
                        ],
                        ["保存当前标签页", "一键。页面进本地索引队列，弹窗底部显示还剩几个。"],
                        ["右键菜单", "右键一个链接或页面就能存。"],
                        ["分组结果", "同一次保存会话里的页面单独成组，不混进排名。"],
                        [
                            "面标签",
                            "每条结果显示命中了哪些面 —— <em>关于</em>、<em>可能会问</em>、<em>词</em>、<em>子串</em>、<em>关联</em>、<em>冷</em>。",
                        ],
                    ],
                ),
                ("h3", "设置项"),
                (
                    "table",
                    ["字段", "含义"],
                    [
                        [
                            "<code>endpoint</code>",
                            "facetmark 监听在哪。默认 <code>http://127.0.0.1:8787</code>。",
                        ],
                        ["<code>token</code>", "<code>facetmark token</code> 的输出。"],
                        ["<code>channelB</code>", "可选的第二个端点，用于同时跑两个库。"],
                        ["<code>paused</code>", "不卸载的前提下让扩展停止和服务通信。"],
                    ],
                ),
                (
                    "callout",
                    "info",
                    "不在应用商店里",
                    "<p>扩展以 zip 形式放在发行页，需要解压后加载。它没有提交到 Chrome 应用商店或 Edge 加载项目录。</p>",
                ),
            ],
        ),
        (
            "mcp",
            "MCP 服务器",
            [
                (
                    "p",
                    "<code>facetmark mcp</code> 在 stdio 上跑一个 FastMCP 服务器，所以 Claude Desktop 这类 MCP "
                    "客户端可以搜你的库、读一次保存会话、存一个页面。",
                ),
                (
                    "cb",
                    "json",
                    "{\n"
                    '  "mcpServers": {\n'
                    '    "facetmark": {\n'
                    '      "command": "facetmark",\n'
                    '      "args": ["mcp"]\n'
                    "    }\n"
                    "  }\n"
                    "}",
                ),
                (
                    "p",
                    '在 <code>args</code> 里加 <code>"--db", "/path/to/facetmark.db"</code> 可以指定库，加 <code>"--mock"</code> '
                    "可以没 key 先试。环境变量的读法和其他命令完全一样。",
                ),
                ("h3", "9 个工具"),
                (
                    "table",
                    ["工具", "作用"],
                    [
                        [
                            "<code>search_bookmarks</code>",
                            "完整管线，和 <code>facetmark search</code> 一样。",
                        ],
                        ["<code>get_bookmark</code>", "一条记录，可选带正文。"],
                        ["<code>list_sessions</code>", "最近的保存会话。"],
                        ["<code>get_session</code>", "一次会话里存的全部。"],
                        ["<code>find_related</code>", "在链接图里往外走一跳。"],
                        ["<code>synthesize</code>", "基于检索到的页面写一份回答。"],
                        [
                            "<code>suggest_from_context</code>",
                            "你正在看的这段文字，库里有什么相关。",
                        ],
                        ["<code>check_link_health</code>", "一个存过的 URL 还活着吗。"],
                        ["<code>save_bookmark</code>", "加一个 URL 并排队索引。"],
                    ],
                ),
                ("h3", "3 个资源"),
                (
                    "ul",
                    [
                        "<code>bookmark://{id}</code> —— 一条记录的 JSON。",
                        "<code>session://{id}</code> —— 一次保存会话。",
                        "<code>facetmark://stats</code> —— 索引规模与覆盖率。",
                    ],
                ),
            ],
        ),
        (
            "karakeep",
            "karakeep 插件",
            [
                (
                    "p",
                    '<a href="https://karakeep.app">karakeep</a> 是一个可自托管的书签管理器，搜索提供者可插拔。这个插件把 facetmark '
                    "接到它的搜索框后面：karakeep 管界面，facetmark 管检索。",
                ),
                (
                    "steps",
                    [
                        "把插件拷进 karakeep 的插件包。",
                        "在 exports 映射里注册它。",
                        "在 meilisearch <b>之后</b>加载，因为插件管理器发出去的是最后注册的那个提供者。",
                        "把它指向一个在跑的 facetmark 服务。",
                    ],
                ),
                (
                    "cb",
                    "shell",
                    "cp -r integrations/karakeep/search-facetmark \\\n"
                    "  /path/to/karakeep/packages/plugins/search-facetmark",
                ),
                (
                    "cb",
                    "json",
                    "// packages/plugins/package.json — exports 映射\n"
                    '"./search-facetmark": "./search-facetmark/index.ts"',
                ),
                (
                    "cb",
                    "ts",
                    "// packages/shared-server/src/plugins.ts 的 loadAllPlugins()\n"
                    'await import("@karakeep/plugins/search-meilisearch");\n'
                    'await import("@karakeep/plugins/search-facetmark");  // 必须在后面',
                ),
                (
                    "cb",
                    "shell",
                    "export FACETMARK_URL=http://127.0.0.1:8787\n"
                    "export FACETMARK_TOKEN=$(facetmark token)\n"
                    "facetmark serve",
                ),
                ("h3", "协议是怎么钉住的"),
                (
                    "ul",
                    [
                        "karakeep 上游的类型按 blob SHA 钉在 <code>integrations/karakeep/typecheck/upstream-pins.json</code>，CI "
                        "会对着它跑 <code>tsc --noEmit</code>。",
                        "报文格式存在 <code>integrations/karakeep/contract/wire.json</code>，由 "
                        "<code>tests/test_karakeep_contract.py</code> 回放。",
                        "这个回放测试真的接住了一个：只有一条命中时的 offset 1，正确答案是 <code>hits: []</code> 配 <code>totalHits: 1</code>。空的 "
                        "<code>hits</code> <b>不等于</b>没有结果。",
                    ],
                ),
                (
                    "callout",
                    "warn",
                    "指望它之前要知道两件事",
                    "<p>第一，没有针对真实在跑的 karakeep 实例的测试 —— 只有对钉死协议的。第二，把库推进 karakeep 再读回来，排名会变：karakeep 的 tag "
                    "就是你浏览器的<em>文件夹</em>名，所以关键词从 19,016 个不同词塌到 13 个。指标层面的结论能过往返，名次层面的不能，除非重建索引。<a "
                    'href="measured.zh.html#karakeep">完整实测</a>。</p>',
                ),
                (
                    "p",
                    "想卸掉这座桥，把 <code>karakeep_doc</code> 表 drop 了就行。<code>enrichment.source_hash == 'karakeep'</code> "
                    "是保留值，意思是这行桥可以覆写；其他任何值都意味着是真模型写的，桥不碰。",
                ),
            ],
        ),
        (
            "data",
            "数据库里有什么",
            [
                (
                    "p",
                    "一个 SQLite 文件。任何 SQLite 工具都能打开，不加密、不混淆、不私有。就算你不用 facetmark 了，数据也还读得出来。",
                ),
                (
                    "table",
                    ["表", "存什么"],
                    [
                        ["<code>bookmark</code>", "URL、标题、文件夹路径、保存时间、来源。"],
                        ["<code>content</code>", "抓回来的正文和抽取结果。"],
                        [
                            "<code>enrichment</code>",
                            "摘要、主题、实体、要点，以及 <code>source_hash</code> 指纹。",
                        ],
                        [
                            "<code>intent</code>",
                            "生成的候选查询，以及它有没有过了「能搜回来」的过滤。",
                        ],
                        [
                            "<code>vec_content</code> / <code>vec_intent</code>",
                            "sqlite-vec 虚拟表，存稠密向量。",
                        ],
                        [
                            "<code>fts_tri</code> / <code>fts_seg</code>",
                            "两个 FTS5 索引：字符三元组和词段。",
                        ],
                        [
                            "<code>session</code> / <code>bookmark_session</code>",
                            "重建出来的保存会话及其成员。",
                        ],
                        [
                            "<code>edge</code>",
                            "带类型的边：<code>session</code>、<code>semantic</code>、<code>same_domain</code>、<code>supersession</code>。",
                        ],
                        [
                            "<code>health</code>",
                            "链接健康结论：<code>ok</code>、<code>gone</code>、<code>drifted</code>、<code>soft_gone</code>。",
                        ],
                        ["<code>karakeep_doc</code>", "桥的状态。drop 掉就是卸载。"],
                        [
                            "<code>meta</code>",
                            "嵌入模型、维度、后端，第一次建索引时写入，之后强制校验。",
                        ],
                    ],
                ),
                ("h3", "链接健康与冷层"),
                (
                    "cb",
                    "shell",
                    "facetmark health                       # 已知的\n"
                    "facetmark health --check               # 真的去探网络\n"
                    "facetmark health --check --no-save-recovered   # 只读扫描",
                ),
                (
                    "p",
                    "扫描可以用 DNS-over-HTTPS、Wayback 可用性 API 和一个阅读代理，来区分「页面没了」和「你 DNS 坏了」。在拿这个库做任何测量之前，请加 "
                    "<code>--no-save-recovered</code>，让扫描除了健康日志之外保持只读。",
                ),
                (
                    "callout",
                    "bad",
                    "一个已知的、而且承重的 bug",
                    "<p>冷层把「URL 死了」当成「存下来的副本没用了」，这是错的：facetmark 存了正文。URL 死了恰恰是本地快照<em>最</em>值钱的时候。现在还没修，因为在出厂 profile "
                    '下另一个意外让这个降权根本没机会执行，而只拆掉其中任一个，结果会实测变差 1.46pp。<a href="measured.zh.html#decay">完整的故事</a>。</p>',
                ),
            ],
        ),
        (
            "env",
            "全部配置项",
            [
                (
                    "p",
                    "作为环境变量时，每个名字前面加 <code>FACETMARK_</code>；放在 <code>.env</code> 里也一样。下面的默认值就是出厂值。",
                ),
                ("h3", "存储"),
                (
                    "table",
                    ["配置项", "默认", "说明"],
                    [
                        ["<code>DATA_DIR</code>", "按系统", '见<a href="#install">安装</a>。'],
                        ["<code>DB_NAME</code>", "<code>facetmark.db</code>", ""],
                        ["<code>PRIVACY_EXCLUDED_DOMAINS</code>", "空", "不导入、不抓、不嵌入。"],
                    ],
                ),
                ("h3", "模型接入"),
                (
                    "table",
                    ["配置项", "默认", "说明"],
                    [
                        ["<code>API_KEY</code>", "空", "空是合法的，代价是失去内容面和意图面。"],
                        [
                            "<code>BASE_URL</code>",
                            "<code>https://api.openai.com/v1</code>",
                            "必须以 <code>/v1</code> 结尾。",
                        ],
                        ["<code>CHAT_MODEL</code>", "<code>gpt-4o-mini</code>", ""],
                        ["<code>CHAT_MODEL_FALLBACKS</code>", "空", "逗号分隔。默认为空是故意的。"],
                        ["<code>EMBED_MODEL</code>", "<code>text-embedding-3-small</code>", ""],
                        [
                            "<code>EMBED_DIM</code>",
                            "<code>1536</code>",
                            "写进 <code>meta</code>，对不上就报错。",
                        ],
                        [
                            "<code>EMBED_BACKEND</code>",
                            "<code>endpoint</code>",
                            "或 <code>local</code>。",
                        ],
                        ["<code>REQUEST_TIMEOUT</code>", "<code>60.0</code>", "秒。"],
                        ["<code>MAX_RETRIES</code>", "<code>3</code>", ""],
                        [
                            "<code>USE_MOCK_PROVIDER</code>",
                            "<code>false</code>",
                            "确定性离线 provider。",
                        ],
                    ],
                ),
                ("h3", "本地嵌入"),
                (
                    "table",
                    ["配置项", "默认", "说明"],
                    [
                        ["<code>LOCAL_EMBED_PATH</code>", "空", "空就下载。"],
                        ["<code>LOCAL_EMBED_DEVICE</code>", "<code>cpu</code>", ""],
                        ["<code>LOCAL_EMBED_BATCH</code>", "<code>8</code>", ""],
                        [
                            "<code>LOCAL_EMBED_MAX_SEQ</code>",
                            "<code>1024</code>",
                            '调低会损失可重现性 —— 见<a href="#models">模型接入</a>。',
                        ],
                    ],
                ),
                ("h3", "抓取"),
                (
                    "table",
                    ["配置项", "默认", "说明"],
                    [
                        ["<code>FETCH_CONCURRENCY</code>", "<code>30</code>", "全局。"],
                        [
                            "<code>FETCH_PER_HOST_CONCURRENCY</code>",
                            "<code>2</code>",
                            "礼貌，不是性能。",
                        ],
                        [
                            "<code>FETCH_PER_HOST_MIN_INTERVAL</code>",
                            "<code>0.5</code>",
                            "同一主机两次请求的秒数间隔。",
                        ],
                        ["<code>FETCH_TIMEOUT</code>", "<code>15.0</code>", ""],
                        ["<code>RESPECT_ROBOTS</code>", "<code>true</code>", ""],
                        [
                            "<code>ROBOTS_ON_ERROR</code>",
                            "<code>allow</code>",
                            "robots.txt 读不到时怎么办。",
                        ],
                        [
                            "<code>ROBOTS_MAX_CRAWL_DELAY</code>",
                            "<code>5.0</code>",
                            "对对方声明的 crawl delay 封顶。",
                        ],
                        ["<code>MIN_BODY_CHARS</code>", "<code>200</code>", "低于此数算无正文。"],
                        ["<code>BODY_TRUNCATE_CHARS</code>", "<code>6000</code>", ""],
                        ["<code>USER_AGENT</code>", "写明自己是 facetmark", ""],
                    ],
                ),
                ("h3", "富化与意图"),
                (
                    "table",
                    ["配置项", "默认", "说明"],
                    [
                        ["<code>ENRICH_CONCURRENCY</code>", "<code>4</code>", ""],
                        ["<code>INTENT_GENERATE_N</code>", "<code>8</code>", "每页生成多少候选。"],
                        ["<code>INTENT_KEEP_N</code>", "<code>4</code>", "每页最多留多少。"],
                        [
                            "<code>INTENT_PROBE_TOP_K</code>",
                            "<code>10</code>",
                            "「能不能搜回来」看多深。",
                        ],
                    ],
                ),
                ("h3", "会话、检索与衰减"),
                (
                    "table",
                    ["配置项", "默认", "说明"],
                    [
                        [
                            "<code>SESSION_EPS_MINUTES</code>",
                            "自动",
                            "不设时，间隔由覆盖率 × 纯度提升在网格上选。",
                        ],
                        [
                            "<code>SESSION_EPS_GRID_MINUTES</code>",
                            "<code>5…240</code>",
                            "搜索的网格。",
                        ],
                        [
                            "<code>RRF_K</code>",
                            "<code>60</code>",
                            "<code>w / (k + rank)</code> 里的 <code>k</code>。",
                        ],
                        ["<code>CANDIDATES_PER_FACET</code>", "<code>50</code>", ""],
                        ["<code>GRAPH_EXPAND_HOPS</code>", "<code>1</code>", ""],
                        ["<code>GRAPH_EXPAND_FACTOR</code>", "<code>0.6</code>", ""],
                        ["<code>DECAY_FACTOR</code>", "<code>0.5</code>", ""],
                        ["<code>DECAY_AGE_DAYS</code>", "<code>365</code>", ""],
                        [
                            "<code>DECAY_RESCUE_THRESHOLD</code>",
                            "<code>0.02</code>",
                            '改它之前先看<a href="measured.zh.html#decay">衰减层实测</a>。',
                        ],
                    ],
                ),
                ("h3", "链接健康与服务"),
                (
                    "table",
                    ["配置项", "默认", "说明"],
                    [
                        [
                            "<code>HEALTH_ENABLE_EXTERNAL</code>",
                            "<code>true</code>",
                            "网络探测总开关。",
                        ],
                        ["<code>HEALTH_ENABLE_DOH</code>", "<code>true</code>", "DNS-over-HTTPS。"],
                        ["<code>HEALTH_ENABLE_WAYBACK</code>", "<code>true</code>", ""],
                        ["<code>HEALTH_ENABLE_READER</code>", "<code>true</code>", ""],
                        [
                            "<code>HEALTH_SOFT_GONE_LENGTH_RATIO</code>",
                            "<code>0.30</code>",
                            "正文缩到这个比例 ⇒ <code>soft_gone</code>。",
                        ],
                        ["<code>HEALTH_GONE_CONFIRM_DAYS</code>", "<code>7</code>", ""],
                        ["<code>HEALTH_PROXY_URL</code>", "未设", ""],
                        ["<code>HOST</code>", "<code>127.0.0.1</code>", ""],
                        ["<code>PORT</code>", "<code>8787</code>", ""],
                    ],
                ),
            ],
        ),
        (
            "commands",
            "全部命令",
            [
                (
                    "p",
                    "使用 <code>facetmark COMMAND --help</code> 查看每条命令支持的参数。数据库相关命令通常支持 <code>--db</code>，许多命令提供 "
                    "<code>--json</code> 便于脚本处理。",
                ),
                (
                    "table",
                    ["命令", "作用", "值得一提的参数"],
                    [
                        ["<code>version</code>", "打印版本。", ""],
                        [
                            "<code>browsers</code>",
                            "列出可导入的活浏览器配置。",
                            "<code>--json</code>",
                        ],
                        [
                            "<code>import [PATH]</code>",
                            "导入 Netscape HTML 或 Chrome JSON。不带路径时自动找活配置。从不写回。",
                            "",
                        ],
                        [
                            "<code>migrate</code>",
                            "把 schema 升到当前构建需要的版本。",
                            "<code>--check</code>、<code>--no-backup</code>",
                        ],
                        [
                            "<code>index</code>",
                            "抓取、富化、嵌入、意图、会话、边。",
                            "<code>--no-fetch</code>、<code>--limit</code>、<code>--force</code>、<code>--mock</code>",
                        ],
                        ["<code>reindex</code>", "从书签重建所有衍生产物。", "<code>--mock</code>"],
                        [
                            "<code>search QUERY</code>",
                            "搜库。",
                            "<code>-n</code>、<code>--quick</code>、<code>--config</code>、<code>--explain</code>",
                        ],
                        ["<code>show ID</code>", "把一条书签打成 JSON。", "<code>--body</code>"],
                        ["<code>sessions</code>", "列出保存会话。", "<code>-n</code>"],
                        [
                            "<code>health</code>",
                            "链接健康，以及衰减层到底看不看得见它。",
                            "<code>--check</code>、<code>--no-external</code>、<code>--no-save-recovered</code>",
                        ],
                        ["<code>stats</code>", "索引规模与覆盖率。", ""],
                        [
                            "<code>export [FILE] [QUERY]</code>",
                            "把库、或者一条过滤查询选中的那部分，写成 <code>import</code> 能读回来的 "
                            "JSON。只接受过滤器——排序结果的前几条不是备份。派生数据不写进去，<code>index</code> 会重建。",
                            "<code>--full</code>",
                        ],
                        [
                            "<code>doctor</code>",
                            "诊断这套装置——配置以及每一项设置来自哪里、schema 版本、索引有没有建起来、已存的向量和设置对不对得上。不修任何东西，也不调用模型；每一条发现都写清楚该跑哪条命令。",
                            "<code>--json</code>",
                        ],
                        ["<code>token</code>", "打印扩展要的配对令牌。", "<code>--rotate</code>"],
                        [
                            "<code>serve</code>",
                            "跑本地 HTTP 服务。",
                            "<code>--host</code>、<code>--port</code>、<code>--mock</code>",
                        ],
                        ["<code>mcp</code>", "在 stdio 上跑 MCP 服务器。", "<code>--mock</code>"],
                        [
                            "<code>crawl URL</code>",
                            "礼貌地把一个站点走进库里：遵守 robots.txt，隐私排除名单上的主机完全不碰，抓到的每一页都是一条普通书签。",
                            "<code>--max-pages</code>、<code>--off-domain</code>",
                        ],
                        [
                            "<code>update</code>",
                            "报告 PyPI 上有没有更新的 facetmark。只在你运行它的时候查——没有后台检查、没有遥测——而且它自己从不执行升级。",
                            "<code>--json</code>",
                        ],
                        [
                            "<code>demo</code>",
                            "离线造一个合成库并搜它。",
                            "<code>--size</code>、<code>--keep</code>",
                        ],
                        [
                            "<code>config path</code> / <code>config show</code>",
                            "`config.toml` 在哪，以及生效的设置和每一项的来源。",
                            "",
                        ],
                        [
                            "<code>eval</code>",
                            "跑检索评测，可以是 A–E 消融。",
                            "<code>--ablation</code>、<code>--rungs</code>、<code>--queries</code>、<code>--bootstrap</code>、<code>--out</code>",
                        ],
                    ],
                ),
                ("h3", "跑你自己的评测"),
                (
                    "p",
                    "评测命令接受包含 <code>{text, qtype, target_url}</code> 的 JSONL "
                    "查询集，在指定书签库上比较检索配置，并输出置信区间与配对检验。先固定数据集和协议，再解释结果。",
                ),
                (
                    "cb",
                    "shell",
                    "facetmark eval --no-build \\\n"
                    "  --queries my-queries.jsonl \\\n"
                    "  --rungs A,C,full \\\n"
                    "  --bootstrap 10000 --concurrency 4 \\\n"
                    "  --out report.json",
                ),
                (
                    "callout",
                    "warn",
                    "并发会摧毁延迟数字",
                    "<p><code>--concurrency &gt; 1</code> 会让 p50 和 p95 失去意义。要质量数字时用它，要延迟就抽一个子集在并发 1 下重跑。</p>",
                ),
            ],
        ),
        (
            "trouble",
            "排错",
            [
                ("h3", "每次模型调用都返回 404"),
                (
                    "p",
                    "核对服务商要求的完整 base URL，包括路径前缀（常见为 <code>/v1</code>），并确认模型名称可用。404 可能来自地址或模型名，不能单凭它判断 API Key 无效。",
                ),
                ("h3", "建索引或搜索时报「维度不匹配」"),
                (
                    "p",
                    "数据库记录的向量维度与 <code>FACETMARK_EMBED_DIM</code> 不一致。先确认模型的实际输出维度，修正配置并重启服务，再重建索引。修改前保留数据库备份。",
                ),
                ("h3", "富化静悄悄地什么也没做"),
                (
                    "p",
                    "存着的 <code>source_hash</code> 已经等于当前正文哈希，指纹认为活干完了。这是正确行为，<code>facetmark index --force</code> "
                    "可以覆盖它。",
                ),
                ("h3", "向量有，但结果很差"),
                (
                    "p",
                    "通常是向量写完之后嵌入文本又变了 —— 比如富化被一座桥覆写了。用 <code>facetmark index --force</code> "
                    "重算。如果是一个全新的索引就差，先确认自己是不是不小心跑在 mock provider 上：<code>facetmark stats</code> 会报当前用的嵌入模型。",
                ),
                ("h3", "SQLite 报 <code>disk I/O error</code>"),
                (
                    "p",
                    "SQLite 在某些网络文件系统和 FUSE 上跑不稳。用 <code>FACETMARK_DATA_DIR</code> 把数据目录换到本地磁盘。",
                ),
                ("h3", "抓得很慢，或者页面是空的"),
                (
                    "p",
                    "两个通常都是故意的。遵守 robots.txt，单主机并发封顶 2，两次请求之间还有最小间隔。有些站就是不给。没正文的页面照样建索引 —— 管线会退到只用标题的指纹 —— "
                    "只是弱一些。想要快而浅的索引，用 <code>--no-fetch</code>。",
                ),
                ("h3", "扩展连不上服务"),
                (
                    "p",
                    "按顺序查三件事：<code>facetmark serve</code> 真的在跑吗；设置里的 endpoint 和它实际监听的主机端口对得上吗；设置里的令牌和 <code>facetmark "
                    "token</code> 一致吗。轮换过令牌的话，扩展要拿新的。",
                ),
                ("h3", "其他"),
                (
                    "p",
                    "<code>facetmark stats</code> 和 <code>facetmark health</code> 会把索引里到底有什么打出来，大部分困惑到这就解了。实在不行就<a "
                    'href="https://github.com/88lin/facetmark/issues">提个 issue</a> —— 最有用的是把出错那条命令的 '
                    "<code>--json</code> 输出贴上来。",
                ),
            ],
        ),
    ],
}

# ---------------------------------------------------------------- 实测 ----

ZH["measured"] = {
    "h1": "评测方法与结果",
    "lede": (
        "记录检索默认值背后的实验、反例和未覆盖的场景。每项结果应结合数据集、协议和样本限制阅读；这些数字不代表所有书签库的表现。"
    ),
    "toc_title": "\u7ed3\u679c",
    "sections": [
        (
            "how",
            "如何阅读评测",
            [
                (
                    "ul",
                    [
                        "<b>预注册。</b>标准在跑之前写好。一个在“激发它的那批查询”上测出来的档位是假设，不是结果，会被标为探索性。",
                        "<b>配对检验。</b>每一条 A 对 B 的结论都在同一批查询上配对，带 bootstrap 置信区间和对不一致对的 McNemar 检验。胜和负分开报 —— “0 变化得到的净零”和“40 "
                        "胜 40 负得到的净零”是两件事。",
                        "<b>不重开。</b>查询集一旦冻结、结论一旦记录，就算数。新问题要新查询集。",
                        "<b>pp</b> 是百分点。<b>CI95</b> 是 95% bootstrap 区间。",
                    ],
                ),
                (
                    "callout",
                    "warn",
                    "最大的一条保留，放在最前面说一次",
                    "<p>这一页上每一套查询集都是工具作者自己写的。bootstrap 修的是抽样噪声，对“作者知道工具擅长什么”这件事一点办法都没有。这个项目最需要的贡献，是一套别人写的查询集。</p>",
                ),
            ],
        ),
        (
            "w1",
            "W1 · 内容检索与多路融合",
            [
                (
                    "raw",
                    '<p><span class="badge fail">默认已撤</span> <span class="tiny">479 条查询 · 一个真实的 1,700 条书签库 · '
                    "预注册</span></p>",
                ),
                (
                    "p",
                    "整个项目的前提就是「四个面融合比任何单一个都强」。三条标准在跑之前就写好了。三条全没达到。",
                ),
                (
                    "table",
                    ["档", "面", "Recall@5", "Recall@1", "MRR@10", "p50"],
                    [
                        [
                            "<b>A</b>",
                            "只用内容向量",
                            "<b>0.643</b>",
                            "0.505",
                            "0.564",
                            "<b>148 ms</b>",
                        ],
                        ["<b>B</b>", "＋两个词面", "0.589", "—", "—", "189 ms"],
                        ["<b>C</b>", "四面全上", "0.635", "—", "—", "526 ms"],
                        ["<b>D</b>", "＋上下文＋图", "0.639", "—", "—", "523 ms"],
                    ],
                    [0],
                ),
                (
                    "p",
                    "融合付出了 <b>5.4pp</b> 的 Recall@5，并且慢了 <b>3.5 倍</b>。A 档分类型看：内容型 <b>0.959</b>、模糊型 <b>0.706</b>、情景型 "
                    "<b>0.279</b>。",
                ),
                ("h3", "它为什么输"),
                (
                    "p",
                    "平权重的 RRF 没有任何表达「有多确定」的手段。两个弱面碰巧一致，得 0.0279；一个强面非常确定，得 0.0164。碰巧赢了。这不是调参问题，这就是公式本身的行为。",
                ),
                ("h3", "同一轮里活下来的"),
                (
                    "table",
                    ["幸存者", "效果", "胜 / 负", "p", "代价"],
                    [
                        [
                            "图扩展作为<em>单独一组</em>",
                            "<b>+2.09pp</b> Recall@5",
                            "10 / 0",
                            "0.0019",
                            "9 ms",
                        ],
                        [
                            "重排，对 Recall@1",
                            "<b>+4.80pp</b> CI95 [+1.46, +8.35]",
                            "45 / 22",
                            "0.0067",
                            "—",
                        ],
                    ],
                ),
                (
                    "p",
                    "两个都发了出去。注意图扩展只在作为<em>补充</em>时成立 —— 单独成组返回，不合进排名。",
                ),
            ],
        ),
        (
            "gate",
            "W2/W3 · 情景门的对照结果",
            [
                ("raw", '<p><span class="badge fail">发出去之后回滚了默认</span></p>'),
                (
                    "p",
                    "情景门识别「和 X 差不多时候存的那个」，然后把检索限制在那个保存窗口内。在它自己的 616 条 holdout 上它赢得很干净，所以发了出去。",
                ),
                (
                    "table",
                    ["查询集", "对比", "ΔRecall@5", "CI95", "胜 / 负", "p"],
                    [
                        [
                            "616 条 holdout",
                            "A → A_gatedctx",
                            '<b class="nowrap">+3.09pp</b>',
                            "[1.79, 4.55]",
                            "19 / 0",
                            "3.8e−6",
                        ],
                        [
                            "361 条精度探针",
                            "A → A_gatedctx",
                            '<b class="nowrap">−18.83pp</b>',
                            "[−23.27, −14.68]",
                            "3 / 71",
                            "—",
                        ],
                    ],
                ),
                (
                    "p",
                    "第二行是同一个功能，只是换了一套事后才建的查询集去问另一个问题：它在不该触发的查询上触发了，会怎样？Recall@5 从 0.9058 掉到 0.7175，Recall@1 从 0.801 掉到 "
                    "0.363。",
                ),
                ("h3", "分层一看就全明白了"),
                (
                    "table",
                    ["分层", "n", "ΔRecall@5"],
                    [
                        ["保存窗口里确实有目标", "57", "<b>+0.00pp</b> —— 恰好是零"],
                        ["保存窗口里没有目标", "304", '<b class="nowrap">−22.37pp</b>'],
                    ],
                ),
                (
                    "p",
                    "门对的时候，它什么都不加。门错的时候，它把答案扔了。结论 <code>gate_precision_unqualified</code>，默认回滚到不加门。",
                ),
                (
                    "callout",
                    "info",
                    "gate_v2 写好了，被毙了",
                    "<p>一个更窄的门在原来那 616 条上拿到 +1.79pp，在精度探针上是 "
                    "<b>−10.52pp</b>。明知道第二个数字存在还拿第一个发货，等于挑了一套能给出我们想要的答案的查询集。没发。</p>",
                ),
            ],
        ),
        (
            "recall",
            "召回门 · 样本不足",
            [
                ("raw", '<p><span class="badge warn">仅描述 · 低于预注册的样本下限</span></p>'),
                (
                    "p",
                    "精度探针问的是「它触发了、但不该触发」。这一轮问反面：它多少次该触发却没触发？协议在跑之前就预注册好了，镜像精度那份。",
                ),
                (
                    "table",
                    ["指标", "值"],
                    [
                        [
                            "可用探针",
                            "冻结的 v3 holdout 里的 <b>16</b> 条 <code>q_save_action</code>",
                        ],
                        ["门触发了几次", "<b>16 条里 0 条</b>"],
                        ["漏检率", "<b>100.0%</b>，Wilson CI95 [80.64, 100.00]"],
                        ["ΔRecall@5（A_gatedctx − A）", "<b>+0.00pp</b>，CI95 [0.00, 0.00]"],
                        ["McNemar", "0 得 0 失，p = 1.0，0 个不一致对"],
                        [
                            "协议自检",
                            '<span class="badge pass">通过</span> —— 未触发子集必须刚好动 0.00pp，它做到了',
                        ],
                        ["结论", "<b>无。</b>16 低于预注册的 25 条下限"],
                    ],
                ),
                (
                    "callout",
                    "warn",
                    "那个零是结构性的，不是让人安心的",
                    "<p>门一次都没触发，所以两边跑的是完全相同的代码，逐查询名次一模一样。一个恰好为零、且不一致对也为零的 Δ，不是「门无害」的证据 —— "
                    "它是「什么都没测到」的证据。可检测最小效应在这里无定义，因为公式要除以不一致对的个数，而它是 0。</p>",
                ),
                (
                    "p",
                    "这 16 条全部是在说「我收起来的那个」 —— <em>之前收起来的那个</em>、<em>the link I set "
                    "aside</em>、<em>我塞进清单里的那篇</em>。没有一条包含门的触发词表里的词 —— 那张表目前看的是 "
                    "<code>保存</code>、<code>收藏</code>、<code>saved</code>、<code>bookmark</code> 等十几个。",
                ),
                (
                    "p",
                    "那个看上去最自然的动作 —— 把这 16 条加进词表 —— 恰恰是协议禁止的，因为用衡量它的探针去选词表是循环论证。要拿到结论，得用新种子、在冻结参数下新生成至少 25 "
                    "条探针，然后<em>同时</em>过漏检率这关和 361 条精度那关。在那之前，词表不动。",
                ),
            ],
        ),
        (
            "five",
            "五种候选修正的比较",
            [
                ("p", "W1 杀掉融合之后，五个看上去很显然的修法，逐个拿去测了，而不是拿去辩论了。"),
                (
                    "table",
                    ["候选", "测到什么", "结论"],
                    [
                        [
                            "干脆把词面删了",
                            "内容型里 80.1%、模糊型里 46.3% 根本不需要向量 —— 但有 <b>6.05%</b>（479 条里 29 条）<em>只有</em>词面能找到，超过预注册的 5% 线。",
                            '<span class="badge fail">保留</span>',
                        ],
                        [
                            "给面加权重而不是平权 RRF",
                            "两个弱面碰巧一致得 0.0279；一个强面确定得 0.0164。",
                            '<span class="badge info">解释了为什么输</span>',
                        ],
                        [
                            "修好中文上的三元组面",
                            "原本 211 条中文查询只命中 25 条（11.85%）。修后 202/211（95.73%）。整体 Recall@5：<b>没变</b>。",
                            '<span class="badge warn">修好了，没收益</span>',
                        ],
                        [
                            "把 boost 上限括大",
                            "<code>MAX_BOOST = 1.60</code> 在 A 档能跨越分数区间的 79.7%，在 C/D 只有 20.9%。要有同等位移能力得 6.03。而且 66.3% "
                            "的候选拿到的就是 1.0。",
                            '<span class="badge info">测了，没发</span>',
                        ],
                        [
                            "把意图面打开",
                            "50 条生成意图里只有 19 条（38%）站得住，低于预注册的 50% 线。信息词根本不在页面上的比例整体 34.0%，正文贫乏的页面上 <b>62.4%</b>。",
                            '<span class="badge fail">关</span>',
                        ],
                    ],
                ),
                (
                    "p",
                    "第三行是最有意思的。一个真的 bug 被找到并修好了 —— 三元组面从在中文上没用变成能用 —— "
                    "而端到端的召回没动。一个确实是修复、但不改变结果的修复，是一个正常结果；把它报出来，是另外四行还能信的唯一理由。",
                ),
            ],
        ),
        (
            "karakeep",
            "karakeep · 往返后的差异",
            [
                (
                    "raw",
                    '<p><span class="badge fail">roundtrip_unfaithful</span> <span class="tiny">2,376 条书签 · 616 条 '
                    "holdout 查询 · 协议先冻结</span></p>",
                ),
                ("p", "问题：把一个库推进 karakeep 桥再读回来，它还是同一个库吗？三条标准先写好。"),
                (
                    "table",
                    ["标准", "线", "实测", "判定"],
                    [
                        [
                            "指标忠实度",
                            "|ΔRecall@5| ≤ 3pp 且 CI95 落在 ±5pp 内",
                            "<b>−0.81pp</b>，CI95 [−2.44, +0.81]",
                            '<span class="badge pass">过</span>',
                        ],
                        [
                            "名次忠实度",
                            "overlap@5 中位数 ≥ 4 <b>且</b> top-1 一致率 ≥ 80%",
                            "中位数 4.0，top-1 <b>79.06%</b>",
                            '<span class="badge fail">差 0.94pp 没过</span>',
                        ],
                        [
                            "读路径等价",
                            "HTTP 与原生在 616×2 上完全一致",
                            "0 处不一致",
                            '<span class="badge pass">过</span>',
                        ],
                    ],
                ),
                ("h3", "原因完全归因清楚"),
                (
                    "ul",
                    [
                        "正文逐字节相同：1,876 / 1,876。",
                        "摘要存活：2,375 / 2,375，100%。",
                        "主题匹配率 <b>0%</b>，实体 <b>1.18%</b> —— 因为 karakeep 的 tag 就是浏览器的<em>文件夹</em>名，不是主题。",
                        "关键词从 <b>19,016 个不同词塌到 13 个</b>；平均每页从 10.32 跌到 0.76；最常见的标签是 <code>未分类</code>，出现在 1,124 页上。",
                        "向量的中位余弦位移是 0.9846 —— 很小，但足够把一个 top-5 洗一遍。",
                    ],
                ),
                (
                    "p",
                    "把源富化植回去之后，2,376 / 2,376 的嵌入文本逐字节相同，残差为零 —— 归因闭环。重跑一次 <code>facetmark index</code> 就修好了：0 个 "
                    "karakeep 正文需要重抓，2,376 行全部重新富化，图除了 212 条语义边之外完全一致（26,485 对 26,697）。",
                ),
                (
                    "callout",
                    "info",
                    "实际意义",
                    "<p>指标层面的结论能迁移到一个经 karakeep 富化的库上。名次层面的不能，除非你重建索引。跑了桥，就再跑一次 <code>facetmark index</code>。</p>",
                ),
            ],
        ),
        (
            "decay",
            "时间衰减 · 两次实验",
            [
                ("p", "衰减层把看起来陈旧的页面往后排。第一轮测完，什么也没测到："),
                (
                    "table",
                    ["第一轮", "值"],
                    [
                        ["ΔRecall@5", "<b>0.0000pp</b>，CI95 [0.00, 0.00]"],
                        ["冷页面", "2,376 中的 8 个"],
                        ["230 个目标里的冷页面", "0"],
                    ],
                ),
                (
                    "callout",
                    "bad",
                    "第一轮测的是一个根本没开的仪器",
                    "<p><code>health</code> 表里是<b>零行</b>，2,376 页的 <code>open_count</code> 全是 "
                    "0。那一层根本无法触发，因为它没东西可读。一个协议执行得很正确的、干净的零 —— 测的是虚空。</p>",
                ),
                ("p", "第二轮用同一份字节，先跑了一次本地健康检查。"),
                (
                    "table",
                    ["第二轮", "出厂值（0.02）", "可达值（0.0）"],
                    [
                        ["Recall@5", "<b>0.5860</b>", "0.5714"],
                        ["Recall@1", "0.4237", "0.4188"],
                        ["救援阀打开", "616 中的 417", "616 中的 0"],
                        ["health 行数", "2,376（原为 0）", "2,376"],
                        ["冷页面", "73 —— 3.07%（原为 8，0.34%）", "73"],
                        ["冷 ∩ 230 个目标", "8，涉及 19 条查询", "8"],
                    ],
                ),
                (
                    "p",
                    'ΔRecall@5 从第一轮的 <code>+0.0000pp</code> 变成第二轮的 <b class="nowrap">−1.4610pp</b>，CI95 [−2.5974, '
                    "−0.4870]。机制是可以数出来的：37 处名次变化里，<b>12 处直接掉出了前 20</b> —— 其中 10 个原本在前 5，5 个原本是第 1。另有 24 处上升，21 "
                    "处只升了一名，恰好 <b>1</b> 处进了前 5。净 −10 + 1 = −9，而 −9/616 = −1.4610pp。",
                ),
                ("h3", "为什么阈值至今没改"),
                ("p", "两个 bug 在互相抵消，而且这个抵消是承重的。"),
                (
                    "ul",
                    [
                        "<b>bug 一：</b>冷层把「URL 死了」当成「存下来的副本没用了」。但 facetmark 存了正文。URL 死了恰恰是本地快照最值钱的时候，<code>drifted</code> "
                        "更糟 —— 那时快照是唯一幸存的记录。",
                        "<b>bug 二：</b><code>rrf_k = 60</code> 下，单个单位权重的面封顶是 <code>1/61 = 0.016393</code>，低于救援阈值 "
                        "<code>0.02</code>。所以在出厂的单面 profile 下，救援阀<em>总是</em>开着，那个降权从来没有真正执行过。",
                        "单拆掉任一个，结果都会实测变差。两者都被 <code>tests/test_decay_reach.py</code> 钉住，防止被当成「顺手清理一下」删掉。",
                    ],
                ),
                (
                    "p",
                    "真正改的是仪表盘。<code>cold_census()</code> 现在分开报三个条件，<code>facetmark stats</code> 和 <code>facetmark "
                    "health --check</code> 会把 <code>never_opened_selects_everything</code> 和 "
                    "<code>health_never_checked</code> 直接叫出来。",
                ),
                (
                    "p",
                    "还有一个值得留着的细节：8 个受损目标里有 4 个 <code>char_count = 0</code>，却仍然被正确检索出来，靠的是标题和词面。正文丢了不等于检索丢了。",
                ),
            ],
        ),
        (
            "real",
            "真实书签库 · 端到端记录",
            [
                (
                    "p",
                    "合成语料会掩盖集成层面的失败。这是一份真实的浏览器导出，用出厂代码路径导入并建索引。",
                ),
                (
                    "table",
                    ["阶段", "结果"],
                    [
                        [
                            "文件",
                            "<code>favorites_2026_8_4.html</code>，1.7 MB，96 个文件夹，四层嵌套",
                        ],
                        ["导入", "解析 1,710 → 写入 1,701，合并 9 条重复，1 条不可索引"],
                        [
                            "建索引（不抓页面）",
                            "322 个保存会话、9,132 条边、1,386 个域名、1,775 个向量",
                        ],
                        ["查询延迟中位数", "2,265 ms"],
                    ],
                ),
                (
                    "p",
                    "延迟那个数字诚实而不好看：它是一个未抓取、冷启的索引在笔记本上的数字，也正是发布博文里会被您默默略掉的那一个。",
                ),
            ],
        ),
        (
            "gaps",
            "已知限制与未覆盖场景",
            [
                (
                    "ul",
                    [
                        "<b>别人的查询是不是长这样。</b>每一套查询集都是工具作者写的。这是这一页上每个数字最大的威胁，而且 bootstrap 一点都碰不到它。",
                        "<b>衰减层到底有没有用</b>，因为在出厂 profile 下它根本触发不了。",
                        "<b>意图面在别的库上会不会有用。</b>它只在这个库上、用一个模型生成、然后输了。",
                        "<b>karakeep 桥对真实实例能不能跑。</b>协议钉住了、回放了；一个真在跑的实例从来没测过。",
                        "<b>真的 cross-encoder 重排有没有用。</b>离线发出去的是词重叠。在那个重排器下跑的消融测的是台架，不是想法，不能引用为「重排有用」的证据。",
                        "<b>长期行为。</b>每一次测量都是快照。没有人把它跑一年，看一个不断长大的库会把会话聚类搞成什么样。",
                    ],
                ),
                (
                    "callout",
                    "info",
                    "怎么帮忙",
                    "<p>对着你自己的库写 100 条查询，每条带上目标 URL，存成 JSONL。跑 <code>facetmark eval --no-build --queries yours.jsonl "
                    "--rungs A,C,full</code>。把 JSON 贴出来。这一件事比任何功能请求都有价值，而且它恰好是作者在结构上做不了的那件事。</p>",
                ),
            ],
        ),
    ],
}


# --------------------------------------------------------------------------
# 浏览器里的那个页面
# --------------------------------------------------------------------------

ZH["nav"]["webui"] = "界面"
ZH["nav"]["config"] = "配置"
ZH["nav"]["integrations"] = "连接"

ZH["meta"]["webui"] = (
    "facetmark · 应用使用指南",
    "从搜索到查看来源，再到管理书签库。了解每个入口能做什么，以及数据状态该怎么看。",
)
ZH["meta"]["config"] = (
    "facetmark · 模型与配置",
    "先确认配置从哪里读取，再选择模型并测试连接。这里保留完整示例，也说明重启、重建索引和常见报错的区别。",
)
ZH["meta"]["integrations"] = (
    "facetmark · 连接工具与备份",
    "让浏览器扩展、AI 客户端和命令行访问同一份书签库，并为迁移准备可恢复的备份。",
)

ZH["webui"] = {
    "h1": "应用使用指南",
    "lede": "从搜索到查看来源，再到管理书签库。了解每个入口能做什么，以及数据状态该怎么看。",
    "toc_title": "本页目录",
    "sections": [
        (
            "open",
            "打开与配对",
            [
                ("cb", "shell", "facetmark serve"),
                (
                    "p",
                    "在服务所在电脑访问 <code>http://127.0.0.1:8787/app</code>，通常自动配对。通过域名或其他设备访问时，填写服务端 <code>facetmark "
                    "token</code> 输出的令牌。",
                ),
                ("p", '<a href="quickstart.zh.html#server">服务器与 SSH 管理步骤</a>'),
            ],
        ),
        (
            "firstrun",
            "首次设置",
            [
                (
                    "steps",
                    [
                        "导入：选择浏览器导出的 HTML 或 Chromium Bookmarks JSON。文件发送到当前连接的 facetmark 服务。",
                        "模型：设置接口与模型，分别测试对话和向量连接。也可以先用词面搜索。",
                        "索引：开始任务，完成后检查正文覆盖与向量数量。失败时保留错误信息，修正配置后重试。",
                    ],
                ),
                (
                    "callout",
                    "",
                    "远程访问的区别",
                    "<p>日常搜索可以通过已配对的远程连接使用。导入、配置和索引管理要求本机连接，或通过 SSH 转发访问。</p>",
                ),
            ],
        ),
        (
            "tabs",
            "选择要做的事",
            [
                (
                    "table",
                    ["入口", "适合做什么"],
                    [
                        [
                            "搜索",
                            "按词语或内容描述找页面；搜索选项里调整模式，按保存日期缩小范围。",
                        ],
                        ["综述", "根据检索到的已存摘要或片段整理答案，沿编号引用核对来源。"],
                        ["书签库", "看收藏时间线、正文与向量覆盖，判断还缺哪些内容。"],
                        ["浏览批次", "找同一时间段保存的书签，恢复当时的阅读线索。"],
                        ["系统", "查看服务状态、抓取队列和链接健康，排查数据问题。"],
                        ["设置", "管理模型与索引；仅限本机连接或 SSH 转发。"],
                    ],
                )
            ],
        ),
        (
            "read",
            "读懂一条搜索结果",
            [
                (
                    "p",
                    "标题打开原始网页；详情入口展示摘要、主题和相关页面。彩色徽章表示检索来源，同一种来源保持同一种颜色。排名高低不代表内容已经核实。",
                ),
                (
                    "ul",
                    [
                        "内容相关：由内容向量命中，可能来自正文或标题推断的摘要。",
                        "提问方式：匹配的是模型生成的候选问题，不是你的历史查询。",
                        "词语 / 子串：按字面匹配，适合明确的术语、网址和中文短语。",
                        "已冷却：排序降低但书签保留。关联结果单列，便于继续探索。",
                    ],
                ),
            ],
        ),
        (
            "keys",
            "快捷键与阅读偏好",
            [
                (
                    "table",
                    ["操作", "效果"],
                    [
                        ["<kbd>/</kbd>", "聚焦搜索框（不在其他输入框内时）。"],
                        ["<kbd>↑</kbd> / <kbd>↓</kbd>", "移动搜索建议中的选中项。"],
                        ["<kbd>Enter</kbd>", "执行搜索，或打开当前选中的建议。"],
                        ["<kbd>Esc</kbd>", "关闭建议列表或详情弹层。"],
                        ["语言 / 主题", "支持中英文、浅色与深色；偏好保存在当前浏览器。"],
                    ],
                )
            ],
        ),
        (
            "trouble",
            "没有结果或无法管理",
            [
                (
                    "p",
                    "先在书签库确认有书签，再分别检查正文和向量覆盖。索引完成并不意味着每个网站都允许抓取。设置页提示访问受限时，按提示使用本机或 SSH 入口。",
                ),
                ("p", '<a href="quickstart.zh.html#trouble">按现象查找解决步骤 →</a>'),
            ],
        ),
    ],
}


# --------------------------------------------------------------------------
# 配置
# --------------------------------------------------------------------------

ZH["config"] = {
    "h1": "模型与配置",
    "lede": "先确认配置从哪里读取，再选择模型并测试连接。这里保留完整示例，也说明重启、重建索引和常见报错的区别。",
    "toc_title": "本页目录",
    "sections": [
        (
            "where",
            "配置来源与优先级",
            [
                (
                    "p",
                    "生效优先级如下。请从同一个工作目录启动命令和服务；工作目录中的 <code>.env</code> 也会参与读取。",
                ),
                ("cb", "优先级", "环境变量   >   config.toml   >   内置默认值"),
                (
                    "p",
                    "设置屏会告诉你每个值来自这三者中的哪一个；如果是环境变量在压着它，那个输入框会变成只读并说明原因，而不是放你写一个根本不会生效的值。在浏览器里改会写进文件，永远不会去动你的环境变量。",
                ),
                ("cb", "文件在哪", "facetmark config path"),
                (
                    "p",
                    "第一次有东西往里写的时候它才被创建。并不要求你必须有这个文件——没有文件、没有环境变量，全用默认值跑起来也是完全正常的一次运行。",
                ),
                (
                    "callout",
                    "",
                    "有三项要重启才生效",
                    "<p><code>embed_backend</code>、<code>embed_dim</code> 和 <code>local_embed_path</code> "
                    "决定向量库的形状。这一屏会把它们存下来，然后明确告诉你要下次启动才生效。</p>",
                ),
            ],
        ),
        (
            "model",
            "连接模型",
            [
                (
                    "table",
                    ["配置项", "人话"],
                    [
                        [
                            "<code>api_key</code>",
                            "你的 key。存在文件里，回显给你看的是掩码，而且你保存别的字段时它不会被重新写一遍。",
                        ],
                        [
                            "<code>base_url</code>",
                            "请求发到哪。任何说 OpenAI 那套 API 的都行，包括跑在你自己机器上的东西。",
                        ],
                        [
                            "<code>chat_model</code>",
                            "用来读页面，以及在「提问」屏上回答。这里便宜快比聪明重要。",
                        ],
                        ["<code>embed_model</code>", "把文字变成向量。决定搜索质量的是这一项。"],
                    ],
                ),
                (
                    "callout",
                    "warn",
                    "换向量模型就要重建索引",
                    "<p>两个不同模型出来的向量不可比。换了就跑一次重建，否则搜索会悄悄变差，而且没有任何报错会告诉你。</p>",
                ),
                (
                    "p",
                    "在本机或 SSH 转发的设置页点击“测试连接”，分别确认对话和向量结果。保存后重新测试；需要重启的字段在重启前仍使用旧值。",
                ),
            ],
        ),
        (
            "presets",
            "服务商配置示例",
            [
                (
                    "p",
                    "以下是配置格式示例。先通过 <code>facetmark config path</code> "
                    "找到文件，再填入你实际开通的模型名。服务商的端点、可用模型和权限可能变化；以当前账户可用能力为准。",
                ),
                (
                    "cb",
                    "OpenAI",
                    'api_key = "sk-..."\n'
                    'base_url = "https://api.openai.com/v1"\n'
                    'chat_model = "gpt-4o-mini"\n'
                    'embed_model = "text-embedding-3-small"\n'
                    "embed_dim = 1536",
                ),
                (
                    "cb",
                    "DeepSeek（只有对话——向量要另找一家）",
                    'api_key = "sk-..."\nbase_url = "https://api.deepseek.com/v1"\nchat_model = "deepseek-chat"',
                ),
                (
                    "cb",
                    "月之暗面 Kimi",
                    'api_key = "sk-..."\nbase_url = "https://api.moonshot.cn/v1"\nchat_model = "moonshot-v1-8k"',
                ),
                (
                    "cb",
                    "智谱 GLM",
                    'api_key = "..."\n'
                    'base_url = "https://open.bigmodel.cn/api/paas/v4"\n'
                    'chat_model = "glm-4-flash"\n'
                    'embed_model = "embedding-3"\n'
                    "embed_dim = 2048",
                ),
                (
                    "cb",
                    "硅基流动 SiliconFlow",
                    'api_key = "sk-..."\n'
                    'base_url = "https://api.siliconflow.cn/v1"\n'
                    'chat_model = "Qwen/Qwen2.5-7B-Instruct"\n'
                    'embed_model = "BAAI/bge-m3"\n'
                    "embed_dim = 1024",
                ),
                (
                    "cb",
                    "阿里云百炼（OpenAI 兼容端点）",
                    'api_key = "sk-..."\n'
                    'base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"\n'
                    'chat_model = "qwen-plus"\n'
                    'embed_model = "text-embedding-v3"\n'
                    "embed_dim = 1024",
                ),
                (
                    "cb",
                    "Ollama（跑在你自己机器上，不用 key）",
                    'base_url = "http://127.0.0.1:11434/v1"\n'
                    'api_key = "ollama"\n'
                    'chat_model = "qwen2.5:7b"\n'
                    'embed_model = "bge-m3"\n'
                    "embed_dim = 1024",
                ),
                (
                    "cb",
                    "vLLM（你自己的服务）",
                    'base_url = "http://127.0.0.1:8000/v1"\n'
                    'api_key = "not-used"\n'
                    'chat_model = "Qwen/Qwen2.5-7B-Instruct"',
                ),
                (
                    "callout",
                    "",
                    "混着用是常态",
                    "<p>facetmark 只发两种请求：对话的和向量的。很多人对话用最便宜的、向量用最好的。把 <code>base_url</code> "
                    "指向做向量那家、对话模型写全名；或者向量放本地跑，API 只留给对话。</p>",
                ),
            ],
        ),
        (
            "local",
            "使用本地向量",
            [
                (
                    "p",
                    "先安装 <code>python -m pip install "
                    '"facetmark[local]"</code>。模型文件首次需要下载，之后可在运行服务的机器上计算向量；网页抓取和已配置的在线对话模型仍会联网。',
                ),
                (
                    "cb",
                    "本地向量",
                    'embed_backend = "local"\nlocal_embed_path = "BAAI/bge-m3"\nembed_dim = 1024',
                ),
                (
                    "p",
                    "建索引更慢，而且模型要先下载一次。搜索质量不错：在 1024 token 的窗口上，bge-m3 两次跑出来的向量自身余弦是 "
                    "0.999976，而这正是一个「要长期留着而不是天天重建」的索引最需要的性质。",
                ),
                (
                    "dashed",
                    "context",
                    "你放弃了什么",
                    [
                        (
                            "p",
                            "有两条路是建立在「让语言模型读一遍你的页面」上的：一个页面能回答的那些问题，以及主题标签。没有对话模型，这两块就是空的，你搜的是正文和全文检索——仍然是最强的两条路，也仍然比你浏览器给你的强。",
                        ),
                        (
                            "p",
                            "你也可以先从这里开始，以后再加 key。什么都不用丢掉；索引会把之前建不出来的那部分补上。",
                        ),
                    ],
                ),
            ],
        ),
        (
            "groups",
            "并发、隐私与其他选项",
            [
                ("h3", "向量"),
                (
                    "table",
                    ["配置项", "人话"],
                    [
                        [
                            "<code>embed_backend</code>",
                            "<code>api</code> 或 <code>local</code>。要重启生效。",
                        ],
                        [
                            "<code>embed_dim</code>",
                            "每个向量多长。必须和模型实际返回的一致。要重启生效。",
                        ],
                        [
                            "<code>local_embed_path</code>",
                            "本地后端用的模型 id 或目录。要重启生效。",
                        ],
                    ],
                ),
                ("h3", "它使多大劲"),
                (
                    "table",
                    ["配置项", "人话"],
                    [
                        [
                            "<code>request_timeout</code>",
                            "多少秒之后放弃一次调用。网慢就调大；某家服务卡住就调小。",
                        ],
                        [
                            "<code>fetch_concurrency</code>",
                            "同时下载几个页面。你的网络抗议的时候调小。",
                        ],
                        [
                            "<code>enrich_concurrency</code>",
                            "同时往模型发几个页面。被限流的时候，要调小的是这一项。",
                        ],
                    ],
                ),
                ("h3", "不许它看的东西"),
                (
                    "table",
                    ["配置项", "人话"],
                    [
                        [
                            "<code>privacy_excluded_domains</code>",
                            "永远不抓、永远不外发的域名。银行、健康、公司内网。书签还在，只有标题进索引。",
                        ],
                        [
                            "<code>chat_model_fallbacks</code>",
                            "第一个模型不干的时候，按顺序往下试的那些。",
                        ],
                    ],
                ),
                (
                    "callout",
                    "",
                    "首次抓取前设置排除名单",
                    "<p>排除规则限制后续处理，不等于删除已经存下的正文或已有备份。先确认排除范围，再导入和建索引。</p>",
                ),
            ],
        ),
        (
            "faq",
            "连接与保存问题",
            [
                (
                    "table",
                    ["报错", "怎么办"],
                    [
                        [
                            "<code>401</code> / <code>invalid_api_key</code>",
                            "key 不对，或者这个 <code>base_url</code> 配了另一家的 key。在设置屏上测一下——它会告诉你是哪一半挂了。",
                        ],
                        [
                            "模型名报 <code>404</code>",
                            "这个端点上没有这个名字。去查服务商的模型列表。",
                        ],
                        [
                            "<code>429</code>",
                            "被限流。把 <code>enrich_concurrency</code> 调小再跑一次；已经完成的阶段不会重做。",
                        ],
                        [
                            "<code>dim mismatch</code>",
                            "<code>embed_dim</code> 和模型不一致。改对，重启，重建。",
                        ],
                        [
                            "对话能用，向量 403",
                            "很常见。这个账号有一种权限没有另一种。把 <code>embed_backend</code> 切成本地，或者把向量指到另一家。",
                        ],
                        [
                            "保存时报 <code>unknown setting</code>",
                            "某个键名打错了。写入器会拒绝不认识的键，而不是存一个从此被永久忽略的东西。",
                        ],
                    ],
                )
            ],
        ),
    ],
}


# --------------------------------------------------------------------------
# 连接
# --------------------------------------------------------------------------

ZH["integrations"] = {
    "h1": "连接工具与备份",
    "lede": "让浏览器扩展、AI 客户端和命令行访问同一份书签库，并为迁移准备可恢复的备份。",
    "toc_title": "本页目录",
    "sections": [
        (
            "extension",
            "浏览器扩展",
            [
                (
                    "p",
                    "从地址栏搜你的书签，以及不离开当前页面就把它存下来。扩展连的是网页界面连的同一个本机服务。",
                ),
                (
                    "steps",
                    [
                        "先起服务：<code>facetmark serve</code>。",
                        "从仓库里的 <code>extension/</code> 加载扩展——Chrome：<i>chrome://extensions</i>，开开发者模式，<i>加载已解压的扩展程序</i>。",
                        "打开它的选项。服务在默认端口上它会自己配对；否则把 <code>facetmark token</code> 的输出粘进去。",
                    ],
                ),
                (
                    "callout",
                    "",
                    "验证连接",
                    "<p>在扩展里搜索一个已知书签，确认返回结果。扩展把请求发到你配置的服务地址；服务端还可能调用已配置的模型。远程使用时检查地址、令牌和浏览器权限。</p>",
                ),
            ],
        ),
        (
            "mcp",
            "Claude、Cursor，以及任何说 MCP 的东西",
            [
                (
                    "p",
                    "facetmark 自带一个 MCP 服务，所以助手可以把「搜你的书签」当成一个工具来用，而不是你手动往对话框里粘链接。",
                ),
                ("cb", "先手动跑一下", "facetmark mcp"),
                (
                    "cb",
                    "Claude Desktop — claude_desktop_config.json",
                    "{\n"
                    '  "mcpServers": {\n'
                    '    "facetmark": {\n'
                    '      "command": "facetmark",\n'
                    '      "args": ["mcp"]\n'
                    "    }\n"
                    "  }\n"
                    "}",
                ),
                (
                    "p",
                    "Cursor 在它自己的 MCP 设置里是同样的形状。如果编辑器看到的 PATH 里没有 "
                    "<code>facetmark</code>，就写绝对路径——几乎每一份「工具一直不出现」的反馈都是这个原因。",
                ),
                (
                    "dashed",
                    "intent",
                    "助手能做什么、不能做什么",
                    [
                        (
                            "p",
                            "它能搜索、能读一条书签、能列时段、能在你的库上提问。它不能删任何东西，不能写配置，也碰不到数据库以外的地方。",
                        )
                    ],
                ),
                (
                    "callout",
                    "",
                    "验证工具是否可用",
                    "<p>重启客户端，确认工具列表中出现 facetmark，再搜索一个已知标题。GUI 客户端可能没有终端中的 PATH 和环境变量；必要时使用可执行文件的绝对路径并显式配置环境。</p>",
                ),
            ],
        ),
        (
            "karakeep",
            "karakeep",
            [
                (
                    "p",
                    "如果你的链接都放在 karakeep 里，facetmark 可以从那边建索引，而不是从浏览器导出文件。",
                ),
                (
                    "p",
                    '具体安装和调用方式见 <a href="guide.zh.html#karakeep">karakeep 接入参考</a>。先用少量页面对照直接检索结果，再决定是否接入整个书签库。',
                ),
                (
                    "callout",
                    "warn",
                    "有实测，值得在你投入之前先知道",
                    "<p>经 karakeep 自己的关键词抽取绕一圈，代价是 <b>Recall@5 掉 0.81 个百分点</b>（CI95 −2.44 到 +0.81），并且和直接建索引在第一名上只有 "
                    "<b>79.06%</b> 一致。词表会塌缩：19,016 个不同词项变成 13 个。仓库里记下来的结论是 "
                    "<code>roundtrip_unfaithful</code>——能用，但不等价。能直接索引页面就直接索引。</p>",
                ),
            ],
        ),
        (
            "cli",
            "命令行",
            [
                (
                    "p",
                    "页面能做的都在这里，还有几样页面做不到的。任何一条后面都能加 <code>--help</code>。",
                ),
                (
                    "table",
                    ["命令", "作用"],
                    [
                        ["<code>facetmark import</code>", "读入一个书签导出文件"],
                        ["<code>facetmark browsers</code>", "找出这台机器上已有的书签文件"],
                        ["<code>facetmark index</code>", "建索引，或者补齐"],
                        ["<code>facetmark reindex</code>", "全部从头再建一遍"],
                        ["<code>facetmark search</code>", "在终端里搜"],
                        ["<code>facetmark show</code>", "一条书签的全部信息"],
                        ["<code>facetmark sessions</code>", "列出所有时段"],
                        ["<code>facetmark stats</code>", "「库」那一屏的文字版"],
                        ["<code>facetmark health</code>", "找死链"],
                        ["<code>facetmark serve</code>", "网页界面和 API"],
                        ["<code>facetmark mcp</code>", "MCP 服务"],
                        ["<code>facetmark token</code>", "打印配对令牌"],
                        ["<code>facetmark config path</code>", "配置写到哪"],
                        ["<code>facetmark config show</code>", "所有配置，敏感项掩码"],
                        ["<code>facetmark migrate</code>", "把旧数据库升上来"],
                        ["<code>facetmark demo</code>", "一个假的库，用来到处点点看"],
                        ["<code>facetmark eval</code>", "重跑那些检索实测"],
                        ["<code>facetmark version</code>", "版本"],
                    ],
                ),
                (
                    "p",
                    "<code>facetmark demo</code> 是判断你到底要不要用这东西最实在的办法：它用生成的页面搭出一个库，不要 key "
                    "不联网，让你在导入任何自己的东西之前先把每一屏都点一遍。",
                ),
            ],
        ),
        (
            "backup",
            "备份与恢复",
            [
                ("h3", "可移植的书签导出"),
                ("cb", "shell", "facetmark export bookmarks-backup.json"),
                (
                    "p",
                    "导出保存书签数据，恢复后需要重建衍生索引。请先在独立数据目录验证恢复；不要覆盖现有书签库。",
                ),
                ("cb", "shell", "facetmark import bookmarks-backup.json\nfacetmark index"),
                ("h3", "保留正文和向量的完整备份"),
                (
                    "p",
                    "用 <code>facetmark stats</code> 确认数据库路径。停止服务及所有使用该库的 CLI / MCP 进程后，复制数据库文件；如果仍有 <code>-wal</code> "
                    "/ <code>-shm</code> 文件，勿直接丢弃，应使用 SQLite 的备份机制取得一致快照。",
                ),
                (
                    "callout",
                    "",
                    "恢复后检查",
                    "<p>把备份放入独立目录，以该数据库运行 <code>facetmark "
                    "stats</code>，检查数量并搜索已知标题。升级版本前保留原始备份。配置文件与配对令牌需要单独保管，其中可能包含密钥。</p>",
                ),
            ],
        ),
    ],
}
