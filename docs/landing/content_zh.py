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
    "copy": {"label": "\u590d\u5236", "done": "\u5df2\u590d\u5236"},
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
            "facetmark \u2014 \u672c\u5730\u4f18\u5148\u7684\u4e66\u7b7e\u68c0\u7d22",
            "\u6309\u9875\u9762\u8bb2\u4e86\u4ec0\u4e48\u3001\u4f60\u4e3a\u4ec0\u4e48\u5b58\u5b83\u3001"
            "\u4ee5\u53ca\u5b58\u5b83\u65f6\u65c1\u8fb9\u8fd8\u5b58\u4e86\u4ec0\u4e48\u6765\u641c"
            "\u4e66\u7b7e\u3002\u5168\u90e8\u6570\u636e\u662f\u4f60\u673a\u5668\u4e0a\u7684\u4e00"
            "\u4e2a SQLite \u6587\u4ef6\u3002\u4e0d\u7528\u8d26\u53f7\uff0c\u4e0d\u4e0a\u4f20\u3002",
        ),
        "quickstart": (
            "\u5feb\u901f\u4e0a\u624b \u2014 facetmark",
            "\u4ece\u4ec0\u4e48\u90fd\u6ca1\u88c5\uff0c\u5230\u6d4f\u89c8\u5668\u91cc\u6253\u5f00\u4e00\u4e2a\u641c\u7d22\u9875\uff1a\u4e94\u6b65\uff0c\u6bcf\u6761\u547d\u4ee4\u90fd\u80fd"
            "\u76f4\u63a5\u590d\u5236\uff0c\u8fd8\u914d\u4e86\u56fe\u544a\u8bc9\u4f60\u6bcf\u4e00\u6b65\u5e94\u8be5\u770b\u5230\u4ec0\u4e48\u3002",
        ),
        "guide": (
            "\u4f7f\u7528\u6307\u5357 \u2014 facetmark",
            "\u5b89\u88c5\u3001\u5bfc\u5165\u3001\u5efa\u7d22\u5f15\u3001\u641c\u7d22\u3001\u8d77"
            "\u670d\u52a1\u3002\u6d4f\u89c8\u5668\u6269\u5c55\u3001MCP \u670d\u52a1\u5668\u3001"
            "karakeep \u63d2\u4ef6\uff0c\u4ee5\u53ca\u5168\u90e8\u914d\u7f6e\u9879\u548c\u547d"
            "\u4ee4\u3002",
        ),
        "measured": (
            "\u5b9e\u6d4b\u8bb0\u5f55 \u2014 facetmark",
            "facetmark \u91cc\u6bcf\u4e00\u6761\u68c0\u7d22\u7ed3\u8bba\uff0c\u8fde\u540c\u5f97"
            "\u51fa\u5b83\u7684\u534f\u8bae\u4e00\u8d77\u516c\u5f00 \u2014\u2014 \u5305\u62ec"
            "\u8f93\u4e86\u7684\u90a3\u56db\u4e2a\u3002",
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
                    ("\u6392\u9519", "guide.zh.html#trouble"),
                ],
            ),
            (
                "\u63a5\u53e3",
                [
                    ("\u672c\u5730\u9875\u9762", "guide.zh.html#webui"),
                    ("\u547d\u4ee4\u884c", "guide.zh.html#commands"),
                    ("HTTP API", "guide.zh.html#serve"),
                    ("MCP \u670d\u52a1\u5668", "guide.zh.html#mcp"),
                    ("\u6d4f\u89c8\u5668\u6269\u5c55", "guide.zh.html#extension"),
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
            "facetmark v1.6.1 \u00b7 MIT",
            "Python 3.10+ \u00b7 \u4e00\u4e2a SQLite \u6587\u4ef6",
            "\u8fd9\u4e2a\u7ad9\u4e0a\u6ca1\u6709\u4e00\u4e2a\u6570\u5b57\u662f\u6ca1\u6709\u534f"
            "\u8bae\u6491\u7740\u7684\u3002",
        ],
    },
}

ZH["index"] = {
    "kicker": "\u672c\u5730\u4f18\u5148\u7684\u4e66\u7b7e\u68c0\u7d22",
    "h1": "\u627e\u56de\u90a3\u4e2a\u4f60<em>\u53ea\u8bb0\u5f97\u4e00\u534a</em>\u7684\u4e66\u7b7e\u3002",
    "lede": (
        "\u4f60\u5b58\u8fc7\u5b83\u3002\u4f60\u5927\u6982\u8bb0\u5f97\u5b83\u8bb2\u4ec0\u4e48\uff0c"
        "\u6216\u8005\u8bb0\u5f97\u5f53\u65f6\u4e3a\u4ec0\u4e48\u60f3\u8981\u5b83\uff0c\u6216\u8005"
        "\u8bb0\u5f97\u90a3\u4e2a\u4e0b\u5348\u4f60\u8fd8\u5728\u770b\u522b\u7684\u4ec0\u4e48 \u2014\u2014 \u5c31\u662f\u4e0d\u8bb0\u5f97\u6807\u9898\u3002facetmark \u628a\u8fd9"
        "\u4e09\u4ef6\u4e8b\u5168\u90e8\u5efa\u6210\u7d22\u5f15\uff0c\u4e00\u8d77\u62ff\u6765"
        "\u641c\uff0c\u5168\u90e8\u843d\u5728<strong>\u4f60\u81ea\u5df1\u673a\u5668\u4e0a\u7684"
        "\u4e00\u4e2a SQLite \u6587\u4ef6</strong>\u91cc\u3002"
    ),
    "cta": [
        ("\u770b\u4f7f\u7528\u6307\u5357", "guide.zh.html", True),
        ("\u770b\u5b9e\u6d4b\u8bb0\u5f55", "measured.zh.html", False),
        ("GitHub", REPO, False),
    ],
    "chips": [
        ("Python", "3.10+"),
        ("\u6d4b\u8bd5", "1,514"),
        ("\u8bb8\u53ef\u8bc1", "MIT"),
        ("\u5b58\u50a8", "1 \u4e2a SQLite \u6587\u4ef6"),
        ("\u4e0a\u4f20", "\u65e0"),
    ],
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
    "prob_h2": "\u4f60\u627e\u4e00\u4e2a\u5b58\u8fc7\u7684\u9875\u9762\uff0c\u53ea\u6709\u4e09\u79cd\u627e\u6cd5",
    "prob_lede": (
        "\u6587\u4ef6\u5939\u6811\u80fd\u56de\u7b54\u7b2c\u4e00\u79cd\u3002\u540e\u4e24\u79cd"
        "\u5b83\u4e00\u53e5\u8bdd\u90fd\u63a5\u4e0d\u4e0a\uff0c\u6240\u4ee5\u4f60\u6700\u540e"
        "\u603b\u662f\u5728\u7ffb\u5386\u53f2\u8bb0\u5f55\u3002\u8fd9\u4e09\u7c7b\u5c31\u662f"
        "\u6574\u5957\u8bc4\u6d4b\u7528\u7684\u4e09\u79cd\u67e5\u8be2\u7c7b\u578b\uff0c\u540e"
        "\u9762\u7684\u6570\u5b57\u662f\u5b83\u4eec\u5728\u4e00\u4e2a\u771f\u5b9e\u7684 1,700 "
        "\u6761\u4e66\u7b7e\u5e93\u4e0a\u771f\u5b9e\u8dd1\u51fa\u6765\u7684 Recall@5\u3002"
    ),
    "prob_cards": [
        (
            "\u5185\u5bb9\u578b",
            "\u4f60\u8bb0\u5f97\u91cc\u9762\u7684\u8bcd",
            "\u9875\u9762\u91cc\u5199\u4e86 <em>sqlite-vec</em>\u3001\u5199\u4e86 "
            "<em>shard</em>\uff0c\u4f60\u60f3\u628a\u5b83\u627e\u56de\u6765\u3002\u8fd9\u79cd"
            "\u4efb\u4f55\u50cf\u6837\u7684\u7d22\u5f15\u90fd\u80fd\u5e72\u3002",
            "\u300csqlite-vec latency shard recall\u300d",
            "0.959",
            "Recall@5",
            "good",
        ),
        (
            "\u6a21\u7cca\u578b",
            "\u4f60\u8bb0\u5f97\u610f\u601d\uff0c\u4e0d\u8bb0\u5f97\u8bcd",
            "\u4f60\u77e5\u9053\u5b83\u89e3\u51b3\u4e86\u4ec0\u4e48\u95ee\u9898\u3002\u4f60"
            "\u4ece\u6765\u5c31\u6ca1\u8bb0\u4f4f\u90a3\u4e2a\u4ea7\u54c1\u53eb\u4ec0\u4e48"
            "\uff0c\u6216\u8005\u5df2\u7ecf\u5fd8\u4e86\u3002\u6587\u4ef6\u5939\u540d\u5b57"
            "\u5728\u8fd9\u91cc\u4e00\u70b9\u5fd9\u4e5f\u5e2e\u4e0d\u4e0a\uff0c\u5185\u5bb9"
            "\u9762\u5c31\u662f\u4e3a\u8fd9\u4e00\u7c7b\u5b58\u5728\u7684\u3002",
            "\u300c\u90a3\u4e2a\u8bb2\u628a\u5411\u91cf\u548c\u5176\u4ed6\u6570\u636e\u653e"
            "\u5728\u4e00\u8d77\u3001\u4e0d\u7528\u518d\u8d77\u4e00\u4e2a\u670d\u52a1\u7684"
            "\u4e1c\u897f\u300d",
            "0.706",
            "Recall@5",
            "",
        ),
        (
            "\u60c5\u666f\u578b",
            "\u4f60\u8bb0\u5f97\u65f6\u95f4\uff0c\u548c\u65c1\u8fb9\u90a3\u4e00\u6279",
            "\u300c\u5c31\u662f\u6211\u770b qdrant \u7684\u90a3\u4e2a\u4e0b\u5348\u3002\u300d"
            "facetmark \u4f1a\u91cd\u5efa\u4fdd\u5b58\u4f1a\u8bdd\u548c\u4e00\u5f20\u94fe"
            "\u63a5\u56fe\u6765\u56de\u7b54\u5b83 \u2014\u2014 \u800c\u5b83\u4f9d\u7136\u662f"
            "\u77ed\u677f\u3002\u653e\u5728\u8fd9\u91cc\u662f\u56e0\u4e3a\u5b83\u662f\u771f"
            "\u7684\uff0c\u4e0d\u662f\u56e0\u4e3a\u5b83\u597d\u770b\u3002",
            "\u300c\u548c qdrant \u90a3\u7bc7\u5dee\u4e0d\u591a\u65f6\u5019\u5b58\u7684\u53e6"
            "\u4e00\u4e2a\u300d",
            "0.279",
            "Recall@5",
            "bad",
        ),
    ],
    "prob_note": (
        "479 \u6761\u67e5\u8be2\uff0c\u4e00\u4e2a\u771f\u5b9e\u5e93\uff0cA \u6863\u3002\u5b8c"
        "\u6574\u534f\u8bae\u548c\u5269\u4e0b\u7684\u8868\u5728<a href=\"measured.zh.html#w1\">"
        "\u5b9e\u6d4b\u9875</a>\u3002"
    ),
    "fac_label": "\u5b83\u662f\u600e\u4e48\u5de5\u4f5c\u7684",
    "fac_h2": "\u56db\u4e2a\u9762\u3002\u51fa\u5382\u9ed8\u8ba4\u53ea\u5f00\u4e00\u4e2a\u3002",
    "fac_lede": (
        "facetmark \u5728\u540c\u4e00\u4e2a\u5e93\u4e0a\u5efa\u4e86\u56db\u5957\u4e92\u76f8"
        "\u72ec\u7acb\u7684\u7d22\u5f15\uff0c\u53ef\u4ee5\u7528 RRF \u628a\u5b83\u4eec\u878d"
        "\u5408\u8d77\u6765\u3002\u7136\u540e\u5b83\u628a\u8fd9\u4e2a\u878d\u5408\u5b9e\u6d4b"
        "\u4e86\u4e00\u904d\uff0c\u53d1\u73b0\u8fd8\u4e0d\u5982\u5355\u62ff\u6700\u597d\u7684"
        "\u90a3\u4e00\u4e2a\u9762\uff0c\u6240\u4ee5\u51fa\u5382\u9ed8\u8ba4\u53ea\u5f00\u4e00"
        "\u4e2a\u9762\u3002\u53e6\u5916\u4e09\u4e2a\u8fd8\u5728\uff0c\u8fd8\u6709\u6d4b\u8bd5"
        "\uff0c\u4e00\u4e2a\u53c2\u6570\u5c31\u80fd\u6253\u5f00 \u2014\u2014 \u53ea\u662f"
        "\u9ed8\u8ba4\u4e0d\u5f00\uff0c\u56e0\u4e3a\u6570\u5b57\u8bf4\u4e0d\u8be5\u5f00\u3002"
    ),
    "fac_head": ["\u9762", "\u7d22\u5f15\u7684\u662f\u4ec0\u4e48",
                 "\u56de\u7b54\u4ec0\u4e48\u6837\u7684\u95ee\u9898", "\u9ed8\u8ba4"],
    "fac_rows": [
        (
            "<b>\u8bcd\u9762</b><br><span class=\"tiny\">\u4e24\u4e2a FTS5 \u7d22\u5f15</span>",
            "\u6807\u9898\u3001URL\u3001\u6b63\u6587\u7684\u5b57\u7b26\u4e09\u5143\u7ec4\u548c"
            "\u8bcd\u6bb5\u3002",
            "\u7cbe\u786e\u5b57\u7b26\u4e32\u3001ID\u3001\u4ee3\u7801\u3001\u62a5\u9519\u4fe1"
            "\u606f\uff0c\u4ee5\u53ca\u6ca1\u6709\u7a7a\u683c\u53ef\u5206\u7684\u4e2d\u6587\u3002",
            "<span class=\"badge warn\">\u5173</span><br>"
            "<span class=\"tiny\">\u878d\u5408\u65f6\u8f93\u4e86 5.4pp</span>",
        ),
        (
            "<b>\u5185\u5bb9\u9762</b><br><span class=\"tiny\">\u7a20\u5bc6\u5411\u91cf</span>",
            "\u9875\u9762\u6b63\u6587\u62bd\u53d6\u540e\u7684\u5d4c\u5165\uff0c\u4e0d\u662f"
            "\u6807\u9898\u7684\u3002",
            "\u6362\u8bf4\u6cd5\u3002\u8bcd\u5fd8\u4e86\u3001\u610f\u601d\u8fd8\u5728\u7684"
            "\u90a3\u79cd\u3002",
            "<span class=\"badge pass\">\u5f00</span><br>"
            "<span class=\"tiny\">W1 \u8d62\u5bb6\uff0c0.643</span>",
        ),
        (
            "<b>\u610f\u56fe\u9762</b><br><span class=\"tiny\">\u751f\u6210\u7684\u67e5\u8be2</span>",
            "\u6a21\u578b\u4e3a\u8fd9\u4e2a\u9875\u9762\u5199\u7684\u5019\u9009\u95ee\u6cd5"
            "\uff0c\u518d\u7528\u300c\u80fd\u4e0d\u80fd\u628a\u8fd9\u9875\u635e\u56de\u6765"
            "\u300d\u8fc7\u6ee4\u4e00\u904d\u3002",
            "\u4f60\u4ee5\u540e\u4f1a\u600e\u4e48\u5f00\u53e3\u627e\u5b83\u3002",
            "<span class=\"badge warn\">\u5173</span><br>"
            "<span class=\"tiny\">\u53ea\u6709 38% \u7684\u610f\u56fe\u7ad9\u5f97\u4f4f</span>",
        ),
        (
            "<b>\u4e0a\u4e0b\u6587\u9762</b><br><span class=\"tiny\">\u4f1a\u8bdd\u4e0e\u56fe</span>",
            "\u4fdd\u5b58\u4f1a\u8bdd\u805a\u7c7b\u3001\u57df\u540d\u7ed3\u6784\uff0c\u4ee5"
            "\u53ca\u5168\u5e93\u7684\u94fe\u63a5\u56fe\u3002",
            "\u300c\u6211\u5b58\u90a3\u4e2a\u7684\u65f6\u5019\u8fd8\u987a\u624b\u5b58\u4e86"
            "\u54ea\u4e9b\uff1f\u300d",
            "<span class=\"badge pass\">\u56fe\u6269\u5c55\u5f00</span> "
            "<span class=\"badge fail\">\u60c5\u666f\u95e8\u5173</span><br>"
            "<span class=\"tiny\">+2.09pp / \u221218.83pp</span>",
        ),
    ],
    "fac_note": (
        "\u8fd9\u56db\u4e2a\u7ed3\u8bba\u6bcf\u4e00\u4e2a\u90fd\u5bf9\u5e94<a href=\""
        "measured.zh.html\">\u5b9e\u6d4b\u9875</a>\u4e0a\u4e00\u4efd\u534f\u8bae\u3001\u4e00"
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
    "app_h2": "\u4e00\u4e2a\u641c\u7d22\u9875\uff0c\u5c31\u5728 <code>127.0.0.1:8787/app</code>",
    "app_lede": (
        "<code>facetmark serve</code> \u4f1a\u6253\u5370\u4e00\u4e2a\u5730\u5740\u3002\u6253\u5f00\u5b83\uff0c\u4f60\u5c31\u62ff\u5230\u4e86\u641c\u7d22"
        "\u6846\u3001\u548c\u6269\u5c55\u91cc\u540c\u4e00\u5957\u7ed3\u679c\u6807\u8bb0\uff0c\u5916\u52a0\u4e00\u4e2a\u544a\u8bc9\u4f60\u7d22\u5f15\u91cc\u5230\u5e95\u6709\u4ec0\u4e48\u7684\u7b2c\u4e8c\u4e2a"
        "\u89c6\u56fe\u3002\u4e0d\u7528\u88c5\uff0c\u4e5f\u4e0d\u7528\u7f16\u8bd1 \u2014\u2014 \u8fd9\u4e2a\u9875\u9762\u5c31\u88c5\u5728 Python \u5305\u91cc\uff0c\u7531\u540c\u4e00\u4e2a"
        "\u8fdb\u7a0b\u53d1\u51fa\u6765\u3002"
    ),
    "app_shot": (
        "assets/app-search-zh.png",
        "facetmark \u641c\u7d22\u9875\uff0c\u4e0a\u9762\u662f\u6392\u597d\u5e8f\u7684\u7ed3\u679c\uff0c\u4e0b\u9762\u662f\u5f53\u65f6\u524d\u540e\u4e00\u8d77\u5b58\u7684\u90a3\u4e00\u7ec4",
        "<b>\u641c\u7d22\u3002</b>\u7b2c\u4e00\u5c4f\u662f\u5b57\u9762\u5339\u914d\uff0c\u4e0d\u82b1\u4efb\u4f55\u6a21\u578b\u8c03\u7528\uff1b\u6392\u597d\u5e8f\u7684\u7b54\u6848\u5230\u4e86\u5c31"
        "\u628a\u5b83\u6362\u6389\u3002\u5f53\u65f6\u524d\u540e\u4e00\u8d77\u5b58\u7684\u9875\u9762\u5355\u72ec\u6210\u4e00\u7ec4\uff0c\u4e0d\u4f1a\u88ab\u6253\u6563\u6df7\u8fdb\u6392\u540d\u91cc\u3002\u8fd9\u5f20"
        "\u56fe\u4f1a\u8ddf\u7740\u4f60\u6b63\u5728\u8bfb\u7684\u8fd9\u4e2a\u9875\u9762\u5207\u6362\u6df1\u6d45\u8272\u3002",
    ),
    "app_shot_dark": (
        "assets/app-search-zh-dark.png",
        "\u540c\u4e00\u4e2a\u641c\u7d22\u9875\u7684\u6df1\u8272\u6a21\u5f0f",
    ),
    "app_points": [
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
        ("0.643", "479 \u6761\u771f\u5b9e\u67e5\u8be2\u3001\u5355\u4e00\u4e2a\u9762\u7684 Recall@5", "good"),
        ("\u22125.4pp", "\u56db\u4e2a\u9762\u5168\u6253\u5f00\u7684\u4ee3\u4ef7", "bad"),
        ("\u221218.83pp", "\u5df2\u7ecf\u53d1\u51fa\u53bb\u7684\u60c5\u666f\u95e8\u7684\u4ee3\u4ef7", "bad"),
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
    "qs_h2": "\u56db\u6761\u547d\u4ee4",
    "qs_lede": (
        "\u5982\u679c\u4f60\u7528\u7684\u662f Chromium \u7cfb\u6d4f\u89c8\u5668 \u2014\u2014 "
        "Chrome\u3001Edge\u3001Brave\u3001Vivaldi\u3001Chromium\u3001Opera \u2014\u2014 "
        "\u8fde\u5bfc\u51fa\u90fd\u4e0d\u7528\u3002<code>facetmark import</code> \u4e0d\u5e26"
        "\u53c2\u6570\u65f6\u4f1a\u81ea\u5df1\u627e\u5230\u6d4f\u89c8\u5668\u914d\u7f6e\u6587"
        "\u4ef6\u5e76\u8bfb\u5b83\u3002"
    ),
    "qs_code": (
        "pip install facetmark\n\n"
        "facetmark import                  # \u81ea\u52a8\u627e\u6d4f\u89c8\u5668\uff0c\u53ea"
        "\u8bfb\n"
        "facetmark index                   # \u6293\u53d6\u3001\u5bcc\u5316\u3001\u5d4c\u5165"
        "\u3001\u4f1a\u8bdd\u3001\u8fb9\n"
        'facetmark search "\u90a3\u7bc7\u8bb2\u628a\u5411\u91cf\u5b58\u5728 sqlite \u91cc\u7684"\n'
    ),
    "qs_steps": [
        "<b>\u5b89\u88c5\u3002</b>Python 3.10 \u4ee5\u4e0a\u3002\u552f\u4e00\u4e00\u4e2a\u5927"
        "\u4f53\u79ef\u7684\u53ef\u9009\u4f9d\u8d56\u662f "
        "<code>sentence-transformers</code>\uff0c\u800c\u4e14\u53ea\u6709\u4f60\u60f3\u672c"
        "\u5730\u8dd1\u5d4c\u5165\u65f6\u624d\u9700\u8981\u3002",
        "<b>\u5bfc\u5165\u3002</b>\u4ece\u4e0d\u5199\u56de\u4f60\u7684\u6d4f\u89c8\u5668\u3002"
        "Firefox \u548c Safari \u4e0d\u662f Chromium \u7cfb\uff0c\u8fd9\u4e24\u4e2a\u9700\u8981"
        "\u5148\u5bfc\u51fa\u4e00\u6b21 HTML \u2014\u2014 "
        "<a href=\"guide.zh.html#import\">\u600e\u4e48\u5bfc</a>\u3002",
        "<b>\u63a5\u4e0a\u6a21\u578b\u3002</b>\u4efb\u4f55 OpenAI \u517c\u5bb9\u7684\u7aef"
        "\u70b9\uff0c\u6216\u8005\u4e00\u4e2a\u672c\u5730\u5d4c\u5165\u6a21\u578b\u3001\u5b8c"
        "\u5168\u4e0d\u8981 key\u3002\u4e00\u4e2a\u6a21\u578b\u90fd\u4e0d\u63a5\u4e5f\u80fd"
        "\u7528\uff0c\u53ea\u662f\u53ea\u5269\u8bcd\u9762\u548c\u4f1a\u8bdd\u56fe\u3002",
        "<b>\u5efa\u7d22\u5f15\u3002</b>\u5e42\u7b49\u3002\u4ee5\u540e\u65b0\u589e\u4e86\u4e66"
        "\u7b7e\u518d\u8dd1\u4e00\u6b21\uff0c\u5b83\u53ea\u505a\u65b0\u589e\u7684\u90a3\u4e00"
        "\u90e8\u5206\u3002",
        "<b>\u641c\u3002</b>\u6216\u8005 <code>facetmark serve</code> \u4e4b\u540e\u7528"
        "\u6d4f\u89c8\u5668\u6269\u5c55\u3001HTTP API\u3001\u6216\u8005 MCP \u5ba2\u6237"
        "\u7aef\u3002",
    ],
    "qs_offline": (
        "\u624b\u8fb9\u6ca1 API key\uff1f<code>facetmark demo</code> \u4f1a\u79bb\u7ebf\u9020"
        "\u4e00\u4e2a 60 \u9875\u7684\u5408\u6210\u5e93\u5e76\u641c\u5b83\uff0c\u8ba9\u4f60"
        "\u5148\u770b\u770b\u8f93\u51fa\u957f\u4ec0\u4e48\u6837\uff0c\u518d\u51b3\u5b9a\u8981"
        "\u4e0d\u8981\u6295\u5165\u3002"
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
            "16 \u6761\u547d\u4ee4\u3002<code>search</code> \u6709 "
            "<code>--explain</code> \u53ef\u4ee5\u6253\u5370\u547d\u4e2d\u7684\u662f\u54ea"
            "\u4e2a\u9762\uff0c<code>--config</code> \u53ef\u4ee5\u6309\u540d\u5b57\u8dd1"
            "\u4efb\u4f55\u4e00\u4e2a\u6d88\u878d\u6863\u3002",
            "guide.zh.html#commands",
            "\u547d\u4ee4\u53c2\u8003",
        ),
        (
            "http",
            "HTTP API",
            "<code>facetmark serve</code> \u76d1\u542c 127.0.0.1:8787\u300227 \u6761\u8def"
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
            "\u6709\u4e1c\u897f\u88ab\u4e0a\u4f20\u5417\uff1f",
            "<p>\u4e24\u4ef6\u4e1c\u897f\u4f1a\u79bb\u5f00\u4f60\u7684\u673a\u5668\uff0c\u4e24"
            "\u4ef6\u90fd\u5f52\u4f60\u63a7\u5236\u3002\u9875\u9762\u6293\u53d6\u4f1a\u53bb"
            "\u4f60\u81ea\u5df1\u5b58\u7684\u7f51\u7ad9\u3002\u5bcc\u5316\u548c\u5d4c\u5165"
            "\u4f1a\u53bb\u4f60\u81ea\u5df1\u914d\u7684\u90a3\u4e2a OpenAI \u517c\u5bb9\u7aef"
            "\u70b9 \u2014\u2014 \u53ef\u4ee5\u662f OpenAI\uff0c\u4e5f\u53ef\u4ee5\u662f"
            "\u4f60\u684c\u5b50\u4e0b\u90a3\u53f0\u673a\u5668\u3002</p>"
            "<p>\u628a <code>FACETMARK_EMBED_BACKEND=local</code> \u6253\u5f00\u3001"
            "<code>FACETMARK_API_KEY</code> \u7559\u7a7a\uff0c\u9664\u4e86\u6293\u9875\u9762"
            "\u4e4b\u5916\u5c31\u4ec0\u4e48\u90fd\u4e0d\u51fa\u53bb\u4e86\u3002\u6ca1\u6709"
            "\u4e00\u4e2a\u53eb facetmark \u7684\u670d\u52a1\u5668\u5728\u7b49\u7740\u6536"
            "\u6570\u636e\u3002\u4e5f\u6ca1\u6709\u8d26\u53f7\u3002</p>",
        ),
        (
            "\u4f1a\u52a8\u6211\u6d4f\u89c8\u5668\u91cc\u7684\u4e66\u7b7e\u5417\uff1f",
            "<p>\u4e0d\u4f1a\u3002\u5bfc\u5165\u662f\u5355\u5411\u53ea\u8bfb\u3002\u5bfc\u5165"
            "\u5668\u6253\u5f00\u6d4f\u89c8\u5668\u914d\u7f6e\u91cc\u7684 "
            "<code>Bookmarks</code> \u6587\u4ef6\u6216\u8005\u4f60\u5bfc\u51fa\u7684 "
            "HTML\uff0c\u8bfb\u5b8c\u5c31\u5173\u3002\u4ee3\u7801\u91cc\u6ca1\u6709\u4efb\u4f55"
            "\u4e00\u5904\u5f80\u6d4f\u89c8\u5668\u914d\u7f6e\u91cc\u5199\u4e1c\u897f\u3002</p>"
            "<p>facetmark \u8fd9\u8fb9\u4e5f\u4e0d\u5220\u3002\u8870\u51cf\u5c42\u53ea\u4f1a"
            "\u628a\u9648\u65e7\u9875\u9762\u5f80\u540e\u6392\uff0c\u4ece\u6765\u4e0d\u5220"
            "\u884c\u3002</p>",
        ),
        (
            "\u5b8c\u5168\u4e0d\u7528\u5927\u6a21\u578b\u80fd\u7528\u5417\uff1f",
            "<p>\u80fd\uff0c\u4f1a\u5dee\uff0c\u800c\u4e14\u5b83\u4f1a\u544a\u8bc9\u4f60\u5dee"
            "\u5728\u54ea\u3002\u4e0d\u63a5\u6a21\u578b\uff0c\u4f60\u4fdd\u7559\u4e24\u4e2a"
            "\u8bcd\u9762\u3001\u6574\u5957\u4fdd\u5b58\u4f1a\u8bdd\u548c\u57df\u540d\u56fe"
            "\u3002\u4f60\u5931\u53bb\u5185\u5bb9\u9762 \u2014\u2014 \u5c31\u662f\u6d4b\u5f97"
            "\u6700\u597d\u7684\u90a3\u4e2a \u2014\u2014 \u548c\u610f\u56fe\u9762\u3002</p>"
            "<p>\u6298\u4e2d\u65b9\u6848\uff1a\u53ea\u8dd1\u4e00\u4e2a\u672c\u5730\u5d4c\u5165"
            "\u6a21\u578b\u652f\u6491\u5185\u5bb9\u9762\uff0c\u4e0d\u63a5 chat \u6a21\u578b"
            "\u3002\u4f60\u5931\u53bb\u6458\u8981\u548c\u751f\u6210\u610f\u56fe\uff0c\u4fdd"
            "\u4f4f\u6362\u8bf4\u6cd5\u641c\u7d22\u3002</p>",
        ),
        (
            "\u5efa\u4e00\u6b21\u7d22\u5f15\u8981\u591a\u5c11\u94b1\uff1f",
            "<p>\u94b1\u4e3b\u8981\u82b1\u5728\u5bcc\u5316\uff1a\u5927\u81f4\u6bcf\u9875\u4e00"
            "\u6b21\u5c0f\u7684 chat \u8c03\u7528\u3002\u7528\u4fbf\u5b9c\u6a21\u578b\u7684"
            "\u8bdd\uff0c1,700 \u9875\u662f\u51e0\u6bdb\u94b1\u7684\u4e8b\u3002\u5d4c\u5165"
            "\u66f4\u4fbf\u5b9c\uff0c\u672c\u5730\u8dd1\u5c31\u662f\u514d\u8d39\u3002</p>"
            "<p>\u4f46\u58c1\u949f\u65f6\u95f4\u7684\u5927\u5934\u662f<em>\u6293\u9875\u9762"
            "</em>\uff0c\u4e0d\u662f\u6a21\u578b\u3002facetmark \u9075\u5b88 robots.txt\uff0c"
            "\u5e76\u4e14\u6309\u57df\u540d\u7ed9\u81ea\u5df1\u9650\u901f \u2014\u2014 \u8fd9"
            "\u662f\u6545\u610f\u7684\u3002<code>--no-fetch</code> \u53ea\u7d22\u5f15\u6807"
            "\u9898\uff0c\u51e0\u79d2\u949f\u5c31\u5b8c\u3002</p>",
        ),
        (
            "\u4e3a\u4ec0\u4e48\u9ed8\u8ba4\u53ea\u5f00\u4e00\u4e2a\u9762\uff1f",
            "<p>\u56e0\u4e3a\u56db\u9762\u878d\u5408\u5728 479 \u6761\u771f\u5b9e\u67e5\u8be2"
            "\u4e0a\u88ab\u6d4b\u4e86\uff0c\u7ed3\u679c\u6bd4\u5355\u72ec\u7528\u5185\u5bb9"
            "\u9762<em>\u4f4e</em> 5.4 \u4e2a\u767e\u5206\u70b9\u7684 Recall@5\uff0c\u5ef6"
            "\u8fdf\u8fd8\u9ad8 3.5 \u500d\u3002</p>"
            "<p>\u673a\u5236\u4e5f\u5199\u4e0b\u6765\u4e86\uff1a\u5e73\u6743\u91cd\u7684 RRF "
            "\u4e0b\uff0c\u4e24\u4e2a\u5f31\u9762\u78b0\u5de7\u7684\u4e00\u81f4\uff080.0279"
            "\uff09\u80fd\u6295\u8d62\u4e00\u4e2a\u5f3a\u9762\u7684\u786e\u5b9a\uff080.0164"
            "\uff09\u3002\u56db\u4e2a\u9762\u90fd\u8fd8\u5728\uff0c\u90fd\u8fd8\u6709\u6d4b"
            "\u8bd5\u3002<code>--config C</code> \u4e00\u4e0b\u5c31\u5168\u6253\u5f00\u4e86"
            "\uff0c\u4f60\u53ef\u4ee5\u81ea\u5df1\u770b\u3002</p>",
        ),
        (
            "\u8fd9\u662f\u4e00\u4e2a\u4ea7\u54c1\u5417\uff1f",
            "<p>\u4e0d\u662f\u3002\u5b83\u662f\u4e00\u4e2a\u5e26\u7740\u8bc4\u6d4b\u53f0\u67b6"
            "\u7684\u5de5\u5177\uff0c\u800c\u53f0\u67b6\u624d\u662f\u91cd\u70b9\u3002\u6bcf"
            "\u4e00\u4e2a\u6539\u8fc7\u7684\u9ed8\u8ba4\u503c\u80cc\u540e\u90fd\u6709\u4e00"
            "\u4efd\u534f\u8bae\u3001\u4e00\u6761\u9884\u6ce8\u518c\u7684\u6807\u51c6\u548c"
            "\u4e00\u4e2a\u7f6e\u4fe1\u533a\u95f4\uff0c\u800c\u5176\u4e2d\u56db\u4efd\u534f"
            "\u8bae\u6740\u6389\u4e86\u5b83\u4eec\u81ea\u5df1\u8981\u8bc1\u660e\u7684\u90a3"
            "\u4e2a\u529f\u80fd\u3002</p>"
            "<p>\u6700\u5927\u7684\u7f3a\u53e3\u5199\u5728\u5b9e\u6d4b\u9875\u4e0a\uff1a\u5230"
            "\u76ee\u524d\u4e3a\u6b62\u6240\u6709\u67e5\u8be2\u96c6\u90fd\u662f\u4f5c\u8005"
            "\u81ea\u5df1\u5199\u7684 \u2014\u2014 \u8fd9\u662f\u518d\u591a bootstrap \u4e5f"
            "\u4fee\u4e0d\u4e86\u7684\u90a3\u4e00\u4e2a\u504f\u5dee\u3002</p>",
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
    "end_h2": "\u56db\u6761\u547d\u4ee4\u5f00\u59cb\uff0c\u6216\u8005\u5148\u628a\u6570\u5b57\u770b\u5b8c\u3002",
    "end_p": (
        "\u6307\u5357\u8986\u76d6\u5b89\u88c5\u3001\u56db\u4e2a\u6d4f\u89c8\u5668\u7684\u5bfc"
        "\u51fa\u3001\u4e24\u79cd\u6a21\u578b\u63a5\u5165\u65b9\u5f0f\u3001\u6269\u5c55\u3001"
        "MCP \u548c karakeep \u63d2\u4ef6\u3002\u5b9e\u6d4b\u9875\u8986\u76d6\u9879\u76ee\u91cc"
        "\u6bcf\u4e00\u6761\u68c0\u7d22\u7ed3\u8bba\uff0c\u5305\u62ec\u8f93\u4e86\u7684\u90a3"
        "\u51e0\u6761\u3002"
    ),
    "end_cta": [
        ("\u770b\u4f7f\u7528\u6307\u5357", "guide.zh.html", True),
        ("\u770b\u5b9e\u6d4b\u8bb0\u5f55", "measured.zh.html", False),
    ],
}

# ---------------------------------------------------------------- 指南 ----

ZH["quickstart"] = {
    "h1": "\u5feb\u901f\u4e0a\u624b",
    "lede": (
        "\u4ece\u4ec0\u4e48\u90fd\u6ca1\u88c5\uff0c\u5230\u6d4f\u89c8\u5668\u91cc\u6253\u5f00\u4e00\u4e2a\u641c\u7d22\u9875\u3002\u4e94\u6b65\uff0c\u6bcf\u6761\u547d\u4ee4\u90fd\u80fd\u76f4\u63a5\u590d\u5236\uff0c"
        "\u8fd8\u914d\u4e86\u56fe\u544a\u8bc9\u4f60\u8dd1\u901a\u4e4b\u540e\u5e94\u8be5\u770b\u5230\u4ec0\u4e48\u3002\u4e0d\u9700\u8981\u4f60\u4e8b\u5148\u61c2 embedding\u3001\u5411\u91cf\u6216"
        "\u8005\u68c0\u7d22 \u2014\u2014 \u8fd9\u4e00\u9875\u91cc\u4e5f\u6ca1\u6709\u4e00\u5904\u9700\u8981\u3002"
    ),
    "toc_title": "\u4e94\u6b65",
    "sections": [
        # ------------------------------------------------------------ 安装
        (
            "install",
            "\u88c5\u4e0a\u5b83",
            [
                ("p",
                 "\u4f60\u9700\u8981 Python 3.10 \u6216\u66f4\u65b0\u7684\u7248\u672c\uff0cWindows\u3001macOS\u3001Linux \u90fd"
                 "\u884c\u3002\u7528 <code>python --version</code> \u770b\u4e00\u4e0b\uff1b\u5982\u679c\u6253\u51fa\u6765\u662f "
                 "3.9 \u6216\u8005\u76f4\u63a5\u62a5\u9519\uff0c\u5148\u53bb "
                 "<a href=\"https://www.python.org/downloads/\" "
                 "rel=\"noopener\">python.org</a> \u88c5 Python\u3002"),
                ("cb", "shell", "pip install facetmark"),
                ("p",
                 "\u5b89\u88c5\u5c31\u8fd9\u4e9b\u3002\u6ca1\u6709\u53e6\u5916\u8981\u8dd1\u7684\u670d\u52a1\u7aef\uff0c\u6ca1\u6709\u8981\u5efa\u7684\u6570\u636e\u5e93\uff0c\u4e5f\u6ca1\u6709"
                 "\u8981\u6ce8\u518c\u7684\u8d26\u53f7\u3002\u786e\u8ba4\u4e00\u4e0b\u88c5\u597d\u4e86\uff1a"),
                ("cb", "shell", "facetmark --version"),
                ("callout", "info", "\u5982\u679c\u7ec8\u7aef\u8bf4 command not found",
                 "<p>pip \u628a\u5b83\u88c5\u5230\u4e86\u4e0d\u5728 <code>PATH</code> \u4e0a\u7684\u5730\u65b9\u3002"
                 "<code>python -m facetmark --version</code> \u65e0\u8bba\u5982\u4f55\u90fd\u80fd\u8dd1\uff0c"
                 "\u672c\u9875\u6bcf\u4e00\u6761\u547d\u4ee4\u90fd\u53ef\u4ee5\u8fd9\u4e48\u5199\u3002</p>"),
            ],
        ),
        # ------------------------------------------------------------ 导入
        (
            "import",
            "\u628a\u4e66\u7b7e\u5bfc\u8fdb\u6765",
            [
                ("p",
                 "Chrome\u3001Edge\u3001Brave\u3001Vivaldi\u3001Chromium\u3001Opera \u90fd\u4e0d\u7528\u4f60\u5bfc\u51fa"
                 "\u4efb\u4f55\u4e1c\u897f\u3002\u5148\u5173\u6389\u6d4f\u89c8\u5668 \u2014\u2014 \u5b83\u5360\u7740\u90a3\u4e2a\u6587\u4ef6 \u2014\u2014 \u7136\u540e\uff1a"),
                ("cb", "shell", "facetmark import"),
                ("p",
                 "\u5b83\u4f1a\u81ea\u5df1\u627e\u5230\u6d4f\u89c8\u5668\u914d\u7f6e\u76ee\u5f55\uff0c\u8bfb\u4e66\u7b7e\u6587\u4ef6\uff0c\u7136\u540e\u6253\u5370\u8bfb\u8fdb\u6765\u591a\u5c11"
                 "\u6761\u3002Firefox \u548c Safari \u4e0d\u5c5e\u4e8e\u8fd9\u4e00\u5bb6\uff0c\u8fd9\u4e24\u4e2a\u8981\u5148\u4e00\u6b21\u6027\u5bfc\u51fa\u6210 "
                 "HTML\uff08<a href=\"guide.zh.html#import\">\u600e\u4e48\u5bfc</a>\uff09\uff0c\u518d\u628a\u8def"
                 "\u5f84\u7ed9\u5b83\uff1a"),
                ("cb", "shell", "facetmark import ~/Downloads/bookmarks.html"),
                ("callout", "info", "\u5b83\u4ece\u4e0d\u5f80\u4f60\u6d4f\u89c8\u5668\u91cc\u5199\u4e1c\u897f",
                 "<p>\u5bfc\u5165\u662f\u5355\u5411\u8bfb\uff1a\u6253\u5f00\u6587\u4ef6\u3001\u8bfb\u3001\u5173\u4e0a\u3002facetmark \u4e0d\u5199\u6d4f\u89c8\u5668\u7684"
                 "\u914d\u7f6e\u76ee\u5f55\uff0c\u4f60\u5728\u8fd9\u91cc\u505a\u7684\u4efb\u4f55\u4e8b\u90fd\u6539\u4e0d\u4e86\u3001\u4e5f\u5220\u4e0d\u6389\u4f60\u5df2\u6709\u7684\u4e66"
                 "\u7b7e\u3002</p>"),
            ],
        ),
        # ------------------------------------------------------------ 模型
        (
            "model",
            "\u7ed9\u5b83\u63a5\u4e00\u4e2a\u6a21\u578b \u2014\u2014 \u6216\u8005\u8df3\u8fc7\u8fd9\u6b65",
            [
                ("p",
                 "\u201c\u6309\u610f\u601d\u641c\u201d\u9700\u8981\u4e00\u4e2a\u80fd\u628a\u6587\u5b57\u53d8\u6210\u6570\u5b57\u7684\u4e1c\u897f\u3002\u62ff\u5230\u5b83\u6709\u4e09\u6761"
                 "\u8def\uff0c\u7b2c\u4e09\u6761\u662f\u5e72\u8106\u4e0d\u8981\u3002"),
                ("h3", "\u7528\u5728\u7ebf API"),
                ("p",
                 "\u4efb\u4f55 OpenAI \u517c\u5bb9\u7684\u63a5\u53e3\u90fd\u884c\u3002\u5199\u8fdb "
                 "<code>~/.facetmark/.env</code> \u2014\u2014 \u8fd9\u4e2a\u6587\u4ef6\u7b2c\u4e00\u6b21\u8fd0\u884c\u65f6\u4f1a"
                 "\u81ea\u52a8\u5efa\u597d\uff1a"),
                ("cb", "dotenv",
                 "FACETMARK_API_BASE=https://api.openai.com/v1\n"
                 "FACETMARK_API_KEY=sk-your-key"),
                ("callout", "warn", "\u6700\u5e38\u89c1\u7684\u4e00\u4e2a\u914d\u7f6e\u9519\u8bef",
                 "<p>base URL \u5fc5\u987b\u4ee5 <code>/v1</code> \u7ed3\u5c3e\u3002\u5c11\u4e86\u5b83\uff0c\u6bcf\u6b21\u6a21\u578b"
                 "\u8c03\u7528\u90fd\u8fd4\u56de 404\uff0c\u800c\u9519\u8bef\u662f\u4ee5\u201c\u4f9b\u5e94\u5546\u62a5\u9519\u201d\u7684\u5f62\u5f0f\u5192\u51fa\u6765\u7684\uff0c"
                 "\u770b\u7740\u5c31\u50cf key \u4e0d\u5bf9\u3002</p>"),
                ("h3", "\u7528\u4f60\u81ea\u5df1\u673a\u5668\u4e0a\u7684\u6a21\u578b"),
                ("p",
                 "\u4e0d\u7528 key\uff0c\u9664\u4e86\u6293\u53d6\u7f51\u9875\u672c\u8eab\uff0c\u6ca1\u6709\u4efb\u4f55\u4e1c\u897f\u79bb\u5f00\u8fd9\u53f0\u673a\u5668\uff1a"),
                ("cb", "dotenv", "FACETMARK_EMBED_BACKEND=local"),
                ("p",
                 "\u7b2c\u4e00\u6b21\u8dd1\u7684\u65f6\u5019\u4f1a\u4e0b\u8f7d\u4e00\u4e2a\u4e0d\u5927\u7684 sentence-transformers \u6a21"
                 "\u578b\u3002"),
                ("h3", "\u4e24\u4e2a\u90fd\u4e0d\u8981"),
                ("p",
                 "\u8fd9\u4e00\u6b65\u6574\u4e2a\u8df3\u8fc7\uff0c\u4f60\u4ecd\u7136\u6709\u5bf9\u6807\u9898\u3001\u6587\u4ef6\u5939\u548c\u7f51\u5740\u7684\u5173\u952e\u8bcd\u641c\u7d22\uff0c"
                 "\u5916\u52a0\u4f1a\u8bdd\u56fe \u2014\u2014 \u4e5f\u5c31\u662f\u4f60\u54ea\u4e9b\u4e66\u7b7e\u662f\u540c\u4e00\u6b21\u4e0a\u7f51\u65f6\u5b58\u7684\u3002\u5931\u53bb\u7684"
                 "\u662f\u6309\u610f\u601d\u641c\u3002\u4ee5\u540e\u968f\u65f6\u53ef\u4ee5\u8865\u4e0a\u6a21\u578b\u518d\u8dd1\u4e00\u904d\u4e0b\u4e00\u6b65\uff1b\u6ca1\u6709\u4ec0\u4e48\u8981"
                 "\u91cd\u6765\u3002"),
            ],
        ),
        # ---------------------------------------------------------- 建索引
        (
            "index",
            "\u5efa\u7d22\u5f15",
            [
                ("p",
                 "\u8fd9\u662f\u6162\u7684\u90a3\u4e00\u6b65\uff0c\u4e5f\u662f\u552f\u4e00\u6162\u7684\u4e00\u6b65\u3002\u5b83\u4f1a\u53bb\u6293\u6bcf\u4e2a\u9875\u9762\u3001\u62bd\u51fa\u6b63"
                 "\u6587\u3001\u5982\u679c\u4f60\u914d\u4e86\u5bf9\u8bdd\u6a21\u578b\u5c31\u987a\u624b\u505a\u4e2a\u6458\u8981\u3001\u505a\u5411\u91cf\uff0c\u518d\u7b97\u51fa\u54ea\u4e9b\u4e66"
                 "\u7b7e\u662f\u4e00\u8d77\u5b58\u7684\u3002"),
                ("cb", "shell", "facetmark index"),
                ("p",
                 "\u82b1\u7684\u65f6\u95f4\u4e3b\u8981\u5728<em>\u6293\u53d6</em>\u4e0a\uff0c\u4e0d\u5728\u6a21\u578b\u4e0a\uff1afacetmark \u9075\u5b88 "
                 "robots.txt\uff0c\u5e76\u4e14\u6309\u7ad9\u70b9\u7ed9\u81ea\u5df1\u9650\u901f\uff0c\u8fd9\u662f\u6545\u610f\u7684\u3002\u51e0\u5343\u6761\u4e66\u7b7e\u662f"
                 "\u4e00\u676f\u5496\u5561\u7684\u4e8b\uff0c\u4e0d\u662f\u4e00\u79d2\u949f\u7684\u4e8b\u3002\u8d76\u65f6\u95f4\uff0c\u6216\u8005\u53ea\u60f3\u5148\u770b\u5b83\u80fd\u4e0d\u80fd"
                 "\u8dd1\uff1a"),
                ("cb", "shell", "facetmark index --no-fetch"),
                ("p",
                 "\u8fd9\u6837\u53ea\u5bf9\u6807\u9898\u5efa\u7d22\u5f15\uff0c\u51e0\u79d2\u949f\u5c31\u5b8c\u3002\u4e4b\u540e\u518d\u6b63\u7ecf\u8dd1\u4e00\u6b21 "
                 "<code>facetmark index</code> \u2014\u2014 \u5b83\u662f\u5e42\u7b49\u7684\uff0c\u53ea\u4f1a\u6361\u8d77\u8fd8\u6ca1"
                 "\u505a\u7684\u90a3\u90e8\u5206\uff0c\u5df2\u7ecf\u505a\u8fc7\u7684\u5168\u90e8\u8df3\u8fc7\u3002"),
                ("callout", "info", "\u53ef\u4ee5\u4e2d\u9014\u505c\uff0c\u4e5f\u53ef\u4ee5\u63a5\u7740\u8dd1",
                 "<p>\u8fdb\u5ea6\u662f\u8fb9\u8dd1\u8fb9\u5199\u7684\u3002\u7528 <kbd>Ctrl</kbd>+<kbd>C</kbd> \u6253\u65ad\uff0c"
                 "\u6700\u591a\u4e22\u6389\u6b63\u5728\u6293\u7684\u90a3\u4e00\u4e2a\u9875\u9762\uff0c\u91cd\u65b0\u8dd1\u662f\u63a5\u7740\u505a\uff0c\u4e0d\u662f\u4ece\u5934"
                 "\u6765\u3002</p>"),
            ],
        ),
        # ------------------------------------------------------------ 打开
        (
            "open",
            "\u6253\u5f00\u9875\u9762",
            [
                ("cb", "shell", "facetmark serve"),
                ("p", "\u5b83\u4f1a\u628a\u5730\u5740\u6253\u51fa\u6765\u3002\u628a\u7b2c\u4e8c\u884c\u90a3\u4e2a\u5728\u6d4f\u89c8\u5668\u91cc\u6253\u5f00\uff1a"),
                ("cb", "shell",
                 "facetmark 1.6.1  http://127.0.0.1:8787\n"
                 "open the search page:     http://127.0.0.1:8787/app"),
                ("p",
                 "\u754c\u9762\u5c31\u8fd9\u4e9b\u3002\u7528\u4f60\u5e73\u65f6\u8bf4\u8bdd\u7684\u65b9\u5f0f\u6253\u4e00\u4e2a\u95ee\u9898\u8fdb\u53bb \u2014\u2014 \u4f60\u4e0d\u7528\u8bb0"
                 "\u5f97\u6807\u9898\uff0c\u4e5f\u4e0d\u7528\u628a\u8bcd\u513f\u8bf4\u51c6\u3002"),
                ("shot",
                 "assets/app-search-zh.png",
                 "facetmark \u641c\u7d22\u9875\uff0c\u8f93\u5165\u4e86\u4e00\u4e2a\u67e5\u8be2\uff0c\u4e0b\u9762\u662f\u6392\u597d\u5e8f\u7684\u7ed3\u679c",
                 "<b>\u4f60\u5e94\u8be5\u770b\u5230\u4ec0\u4e48\u3002</b>\u7ed3\u679c\u968f\u7740\u4f60\u6253\u5b57\u51fa\u73b0\uff0c\u5148\u662f\u4e00\u4e2a\u4e0d\u82b1\u4efb\u4f55"
                 "\u4ee3\u4ef7\u7684\u5b57\u9762\u5339\u914d\uff0c\u7b49\u6a21\u578b\u7b54\u5b8c\u518d\u91cd\u65b0\u6392\u4e00\u6b21\u3002\u8fd9\u5f20\u56fe\u4f1a\u8ddf\u7740\u4f60\u6b63\u5728"
                 "\u8bfb\u7684\u8fd9\u4e2a\u9875\u9762\u5207\u6362\u6df1\u6d45\u8272\u3002",
                 "assets/app-search-zh-dark.png",
                 "\u540c\u4e00\u4e2a\u641c\u7d22\u9875\u7684\u6df1\u8272\u6a21\u5f0f"),
                ("p",
                 "\u7b2c\u4e8c\u4e2a\u89c6\u56fe\u56de\u7b54\u7684\u662f\u6240\u6709\u4eba\u5230\u8fd9\u4e00\u6b65\u90fd\u4f1a\u6709\u7684\u90a3\u4e2a\u95ee\u9898 \u2014\u2014 "
                 "<em>\u521a\u624d\u90a3\u4e9b\u5230\u5e95\u6210\u6ca1\u6210\uff1f</em>\u70b9\u9876\u680f\u7684<b>\u4e66\u7b7e\u5e93</b>\u3002"),
                ("shot",
                 "assets/app-library-zh.png",
                 "facetmark \u4e66\u7b7e\u5e93\u89c6\u56fe\uff0c\u5217\u7740\u4e66\u7b7e\u3001\u5411\u91cf\u3001\u4f1a\u8bdd\u548c\u8fb9\u7684\u6570\u91cf",
                 "<b>\u4e66\u7b7e\u5e93\u3002</b>\u5982\u679c<em>\u5185\u5bb9\u5411\u91cf</em>\u662f 0\uff0c\u6309\u610f\u601d\u641c\u5c31\u8fd8\u6ca1\u5f00"
                 "\u8d77\u6765\uff1a\u8981\u4e48\u6ca1\u914d\u6a21\u578b\uff0c\u8981\u4e48 <code>facetmark index</code> \u8fd8\u6ca1"
                 "\u8dd1\u5b8c\u3002\u5982\u679c<em>\u4e66\u7b7e</em>\u662f 0\uff0c\u90a3\u662f\u5bfc\u5165\u6ca1\u6210\u3002",
                 "assets/app-library-zh-dark.png",
                 "\u540c\u4e00\u4e2a\u4e66\u7b7e\u5e93\u89c6\u56fe\u7684\u6df1\u8272\u6a21\u5f0f"),
                ("callout", "info", "\u8ba9\u5b83\u4e00\u76f4\u5f00\u7740",
                 "<p><code>facetmark serve</code> \u662f\u4e2a\u524d\u53f0\u8fdb\u7a0b\uff1b\u5b83\u5f00\u7740\u9875\u9762\u624d"
                 "\u80fd\u7528\u3002\u5b83\u76d1\u542c 127.0.0.1\uff0c\u4e5f\u5c31\u662f\u53ea\u6709\u4f60\u8fd9\u53f0\u673a\u5668\uff0c\u7f51\u7edc\u4e0a\u522b\u7684\u673a"
                 "\u5668\u78b0\u4e0d\u5230\u3002\u6d4f\u89c8\u5668\u6269\u5c55\u3001API \u548c MCP \u5ba2\u6237\u7aef\u8bf4\u8bdd\u7684\u90fd\u662f\u8fd9\u540c\u4e00\u4e2a\u8fdb"
                 "\u7a0b \u2014\u2014 \u89c1<a href=\"guide.zh.html#webui\">\u4f7f\u7528\u6307\u5357</a>\u3002</p>"),
            ],
        ),
        # ------------------------------------------------------------ 读结果
        (
            "read",
            "\u8bfb\u61c2\u4e00\u6761\u7ed3\u679c",
            [
                ("p",
                 "\u6bcf\u4e00\u884c\u90fd\u4f1a\u8bf4\u5b83\u4e3a\u4ec0\u4e48\u5728\u8fd9\u513f\u3002\u5728\u9875\u9762\u91cc\u628a\u9f20\u6807\u653e\u5230\u6807\u8bb0\u4e0a\u5c31\u6709\u89e3"
                 "\u91ca\uff1b\u8fd9\u91cc\u662f\u540c\u4e00\u4ef6\u4e8b\u7684\u4e00\u5f20\u8868\u3002"),
                ("table",
                 ["\u884c\u4e0a\u7684\u6807\u8bb0", "\u610f\u601d"],
                 [["<span class=\"chip mk\">\u5185\u5bb9\u76f8\u5173</span>",
                   "\u9875\u9762\u81ea\u5df1\u7684\u6b63\u6587\u547d\u4e2d\u4e86 \u2014\u2014 \u6309\u610f\u601d\uff0c\u4e0d\u662f\u6309\u5173\u952e\u8bcd\u3002\u60f3\u4e0d\u8d77\u6765"
                   "\u7528\u8bcd\u7684\u90a3\u79cd\u9875\u9762\uff0c\u5c31\u662f\u9760\u8fd9\u4e2a\u627e\u51fa\u6765\u7684\u3002"],
                  ["<span class=\"chip mk\">\u8bcd\u8bed</span>",
                   "\u6807\u9898\u3001\u6587\u4ef6\u5939\u6216\u7f51\u5740\u91cc\u6709\u4e00\u4e2a\u5b8c\u6574\u7684\u8bcd\u547d\u4e2d\u4e86\u3002"],
                  ["<span class=\"chip mk\">\u5b50\u4e32</span>",
                   "\u8bcd\u7684\u4e00\u90e8\u5206\u547d\u4e2d\u4e86 \u2014\u2014 \u4e2d\u6587\u67e5\u8be2\u548c\u53ea\u6253\u4e86\u4e00\u534a\u7684\u8bcd\u80fd\u7528\uff0c\u5c31"
                   "\u662f\u56e0\u4e3a\u5b83\u3002"],
                  ["<span class=\"chip mk\">\u63d0\u95ee\u65b9\u5f0f</span>",
                   "\u5f53\u521d\u4e3a\u8fd9\u4e2a\u9875\u9762\u7559\u4e0b\u7684\u67d0\u4e2a\u95ee\u9898\u547d\u4e2d\u4e86\u3002"],
                  ["<span class=\"badge warn mk\">\u5df2\u51b7\u5374</span>",
                   "\u5f88\u4e45\u4ee5\u524d\u5b58\u7684\uff0c\u4e00\u76f4\u6ca1\u6253\u5f00\u8fc7\uff0c\u800c\u4e14\u6709\u66f4\u65b0\u7684\u4e1c\u897f\u770b\u8d77\u6765\u628a\u5b83\u53d6"
                   "\u4ee3\u4e86\u3002\u5f80\u4e0b\u538b\uff0c\u7edd\u4e0d\u5220\u9664\u3002"]]),
                ("p",
                 "\u6392\u597d\u5e8f\u7684\u5217\u8868\u4e0b\u9762\uff0c\u6709\u65f6\u4f1a\u6709\u5355\u72ec\u7684\u7b2c\u4e8c\u7ec4\uff0c\u6807\u7740<b>\u5f53\u65f6\u524d\u540e\u4e00\u8d77"
                 "\u5b58\u7684</b>\u3002\u90a3\u4e9b\u4e0d\u662f\u4f60\u8fd9\u4e2a\u67e5\u8be2\u7684\u7b54\u6848 \u2014\u2014 \u5b83\u4eec\u662f\u4f60\u548c\u4e0a\u9762\u67d0\u6761"
                 "\u7ed3\u679c\u540c\u4e00\u6b21\u4e0a\u7f51\u65f6\u5b58\u4e0b\u7684\u9875\u9762\uff0c\u800c\u8fd9\u5f80\u5f80\u624d\u662f\u4f60\u771f\u6b63\u8bb0\u5f97\u67d0\u4e2a\u9875\u9762"
                 "\u5728\u54ea\u513f\u7684\u65b9\u5f0f\u3002\u5b83\u4eec\u88ab\u6545\u610f\u9694\u5f00\uff0c\u7edd\u4e0d\u6df7\u8fdb\u6392\u540d\u3002"),
                ("p",
                 "\u5e95\u90e8\u7684<b>\u52a0\u8f7d\u66f4\u591a</b>\u53d6\u7684\u662f\u540c\u4e00\u6b21\u6392\u540d\u7684\u4e0b\u4e00\u9875\uff0c\u800c\u4e0d\u662f\u91cd\u65b0\u641c"
                 "\u4e00\u904d\uff0c\u6240\u4ee5\u4f60\u5df2\u7ecf\u8bfb\u8fc7\u7684\u987a\u5e8f\u4e0d\u4f1a\u5728\u811a\u5e95\u4e0b\u91cd\u6392\u3002\u5217\u8868\u4e0a\u65b9\u7684\u8ba1\u6570"
                 "\u544a\u8bc9\u4f60\u73b0\u5728\u770b\u7684\u662f\u54ea\u4e00\u6bb5\u3002"),
            ],
        ),
        # ------------------------------------------------------------ 排错
        (
            "trouble",
            "\u4e0d\u5bf9\u52b2\u7684\u65f6\u5019",
            [
                ("h3", "\u9875\u9762\u95ee\u6211\u8981\u4ee4\u724c"),
                ("p",
                 "\u4f60\u4e0d\u662f\u901a\u8fc7 127.0.0.1 \u8bbf\u95ee\u5b83\u7684 \u2014\u2014 \u5c40\u57df\u7f51\u5730\u5740\u3001\u4e3b\u673a\u540d\u3001\u53cd\u5411"
                 "\u4ee3\u7406\uff0c\u5728\u90a3\u4e2a\u68c0\u67e5\u770b\u6765\u90fd\u662f\u4e00\u56de\u4e8b\u3002\u8dd1\u4e00\u4e0b "
                 "<code>facetmark token</code>\uff0c\u628a\u503c\u7c98\u8fdb\u90a3\u4e2a\u8f93\u5165\u6846\u4e00\u6b21\uff0c\u6d4f\u89c8"
                 "\u5668\u5c31\u8bb0\u4f4f\u4e86\u3002<a href=\"guide.zh.html#webui\">\u8fd9\u4e2a\u68c0\u67e5\u4e3a\u4ec0\u4e48\u5b58"
                 "\u5728\u3002</a>"),
                ("h3", "\u9875\u9762\u6839\u672c\u6253\u4e0d\u5f00"),
                ("p",
                 "<code>facetmark serve</code> \u5f97\u4e00\u76f4\u5728\u67d0\u4e2a\u7ec8\u7aef\u91cc\u8dd1\u7740\u3002\u5982\u679c\u5b83"
                 "\u5e26\u7740 <code>address already in use</code> \u9000\u51fa\u4e86\uff0c\u8bf4\u660e 8787 "
                 "\u88ab\u522b\u7684\u4e1c\u897f\u5360\u4e86\uff1a\u8dd1 <code>facetmark serve --port 8788</code>\uff0c"
                 "\u7136\u540e\u6253\u5f00\u90a3\u4e2a\u7aef\u53e3\u3002"),
                ("h3", "\u641c\u4e0d\u5230\u4e1c\u897f\uff0c\u6216\u8005\u53ea\u80fd\u641c\u5230\u4e00\u6a21\u4e00\u6837\u7684\u8bcd"),
                ("p",
                 "\u6253\u5f00<b>\u4e66\u7b7e\u5e93</b>\u3002<em>\u5185\u5bb9\u5411\u91cf</em>\u662f 0\uff0c\u8bf4\u660e\u6309\u610f\u601d\u641c\u6ca1\u5f00"
                 "\u8d77\u6765\uff1a\u6ca1\u914d\u6a21\u578b\uff0c\u6216\u8005 <code>facetmark index</code> \u6ca1\u8dd1\u5b8c\u3002"
                 "<em>\u6293\u53d6\u961f\u5217</em>\u4e0d\u7a7a\uff0c\u8bf4\u660e\u8fd8\u5728\u5904\u7406\u4f60\u7684\u4e66\u7b7e\u5e93\uff0c\u7ed3\u679c\u4f1a\u7ee7\u7eed\u53d8"
                 "\u597d\u3002"),
                ("h3", "\u6bcf\u6b21\u6a21\u578b\u8c03\u7528\u90fd\u8fd4\u56de 404"),
                ("p",
                 "base URL \u5c11\u4e86 <code>/v1</code>\u3002\u8fd9\u662f\u9065\u9065\u9886\u5148\u7684\u7b2c\u4e00\u5927\u6545\u969c"
                 "\u539f\u56e0\u3002"),
                ("h3", "\u6211\u7684\u6570\u636e\u5728\u54ea\u513f"),
                ("p",
                 "\u4e00\u4e2a\u76ee\u5f55\uff1amacOS \u548c Linux \u4e0a\u662f <code>~/.facetmark</code>\uff0c"
                 "Windows \u4e0a\u662f <code>%USERPROFILE%\\.facetmark</code>\u3002\u91cc\u9762\u662f"
                 "\u4e00\u4e2a SQLite \u6587\u4ef6\u52a0\u4e00\u4e2a\u914d\u5bf9\u4ee4\u724c\u3002\u642c\u8d70\u3001\u5907\u4efd\u3001\u62f7\u5230\u53e6\u4e00\u53f0\u673a"
                 "\u5668 \u2014\u2014 \u8fd9\u5c31\u662f\u5168\u90e8\u72b6\u6001\u3002<code>FACETMARK_DATA_DIR</code> \u53ef\u4ee5"
                 "\u628a\u5b83\u653e\u5230\u522b\u5904\u3002"),
                ("h3", "\u600e\u4e48\u628a\u5b83\u5168\u90e8\u5220\u6389"),
                ("p",
                 "\u5220\u6389\u90a3\u4e2a\u76ee\u5f55\u3002\u6ca1\u6709\u5378\u8f7d\u6b65\u9aa4\uff0c\u5916\u9762\u4e5f\u6ca1\u6709\u522b\u7684\u4e1c\u897f \u2014\u2014 \u6ca1\u6709\u6ce8"
                 "\u518c\u8868\u9879\uff0c\u6ca1\u6709\u6539\u8fc7\u6d4f\u89c8\u5668\uff0c\u54ea\u513f\u4e5f\u6ca1\u6709\u8d26\u53f7\u3002"
                 "<code>pip uninstall facetmark</code> \u5220\u6389\u7a0b\u5e8f\u672c\u8eab\u3002"),
                ("h3", "\u522b\u7684\u95ee\u9898"),
                ("p",
                 "<code>facetmark stats</code> \u4f1a\u6253\u5370\u7d22\u5f15\u91cc\u5230\u5e95\u6709\u4ec0\u4e48\uff0c\u5927\u90e8\u5206"
                 "\u56f0\u60d1\u770b\u4e00\u773c\u5c31\u6e05\u695a\u4e86\uff0c"
                 "<a href=\"guide.zh.html#trouble\">\u4f7f\u7528\u6307\u5357\u91cc\u6709\u66f4\u957f\u7684\u6392\u9519"
                 "\u6e05\u5355</a>\u3002\u518d\u4e0d\u884c\uff0c\u5c31\u53bb "
                 "<a href=\"https://github.com/88lin/facetmark/issues\" "
                 "rel=\"noopener\">\u63d0\u4e2a issue</a>\u3002"),
            ],
        ),
    ],
}


ZH["guide"] = {
    "h1": "\u4f7f\u7528\u6307\u5357",
    "lede": (
        "\u56db\u6761\u547d\u4ee4\u4ece\u5b89\u88c5\u5230\u7b2c\u4e00\u6b21\u641c\u7d22\uff0c"
        "\u7136\u540e\u662f\u5176\u4f59\u5168\u90e8\uff1a\u56db\u4e2a\u6d4f\u89c8\u5668\u7684"
        "\u5bfc\u5165\u3001\u4e24\u79cd\u63a5\u6a21\u578b\u7684\u65b9\u5f0f\u3001HTTP API\u3001"
        "\u6d4f\u89c8\u5668\u6269\u5c55\u3001MCP\u3001karakeep \u63d2\u4ef6\uff0c\u4ee5\u53ca"
        "\u5168\u90e8\u914d\u7f6e\u9879\u548c\u5168\u90e8\u547d\u4ee4\u3002"
    ),
    "toc_title": "\u672c\u9875\u76ee\u5f55",
    "sections": [
        (
            "install",
            "\u5b89\u88c5",
            [
                ("p",
                 "Python 3.10 \u4ee5\u4e0a\uff0cWindows / macOS / Linux \u90fd\u884c\u3002"
                 "\u57fa\u7840\u5b89\u88c5\u6ca1\u6709\u4efb\u4f55\u9700\u8981\u7f16\u8bd1\u7684"
                 "\u673a\u5668\u5b66\u4e60\u4f9d\u8d56\uff1b\u5411\u91cf\u68c0\u7d22\u6765\u81ea "
                 "<code>sqlite-vec</code>\uff0c\u5b83\u662f\u4e00\u4e2a SQLite \u6269\u5c55"
                 "\u3002"),
                ("cb", "shell",
                 "pip install facetmark\n"
                 "# \u6216\u8005\u7528 uv\uff1a\n"
                 "uv pip install facetmark\n\n"
                 "facetmark version"),
                ("h3", "\u5e26\u672c\u5730\u5d4c\u5165"),
                ("p",
                 "\u53ea\u6709\u4f60\u60f3\u5728\u81ea\u5df1\u673a\u5668\u4e0a\u7b97\u5d4c"
                 "\u5165\u3001\u800c\u4e0d\u8d70\u7aef\u70b9\u65f6\u624d\u9700\u8981\u3002"
                 "\u5b83\u4f1a\u62c9 PyTorch \u548c "
                 "<code>sentence-transformers</code>\uff0c\u51e0\u767e MB\u3002"),
                ("cb", "shell", 'pip install "facetmark[local]"'),
                ("h3", "\u4ece\u6e90\u7801\u88c5"),
                ("cb", "shell",
                 "git clone https://github.com/88lin/facetmark\n"
                 "cd facetmark\n"
                 "python -m venv .venv && . .venv/bin/activate\n"
                 'pip install -e ".[dev]"\n\n'
                 "pytest -q                 # 1,514 \u4e2a\u6d4b\u8bd5\n"
                 "ruff check src tests scripts"),
                ("callout", "warn", "\u4e0d\u8981\u683c\u5f0f\u5316\u4ee3\u7801\u5e93",
                 "<p>\u5b83\u662f\u624b\u5199\u6392\u7248\u7684\u3002CI \u8dd1\u7684\u662f "
                 "<code>ruff check</code>\uff0c\u4e0d\u662f "
                 "<code>ruff format</code>\uff1b\u8dd1\u540e\u8005\u4f1a\u751f\u6210\u4e00"
                 "\u4efd\u6ca1\u4eba\u60f3 review \u7684 diff\u3002</p>"),
                ("h3", "\u6570\u636e\u5b58\u5728\u54ea"),
                ("p",
                 "\u4e00\u4e2a\u76ee\u5f55\uff0c\u6309\u5e73\u53f0\u9009\uff0c\u91cc\u9762"
                 "\u4e00\u4e2a SQLite \u6587\u4ef6\u3002\u7528 "
                 "<code>FACETMARK_DATA_DIR</code> \u6362\u76ee\u5f55\uff0c\u6216\u8005\u7528 "
                 "<code>--db</code> \u7ed9\u5355\u6761\u547d\u4ee4\u6307\u4e00\u4e2a\u6587"
                 "\u4ef6\u3002"),
                ("table",
                 ["\u5e73\u53f0", "\u9ed8\u8ba4\u6570\u636e\u76ee\u5f55"],
                 [["Windows", "<code>%LOCALAPPDATA%\\facetmark\\</code>"],
                  ["Linux / macOS", "<code>~/.local/share/facetmark/</code>"],
                  ["\u8bbe\u4e86 <code>XDG_DATA_HOME</code> \u65f6",
                   "<code>$XDG_DATA_HOME/facetmark/</code>"]]),
                ("p",
                 "\u91cc\u9762\u662f <code>facetmark.db</code> \u548c "
                 "<code>pairing-token.txt</code>\u3002\u5168\u90e8\u5b89\u88c5\u8db3\u8ff9"
                 "\u5c31\u8fd9\u4e48\u591a\uff0c\u5220\u76ee\u5f55\u7b49\u4e8e\u5378\u6570"
                 "\u636e\u3002"),
                ("h3", "\u6ca1 key \u6ca1\u7f51\u4e5f\u80fd\u5148\u8bd5"),
                ("p",
                 "<code>facetmark demo</code> \u4f1a\u9020\u4e00\u4e2a\u5408\u6210\u5e93"
                 "\uff0c\u7528\u786e\u5b9a\u6027\u7684\u79bb\u7ebf provider \u5efa\u7d22"
                 "\u5f15\uff0c\u7136\u540e\u8dd1\u4e09\u6761\u641c\u7d22\u3002\u9996\u9875"
                 "\u90a3\u4e2a\u7ec8\u7aef\u5c31\u662f\u8fd9\u4e48\u5f55\u7684\u3002"),
                ("cb", "shell", "facetmark demo --size 60"),
            ],
        ),
        (
            "import",
            "\u628a\u4e66\u7b7e\u5bfc\u8fdb\u6765",
            [
                ("p",
                 "\u5bfc\u5165\u662f\u5355\u5411\u53ea\u8bfb\u7684\u3002facetmark \u8bfb"
                 "\u6d4f\u89c8\u5668\u914d\u7f6e\u6216\u8005\u5bfc\u51fa\u6587\u4ef6\uff0c"
                 "\u4e24\u8005\u90fd\u4e0d\u5199\u3002"),
                ("h3", "Chromium \u7cfb\uff1a\u4e0d\u7528\u5bfc\u51fa"),
                ("p",
                 "Chrome\u3001Edge\u3001Brave\u3001Vivaldi\u3001Chromium\u3001Opera \u548c "
                 "Opera GX \u90fd\u628a\u4e66\u7b7e\u653e\u5728\u4e00\u4e2a JSON \u6587\u4ef6"
                 "\u91cc\uff0cfacetmark \u80fd\u81ea\u5df1\u627e\u5230\u3002\u6d4f\u89c8"
                 "\u5668\u5f00\u7740\u4e5f\u80fd\u5b89\u5168\u8bfb\u3002"),
                ("cb", "shell",
                 "facetmark browsers        # \u5b83\u80fd\u770b\u5230\u54ea\u4e9b\n"
                 "facetmark import          # \u53ea\u6709\u4e00\u4e2a\u65f6\u76f4\u63a5"
                 "\u5bfc"),
                ("p",
                 "\u88c5\u4e86\u591a\u4e2a\u914d\u7f6e\u65f6\uff0c\u5b83\u4e0d\u731c "
                 "\u2014\u2014 \u5bfc\u9519\u4eba\u7684\u4e66\u7b7e\u6bd4\u591a\u6572\u4e00"
                 "\u6761\u547d\u4ee4\u7cdf\u7cd5\u5f97\u591a\u3002\u5b83\u4f1a\u628a\u5019"
                 "\u9009\u5217\u51fa\u6765\uff0c\u4f60\u81ea\u5df1\u6307\uff1a"),
                ("cb", "shell",
                 "facetmark import "
                 '"$HOME/.config/google-chrome/Default/Bookmarks"'),
                ("h3", "Firefox \u548c Safari\uff1a\u5148\u5bfc\u51fa HTML"),
                ("table",
                 ["\u6d4f\u89c8\u5668", "\u5bfc\u51fa\u5165\u53e3"],
                 [["Firefox",
                   "\u4e66\u7b7e \u2192 \u7ba1\u7406\u4e66\u7b7e \u2192 \u5bfc\u5165\u548c"
                   "\u5907\u4efd \u2192 <b>\u5c06\u4e66\u7b7e\u5bfc\u51fa\u4e3a "
                   "HTML</b>"],
                  ["Safari",
                   "\u6587\u4ef6 \u2192 \u5bfc\u51fa \u2192 <b>\u4e66\u7b7e</b>"],
                  ["Chrome / Edge\uff08\u624b\u52a8\u8def\u7ebf\uff09",
                   "<code>chrome://bookmarks</code> \u2192 \u22ee \u2192 "
                   "<b>\u5bfc\u51fa\u4e66\u7b7e</b>"],
                  ["\u5176\u4ed6",
                   "\u4efb\u4f55 Netscape \u683c\u5f0f\u7684 "
                   "<code>bookmarks.html</code> \u90fd\u884c\u3002\u8fd9\u662f 1994 \u5e74"
                   "\u7684\u683c\u5f0f\uff0c\u5230\u4eca\u5929\u6240\u6709\u4eba\u8fd8\u5728"
                   "\u5199\u5b83\u3002"]]),
                ("cb", "shell", "facetmark import ~/Downloads/bookmarks.html"),
                ("h3", "\u5bfc\u5165\u4f1a\u62a5\u4ec0\u4e48"),
                ("p",
                 "\u540c\u4e00\u6761\u547d\u4ee4\u540c\u65f6\u5904\u7406 Netscape HTML \u548c "
                 "Chrome JSON\uff0c\u5e76\u4e14\u62a5\u5b83\u5e72\u4e86\u4ec0\u4e48\uff0c"
                 "\u800c\u4e0d\u662f\u8f6c\u4e00\u4e2a\u5708\u3002\u5728\u4e00\u4efd\u771f"
                 "\u5b9e\u7684 1.7&nbsp;MB \u5bfc\u51fa\u4e0a\uff0896 \u4e2a\u6587\u4ef6\u5939"
                 "\u3001\u56db\u5c42\u5d4c\u5957\uff09\uff1a\u89e3\u6790 1,710 \u6761\uff0c"
                 "\u5199\u5165 1,701 \u6761\uff0c\u5408\u5e76 9 \u6761\u91cd\u590d\uff0c1 "
                 "\u6761\u4e0d\u53ef\u7d22\u5f15\u3002"),
                ("table",
                 ["\u5b57\u6bb5", "\u542b\u4e49"],
                 [["<code>parsed</code>", "\u6587\u4ef6\u91cc\u627e\u5230\u7684\u6761\u76ee"
                   "\u6570\u3002"],
                  ["<code>inserted</code> / <code>updated</code>",
                   "\u65b0\u5199\u5165\u7684\uff0c\u4ee5\u53ca\u6807\u9898\u6216\u6587\u4ef6"
                   "\u5939\u53d8\u4e86\u7684\u3002"],
                  ["<code>merged_duplicates</code>",
                   "\u540c\u4e00\u4e2a URL \u5b58\u4e86\u4e24\u6b21\uff0c\u53d6\u65f6\u95f4"
                   "\u65e9\u7684\u90a3\u4e2a\u3002"],
                  ["<code>non_indexable</code>",
                   "<code>javascript:</code>\u3001<code>place:</code>\u3001"
                   "<code>file:</code> \u4e4b\u7c7b\u3002"],
                  ["<code>missing_dates</code>",
                   "\u6ca1\u6709\u4fdd\u5b58\u65f6\u95f4\u7684\u3002\u7167\u6837\u5bfc"
                   "\u5165\uff0c\u4f46\u8fdb\u4e0d\u4e86\u4fdd\u5b58\u4f1a\u8bdd\u3002"],
                  ["<code>privacy_skipped</code>",
                   "\u88ab "
                   "<code>FACETMARK_PRIVACY_EXCLUDED_DOMAINS</code> \u6321\u4e0b\u7684"
                   "\u3002"],
                  ["<code>timestamp_unit</code>",
                   "\u6e90\u6587\u4ef6\u7528\u7684\u662f\u54ea\u79cd\u65f6\u95f4\u6233\u3002"
                   "Chrome \u548c Netscape \u4e0d\u4e00\u6837\uff0c\u8fd9\u91cc\u544a\u8bc9"
                   "\u4f60\u8bc6\u522b\u51fa\u7684\u662f\u54ea\u79cd\u3002"]]),
                ("callout", "info", "\u5148\u6392\u9664\u57df\u540d\uff0c\u518d\u5bfc\u5165",
                 "<p>\u628a "
                 "<code>FACETMARK_PRIVACY_EXCLUDED_DOMAINS</code> \u8bbe\u6210\u9017\u53f7"
                 "\u5206\u9694\u7684\u5217\u8868\uff0c\u8fd9\u4e9b\u4e3b\u673a\u5c31\u4e0d"
                 "\u4f1a\u88ab\u5199\u5165\u3001\u4e0d\u4f1a\u88ab\u6293\u3001\u4e5f\u4e0d"
                 "\u4f1a\u88ab\u5d4c\u5165\u3002\u6bd4\u4e8b\u540e\u5220\u884c\u7701\u4e8b"
                 "\u3002</p>"),
            ],
        ),
        (
            "models",
            "\u6a21\u578b\u63a5\u5165",
            [
                ("p",
                 "facetmark \u53ea\u901a\u8fc7<b>\u4e00\u4e2a</b> OpenAI \u517c\u5bb9\u7aef"
                 "\u70b9\u8bbf\u95ee\u6a21\u578b\u3002\u4ee3\u7801\u91cc\u6545\u610f\u6ca1"
                 "\u6709\u4efb\u4f55\u9488\u5bf9\u5177\u4f53\u5382\u5546\u7684\u5206\u652f"
                 "\uff1a\u4e00\u4e2a <code>base_url</code> \u52a0\u4e00\u4e2a "
                 "<code>api_key</code> \u5c31\u8986\u76d6 OpenAI\u3001DeepSeek\u3001Kimi"
                 "\u3001\u667a\u8c31\u3001\u7845\u57fa\u6d41\u52a8\u3001\u963f\u91cc\u767e"
                 "\u70bc\u3001together.ai\u3001Azure OpenAI\u3001Ollama\u3001vLLM\u3001LM "
                 "Studio\uff0c\u4ee5\u53ca\u4efb\u4f55\u8bf4\u540c\u4e00\u5957\u534f\u8bae"
                 "\u7684\u5185\u90e8\u7f51\u5173\u3002"),
                ("p",
                 "\u7528\u5230\u4e24\u4e2a\u89d2\u8272\u3002<b>chat \u6a21\u578b</b>\u5199"
                 "\u5bcc\u5316\uff08\u6458\u8981\u3001\u4e3b\u9898\u3001\u5b9e\u4f53\u3001"
                 "\u8981\u70b9\uff09\u548c\u5019\u9009\u610f\u56fe\u67e5\u8be2\u3002"
                 "<b>\u5d4c\u5165\u6a21\u578b</b>\u628a\u9875\u9762\u6b63\u6587\u53d8\u6210"
                 "\u5411\u91cf\u3002"),
                ("h3", "\u8d70\u7aef\u70b9"),
                ("cb", "shell",
                 "export FACETMARK_API_KEY=sk-...\n"
                 "export FACETMARK_BASE_URL=https://api.openai.com/v1\n"
                 "export FACETMARK_CHAT_MODEL=gpt-4o-mini\n"
                 "export FACETMARK_EMBED_MODEL=text-embedding-3-small\n"
                 "export FACETMARK_EMBED_DIM=1536"),
                ("callout", "warn",
                 "base URL \u5fc5\u987b\u4ee5 /v1 \u7ed3\u5c3e",
                 "<p>\u8fd9\u662f\u6700\u5e38\u89c1\u7684\u914d\u7f6e\u5931\u8d25\uff0c\u6ca1"
                 "\u4e4b\u4e00\u3002\u5c11\u4e86 <code>/v1</code>\uff0c\u6bcf\u4e00\u6b21"
                 "\u8c03\u7528\u90fd 404\uff0c\u5305\u62ec\u7b2c\u4e00\u6b21\uff1b\u800c"
                 "\u9519\u8bef\u662f\u4ece provider \u90a3\u8fb9\u56de\u6765\u7684\uff0c"
                 "\u770b\u8d77\u6765\u50cf\u662f\u5bc6\u94a5\u95ee\u9898\u3002</p>"),
                ("p",
                 "\u4e0d\u60f3\u8bbe\u73af\u5883\u53d8\u91cf\uff0c\u53ef\u4ee5\u5728\u8fd0"
                 "\u884c\u76ee\u5f55\u653e\u4e00\u4e2a <code>.env</code>\u3002\u540d\u5b57"
                 "\u4e00\u6837\uff0c\u524d\u7f00\u4e00\u6837\u3002"),
                ("cb", "dotenv",
                 "FACETMARK_API_KEY=sk-...\n"
                 "FACETMARK_BASE_URL=https://api.deepseek.com/v1\n"
                 "FACETMARK_CHAT_MODEL=deepseek-chat"),
                ("h3", "\u5171\u4eab\u7aef\u70b9\u6216\u514d\u8d39\u7aef\u70b9"),
                ("p",
                 "\u5982\u679c\u7aef\u70b9\u4e0a\u4e00\u4e2a\u5217\u51fa\u6765\u7684\u6a21"
                 "\u578b\u53ef\u80fd\u6839\u672c\u4e0d\u5728\u3001\u53ef\u80fd\u6b20\u8d39"
                 "\u3001\u4e5f\u53ef\u80fd\u4e0d\u652f\u6301 "
                 "<code>response_format</code>\uff0c\u90a3\u5c31\u914d\u4e00\u6761\u964d"
                 "\u7ea7\u94fe\u3002\u9ed8\u8ba4\u4e3a\u7a7a\u662f\u6545\u610f\u7684\uff1a"
                 "\u4ed8\u8d39\u7aef\u70b9\u62a5\u9519\u662f\u5728\u544a\u8bc9\u4f60\u4e8b"
                 "\u60c5\uff0c\u5420\u6389\u5b83\u6bd4\u5931\u8d25\u66f4\u7cdf\u3002"),
                ("cb", "shell",
                 "export FACETMARK_CHAT_MODEL_FALLBACKS="
                 "deepseek-chat,qwen-plus"),
                ("p",
                 "provider \u4f1a\u8bb0\u5f55\u6bcf\u4e00\u6b21\u8c03\u7528\u5230\u5e95\u662f"
                 "\u54ea\u4e2a\u6a21\u578b\u7b54\u7684\u3002\u4efb\u4f55\u5efa\u7acb\u5728"
                 "\u964d\u7ea7\u94fe\u4e0a\u7684\u62a5\u544a\uff0c\u90fd\u5fc5\u987b\u628a"
                 "\u8fd9\u4e2a\u6df7\u5408\u6bd4\u4f8b\u516c\u5f00\u3002"),
                ("h3", "\u672c\u5730\u5d4c\u5165\uff0c\u4e0d\u8981 key"),
                ("p",
                 "\u7528 <code>sentence-transformers</code> \u5728\u4f60\u81ea\u5df1\u673a"
                 "\u5668\u4e0a\u8dd1\u5d4c\u5165\u6a21\u578b\u3002\u518d\u628a API key "
                 "\u7559\u7a7a\uff0c\u9664\u4e86\u6293\u9875\u9762\u4e4b\u5916\u5c31\u4ec0"
                 "\u4e48\u90fd\u4e0d\u51fa\u53bb\u4e86\u3002"),
                ("cb", "shell",
                 'pip install "facetmark[local]"\n\n'
                 "export FACETMARK_EMBED_BACKEND=local\n"
                 "export FACETMARK_EMBED_MODEL=bge-m3\n"
                 "export FACETMARK_EMBED_DIM=1024\n"
                 "export FACETMARK_LOCAL_EMBED_PATH=/path/to/bge-m3   "
                 "# \u4e0d\u8bbe\u5c31\u4e0b\u8f7d\n"
                 "export FACETMARK_LOCAL_EMBED_MAX_SEQ=1024"),
                ("callout", "info",
                 "\u4e3a\u4ec0\u4e48\u5e8f\u5217\u957f\u5ea6\u9ed8\u8ba4\u662f 1024",
                 "<p>\u540c\u4e00\u7bc7\u6587\u6863\u5d4c\u5165\u4e24\u6b21\uff0c\u5fc5\u987b"
                 "\u843d\u5728\u540c\u4e00\u4e2a\u5730\u65b9\u3002bge-m3 \u5728 1024 token "
                 "\u4e0b\uff0c\u4e00\u4e2a\u56fa\u5b9a\u7684 64 \u7bc7\u63a2\u9488\u96c6"
                 "\u4e0a\u6700\u5c0f\u81ea\u4f59\u5f26\u662f <b>0.999976</b>\uff0c64/64 "
                 "\u5168\u90e8\u81ea\u5339\u914d\u3002\u964d\u5230 512 token\uff0c\u6700"
                 "\u5c0f\u503c\u6389\u5230 <b>0.9769</b> \u2014\u2014 \u56e0\u4e3a\u622a"
                 "\u65ad\u5f00\u59cb\u4ece\u540c\u4e00\u6bb5\u6587\u672c\u4e0a\u526a\u6389"
                 "\u4e0d\u540c\u7684\u91cf\u3002\u6240\u4ee5\u9ed8\u8ba4\u662f 1024\uff0c"
                 "\u800c\u4e14\u8c03\u4f4e\u5b83\u662f\u4e00\u7b14\u771f\u7684\u4ea4\u6613"
                 "\u3002</p>"),
                ("callout", "bad",
                 "\u6539\u7ef4\u5ea6\u7b49\u4e8e\u4f5c\u5e9f\u6240\u6709\u5411\u91cf",
                 "<p><code>FACETMARK_EMBED_DIM</code> \u5728\u7b2c\u4e00\u6b21\u5efa\u7d22"
                 "\u5f15\u65f6\u5199\u8fdb <code>meta</code> \u8868\u3002\u4e4b\u540e\u5bf9"
                 "\u4e0d\u4e0a\u5c31\u62a5\u9519\uff0c\u800c\u4e0d\u662f\u9ed8\u9ed8\u628a"
                 "\u4e0d\u517c\u5bb9\u7684\u5411\u91cf\u6df7\u5728\u4e00\u8d77\u3002\u6362"
                 "\u5d4c\u5165\u6a21\u578b\u6216\u6362\u7ef4\u5ea6\uff0c\u8bf7\u7528 "
                 "<code>facetmark index --force</code> \u91cd\u7b97\u3002</p>"),
                ("h3", "\u4e00\u4e2a\u6a21\u578b\u90fd\u4e0d\u63a5"),
                ("p",
                 "\u7167\u88c5\u7167\u8dd1\u3002\u4f60\u4fdd\u7559\u4e24\u4e2a\u8bcd\u9762"
                 "\u3001\u4fdd\u5b58\u4f1a\u8bdd\u3001\u57df\u540d\u4e0e\u94fe\u63a5\u56fe"
                 "\u3001\u94fe\u63a5\u5065\u5eb7\u3002\u4f60\u5931\u53bb\u5185\u5bb9\u9762"
                 "\u548c\u610f\u56fe\u9762\u3002<code>facetmark search --quick</code> "
                 "\u662f\u660e\u786e\u7684\u7eaf\u8bcd\u9762\u8def\u5f84\uff0c\u4e00\u6b21"
                 "\u6a21\u578b\u8c03\u7528\u90fd\u4e0d\u53d1\u3002"),
            ],
        ),
        (
            "index",
            "\u5efa\u7d22\u5f15",
            [
                ("cb", "shell", "facetmark index"),
                ("p",
                 "\u4e00\u6761\u547d\u4ee4\u6309\u987a\u5e8f\u8dd1\u5b8c\u6240\u6709\u9636"
                 "\u6bb5\u3002\u6bcf\u4e2a\u9636\u6bb5\u90fd\u5e42\u7b49\u4e14\u5e26\u6307"
                 "\u7eb9\uff0c\u6240\u4ee5\u65b0\u589e 50 \u6761\u4e66\u7b7e\u540e\u518d"
                 "\u8dd1\uff0c\u5b83\u53ea\u505a\u8fd9 50 \u6761\u7684\u6d3b\uff0c\u4e0d"
                 "\u662f\u6574\u4e2a\u5e93\u3002"),
                ("table",
                 ["\u9636\u6bb5", "\u5e72\u4ec0\u4e48", "\u8981\u6a21\u578b\u5417\uff1f"],
                 [["<code>fetch</code>",
                   "\u6293\u9875\u9762\uff0c\u9075\u5b88 robots.txt \u548c\u5355\u57df"
                   "\u540d\u9650\u901f\uff0c\u62bd\u53d6\u53ef\u8bfb\u6b63\u6587\u3002",
                   "\u4e0d\u8981"],
                  ["<code>enrich</code>",
                   "\u6458\u8981\u3001\u4e3b\u9898\u3001\u5b9e\u4f53\u3001\u8981\u70b9 \u2014\u2014 \u6bcf\u9875\u4e00\u6b21\u5c0f\u7684 chat \u8c03\u7528"
                   "\u3002", "chat"],
                  ["<code>embed_content</code>",
                   "\u628a\u91cd\u5efa\u540e\u7684\u6587\u672c\u5d4c\u5165\u3002",
                   "\u5d4c\u5165"],
                  ["<code>intents</code>",
                   "\u4e3a\u6bcf\u9875\u751f\u6210\u5019\u9009\u67e5\u8be2\u3002", "chat"],
                  ["<code>filter_intents</code>",
                   "\u53ea\u7559\u4e0b\u80fd\u628a\u8fd9\u9875\u641c\u56de\u6765\u7684\u90a3"
                   "\u4e9b\u3002\u5178\u578b\u60c5\u51b5\u4e0b\u4e0d\u5230\u4e00\u534a\u80fd"
                   "\u6d3b\u3002", "\u4e0d\u8981"],
                  ["<code>embed_intents</code>",
                   "\u628a\u5b58\u6d3b\u4e0b\u6765\u7684\u610f\u56fe\u5d4c\u5165\u3002",
                   "\u5d4c\u5165"],
                  ["<code>sessions</code>",
                   "\u6309\u65f6\u95f4\u95f4\u9694\u628a\u4fdd\u5b58\u884c\u4e3a\u805a\u6210"
                   "\u4e00\u6b21\u6b21\u4f1a\u8bdd\uff0c\u95f4\u9694\u9009\u54ea\u4e2a\u7531"
                   "\u300c\u8986\u76d6\u7387 \u00d7 \u76f8\u5bf9\u6253\u4e71\u5bf9\u7167"
                   "\u7684\u7eaf\u5ea6\u63d0\u5347\u300d\u51b3\u5b9a\u3002", "\u4e0d\u8981"],
                  ["<code>edges</code>",
                   "\u5efa\u4f1a\u8bdd\u8fb9\u3001\u8bed\u4e49\u8fb9\u3001\u540c\u57df\u540d"
                   "\u8fb9\u548c\u66ff\u4ee3\u8fb9\u3002", "\u4e0d\u8981"]]),
                ("h3", "\u5e38\u7528\u53c2\u6570"),
                ("table",
                 ["\u53c2\u6570", "\u4f5c\u7528"],
                 [["<code>--no-fetch</code>",
                   "\u5b8c\u5168\u4e0d\u6293\u7f51\uff0c\u53ea\u7d22\u5f15\u6807\u9898"
                   "\u3002\u51e0\u79d2\u949f\u800c\u4e0d\u662f\u51e0\u5c0f\u65f6\uff0c"
                   "\u6548\u679c\u4e5f\u5f31\u5f88\u591a\u3002"],
                  ["<code>--limit N</code>",
                   "\u6bcf\u9636\u6bb5\u53ea\u5904\u7406 N \u6761\u3002\u9002\u5408\u5148"
                   "\u770b\u4e00\u773c\u8fd9\u4e00\u8dd1\u5230\u5e95\u8981\u591a\u5c11"
                   "\u94b1\u3002"],
                  ["<code>--force</code>",
                   "\u4e0d\u770b\u6307\u7eb9\uff0c\u5df2\u7ecf\u505a\u8fc7\u7684\u4e5f\u91cd"
                   "\u505a\u3002"],
                  ["<code>--mock</code>",
                   "\u786e\u5b9a\u6027\u79bb\u7ebf provider\u3002\u4e0d\u8981 key\u3001"
                   "\u4e0d\u8054\u7f51\u3001\u4e5f\u6ca1\u8d28\u91cf\u3002"],
                  ["<code>--json</code>",
                   "\u6bcf\u4e2a\u9636\u6bb5\u7684\u673a\u5668\u53ef\u8bfb\u62a5\u544a\uff0c"
                   "\u542b\u5404\u9636\u6bb5\u8017\u65f6\u3002"]]),
                ("h3", "\u6307\u7eb9\u662f\u600e\u4e48\u7b97\u7684"),
                ("ul",
                 ["<b>\u5bcc\u5316</b>\u6309\u6b63\u6587\u54c8\u5e0c\u3002\u6b63\u6587\u6ca1"
                  "\u53d8\uff0c\u5c31\u4e0d\u53d1\u7b2c\u4e8c\u6b21 chat \u8bf7\u6c42\u3002",
                  "<b>\u5d4c\u5165</b>\u6309<em>\u91cd\u5efa\u540e\u7684\u5d4c\u5165\u6587"
                  "\u672c</em>\uff0c\u800c\u4e0d\u662f\u6309\u6b63\u6587\u3002\u6240\u4ee5"
                  "\u5bcc\u5316\u53d8\u4e86\u3001\u5d4c\u5165\u6587\u672c\u8ddf\u7740\u53d8"
                  "\u4e86\uff0c\u90a3\u4e2a\u9648\u65e7\u5411\u91cf\u4f1a\u88ab\u53d1\u73b0 \u2014\u2014 karakeep \u5f80\u8fd4\u7684\u635f\u4f24\u5c31\u662f\u8fd9"
                  "\u4e48\u63d2\u51fa\u6765\u7684\u3002",
                  "<b>\u4f1a\u8bdd\u548c\u8fb9</b>\u6bcf\u6b21\u91cd\u5efa\uff1b\u5b83\u4eec"
                  "\u4fbf\u5b9c\uff0c\u800c\u4e14\u4f9d\u8d56\u6574\u4e2a\u5e93\u3002"]),
                ("p",
                 "<code>facetmark reindex</code> \u628a\u6240\u6709\u884d\u751f\u4ea7\u7269"
                 "\u4e22\u6389\uff0c\u4ece\u4e66\u7b7e\u672c\u8eab\u91cd\u5efa\u3002"
                 "<code>facetmark migrate</code> \u628a\u65e7\u5e93\u5347\u5230\u5f53\u524d schema\uff0c\u9ed8\u8ba4\u5148\u5feb\u7167\u4e00\u4efd\uff0c\u9664\u975e"
                 "\u4f60\u52a0 <code>--no-backup</code>\u3002"),
                ("h3", "\u8fd9\u4e00\u8dd1\u7684\u4ee3\u4ef7"),
                ("p",
                 "\u94b1\u4e3b\u8981\u5728\u5bcc\u5316\uff1a\u5927\u81f4\u6bcf\u9875\u4e00"
                 "\u6b21\u5c0f\u7684 chat \u8c03\u7528\uff0c\u6240\u4ee5 1,700 \u9875\u7684"
                 "\u5e93\u7528\u4fbf\u5b9c\u6a21\u578b\u662f\u51e0\u6bdb\u94b1\u3002\u58c1"
                 "\u949f\u65f6\u95f4\u4e3b\u8981\u5728\u6293\u9875\u9762\uff0c\u800c\u6293"
                 "\u9875\u9762\u662f\u6545\u610f\u6162\u7684 \u2014\u2014 "
                 "<code>FETCH_PER_HOST_CONCURRENCY</code> \u662f 2\uff0c\u540c\u4e00\u4e3b"
                 "\u673a\u4e24\u6b21\u8bf7\u6c42\u4e4b\u95f4\u8fd8\u6709\u6700\u5c0f\u95f4"
                 "\u9694\u3002"),
                ("p",
                 "\u7ed9\u4e2a\u91cf\u7ea7\u611f\uff1a\u521a\u624d\u90a3\u4e2a\u771f\u5b9e"
                 "\u7684 1,700 \u6761\u4e66\u7b7e\u5e93\uff0c\u7528 "
                 "<code>--no-fetch</code> \u5efa\u7d22\u5f15\uff0c\u5f97\u5230 322 \u4e2a"
                 "\u4fdd\u5b58\u4f1a\u8bdd\u30019,132 \u6761\u8fb9\u30011,386 \u4e2a\u57df"
                 "\u540d\u30011,775 \u4e2a\u5411\u91cf\u3002"),
            ],
        ),
        (
            "search",
            "\u641c\u7d22",
            [
                ("cb", "shell",
                 'facetmark search "\u90a3\u7bc7\u8bb2\u628a\u5411\u91cf\u5b58\u5728 sqlite '
                 '\u91cc\u7684"\n'
                 'facetmark search "sqlite-vec" -n 20 --explain\n'
                 'facetmark search "error EADDRINUSE" --quick'),
                ("table",
                 ["\u53c2\u6570", "\u4f5c\u7528"],
                 [["<code>-n, --limit</code>",
                   "\u8fd4\u56de\u591a\u5c11\u6761\u3002\u9ed8\u8ba4 10\u3002"],
                  ["<code>--quick</code>",
                   "\u53ea\u8d70\u8bcd\u9762\u3002\u4e0d\u8c03\u6a21\u578b\u3001\u4e0d"
                   "\u8054\u7f51\u3001\u4e9a\u6beb\u79d2\u7ea7\u3002"],
                  ["<code>--explain</code>",
                   "\u6253\u5370\u6bcf\u6761\u547d\u4e2d\u7684\u662f\u54ea\u4e2a\u9762\u3002"
                   "\u641e\u6e05\u695a\u300c\u5b83\u4e3a\u4ec0\u4e48\u6392\u5728\u8fd9"
                   "\u300d\u6700\u5feb\u7684\u529e\u6cd5\u3002"],
                  ["<code>--config NAME</code>",
                   "\u8dd1\u6307\u5b9a\u7684 profile \u6216\u6d88\u878d\u6863\u3002\u9ed8"
                   "\u8ba4 <code>full</code>\u3002"],
                  ["<code>--json</code>",
                   "\u673a\u5668\u53ef\u8bfb\uff0c\u5305\u542b\u6bcf\u4e2a\u9636\u6bb5"
                   "\u7684\u8017\u65f6\u3002"]]),
                ("h3", "profile \u548c\u6d88\u878d\u6863"),
                ("p",
                 "<code>--config</code> \u63a5\u53d7\u4efb\u4f55\u9884\u6ce8\u518c\u6863"
                 "\u3001\u4efb\u4f55\u51fa\u5382 profile\uff0c\u4ee5\u53ca\u5927\u7ea6 20 "
                 "\u4e2a\u63a2\u7d22\u6027\u6d88\u878d\u6863\u3002\u6863\u4f4d\u7684\u5b9a"
                 "\u4e49\u5728 <code>search/pipeline.py</code> \u91cc\u3002"),
                ("table",
                 ["\u540d\u5b57", "\u9762\u4e0e\u9636\u6bb5", "\u72b6\u6001"],
                 [["<code>A</code>", "\u53ea\u7528\u5185\u5bb9\u5411\u91cf",
                   "<span class=\"badge pass\">W1 \u8d62\u5bb6 \u00b7 0.643</span>"],
                  ["<code>B</code>", "\u5185\u5bb9 + \u4e24\u4e2a\u8bcd\u9762",
                   "<span class=\"badge fail\">\u22125.4pp</span>"],
                  ["<code>C</code>", "\u56db\u4e2a\u9762\u5168\u4e0a", "\u5df2\u5b9e\u6d4b"],
                  ["<code>D</code>", "\u56db\u9762 + \u4e0a\u4e0b\u6587 + \u56fe",
                   "\u5df2\u5b9e\u6d4b"],
                  ["<code>E</code>", "\u56db\u9762 + \u4e0a\u4e0b\u6587 + \u56fe + \u91cd"
                   "\u6392", "\u5df2\u5b9e\u6d4b"],
                  ["<code>full</code>", "\u5185\u5bb9 + \u56fe + \u8870\u51cf",
                   "<span class=\"badge info\">\u771f\u5b9e provider \u4e0b\u7684\u9ed8"
                   "\u8ba4</span>"],
                  ["<code>fused</code>",
                   "\u56db\u9762 + \u4e0a\u4e0b\u6587 + \u56fe + \u91cd\u6392 + \u8870"
                   "\u51cf",
                   "<span class=\"badge info\">mock provider \u4e0b\u7684\u9ed8\u8ba4</span>"]]),
                ("callout", "info",
                 "\u4e3a\u4ec0\u4e48 mock \u4e0b\u9ed8\u8ba4\u4e0d\u4e00\u6837",
                 "<p>mock \u662f\u628a\u6587\u672c\u54c8\u5e0c\u6210\u5411\u91cf\u7684\uff0c"
                 "\u6240\u4ee5\u5185\u5bb9\u9762 \u2014\u2014 \u5728\u771f\u5b9e\u5e93\u4e0a"
                 "\u5b8c\u80dc\u7684\u90a3\u4e2a \u2014\u2014 \u6070\u597d\u5c31\u662f\u5728 "
                 "mock \u4e0b\u8fd4\u56de\u566a\u58f0\u7684\u90a3\u4e2a\u3002\u5728\u90a3"
                 "\u79cd\u90e8\u7f72\u4e0b\u518d\u628a\u8bcd\u9762\u53bb\u6389\uff0c\u5c31"
                 "\u4ec0\u4e48\u80fd\u7528\u7684\u90fd\u4e0d\u5269\u4e86\u3002\u6709\u771f"
                 "\u5b9e\u5d4c\u5165\u7684\u62ff\u5b9e\u6d4b\u7ed3\u8bba\uff1b\u5176\u4ed6"
                 "\u4eba\u62ff\u95e8\u63a7\u4e4b\u524d\u7684\u884c\u4e3a\uff0c\u81f3\u5c11"
                 "\u80fd\u6309\u8bcd\u641c\u3002</p>"),
                ("h3", "\u6392\u540d\u662f\u600e\u4e48\u6784\u6210\u7684"),
                ("p",
                 "\u9009\u4e2d\u7684\u6bcf\u4e2a\u9762\u5404\u8fd4\u56de\u6700\u591a "
                 "<code>CANDIDATES_PER_FACET</code> \u6761\u5019\u9009\u3002RRF \u6309 "
                 "<code>sum_f w_f / (k + rank_f)</code> \u5408\u5e76\uff0c"
                 "<code>k = 60</code>\u3002\u7136\u540e\u6309\u987a\u5e8f\u8dd1\u4e0a\u4e0b"
                 "\u6587\u3001\u8870\u51cf\u3001\u91cd\u6392\uff1b\u4e00\u8df3\u56fe\u6269"
                 "\u5c55\u4f5c\u4e3a<em>\u5355\u72ec\u4e00\u7ec4</em>\u8fd4\u56de \u2014"
                 "\u2014 \u4e0d\u6df7\u8fdb\u6392\u540d\uff0c\u56e0\u4e3a\u5f53\u521d\u6d4b"
                 "\u7684\u5c31\u662f\u5b83\u4f5c\u4e3a\u201c\u8865\u5145\u201d\u7684\u6548"
                 "\u679c\uff0c\u4e0d\u662f\u201c\u66ff\u4ee3\u201d\u3002"),
                ("callout", "warn",
                 "\u540d\u6b21\u5217\u548c\u5206\u6570\u5217\u4e0d\u4e00\u81f4",
                 "<p>\u8fd9\u662f\u8bbe\u8ba1\u5982\u6b64\u3002\u91cd\u6392\u4f1a\u91cd"
                 "\u6392\u524d 20 \u6761\uff0c\u4f46\u6545\u610f\u4fdd\u7559\u6bcf\u6761"
                 "\u4e0a\u7684\u878d\u5408\u5206\uff0c\u6240\u4ee5\u91cd\u6392\u8fc7\u7684"
                 "\u5217\u8868\u770b\u8d77\u6765\u5206\u6570\u662f\u4e71\u7684\u3002\u5982"
                 "\u679c\u5b83\u628a\u5206\u6570\u8986\u76d6\u4e86\uff0c\u4f60\u5c31\u518d"
                 "\u4e5f\u770b\u4e0d\u5230\u878d\u5408\u5f53\u65f6\u662f\u600e\u4e48\u60f3"
                 "\u7684\u3002</p>"),
                ("h3", "\u770b\u4e00\u6b21\u4fdd\u5b58\u4f1a\u8bdd"),
                ("cb", "shell",
                 "facetmark sessions -n 20     # \u6700\u8fd1\u7684\u4fdd\u5b58\u4f1a\u8bdd\n"
                 "facetmark show 412 --body    # \u4e00\u6761\u4e66\u7b7e\u7684 JSON\n"
                 "facetmark stats              # \u7d22\u5f15\u89c4\u6a21\u4e0e\u8986\u76d6"
                 "\u7387"),
            ],
        ),
        (
            "serve",
            "\u8d77\u670d\u52a1\uff1aHTTP API \u4e0e\u914d\u5bf9\u4ee4\u724c",
            [
                ("cb", "shell", "facetmark serve        # 127.0.0.1:8787"),
                ("callout", "warn",
                 "\u53ea\u542c\u56de\u73af\u5730\u5740\u4e0d\u7b97\u9274\u6743",
                 "<p>\u9664\u4e86 <code>/</code>\u3001<code>/health</code>\uff0c\u4ee5\u53ca\u672c\u5730\u9875"
                 "\u9762\u52a0\u8f7d\u81ea\u5df1\u7528\u7684 <code>/app</code> \u548c <code>/app/boot</code>\uff0c"
                 "\u6bcf\u6761\u8def\u7531\u90fd\u8981\u4ee4\u724c\uff0c\u5728 localhost \u4e0a"
                 "\u4e5f\u8981 \u2014\u2014 \u56e0\u4e3a\u4f60\u673a\u5668\u4e0a\u4efb\u4f55"
                 "\u4e00\u4e2a\u8fdb\u7a0b\u90fd\u80fd\u8bbf\u95ee 127.0.0.1\u3002"
                 "<code>--host</code> \u4e0d\u662f\u56de\u73af\u5730\u5740\u65f6\uff0c"
                 "<code>facetmark serve</code> \u4f1a\u544a\u8b66\uff1a\u8fd9\u4e2a\u7d22"
                 "\u5f15\u91cc\u662f\u4f60\u6574\u4e2a\u6d4f\u89c8\u5174\u8da3\u56fe"
                 "\u8c31\u3002</p>"),
                ("h3", "\u4ee4\u724c"),
                ("p",
                 "\u9996\u6b21\u8fd0\u884c\u65f6\u751f\u6210\uff0c\u5199\u5728\u6570\u636e"
                 "\u76ee\u5f55\u7684 <code>pairing-token.txt</code> \u91cc\u3002\u8bf7\u6c42"
                 "\u65f6\u653e\u5728 <code>x-facetmark-token</code> \u5934\u91cc\u3002"),
                ("cb", "shell",
                 "facetmark token             # \u6253\u5370\n"
                 "facetmark token --rotate    # \u4f5c\u5e9f\u65e7\u7684"),
                ("cb", "shell",
                 "TOKEN=$(facetmark token)\n\n"
                 "curl -s http://127.0.0.1:8787/health\n\n"
                 "curl -s -X POST http://127.0.0.1:8787/search \\\n"
                 "  -H 'content-type: application/json' \\\n"
                 "  -H \"x-facetmark-token: $TOKEN\" \\\n"
                 "  -d '{\"q\":\"vectors inside sqlite\",\"limit\":5}'"),
                ("h3", "POST /search"),
                ("table",
                 ["\u5b57\u6bb5", "\u7c7b\u578b", "\u542b\u4e49"],
                 [["<code>q</code>", "string", "\u67e5\u8be2\u3002\u5fc5\u586b\u3002"],
                  ["<code>limit</code>", "int", "\u8fd4\u56de\u6761\u6570\u3002"],
                  ["<code>config</code>", "string",
                   "profile \u6216\u6863\u4f4d\u540d\u3002<code>\"\"</code> \u548c "
                   "<code>\"full\"</code> \u90fd\u8d70 "
                   "<code>default_config</code>\u3002"],
                  ["<code>assist</code>", "bool",
                   "\u5141\u8bb8\u6a21\u578b\u53c2\u4e0e\u7684\u7406\u89e3\u9636\u6bb5"
                   "\u3002"],
                  ["<code>expand</code>", "bool",
                   "\u540c\u65f6\u8fd4\u56de\u4e00\u8df3\u56fe\u6269\u5c55\u90a3\u4e00"
                   "\u7ec4\u3002"]]),
                ("h3", "\u5168\u90e8\u8def\u7531"),
                ("table",
                 ["\u5206\u7ec4", "\u8def\u7531"],
                 [["\u516c\u5f00",
                   "<code>GET /</code> \u00b7 <code>GET /health</code>"],
                  ["\u672c\u5730\u9875\u9762 \u2014\u2014 \u540c\u6837\u516c\u5f00",
                   "<code>GET /app</code> \u00b7 "
                   "<code>GET /app/static/*</code> \u00b7 "
                   "<code>GET /app/boot</code>"],
                  ["\u641c\u7d22",
                   "<code>GET /stats</code> \u00b7 <code>GET /quick</code> "
                   "\u00b7 <code>POST /search</code> \u00b7 "
                   "<code>POST /suggest</code> \u00b7 "
                   "<code>POST /synthesize</code>"],
                  ["\u8bb0\u5f55",
                   "<code>GET /bookmark/{id}</code> \u00b7 "
                   "<code>GET /bookmark/{id}/related</code> \u00b7 "
                   "<code>POST /bookmark</code> \u00b7 "
                   "<code>POST /open</code>"],
                  ["\u4f1a\u8bdd",
                   "<code>GET /sessions</code> \u00b7 "
                   "<code>GET /session/{id}</code>"],
                  ["\u7d22\u5f15\u961f\u5217",
                   "<code>GET /queue/next</code> \u00b7 "
                   "<code>POST /queue/complete</code> \u00b7 "
                   "<code>GET /queue/stats</code>"],
                  ["\u94fe\u63a5\u5065\u5eb7",
                   "<code>GET /link-health/summary</code> \u00b7 "
                   "<code>GET /link-health/{id}</code> \u00b7 "
                   "<code>POST /link-health/check</code> \u00b7 "
                   "<code>GET /graveyard</code>"],
                  ["karakeep \u6865",
                   "<code>POST /karakeep/documents</code> \u00b7 "
                   "<code>POST /karakeep/documents/delete</code> \u00b7 "
                   "<code>POST /karakeep/search</code> \u00b7 "
                   "<code>POST /karakeep/clear</code> \u00b7 "
                   "<code>GET /karakeep/stats</code>"]]),
            ],
        ),
        (
            "webui",
            "\u672c\u5730\u9875\u9762",
            [
                ("p",
                 "<code>facetmark serve</code> \u540c\u65f6\u8fd8\u6258\u7ba1\u7740\u4e00\u4e2a\u641c\u7d22\u9875\u3002\u5b83\u662f\u552f"
                 "\u4e00\u4e00\u4e2a\u9664\u4e86 facetmark \u672c\u8eab\u4ec0\u4e48\u90fd\u4e0d\u7528\u88c5\u7684\u5165\u53e3 \u2014\u2014 \u4e0d\u7528\u52a0\u8f7d\u6d4f"
                 "\u89c8\u5668\u6269\u5c55\uff0c\u4e0d\u7528\u914d\u7f16\u8f91\u5668\uff0c\u4e5f\u4e0d\u7528 <code>curl</code>\u3002"),
                ("cb", "shell",
                 "facetmark serve\n"
                 "# facetmark 1.6.1  http://127.0.0.1:8787\n"
                 "# open the search page:     http://127.0.0.1:8787/app\n"
                 "# pairing token written to: ~/.facetmark/pairing-token.txt"),
                ("p",
                 "Python \u5305\u91cc\u7684\u7eaf HTML\u3001CSS \u548c ES \u6a21\u5757\uff1a\u6ca1\u6709 Node\uff0c\u6ca1\u6709\u6253\u5305\u5668\uff0c"
                 "\u4e5f\u5c31\u6ca1\u6709\u4f1a\u548c\u670d\u52a1\u7aef\u5bf9\u4e0d\u4e0a\u7684\u6784\u5efa\u4ea7\u7269\u3002\u9875\u9762\u548c API \u7531\u540c\u4e00\u4e2a\u8fdb\u7a0b"
                 "\u53d1\u51fa\uff0c\u6240\u4ee5\u662f\u540c\u6e90\u7684 \u2014\u2014 \u8fd9\u4e5f\u662f\u5b83\u6ca1\u6cd5\u6258\u7ba1\u5230\u522b\u5904\u53bb\u7684\u539f\u56e0\uff1a"
                 "\u8fd9\u4e2a\u670d\u52a1\u7684 CORS \u53ea\u5bf9\u6d4f\u89c8\u5668\u6269\u5c55\u7684\u6765\u6e90\u5f00\u653e\u3002"),
                ("h3", "\u4e24\u4e2a\u89c6\u56fe"),
                ("table",
                 ["\u89c6\u56fe", "\u5730\u5740", "\u5e72\u4ec0\u4e48\u7528"],
                 [["\u641c\u7d22", "<code>/app#/search</code>",
                   "\u641c\u7d22\u6846\u548c\u6392\u597d\u5e8f\u7684\u5217\u8868\u3002\u4e00\u6572\u5b57\u5148\u51fa\u5b57\u9762\u5339\u914d\u7684\u7ed3\u679c\uff0c\u5b8c\u5168\u4e0d\u8c03"
                   "\u6a21\u578b\uff1b\u6392\u597d\u5e8f\u7684\u7b54\u6848\u5230\u4e86\u5c31\u66ff\u6362\u6389\uff0c<b>\u52a0\u8f7d\u66f4\u591a</b>\u7ffb\u540e\u9762\u7684\u3002"],
                  ["\u4e66\u7b7e\u5e93", "<code>/app#/library</code>",
                   "<code>facetmark stats</code> \u6253\u5370\u7684\u6240\u6709\u4e1c\u897f\uff0c\u6309\u884c\u5217\u51fa\u6765\uff1a"
                   "\u4e66\u7b7e\u6570\u3001\u591a\u5c11\u6761\u6293\u5230\u4e86\u6b63\u6587\u3001\u591a\u5c11\u6761\u505a\u4e86\u5411\u91cf\u3001\u4f1a\u8bdd\u3001\u6309\u7c7b\u578b\u5206"
                   "\u7684\u8fb9\u3001\u6293\u53d6\u961f\u5217\u3001\u94fe\u63a5\u5065\u5eb7\uff0c\u8fd8\u6709\u51b7\u5c42\u6e05\u70b9\u3002\u201c\u6211\u641c\u4e86\u4f46\u4ec0\u4e48\u90fd\u6ca1"
                   "\u6709\u201d \u8fd9\u4e2a\u95ee\u9898\u5c31\u9760\u8fd9\u4e2a\u89c6\u56fe\u56de\u7b54\u3002"]]),
                ("callout", "info", "\u5b83\u6545\u610f\u4e0d\u505a\u7684\u4e8b",
                 "<p>\u5b83\u53ea\u8bfb\u3002\u6ca1\u6709\u5220\u9664\uff0c\u6ca1\u6709\u7f16\u8f91\uff0c\u6ca1\u6709\u961f\u5217\u63a7\u5236\uff0c\u4e5f\u6ca1\u6709\u7efc\u8ff0\u6309"
                 "\u94ae\u3002\u90a3\u4e9b\u5728\u547d\u4ee4\u884c\u548c API \u91cc\u6709\uff0c\u5728\u90a3\u513f\u72af\u9519\u81f3\u5c11\u662f\u4e3b\u52a8\u72af\u7684\u3002\u9875\u9762"
                 "\u552f\u4e00\u5199\u7684\u4e00\u6b21\uff0c\u662f\u4f60\u70b9\u5f00\u67d0\u6761\u7ed3\u679c\u65f6\u7684 <code>POST /open</code>\uff0c"
                 "\u51b7\u5c42\u5c31\u662f\u9760\u5b83\u5582\u7684\u3002</p>"),
                ("h3", "\u7ed3\u679c\u884c\u4e0a\u7684\u6807\u8bb0\u662f\u4ec0\u4e48\u610f\u601d"),
                ("p",
                 "\u548c\u6269\u5c55\u5f39\u7a97\u7528\u7684\u662f\u540c\u4e00\u5957\u8bcd\u3002\u5728\u9875\u9762\u91cc\uff0c\u6bcf\u4e2a\u6807\u8bb0\u9f20\u6807\u60ac\u505c\u90fd\u6709\u4e00"
                 "\u884c\u89e3\u91ca\uff1b\u8fd9\u5f20\u8868\u662f\u4e3a\u4e86\u8ba9\u4f60\u4e00\u6b21\u770b\u5168\u3002"),
                ("table",
                 ["\u6807\u8bb0", "\u610f\u601d", "\u9ed8\u8ba4"],
                 [["<span class=\"chip mk\">\u5185\u5bb9\u76f8\u5173</span>",
                   "\u547d\u4e2d\u4e86<b>\u5185\u5bb9</b>\u9762 \u2014\u2014 \u9875\u9762\u81ea\u5df1\u6b63\u6587\u7684\u5411\u91cf\u3002",
                   "<span class=\"badge info\">\u5f00</span>"],
                  ["<span class=\"chip mk\">\u63d0\u95ee\u65b9\u5f0f</span>",
                   "\u547d\u4e2d\u4e86<b>\u610f\u56fe</b>\u9762 \u2014\u2014 \u7ed9\u8fd9\u4e2a\u9875\u9762\u751f\u6210\u7684\u95ee\u9898\u7684\u5411\u91cf\u3002",
                   "\u5173"],
                  ["<span class=\"chip mk\">\u8bcd\u8bed</span>",
                   "\u547d\u4e2d\u4e86<b>\u5b57\u9762 \u00b7 \u5206\u8bcd</b>\u9762 \u2014\u2014 \u5bf9\u6807\u9898\u3001\u6587\u4ef6\u5939\u3001\u7f51\u5740\u91cc"
                   "\u5b8c\u6574\u8bcd\u7684 FTS5\u3002", "\u5173"],
                  ["<span class=\"chip mk\">\u5b50\u4e32</span>",
                   "\u547d\u4e2d\u4e86<b>\u5b57\u9762 \u00b7 \u4e09\u5143\u7ec4</b>\u9762 \u2014\u2014 \u5bf9\u5b57\u7b26\u7684 FTS5\uff0c\u4e2d\u6587"
                   "\u67e5\u8be2\u548c\u53ea\u6253\u4e86\u4e00\u534a\u7684\u8bcd\u80fd\u547d\u4e2d\uff0c\u9760\u7684\u5c31\u662f\u5b83\u3002", "\u5173"],
                  ["<span class=\"badge warn mk\">\u5df2\u51b7\u5374</span>",
                   "\u5f88\u4e45\u4ee5\u524d\u5b58\u7684\uff0c\u4e00\u76f4\u6ca1\u6253\u5f00\u8fc7\uff0c\u800c\u4e14\u6709\u66f4\u65b0\u7684\u4e1c\u897f\u770b\u8d77\u6765\u628a\u5b83\u53d6"
                   "\u4ee3\u4e86\u3002\u6392\u540d\u538b\u4f4e\uff0c\u7edd\u4e0d\u5220\u9664\u3002",
                   "<span class=\"badge info\">\u5f00</span>"],
                  ["<span class=\"gmk mk\">\u5f53\u65f6\u524d\u540e\u4e00\u8d77\u5b58\u7684</span>",
                   "\u7b2c\u4e8c\u7ec4\uff1a\u4ece\u4e0a\u9762\u67d0\u6761\u7ed3\u679c\u51fa\u53d1\uff0c\u5728\u94fe\u63a5\u56fe\u4e0a\u8d70\u4e00\u8df3\u3002\u7edd\u4e0d\u6df7\u8fdb\u6392"
                   "\u540d\u91cc\u3002",
                   "<span class=\"badge info\">\u5f00</span>"]]),
                ("p",
                 "\u7b2c\u4e8c\u7ec4\u91cc\u6bcf\u4e00\u884c\u90fd\u5e26\u7740\u8d70\u5230\u5b83\u7684\u90a3\u6761\u8fb9 \u2014\u2014 <em>\u540c\u4e00\u6b21\u6d4f\u89c8</em>"
                 "\uff08\u540c\u4e00\u6b21\u4e0a\u7f51\u65f6\u5b58\u7684\uff09\u3001<em>\u8bed\u4e49\u76f8\u8fd1</em>\u3001<em>\u5df2\u88ab\u53d6\u4ee3</em>\u3001"
                 "<em>\u540c\u4e00\u9875\u9762</em>\u3001<em>\u540c\u4e00\u7ad9\u70b9</em>\u3002\u8fd9\u4e9b\u540d\u5b57\u80cc\u540e\u7684\u6743\u91cd\u5728"
                 "<a href=\"#env\">\u914d\u7f6e\u8868</a>\u91cc\u3002"),
                ("h3", "\u9875\u9762\u600e\u4e48\u62ff\u5230\u4ee4\u724c"),
                ("p",
                 "\u5b83\u53bb\u95ee <code>GET /app/boot</code>\u3002\u8fd9\u662f\u552f\u4e00\u4e00\u6761\u80fd\u628a\u914d\u5bf9\u4ee4\u724c"
                 "\u4ea4\u51fa\u53bb\u7684\u8def\u7531\uff0c\u800c\u4e14\u53ea\u5728\u8c03\u7528\u65b9\u548c\u8bf7\u6c42\u91cc\u5199\u7684\u5730\u5740\u4e24\u8005\u90fd\u662f\u56de\u73af\u5730"
                 "\u5740\u65f6\u624d\u4ea4\u3002\u5728\u4f60\u81ea\u5df1\u673a\u5668\u4e0a\u4e24\u6761\u90fd\u6210\u7acb\uff0c\u9875\u9762\u5c31\u81ea\u5df1\u914d\u5bf9\u597d\u4e86\uff0c\u6ca1"
                 "\u6709\u4ec0\u4e48\u8981\u590d\u5236\u7684\u3002"),
                ("callout", "warn", "\u7b2c\u4e8c\u4e2a\u6761\u4ef6\u662f\u5e72\u4ec0\u4e48\u7684",
                 "<p>\u516c\u7f51\u4e0a\u7684\u4e00\u4e2a\u9875\u9762\u53ef\u4ee5\u628a\u67d0\u4e2a\u57df\u540d\u89e3\u6790\u5230 127.0.0.1\uff0c\u7136\u540e\u8ba9"
                 "<em>\u4f60\u7684</em>\u6d4f\u89c8\u5668\u53bb\u53d1\u8fd9\u4e2a\u8bf7\u6c42 \u2014\u2014 \u8c03\u7528\u65b9\u786e\u5b9e\u662f\u56de\u73af\u5730\u5740\u3002"
                 "\u4f46\u5b83\u6539\u4e0d\u4e86 <code>Host</code> \u5934\uff0c\u90a3\u91cc\u9762\u8fd8\u5199\u7740\u653b\u51fb\u8005\u7684\u57df\u540d\u3002"
                 "\u67e5\u8fd9\u4e00\u9879\uff0c\u624d\u662f\u62e6\u4f4f\u4e00\u4e2a\u7f51\u7ad9\u8bfb\u8d70\u4f60\u4ee4\u724c\u7684\u4e1c\u897f\uff1b\u8fd9\u4e5f\u662f\u4e3a\u4ec0\u4e48\u5b83"
                 "\u662f\u4e00\u6761\u5355\u72ec\u7684\u8def\u7531\uff0c\u800c\u4e0d\u662f\u6302\u5728\u73b0\u6709\u8def\u7531\u4e0a\u7684\u4e00\u4e2a\u5f00\u5173\u3002</p><p>\u5728"
                 "\u53cd\u5411\u4ee3\u7406\u540e\u9762\uff0c\u6216\u8005\u7528\u5c40\u57df\u7f51\u5730\u5740\u8bbf\u95ee\u65f6\uff0c\u8fd9\u4e2a\u68c0\u67e5\u4f1a\u4e0d\u901a\u8fc7 \u2014\u2014 "
                 "\u8fd9\u662f\u6545\u610f\u7684\uff1a\u9875\u9762\u8fd9\u65f6\u7ed9\u4f60\u4e00\u4e2a\u8f93\u5165\u6846\uff0c\u628a "
                 "<code>facetmark token</code> \u7c98\u4e00\u6b21\u5c31\u884c\u3002\u5b83\u5b58\u5728\u90a3\u4e2a\u6d4f\u89c8\u5668\u7684"
                 "\u672c\u5730\u5b58\u50a8\u91cc\uff0c\u4e0d\u5728\u9875\u9762\u91cc\u3002</p>"),
                ("h3", "\u952e\u76d8"),
                ("table",
                 ["\u6309\u952e", "\u4f5c\u7528"],
                 [["<kbd>/</kbd>", "\u5728\u9875\u9762\u4efb\u4f55\u5730\u65b9\u805a\u7126\u5230\u641c\u7d22\u6846\u3002"],
                  ["<kbd>Enter</kbd>", "\u641c\u7d22\u3002"],
                  ["<kbd>\u2191</kbd> <kbd>\u2193</kbd>",
                   "\u5728\u7ed3\u679c\u4e4b\u95f4\u79fb\u52a8\u3002\u5728\u641c\u7d22\u6846\u91cc\u6309 <kbd>\u2193</kbd> \u8fdb\u5165\u5217\u8868\u3002"],
                  ["<kbd>Esc</kbd>", "\u6e05\u7a7a\u67e5\u8be2\uff0c\u56de\u5230\u641c\u7d22\u6846\u3002"]]),
                ("h3", "\u8bed\u8a00\u548c\u4e3b\u9898"),
                ("p",
                 "\u4e2d\u82f1\u6587\uff0c\u9876\u680f\u5207\u6362\uff0c\u4e0b\u6b21\u8bb0\u5f97\u3002\u6ca1\u5b58\u8fc7\u9009\u62e9\u65f6\u8ddf\u968f\u6d4f\u89c8\u5668\u8bed\u8a00\u3002\u4e3b"
                 "\u9898\u5f00\u5173\u5728 \u8ddf\u968f\u7cfb\u7edf \u2192 \u6d45\u8272 \u2192 \u6df1\u8272 \u4e4b\u95f4\u5faa\u73af\uff0c\u800c\u4e14\u548c\u672c\u7ad9\u5171\u7528"
                 "\u540c\u4e00\u4e2a\u5b58\u50a8\u952e\uff0c\u6240\u4ee5\u5728\u8fd9\u91cc\u9009\u4e86\u6df1\u8272\u7684\u4eba\uff0c\u90a3\u8fb9\u4e5f\u662f\u6df1\u8272\u3002\u6240\u6709\u52a8"
                 "\u6548\u90fd\u5305\u5728 <code>prefers-reduced-motion</code> \u67e5\u8be2\u91cc\u3002"),
            ],
        ),
        # ------------------------------------------------------------- 翻页
        (
            "paging",
            "\u7ffb\u9875\uff1alimit\u3001offset \u548c depth",
            [
                ("p",
                 "\u6bcf\u4e2a\u641c\u7d22\u5165\u53e3\u90fd\u6536 <code>limit</code>\u3001<code>offset</code> \u548c "
                 "<code>depth</code>\uff0c\u800c\u6bcf\u4e2a\u641c\u7d22\u54cd\u5e94\u62a5\u7684\u662f\u5b83<em>\u5b9e\u9645</em>\u7ed9\u51fa"
                 "\u7684\u90a3\u4e2a\u7a97\u53e3\uff0c\u4e0d\u662f\u628a\u4f60\u8981\u7684\u539f\u6837\u56de\u663e\u3002"),
                ("cb", "shell",
                 'facetmark search "kafka rebalance" -n 20\n'
                 'facetmark search "kafka rebalance" -n 20 -o 20 --depth 60'),
                ("p",
                 "\u53ea\u8981\u8fd8\u6709\u4e0b\u4e00\u9875\uff0cCLI \u5c31\u4f1a\u628a\u4e0b\u4e00\u9875\u7684 <code>--offset</code> \u548c "
                 "<code>--depth</code> \u6253\u51fa\u6765\u3002\u8d70 HTTP \u65f6\uff0c\u540c\u6837\u8fd9\u4e09\u4e2a\u5b57\u6bb5\u653e\u5728 "
                 "<code>POST /search</code> \u7684\u8bf7\u6c42\u4f53\u91cc\uff1a"),
                ("cb", "json",
                 "{\n"
                 '  "hits": [ ],\n'
                 '  "limit": 20,          // \u5b9e\u9645\u7ed9\u7684\uff0c\u5df2\u7ecf\u5939\u8fc7\n'
                 '  "offset": 20,\n'
                 '  "depth": 60,          // \u8fd9\u6b21\u6392\u540d\u8dd1\u7684\u6df1\u5ea6\n'
                 '  "total": 137,         // \u5df2\u7ecf\u6392\u8fc7\u7684\u6761\u6570\uff1b\u5c01\u9876\u65f6\u662f\u4e0b\u754c\n'
                 '  "has_more": true,\n'
                 '  "depth_capped": false\n'
                 "}"),
                ("table",
                 ["\u5b57\u6bb5", "\u542b\u4e49"],
                 [["<code>limit</code>",
                   "\u8fd9\u4e00\u9875\u7684\u6761\u6570\u3002\u4f1a\u5939\u5230 <code>MAX_PAGE_SIZE</code>\uff0c\u9ed8\u8ba4 "
                   "200\u3002"],
                  ["<code>offset</code>",
                   "\u8df3\u8fc7\u7684\u6761\u6570\u3002\u4f1a\u5939\u5728 <code>MAX_CANDIDATE_DEPTH</code> \u4ee5\u4e0b\u3002"],
                  ["<code>depth</code>",
                   "\u878d\u5408\u4e4b\u524d\u6bcf\u4e2a\u9762\u5404\u8bfb\u591a\u6df1\u3002\u4e0d\u586b\u5c31\u6309\u7a97\u53e3\u63a8\u7b97\uff1b\u628a\u4e0a\u4e00\u9875\u62a5\u7684\u503c"
                   "\u539f\u6837\u9001\u56de\u6765\uff0c\u8fd9\u4e00\u9875\u5c31\u63a5\u7740<em>\u540c\u4e00\u6b21</em>\u6392\u540d\u5f80\u4e0b\u8d70\u3002"],
                  ["<code>total</code>",
                   "\u878d\u5408\u8fd9\u4e00\u6b65\u6392\u8fc7\u7684\u6587\u6863\u6570\u3002\u662f\u4e2a\u4e0b\u754c\uff0c\u4e0d\u662f\u4e66\u7b7e\u5e93\u7684\u603b\u6570\uff1b"
                   "<code>depth_capped</code> \u4e3a\u771f\u65f6\u66f4\u662f\u660e\u786e\u53ea\u5f53\u4e0b\u754c\u770b\u3002"],
                  ["<code>has_more</code>",
                   "\u8fd9\u4e2a\u7a97\u53e3\u540e\u9762\u8fd8\u6709\u4e1c\u897f\u3002\u5728\u51fa\u5382\u7684\u5355\u9762\u9ed8\u8ba4\u6863\u4e0b\u662f\u51c6\u7684\uff1b\u5f00\u4e86\u597d"
                   "\u51e0\u4e2a\u9762\u65f6\u662f\u4e0a\u754c \u2014\u2014 \u591a\u51fa\u6765\u7684\u90a3\u4e00\u6761\u6709\u53ef\u80fd\u662f\u5019\u9009\u6c60\u91cc\u5df2\u7ecf"
                   "\u6709\u7684\u6587\u6863\u3002"],
                  ["<code>depth_capped</code>",
                   "\u540e\u9762<em>\u786e\u5b9e</em>\u8fd8\u6709\uff0c\u800c\u4e14\u505c\u4e0b\u6765\u7684\u539f\u56e0\u662f\u649e\u5230\u4e86\u6df1\u5ea6\u4e0a\u9650\uff0c"
                   "\u4e0d\u662f\u4f60\u7684\u7a97\u53e3 \u2014\u2014 \u8fd9\u662f\u201c\u70b9\u4e0b\u4e00\u9875\u201d\u548c\u201c\u628a\u6df1\u5ea6\u8c03\u5927\uff0c\u6216\u8005"
                   "\u628a\u67e5\u8be2\u6536\u7a84\u201d\u4e4b\u95f4\u7684\u533a\u522b\u3002"]]),
                ("h3", "\u4e3a\u4ec0\u4e48 depth \u662f\u4e2a\u53c2\u6570\uff0c\u800c\u4e0d\u662f\u5b9e\u73b0\u7ec6\u8282"),
                ("p",
                 "\u4ee5\u524d\u9875\u5927\u5c0f\u548c\u68c0\u7d22\u6df1\u5ea6\u662f\u540c\u4e00\u4e2a\u6570\uff1a\u8981\u66f4\u591a\u6761\u5c31\u4f1a\u6084\u6084\u68c0\u7d22\u5f97\u66f4"
                 "\u6df1\uff0c\u800c\u7b2c 51 \u6761\u5728\u4efb\u4f55\u9875\u5927\u5c0f\u4e0b\u90fd\u591f\u4e0d\u7740\uff0c\u56e0\u4e3a\u5019\u9009\u6c60\u4e0d\u7ba1\u600e\u6837\u90fd"
                 "\u662f 50 \u6761\u3002\u73b0\u5728\uff0c\u9875\u662f\u4e00\u4e2a\u7a97\u53e3\uff0c\u770b\u7684\u662f\u4e00\u4e2a\u4f60\u80fd\u770b\u89c1\u3001\u4e5f\u80fd\u9489\u4f4f"
                 "\u7684\u5019\u9009\u6c60\u3002"),
                ("callout", "warn", "\u9489\u4f4f depth\uff0c\u5426\u5219\u7b2c\u4e8c\u9875\u4f1a\u548c\u7b2c\u4e00\u9875\u6253\u67b6",
                 "<p>\u53ea\u6709\u5728<em>\u4e00\u4e2a</em>\u9762\u7684\u65f6\u5019\uff0cRRF \u624d\u5728\u5019\u9009\u6c60\u53d8\u5927\u65f6\u4fdd\u6301\u540d"
                 "\u6b21\u7a33\u5b9a\u3002\u4e00\u4e2a\u6587\u6863\u7684\u5206\u6570\uff0c\u662f\u5b83\u5728\u201c\u6df1\u5ea6\u4ee5\u5185\u6392\u5230\u4e86\u5b83\u201d\u7684\u90a3\u4e9b\u9762"
                 "\u4e0a\u6c42\u548c\uff0c\u6240\u4ee5\u66f4\u6df1\u7684\u6c60\u5b50\u53ef\u80fd\u51ed\u7a7a\u7ed9\u67d0\u4e2a\u6587\u6863\u8865\u4e0a\u4e00\u9879 \u2014\u2014 \u800c\u8fd9"
                 "\u4e00\u9879\u53ef\u80fd\u538b\u8fc7\u5bf9\u624b\u7684\u6574\u4e2a\u5206\u6570\u3002\u5728\u4e00\u4e2a\u9762\u4e0a\u6392\u7b2c 2\u3001\u5728\u53e6\u4e00\u4e2a\u9762\u4e0a"
                 "\u6392\u7b2c 40\uff0c\u5408\u8d77\u6765\u8d62\u8fc7\u53ea\u5728\u4e00\u4e2a\u9762\u4e0a\u6392\u7b2c 1 \u7684\uff081/62 + 1/100 \u5bf9 "
                 "1/61\uff09\uff0c\u4f46\u5728\u6df1\u5ea6 30 \u65f6\u540e\u9762\u90a3\u4e00\u9879\u6839\u672c\u4e0d\u5b58\u5728\u3002</p><p>\u6240\u4ee5\u5f00\u4e86"
                 "\u597d\u51e0\u4e2a\u9762\u65f6\uff0c\u4e3a\u4e86\u7ffb\u5230\u7b2c 2 \u9875\u800c\u628a\u6df1\u5ea6\u52a0\u5927\uff0c\u4f1a\u8ba9\u7b2c 2 \u9875\u5bf9\u201c\u7b2c "
                 "1 \u9875\u662f\u4ec0\u4e48\u201d\u8fd9\u4ef6\u4e8b\u548c\u7b2c 1 \u9875\u4ea7\u751f\u5206\u6b67\u3002\u89e3\u6cd5\u4e0d\u662f\u52a0\u5927\u5b83\uff1a\u628a\u4e0a\u4e00"
                 "\u9875\u62a5\u7684 <code>depth</code> \u539f\u6837\u9001\u56de\u6765\uff0c\u6bcf\u4e00\u9875\u5c31\u90fd\u662f\u540c\u4e00\u6b21\u6392\u540d"
                 "\u7684\u4e00\u4e2a\u5207\u7247\u3002\u672c\u5730\u9875\u9762\u548c\u6d4f\u89c8\u5668\u6269\u5c55\u90fd\u662f\u8fd9\u4e48\u505a\u7684\u3002</p>"),
                ("h3", "\u4e24\u4e2a\u4e0a\u9650"),
                ("p",
                 "<code>MAX_PAGE_SIZE</code>\uff08200\uff09\u9650\u4f4f\u4e00\u9875\u3002"
                 "<code>MAX_CANDIDATE_DEPTH</code>\uff082000\uff09\u9650\u4f4f\u5b83\u4eec\u80cc\u540e\u7684\u6574\u4e2a\u5019"
                 "\u9009\u6c60\uff0c\u649e\u4e0a\u5b83\u5c31\u662f <code>depth_capped</code> \u88ab\u7f6e\u4e0a\u7684\u539f\u56e0\u3002\u4e24"
                 "\u4e2a\u90fd\u5728\u540c\u4e00\u4e2a\u5730\u65b9\u3001\u5728\u4efb\u4f55\u67e5\u8be2\u5f00\u8dd1\u4e4b\u524d\u5939\u597d\uff0c\u6240\u4ee5\u4e00\u4e2a\u8d85\u5927\u7684\u8bf7"
                 "\u6c42\u4e0d\u82b1\u4ec0\u4e48\u4ee3\u4ef7\uff0c\u56de\u7ed9\u4f60\u7684\u5c31\u662f\u5b9e\u9645\u7ed9\u51fa\u7684\u90a3\u4e2a\u7a97\u53e3\u3002"),
            ],
        ),
        (
            "extension",
            "\u6d4f\u89c8\u5668\u6269\u5c55",
            [
                ("p",
                 "Manifest V3\uff0cChromium \u7cfb\u6d4f\u89c8\u5668\u3002\u5b83\u53ea\u548c "
                 "<code>127.0.0.1:8787</code> \u8bf4\u8bdd \u2014\u2014 \u90a3\u5c31\u662f"
                 "\u5b83\u5168\u90e8\u7684\u5fc5\u9700\u4e3b\u673a\u6743\u9650\u3002"),
                ("steps",
                 ["\u4ece<a href=\"" + REPO + "/releases\">\u53d1\u884c\u9875</a>\u4e0b"
                  "\u8f7d <code>facetmark-extension.zip</code> \u5e76\u89e3\u538b\u3002",
                  "\u6253\u5f00 <code>chrome://extensions</code>\uff0c\u5f00\u542f<b>"
                  "\u5f00\u53d1\u8005\u6a21\u5f0f</b>\uff0c\u9009<b>\u52a0\u8f7d\u5df2\u89e3"
                  "\u538b\u7684\u6269\u5c55</b>\uff0c\u6307\u5411\u521a\u624d\u90a3\u4e2a"
                  "\u76ee\u5f55\u3002",
                  "\u5728\u7ec8\u7aef\u8dd1 <code>facetmark serve</code> \u5e76\u4fdd\u6301"
                  "\u8fd0\u884c\u3002",
                  "\u8dd1 <code>facetmark token</code>\uff0c\u6253\u5f00\u6269\u5c55\u7684"
                  "\u8bbe\u7f6e\u9875\uff0c\u628a\u4ee4\u724c\u7c98\u8fdb\u53bb\u3002",
                  "\u6309 <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd>\uff08macOS \u662f "
                  "<kbd>Cmd</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd>\uff09\u5c31\u80fd\u641c"
                  "\u4e86\u3002"]),
                ("h3", "\u5b83\u80fd\u5e72\u4ec0\u4e48"),
                ("table",
                 ["\u529f\u80fd", "\u8bf4\u660e"],
                 [["\u5730\u5740\u680f\u5173\u952e\u5b57",
                   "\u5730\u5740\u680f\u8f93 <code>fm</code> \u518d\u6572\u7a7a\u683c"
                   "\uff0c\u4e0d\u7528\u5f00\u5f39\u7a97\u5c31\u80fd\u641c\u3002"],
                  ["\u5feb\u6377\u952e",
                   "<kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd> / "
                   "<kbd>Cmd</kbd>+<kbd>Shift</kbd>+<kbd>K</kbd>\u3002"],
                  ["\u4fdd\u5b58\u5f53\u524d\u6807\u7b7e\u9875",
                   "\u4e00\u952e\u3002\u9875\u9762\u8fdb\u672c\u5730\u7d22\u5f15\u961f"
                   "\u5217\uff0c\u5f39\u7a97\u5e95\u90e8\u663e\u793a\u8fd8\u5269\u51e0"
                   "\u4e2a\u3002"],
                  ["\u53f3\u952e\u83dc\u5355",
                   "\u53f3\u952e\u4e00\u4e2a\u94fe\u63a5\u6216\u9875\u9762\u5c31\u80fd"
                   "\u5b58\u3002"],
                  ["\u5206\u7ec4\u7ed3\u679c",
                   "\u540c\u4e00\u6b21\u4fdd\u5b58\u4f1a\u8bdd\u91cc\u7684\u9875\u9762"
                   "\u5355\u72ec\u6210\u7ec4\uff0c\u4e0d\u6df7\u8fdb\u6392\u540d\u3002"],
                  ["\u9762\u6807\u7b7e",
                   "\u6bcf\u6761\u7ed3\u679c\u663e\u793a\u547d\u4e2d\u4e86\u54ea\u4e9b"
                   "\u9762 \u2014\u2014 <em>\u5173\u4e8e</em>\u3001<em>\u53ef\u80fd\u4f1a"
                   "\u95ee</em>\u3001<em>\u8bcd</em>\u3001<em>\u5b50\u4e32</em>\u3001"
                   "<em>\u5173\u8054</em>\u3001<em>\u51b7</em>\u3002"]]),
                ("h3", "\u8bbe\u7f6e\u9879"),
                ("table",
                 ["\u5b57\u6bb5", "\u542b\u4e49"],
                 [["<code>endpoint</code>",
                   "facetmark \u76d1\u542c\u5728\u54ea\u3002\u9ed8\u8ba4 "
                   "<code>http://127.0.0.1:8787</code>\u3002"],
                  ["<code>token</code>",
                   "<code>facetmark token</code> \u7684\u8f93\u51fa\u3002"],
                  ["<code>channelB</code>",
                   "\u53ef\u9009\u7684\u7b2c\u4e8c\u4e2a\u7aef\u70b9\uff0c\u7528\u4e8e"
                   "\u540c\u65f6\u8dd1\u4e24\u4e2a\u5e93\u3002"],
                  ["<code>paused</code>",
                   "\u4e0d\u5378\u8f7d\u7684\u524d\u63d0\u4e0b\u8ba9\u6269\u5c55\u505c"
                   "\u6b62\u548c\u670d\u52a1\u901a\u4fe1\u3002"]]),
                ("callout", "info", "\u4e0d\u5728\u5e94\u7528\u5546\u5e97\u91cc",
                 "<p>\u6269\u5c55\u4ee5 zip \u5f62\u5f0f\u653e\u5728\u53d1\u884c\u9875"
                 "\uff0c\u9700\u8981\u89e3\u538b\u540e\u52a0\u8f7d\u3002\u5b83\u6ca1\u6709"
                 "\u63d0\u4ea4\u5230 Chrome \u5e94\u7528\u5546\u5e97\u6216 Edge \u52a0\u8f7d"
                 "\u9879\u76ee\u5f55\u3002</p>"),
            ],
        ),
        (
            "mcp",
            "MCP \u670d\u52a1\u5668",
            [
                ("p",
                 "<code>facetmark mcp</code> \u5728 stdio \u4e0a\u8dd1\u4e00\u4e2a FastMCP "
                 "\u670d\u52a1\u5668\uff0c\u6240\u4ee5 Claude Desktop \u8fd9\u7c7b MCP "
                 "\u5ba2\u6237\u7aef\u53ef\u4ee5\u641c\u4f60\u7684\u5e93\u3001\u8bfb\u4e00"
                 "\u6b21\u4fdd\u5b58\u4f1a\u8bdd\u3001\u5b58\u4e00\u4e2a\u9875\u9762\u3002"),
                ("cb", "json",
                 "{\n"
                 '  "mcpServers": {\n'
                 '    "facetmark": {\n'
                 '      "command": "facetmark",\n'
                 '      "args": ["mcp"]\n'
                 "    }\n"
                 "  }\n"
                 "}"),
                ("p",
                 "\u5728 <code>args</code> \u91cc\u52a0 "
                 "<code>\"--db\", \"/path/to/facetmark.db\"</code> \u53ef\u4ee5\u6307\u5b9a"
                 "\u5e93\uff0c\u52a0 <code>\"--mock\"</code> \u53ef\u4ee5\u6ca1 key \u5148"
                 "\u8bd5\u3002\u73af\u5883\u53d8\u91cf\u7684\u8bfb\u6cd5\u548c\u5176\u4ed6"
                 "\u547d\u4ee4\u5b8c\u5168\u4e00\u6837\u3002"),
                ("h3", "9 \u4e2a\u5de5\u5177"),
                ("table",
                 ["\u5de5\u5177", "\u4f5c\u7528"],
                 [["<code>search_bookmarks</code>",
                   "\u5b8c\u6574\u7ba1\u7ebf\uff0c\u548c "
                   "<code>facetmark search</code> \u4e00\u6837\u3002"],
                  ["<code>get_bookmark</code>",
                   "\u4e00\u6761\u8bb0\u5f55\uff0c\u53ef\u9009\u5e26\u6b63\u6587\u3002"],
                  ["<code>list_sessions</code>", "\u6700\u8fd1\u7684\u4fdd\u5b58\u4f1a\u8bdd"
                   "\u3002"],
                  ["<code>get_session</code>",
                   "\u4e00\u6b21\u4f1a\u8bdd\u91cc\u5b58\u7684\u5168\u90e8\u3002"],
                  ["<code>find_related</code>", "\u5728\u94fe\u63a5\u56fe\u91cc\u5f80\u5916"
                   "\u8d70\u4e00\u8df3\u3002"],
                  ["<code>synthesize</code>",
                   "\u57fa\u4e8e\u68c0\u7d22\u5230\u7684\u9875\u9762\u5199\u4e00\u4efd"
                   "\u56de\u7b54\u3002"],
                  ["<code>suggest_from_context</code>",
                   "\u4f60\u6b63\u5728\u770b\u7684\u8fd9\u6bb5\u6587\u5b57\uff0c\u5e93\u91cc"
                   "\u6709\u4ec0\u4e48\u76f8\u5173\u3002"],
                  ["<code>check_link_health</code>",
                   "\u4e00\u4e2a\u5b58\u8fc7\u7684 URL \u8fd8\u6d3b\u7740\u5417\u3002"],
                  ["<code>save_bookmark</code>",
                   "\u52a0\u4e00\u4e2a URL \u5e76\u6392\u961f\u7d22\u5f15\u3002"]]),
                ("h3", "3 \u4e2a\u8d44\u6e90"),
                ("ul",
                 ["<code>bookmark://{id}</code> \u2014\u2014 \u4e00\u6761\u8bb0\u5f55\u7684 "
                  "JSON\u3002",
                  "<code>session://{id}</code> \u2014\u2014 \u4e00\u6b21\u4fdd\u5b58\u4f1a"
                  "\u8bdd\u3002",
                  "<code>facetmark://stats</code> \u2014\u2014 \u7d22\u5f15\u89c4\u6a21"
                  "\u4e0e\u8986\u76d6\u7387\u3002"]),
            ],
        ),
        (
            "karakeep",
            "karakeep \u63d2\u4ef6",
            [
                ("p",
                 "<a href=\"https://karakeep.app\">karakeep</a> \u662f\u4e00\u4e2a\u53ef"
                 "\u81ea\u6258\u7ba1\u7684\u4e66\u7b7e\u7ba1\u7406\u5668\uff0c\u641c\u7d22"
                 "\u63d0\u4f9b\u8005\u53ef\u63d2\u62d4\u3002\u8fd9\u4e2a\u63d2\u4ef6\u628a "
                 "facetmark \u63a5\u5230\u5b83\u7684\u641c\u7d22\u6846\u540e\u9762\uff1a"
                 "karakeep \u7ba1\u754c\u9762\uff0cfacetmark \u7ba1\u68c0\u7d22\u3002"),
                ("steps",
                 ["\u628a\u63d2\u4ef6\u62f7\u8fdb karakeep \u7684\u63d2\u4ef6\u5305\u3002",
                  "\u5728 exports \u6620\u5c04\u91cc\u6ce8\u518c\u5b83\u3002",
                  "\u5728 meilisearch <b>\u4e4b\u540e</b>\u52a0\u8f7d\uff0c\u56e0\u4e3a"
                  "\u63d2\u4ef6\u7ba1\u7406\u5668\u53d1\u51fa\u53bb\u7684\u662f\u6700\u540e"
                  "\u6ce8\u518c\u7684\u90a3\u4e2a\u63d0\u4f9b\u8005\u3002",
                  "\u628a\u5b83\u6307\u5411\u4e00\u4e2a\u5728\u8dd1\u7684 facetmark \u670d"
                  "\u52a1\u3002"]),
                ("cb", "shell",
                 "cp -r integrations/karakeep/search-facetmark \\\n"
                 "  /path/to/karakeep/packages/plugins/search-facetmark"),
                ("cb", "json",
                 "// packages/plugins/package.json \u2014 exports \u6620\u5c04\n"
                 '"./search-facetmark": "./search-facetmark/index.ts"'),
                ("cb", "ts",
                 "// packages/shared-server/src/plugins.ts \u7684 loadAllPlugins()\n"
                 "await import(\"@karakeep/plugins/search-meilisearch\");\n"
                 "await import(\"@karakeep/plugins/search-facetmark\");  "
                 "// \u5fc5\u987b\u5728\u540e\u9762"),
                ("cb", "shell",
                 "export FACETMARK_URL=http://127.0.0.1:8787\n"
                 "export FACETMARK_TOKEN=$(facetmark token)\n"
                 "facetmark serve"),
                ("h3", "\u534f\u8bae\u662f\u600e\u4e48\u9489\u4f4f\u7684"),
                ("ul",
                 ["karakeep \u4e0a\u6e38\u7684\u7c7b\u578b\u6309 blob SHA \u9489\u5728 "
                  "<code>integrations/karakeep/typecheck/upstream-pins.json</code>\uff0c"
                  "CI \u4f1a\u5bf9\u7740\u5b83\u8dd1 <code>tsc --noEmit</code>\u3002",
                  "\u62a5\u6587\u683c\u5f0f\u5b58\u5728 "
                  "<code>integrations/karakeep/contract/wire.json</code>\uff0c\u7531 "
                  "<code>tests/test_karakeep_contract.py</code> \u56de\u653e\u3002",
                  "\u8fd9\u4e2a\u56de\u653e\u6d4b\u8bd5\u771f\u7684\u63a5\u4f4f\u4e86\u4e00"
                  "\u4e2a\uff1a\u53ea\u6709\u4e00\u6761\u547d\u4e2d\u65f6\u7684 offset "
                  "1\uff0c\u6b63\u786e\u7b54\u6848\u662f <code>hits: []</code> \u914d "
                  "<code>totalHits: 1</code>\u3002\u7a7a\u7684 <code>hits</code> "
                  "<b>\u4e0d\u7b49\u4e8e</b>\u6ca1\u6709\u7ed3\u679c\u3002"]),
                ("callout", "warn",
                 "\u6307\u671b\u5b83\u4e4b\u524d\u8981\u77e5\u9053\u4e24\u4ef6\u4e8b",
                 "<p>\u7b2c\u4e00\uff0c\u6ca1\u6709\u9488\u5bf9\u771f\u5b9e\u5728\u8dd1"
                 "\u7684 karakeep \u5b9e\u4f8b\u7684\u6d4b\u8bd5 \u2014\u2014 \u53ea\u6709"
                 "\u5bf9\u9489\u6b7b\u534f\u8bae\u7684\u3002\u7b2c\u4e8c\uff0c\u628a\u5e93"
                 "\u63a8\u8fdb karakeep \u518d\u8bfb\u56de\u6765\uff0c\u6392\u540d\u4f1a"
                 "\u53d8\uff1akarakeep \u7684 tag \u5c31\u662f\u4f60\u6d4f\u89c8\u5668\u7684"
                 "<em>\u6587\u4ef6\u5939</em>\u540d\uff0c\u6240\u4ee5\u5173\u952e\u8bcd"
                 "\u4ece 19,016 \u4e2a\u4e0d\u540c\u8bcd\u584c\u5230 13 \u4e2a\u3002\u6307"
                 "\u6807\u5c42\u9762\u7684\u7ed3\u8bba\u80fd\u8fc7\u5f80\u8fd4\uff0c\u540d"
                 "\u6b21\u5c42\u9762\u7684\u4e0d\u80fd\uff0c\u9664\u975e\u91cd\u5efa\u7d22"
                 "\u5f15\u3002<a href=\"measured.zh.html#karakeep\">\u5b8c\u6574\u5b9e"
                 "\u6d4b</a>\u3002</p>"),
                ("p",
                 "\u60f3\u5378\u6389\u8fd9\u5ea7\u6865\uff0c\u628a "
                 "<code>karakeep_doc</code> \u8868 drop \u4e86\u5c31\u884c\u3002"
                 "<code>enrichment.source_hash == 'karakeep'</code> \u662f\u4fdd\u7559"
                 "\u503c\uff0c\u610f\u601d\u662f\u8fd9\u884c\u6865\u53ef\u4ee5\u8986\u5199"
                 "\uff1b\u5176\u4ed6\u4efb\u4f55\u503c\u90fd\u610f\u5473\u7740\u662f\u771f"
                 "\u6a21\u578b\u5199\u7684\uff0c\u6865\u4e0d\u78b0\u3002"),
            ],
        ),
        (
            "data",
            "\u6570\u636e\u5e93\u91cc\u6709\u4ec0\u4e48",
            [
                ("p",
                 "\u4e00\u4e2a SQLite \u6587\u4ef6\u3002\u4efb\u4f55 SQLite \u5de5\u5177"
                 "\u90fd\u80fd\u6253\u5f00\uff0c\u4e0d\u52a0\u5bc6\u3001\u4e0d\u6df7\u6dc6"
                 "\u3001\u4e0d\u79c1\u6709\u3002\u5c31\u7b97\u4f60\u4e0d\u7528 facetmark "
                 "\u4e86\uff0c\u6570\u636e\u4e5f\u8fd8\u8bfb\u5f97\u51fa\u6765\u3002"),
                ("table",
                 ["\u8868", "\u5b58\u4ec0\u4e48"],
                 [["<code>bookmark</code>",
                   "URL\u3001\u6807\u9898\u3001\u6587\u4ef6\u5939\u8def\u5f84\u3001\u4fdd"
                   "\u5b58\u65f6\u95f4\u3001\u6765\u6e90\u3002"],
                  ["<code>content</code>",
                   "\u6293\u56de\u6765\u7684\u6b63\u6587\u548c\u62bd\u53d6\u7ed3\u679c"
                   "\u3002"],
                  ["<code>enrichment</code>",
                   "\u6458\u8981\u3001\u4e3b\u9898\u3001\u5b9e\u4f53\u3001\u8981\u70b9"
                   "\uff0c\u4ee5\u53ca <code>source_hash</code> \u6307\u7eb9\u3002"],
                  ["<code>intent</code>",
                   "\u751f\u6210\u7684\u5019\u9009\u67e5\u8be2\uff0c\u4ee5\u53ca\u5b83"
                   "\u6709\u6ca1\u6709\u8fc7\u4e86\u300c\u80fd\u641c\u56de\u6765\u300d"
                   "\u7684\u8fc7\u6ee4\u3002"],
                  ["<code>vec_content</code> / <code>vec_intent</code>",
                   "sqlite-vec \u865a\u62df\u8868\uff0c\u5b58\u7a20\u5bc6\u5411\u91cf"
                   "\u3002"],
                  ["<code>fts_tri</code> / <code>fts_seg</code>",
                   "\u4e24\u4e2a FTS5 \u7d22\u5f15\uff1a\u5b57\u7b26\u4e09\u5143\u7ec4"
                   "\u548c\u8bcd\u6bb5\u3002"],
                  ["<code>session</code> / <code>bookmark_session</code>",
                   "\u91cd\u5efa\u51fa\u6765\u7684\u4fdd\u5b58\u4f1a\u8bdd\u53ca\u5176"
                   "\u6210\u5458\u3002"],
                  ["<code>edge</code>",
                   "\u5e26\u7c7b\u578b\u7684\u8fb9\uff1a<code>session</code>\u3001"
                   "<code>semantic</code>\u3001<code>same_domain</code>\u3001"
                   "<code>supersession</code>\u3002"],
                  ["<code>health</code>",
                   "\u94fe\u63a5\u5065\u5eb7\u7ed3\u8bba\uff1a<code>ok</code>\u3001"
                   "<code>gone</code>\u3001<code>drifted</code>\u3001"
                   "<code>soft_gone</code>\u3002"],
                  ["<code>karakeep_doc</code>",
                   "\u6865\u7684\u72b6\u6001\u3002drop \u6389\u5c31\u662f\u5378\u8f7d"
                   "\u3002"],
                  ["<code>meta</code>",
                   "\u5d4c\u5165\u6a21\u578b\u3001\u7ef4\u5ea6\u3001\u540e\u7aef\uff0c"
                   "\u7b2c\u4e00\u6b21\u5efa\u7d22\u5f15\u65f6\u5199\u5165\uff0c\u4e4b"
                   "\u540e\u5f3a\u5236\u6821\u9a8c\u3002"]]),
                ("h3", "\u94fe\u63a5\u5065\u5eb7\u4e0e\u51b7\u5c42"),
                ("cb", "shell",
                 "facetmark health                       # \u5df2\u77e5\u7684\n"
                 "facetmark health --check               # \u771f\u7684\u53bb\u63a2\u7f51"
                 "\u7edc\n"
                 "facetmark health --check --no-save-recovered   # \u53ea\u8bfb\u626b"
                 "\u63cf"),
                ("p",
                 "\u626b\u63cf\u53ef\u4ee5\u7528 DNS-over-HTTPS\u3001Wayback \u53ef\u7528"
                 "\u6027 API \u548c\u4e00\u4e2a\u9605\u8bfb\u4ee3\u7406\uff0c\u6765\u533a"
                 "\u5206\u300c\u9875\u9762\u6ca1\u4e86\u300d\u548c\u300c\u4f60 DNS \u574f"
                 "\u4e86\u300d\u3002\u5728\u62ff\u8fd9\u4e2a\u5e93\u505a\u4efb\u4f55\u6d4b"
                 "\u91cf\u4e4b\u524d\uff0c\u8bf7\u52a0 "
                 "<code>--no-save-recovered</code>\uff0c\u8ba9\u626b\u63cf\u9664\u4e86"
                 "\u5065\u5eb7\u65e5\u5fd7\u4e4b\u5916\u4fdd\u6301\u53ea\u8bfb\u3002"),
                ("callout", "bad",
                 "\u4e00\u4e2a\u5df2\u77e5\u7684\u3001\u800c\u4e14\u627f\u91cd\u7684 bug",
                 "<p>\u51b7\u5c42\u628a\u300cURL \u6b7b\u4e86\u300d\u5f53\u6210\u300c\u5b58"
                 "\u4e0b\u6765\u7684\u526f\u672c\u6ca1\u7528\u4e86\u300d\uff0c\u8fd9\u662f"
                 "\u9519\u7684\uff1afacetmark \u5b58\u4e86\u6b63\u6587\u3002URL \u6b7b\u4e86"
                 "\u6070\u6070\u662f\u672c\u5730\u5feb\u7167<em>\u6700</em>\u503c\u94b1"
                 "\u7684\u65f6\u5019\u3002\u73b0\u5728\u8fd8\u6ca1\u4fee\uff0c\u56e0\u4e3a"
                 "\u5728\u51fa\u5382 profile \u4e0b\u53e6\u4e00\u4e2a\u610f\u5916\u8ba9"
                 "\u8fd9\u4e2a\u964d\u6743\u6839\u672c\u6ca1\u673a\u4f1a\u6267\u884c\uff0c"
                 "\u800c\u53ea\u62c6\u6389\u5176\u4e2d\u4efb\u4e00\u4e2a\uff0c\u7ed3\u679c"
                 "\u4f1a\u5b9e\u6d4b\u53d8\u5dee 1.46pp\u3002"
                 "<a href=\"measured.zh.html#decay\">\u5b8c\u6574\u7684\u6545\u4e8b</a>"
                 "\u3002</p>"),
            ],
        ),
        (
            "env",
            "\u5168\u90e8\u914d\u7f6e\u9879",
            [
                ("p",
                 "\u4f5c\u4e3a\u73af\u5883\u53d8\u91cf\u65f6\uff0c\u6bcf\u4e2a\u540d\u5b57"
                 "\u524d\u9762\u52a0 <code>FACETMARK_</code>\uff1b\u653e\u5728 "
                 "<code>.env</code> \u91cc\u4e5f\u4e00\u6837\u3002\u4e0b\u9762\u7684\u9ed8"
                 "\u8ba4\u503c\u5c31\u662f\u51fa\u5382\u503c\u3002"),
                ("h3", "\u5b58\u50a8"),
                ("table",
                 ["\u914d\u7f6e\u9879", "\u9ed8\u8ba4", "\u8bf4\u660e"],
                 [["<code>DATA_DIR</code>", "\u6309\u7cfb\u7edf",
                   "\u89c1<a href=\"#install\">\u5b89\u88c5</a>\u3002"],
                  ["<code>DB_NAME</code>", "<code>facetmark.db</code>", ""],
                  ["<code>PRIVACY_EXCLUDED_DOMAINS</code>", "\u7a7a",
                   "\u4e0d\u5bfc\u5165\u3001\u4e0d\u6293\u3001\u4e0d\u5d4c\u5165\u3002"]]),
                ("h3", "\u6a21\u578b\u63a5\u5165"),
                ("table",
                 ["\u914d\u7f6e\u9879", "\u9ed8\u8ba4", "\u8bf4\u660e"],
                 [["<code>API_KEY</code>", "\u7a7a",
                   "\u7a7a\u662f\u5408\u6cd5\u7684\uff0c\u4ee3\u4ef7\u662f\u5931\u53bb"
                   "\u5185\u5bb9\u9762\u548c\u610f\u56fe\u9762\u3002"],
                  ["<code>BASE_URL</code>",
                   "<code>https://api.openai.com/v1</code>",
                   "\u5fc5\u987b\u4ee5 <code>/v1</code> \u7ed3\u5c3e\u3002"],
                  ["<code>CHAT_MODEL</code>", "<code>gpt-4o-mini</code>", ""],
                  ["<code>CHAT_MODEL_FALLBACKS</code>", "\u7a7a",
                   "\u9017\u53f7\u5206\u9694\u3002\u9ed8\u8ba4\u4e3a\u7a7a\u662f\u6545"
                   "\u610f\u7684\u3002"],
                  ["<code>EMBED_MODEL</code>",
                   "<code>text-embedding-3-small</code>", ""],
                  ["<code>EMBED_DIM</code>", "<code>1536</code>",
                   "\u5199\u8fdb <code>meta</code>\uff0c\u5bf9\u4e0d\u4e0a\u5c31\u62a5"
                   "\u9519\u3002"],
                  ["<code>EMBED_BACKEND</code>", "<code>endpoint</code>",
                   "\u6216 <code>local</code>\u3002"],
                  ["<code>REQUEST_TIMEOUT</code>", "<code>60.0</code>", "\u79d2\u3002"],
                  ["<code>MAX_RETRIES</code>", "<code>3</code>", ""],
                  ["<code>USE_MOCK_PROVIDER</code>", "<code>false</code>",
                   "\u786e\u5b9a\u6027\u79bb\u7ebf provider\u3002"]]),
                ("h3", "\u672c\u5730\u5d4c\u5165"),
                ("table",
                 ["\u914d\u7f6e\u9879", "\u9ed8\u8ba4", "\u8bf4\u660e"],
                 [["<code>LOCAL_EMBED_PATH</code>", "\u7a7a",
                   "\u7a7a\u5c31\u4e0b\u8f7d\u3002"],
                  ["<code>LOCAL_EMBED_DEVICE</code>", "<code>cpu</code>", ""],
                  ["<code>LOCAL_EMBED_BATCH</code>", "<code>8</code>", ""],
                  ["<code>LOCAL_EMBED_MAX_SEQ</code>", "<code>1024</code>",
                   "\u8c03\u4f4e\u4f1a\u635f\u5931\u53ef\u91cd\u73b0\u6027 \u2014\u2014 "
                   "\u89c1<a href=\"#models\">\u6a21\u578b\u63a5\u5165</a>\u3002"]]),
                ("h3", "\u6293\u53d6"),
                ("table",
                 ["\u914d\u7f6e\u9879", "\u9ed8\u8ba4", "\u8bf4\u660e"],
                 [["<code>FETCH_CONCURRENCY</code>", "<code>30</code>", "\u5168\u5c40"
                   "\u3002"],
                  ["<code>FETCH_PER_HOST_CONCURRENCY</code>", "<code>2</code>",
                   "\u793c\u8c8c\uff0c\u4e0d\u662f\u6027\u80fd\u3002"],
                  ["<code>FETCH_PER_HOST_MIN_INTERVAL</code>", "<code>0.5</code>",
                   "\u540c\u4e00\u4e3b\u673a\u4e24\u6b21\u8bf7\u6c42\u7684\u79d2\u6570"
                   "\u95f4\u9694\u3002"],
                  ["<code>FETCH_TIMEOUT</code>", "<code>15.0</code>", ""],
                  ["<code>RESPECT_ROBOTS</code>", "<code>true</code>", ""],
                  ["<code>ROBOTS_ON_ERROR</code>", "<code>allow</code>",
                   "robots.txt \u8bfb\u4e0d\u5230\u65f6\u600e\u4e48\u529e\u3002"],
                  ["<code>ROBOTS_MAX_CRAWL_DELAY</code>", "<code>5.0</code>",
                   "\u5bf9\u5bf9\u65b9\u58f0\u660e\u7684 crawl delay \u5c01\u9876\u3002"],
                  ["<code>MIN_BODY_CHARS</code>", "<code>200</code>",
                   "\u4f4e\u4e8e\u6b64\u6570\u7b97\u65e0\u6b63\u6587\u3002"],
                  ["<code>BODY_TRUNCATE_CHARS</code>", "<code>6000</code>", ""],
                  ["<code>USER_AGENT</code>",
                   "\u5199\u660e\u81ea\u5df1\u662f facetmark", ""]]),
                ("h3", "\u5bcc\u5316\u4e0e\u610f\u56fe"),
                ("table",
                 ["\u914d\u7f6e\u9879", "\u9ed8\u8ba4", "\u8bf4\u660e"],
                 [["<code>ENRICH_CONCURRENCY</code>", "<code>4</code>", ""],
                  ["<code>INTENT_GENERATE_N</code>", "<code>8</code>",
                   "\u6bcf\u9875\u751f\u6210\u591a\u5c11\u5019\u9009\u3002"],
                  ["<code>INTENT_KEEP_N</code>", "<code>4</code>",
                   "\u6bcf\u9875\u6700\u591a\u7559\u591a\u5c11\u3002"],
                  ["<code>INTENT_PROBE_TOP_K</code>", "<code>10</code>",
                   "\u300c\u80fd\u4e0d\u80fd\u641c\u56de\u6765\u300d\u770b\u591a\u6df1"
                   "\u3002"]]),
                ("h3", "\u4f1a\u8bdd\u3001\u68c0\u7d22\u4e0e\u8870\u51cf"),
                ("table",
                 ["\u914d\u7f6e\u9879", "\u9ed8\u8ba4", "\u8bf4\u660e"],
                 [["<code>SESSION_EPS_MINUTES</code>", "\u81ea\u52a8",
                   "\u4e0d\u8bbe\u65f6\uff0c\u95f4\u9694\u7531\u8986\u76d6\u7387 \u00d7 "
                   "\u7eaf\u5ea6\u63d0\u5347\u5728\u7f51\u683c\u4e0a\u9009\u3002"],
                  ["<code>SESSION_EPS_GRID_MINUTES</code>",
                   "<code>5\u2026240</code>", "\u641c\u7d22\u7684\u7f51\u683c\u3002"],
                  ["<code>RRF_K</code>", "<code>60</code>",
                   "<code>w / (k + rank)</code> \u91cc\u7684 <code>k</code>\u3002"],
                  ["<code>CANDIDATES_PER_FACET</code>", "<code>50</code>", ""],
                  ["<code>GRAPH_EXPAND_HOPS</code>", "<code>1</code>", ""],
                  ["<code>GRAPH_EXPAND_FACTOR</code>", "<code>0.6</code>", ""],
                  ["<code>DECAY_FACTOR</code>", "<code>0.5</code>", ""],
                  ["<code>DECAY_AGE_DAYS</code>", "<code>365</code>", ""],
                  ["<code>DECAY_RESCUE_THRESHOLD</code>", "<code>0.02</code>",
                   "\u6539\u5b83\u4e4b\u524d\u5148\u770b<a href=\"measured.zh.html#decay\">"
                   "\u8870\u51cf\u5c42\u5b9e\u6d4b</a>\u3002"]]),
                ("h3", "\u94fe\u63a5\u5065\u5eb7\u4e0e\u670d\u52a1"),
                ("table",
                 ["\u914d\u7f6e\u9879", "\u9ed8\u8ba4", "\u8bf4\u660e"],
                 [["<code>HEALTH_ENABLE_EXTERNAL</code>", "<code>true</code>",
                   "\u7f51\u7edc\u63a2\u6d4b\u603b\u5f00\u5173\u3002"],
                  ["<code>HEALTH_ENABLE_DOH</code>", "<code>true</code>",
                   "DNS-over-HTTPS\u3002"],
                  ["<code>HEALTH_ENABLE_WAYBACK</code>", "<code>true</code>", ""],
                  ["<code>HEALTH_ENABLE_READER</code>", "<code>true</code>", ""],
                  ["<code>HEALTH_SOFT_GONE_LENGTH_RATIO</code>",
                   "<code>0.30</code>",
                   "\u6b63\u6587\u7f29\u5230\u8fd9\u4e2a\u6bd4\u4f8b \u21d2 "
                   "<code>soft_gone</code>\u3002"],
                  ["<code>HEALTH_GONE_CONFIRM_DAYS</code>", "<code>7</code>", ""],
                  ["<code>HEALTH_PROXY_URL</code>", "\u672a\u8bbe", ""],
                  ["<code>HOST</code>", "<code>127.0.0.1</code>", ""],
                  ["<code>PORT</code>", "<code>8787</code>", ""]]),
            ],
        ),
        (
            "commands",
            "\u5168\u90e8\u547d\u4ee4",
            [
                ("p",
                 "\u6bcf\u6761\u547d\u4ee4\u90fd\u6709 <code>--db</code>\uff0c\u53ef\u4ee5"
                 "\u6307\u5411\u5177\u4f53\u7684\u6570\u636e\u5e93\u6587\u4ef6\u6216\u6570"
                 "\u636e\u76ee\u5f55\u3002\u5927\u90e8\u5206\u90fd\u652f\u6301 "
                 "<code>--json</code>\u3002"),
                ("table",
                 ["\u547d\u4ee4", "\u4f5c\u7528", "\u503c\u5f97\u4e00\u63d0\u7684\u53c2\u6570"],
                 [["<code>version</code>", "\u6253\u5370\u7248\u672c\u3002", ""],
                  ["<code>browsers</code>",
                   "\u5217\u51fa\u53ef\u5bfc\u5165\u7684\u6d3b\u6d4f\u89c8\u5668\u914d"
                   "\u7f6e\u3002", "<code>--json</code>"],
                  ["<code>import [PATH]</code>",
                   "\u5bfc\u5165 Netscape HTML \u6216 Chrome JSON\u3002\u4e0d\u5e26\u8def"
                   "\u5f84\u65f6\u81ea\u52a8\u627e\u6d3b\u914d\u7f6e\u3002\u4ece\u4e0d"
                   "\u5199\u56de\u3002", ""],
                  ["<code>migrate</code>",
                   "\u628a schema \u5347\u5230\u5f53\u524d\u6784\u5efa\u9700\u8981\u7684"
                   "\u7248\u672c\u3002",
                   "<code>--check</code>\u3001<code>--no-backup</code>"],
                  ["<code>index</code>",
                   "\u6293\u53d6\u3001\u5bcc\u5316\u3001\u5d4c\u5165\u3001\u610f\u56fe"
                   "\u3001\u4f1a\u8bdd\u3001\u8fb9\u3002",
                   "<code>--no-fetch</code>\u3001<code>--limit</code>\u3001"
                   "<code>--force</code>\u3001<code>--mock</code>"],
                  ["<code>reindex</code>",
                   "\u4ece\u4e66\u7b7e\u91cd\u5efa\u6240\u6709\u884d\u751f\u4ea7\u7269"
                   "\u3002", "<code>--mock</code>"],
                  ["<code>search QUERY</code>", "\u641c\u5e93\u3002",
                   "<code>-n</code>\u3001<code>--quick</code>\u3001"
                   "<code>--config</code>\u3001<code>--explain</code>"],
                  ["<code>show ID</code>", "\u628a\u4e00\u6761\u4e66\u7b7e\u6253\u6210 "
                   "JSON\u3002", "<code>--body</code>"],
                  ["<code>sessions</code>", "\u5217\u51fa\u4fdd\u5b58\u4f1a\u8bdd\u3002",
                   "<code>-n</code>"],
                  ["<code>health</code>",
                   "\u94fe\u63a5\u5065\u5eb7\uff0c\u4ee5\u53ca\u8870\u51cf\u5c42\u5230"
                   "\u5e95\u770b\u4e0d\u770b\u5f97\u89c1\u5b83\u3002",
                   "<code>--check</code>\u3001<code>--no-external</code>\u3001"
                   "<code>--no-save-recovered</code>"],
                  ["<code>stats</code>", "\u7d22\u5f15\u89c4\u6a21\u4e0e\u8986\u76d6"
                   "\u7387\u3002", ""],
                  ["<code>token</code>", "\u6253\u5370\u6269\u5c55\u8981\u7684\u914d\u5bf9"
                   "\u4ee4\u724c\u3002", "<code>--rotate</code>"],
                  ["<code>serve</code>", "\u8dd1\u672c\u5730 HTTP \u670d\u52a1\u3002",
                   "<code>--host</code>\u3001<code>--port</code>\u3001"
                   "<code>--mock</code>"],
                  ["<code>mcp</code>", "\u5728 stdio \u4e0a\u8dd1 MCP \u670d\u52a1\u5668"
                   "\u3002", "<code>--mock</code>"],
                  ["<code>demo</code>",
                   "\u79bb\u7ebf\u9020\u4e00\u4e2a\u5408\u6210\u5e93\u5e76\u641c\u5b83"
                   "\u3002", "<code>--size</code>\u3001<code>--keep</code>"],
                  ["<code>eval</code>",
                   "\u8dd1\u68c0\u7d22\u8bc4\u6d4b\uff0c\u53ef\u4ee5\u662f A\u2013E "
                   "\u6d88\u878d\u3002",
                   "<code>--ablation</code>\u3001<code>--rungs</code>\u3001"
                   "<code>--queries</code>\u3001<code>--bootstrap</code>\u3001"
                   "<code>--out</code>"]]),
                ("h3", "\u8dd1\u4f60\u81ea\u5df1\u7684\u8bc4\u6d4b"),
                ("p",
                 "\u8fd9\u662f facetmark \u6700\u91cd\u8981\u3001\u4e5f\u662f\u81f3\u4eca"
                 "\u6ca1\u6709\u7b2c\u4e8c\u4e2a\u4eba\u7528\u8fc7\u7684\u90e8\u5206\u3002"
                 "\u7ed9\u5b83\u4e00\u4e2a "
                 "<code>{text, qtype, target_url}</code> \u7684 JSONL\uff0c\u5b83\u5c31"
                 "\u80fd\u5728\u4f60\u81ea\u5df1\u7684\u5e93\u4e0a\u8dd1\u4efb\u610f\u4e00"
                 "\u7ec4\u6863\u4f4d\uff0c\u7ed9\u51fa bootstrap \u7f6e\u4fe1\u533a\u95f4"
                 "\u548c\u914d\u5bf9\u5dee\u5f02\u7684 McNemar \u68c0\u9a8c\u3002"),
                ("cb", "shell",
                 "facetmark eval --no-build \\\n"
                 "  --queries my-queries.jsonl \\\n"
                 "  --rungs A,C,full \\\n"
                 "  --bootstrap 10000 --concurrency 4 \\\n"
                 "  --out report.json"),
                ("callout", "warn",
                 "\u5e76\u53d1\u4f1a\u6467\u6bc1\u5ef6\u8fdf\u6570\u5b57",
                 "<p><code>--concurrency &gt; 1</code> \u4f1a\u8ba9 p50 \u548c p95 \u5931"
                 "\u53bb\u610f\u4e49\u3002\u8981\u8d28\u91cf\u6570\u5b57\u65f6\u7528\u5b83"
                 "\uff0c\u8981\u5ef6\u8fdf\u5c31\u62bd\u4e00\u4e2a\u5b50\u96c6\u5728\u5e76"
                 "\u53d1 1 \u4e0b\u91cd\u8dd1\u3002</p>"),
            ],
        ),
        (
            "trouble",
            "\u6392\u9519",
            [
                ("h3", "\u6bcf\u6b21\u6a21\u578b\u8c03\u7528\u90fd\u8fd4\u56de 404"),
                ("p",
                 "base URL \u6f0f\u4e86 <code>/v1</code>\u3002\u8fd9\u662f\u5dee\u8ddd"
                 "\u5f88\u5927\u7684\u7b2c\u4e00\u540d\u914d\u7f6e\u5931\u8d25\uff0c\u800c"
                 "\u4e14\u9519\u8bef\u4ee5 provider error \u7684\u5f62\u5f0f\u5192\u51fa"
                 "\u6765\uff0c\u770b\u8d77\u6765\u5f88\u50cf\u5bc6\u94a5\u4e0d\u5bf9\u3002"),
                ("h3", "\u5efa\u7d22\u5f15\u6216\u641c\u7d22\u65f6\u62a5\u300c\u7ef4\u5ea6"
                       "\u4e0d\u5339\u914d\u300d"),
                ("p",
                 "\u7b2c\u4e00\u6b21\u5efa\u5e93\u65f6\u8bb0\u5728 <code>meta</code> "
                 "\u91cc\u7684\u5d4c\u5165\u7ef4\u5ea6\uff0c\u548c\u5f53\u524d\u7684 "
                 "<code>FACETMARK_EMBED_DIM</code> \u5bf9\u4e0d\u4e0a\u4e86\u3002"
                 "facetmark \u5b81\u53ef\u62a5\u9519\u4e5f\u4e0d\u6df7\u7ef4\u5ea6\u3002"
                 "\u8981\u4e48\u6539\u56de\u53bb\uff0c\u8981\u4e48\u7528 "
                 "<code>facetmark index --force</code> \u91cd\u7b97\u5168\u90e8\u5411\u91cf"
                 "\u3002"),
                ("h3", "\u5bcc\u5316\u9759\u6084\u6084\u5730\u4ec0\u4e48\u4e5f\u6ca1\u505a"),
                ("p",
                 "\u5b58\u7740\u7684 <code>source_hash</code> \u5df2\u7ecf\u7b49\u4e8e"
                 "\u5f53\u524d\u6b63\u6587\u54c8\u5e0c\uff0c\u6307\u7eb9\u8ba4\u4e3a\u6d3b"
                 "\u5e72\u5b8c\u4e86\u3002\u8fd9\u662f\u6b63\u786e\u884c\u4e3a\uff0c"
                 "<code>facetmark index --force</code> \u53ef\u4ee5\u8986\u76d6\u5b83"
                 "\u3002"),
                ("h3", "\u5411\u91cf\u6709\uff0c\u4f46\u7ed3\u679c\u5f88\u5dee"),
                ("p",
                 "\u901a\u5e38\u662f\u5411\u91cf\u5199\u5b8c\u4e4b\u540e\u5d4c\u5165\u6587"
                 "\u672c\u53c8\u53d8\u4e86 \u2014\u2014 \u6bd4\u5982\u5bcc\u5316\u88ab"
                 "\u4e00\u5ea7\u6865\u8986\u5199\u4e86\u3002\u7528 "
                 "<code>facetmark index --force</code> \u91cd\u7b97\u3002\u5982\u679c\u662f"
                 "\u4e00\u4e2a\u5168\u65b0\u7684\u7d22\u5f15\u5c31\u5dee\uff0c\u5148\u786e"
                 "\u8ba4\u81ea\u5df1\u662f\u4e0d\u662f\u4e0d\u5c0f\u5fc3\u8dd1\u5728 mock "
                 "provider \u4e0a\uff1a<code>facetmark stats</code> \u4f1a\u62a5\u5f53"
                 "\u524d\u7528\u7684\u5d4c\u5165\u6a21\u578b\u3002"),
                ("h3", "SQLite \u62a5 <code>disk I/O error</code>"),
                ("p",
                 "SQLite \u5728\u67d0\u4e9b\u7f51\u7edc\u6587\u4ef6\u7cfb\u7edf\u548c FUSE "
                 "\u4e0a\u8dd1\u4e0d\u7a33\u3002\u7528 "
                 "<code>FACETMARK_DATA_DIR</code> \u628a\u6570\u636e\u76ee\u5f55\u6362"
                 "\u5230\u672c\u5730\u78c1\u76d8\u3002"),
                ("h3", "\u6293\u5f97\u5f88\u6162\uff0c\u6216\u8005\u9875\u9762\u662f\u7a7a\u7684"),
                ("p",
                 "\u4e24\u4e2a\u901a\u5e38\u90fd\u662f\u6545\u610f\u7684\u3002\u9075\u5b88 "
                 "robots.txt\uff0c\u5355\u4e3b\u673a\u5e76\u53d1\u5c01\u9876 2\uff0c"
                 "\u4e24\u6b21\u8bf7\u6c42\u4e4b\u95f4\u8fd8\u6709\u6700\u5c0f\u95f4\u9694"
                 "\u3002\u6709\u4e9b\u7ad9\u5c31\u662f\u4e0d\u7ed9\u3002\u6ca1\u6b63\u6587"
                 "\u7684\u9875\u9762\u7167\u6837\u5efa\u7d22\u5f15 \u2014\u2014 \u7ba1\u7ebf"
                 "\u4f1a\u9000\u5230\u53ea\u7528\u6807\u9898\u7684\u6307\u7eb9 \u2014"
                 "\u2014 \u53ea\u662f\u5f31\u4e00\u4e9b\u3002\u60f3\u8981\u5feb\u800c\u6d45"
                 "\u7684\u7d22\u5f15\uff0c\u7528 <code>--no-fetch</code>\u3002"),
                ("h3", "\u6269\u5c55\u8fde\u4e0d\u4e0a\u670d\u52a1"),
                ("p",
                 "\u6309\u987a\u5e8f\u67e5\u4e09\u4ef6\u4e8b\uff1a"
                 "<code>facetmark serve</code> \u771f\u7684\u5728\u8dd1\u5417\uff1b\u8bbe"
                 "\u7f6e\u91cc\u7684 endpoint \u548c\u5b83\u5b9e\u9645\u76d1\u542c\u7684"
                 "\u4e3b\u673a\u7aef\u53e3\u5bf9\u5f97\u4e0a\u5417\uff1b\u8bbe\u7f6e\u91cc"
                 "\u7684\u4ee4\u724c\u548c <code>facetmark token</code> \u4e00\u81f4\u5417"
                 "\u3002\u8f6e\u6362\u8fc7\u4ee4\u724c\u7684\u8bdd\uff0c\u6269\u5c55\u8981"
                 "\u62ff\u65b0\u7684\u3002"),
                ("h3", "\u5176\u4ed6"),
                ("p",
                 "<code>facetmark stats</code> \u548c "
                 "<code>facetmark health</code> \u4f1a\u628a\u7d22\u5f15\u91cc\u5230\u5e95"
                 "\u6709\u4ec0\u4e48\u6253\u51fa\u6765\uff0c\u5927\u90e8\u5206\u56f0\u60d1"
                 "\u5230\u8fd9\u5c31\u89e3\u4e86\u3002\u5b9e\u5728\u4e0d\u884c\u5c31"
                 "<a href=\"" + REPO + "/issues\">\u63d0\u4e2a issue</a> \u2014\u2014 "
                 "\u6700\u6709\u7528\u7684\u662f\u628a\u51fa\u9519\u90a3\u6761\u547d\u4ee4"
                 "\u7684 <code>--json</code> \u8f93\u51fa\u8d34\u4e0a\u6765\u3002"),
            ],
        ),
    ],
}

# ---------------------------------------------------------------- 实测 ----

ZH["measured"] = {
    "h1": "\u5b9e\u6d4b\u5230\u4e86\u4ec0\u4e48",
    "lede": (
        "\u4e5d\u4e2a\u7ed3\u679c\u3002\u5176\u4e2d\u56db\u4e2a\u6740\u6b7b\u4e86\u5b83\u4eec"
        "\u81ea\u5df1\u8981\u8bc1\u660e\u7684\u90a3\u4e2a\u529f\u80fd\uff0c\u4e00\u4e2a\u63a8"
        "\u7ffb\u4e86\u540c\u4e00\u4e2a\u9879\u76ee\u91cc\u65e9\u5148\u7684\u7ed3\u8bba"
        "\uff0c\u8fd8\u6709\u4e00\u4e2a\u6839\u672c\u6ca1\u6709\u7ed3\u8bba \u2014\u2014 "
        "\u56e0\u4e3a\u6837\u672c\u592a\u5c0f\u3002\u5b83\u4eec\u90fd\u5728\u8fd9\u91cc"
        "\uff0c\u7406\u7531\u76f8\u540c\uff1a\u4e00\u6761\u6ca1\u6709\u534f\u8bae\u7684"
        "\u68c0\u7d22\u7ed3\u8bba\uff0c\u53ea\u662f\u4e00\u79cd\u504f\u597d\u3002"
    ),
    "toc_title": "\u7ed3\u679c",
    "sections": [
        (
            "how",
            "\u600e\u4e48\u8bfb\u8fd9\u4e00\u9875",
            [
                ("ul",
                 ["<b>\u9884\u6ce8\u518c\u3002</b>\u6807\u51c6\u5728\u8dd1\u4e4b\u524d"
                  "\u5199\u597d\u3002\u4e00\u4e2a\u5728\u201c\u6fc0\u53d1\u5b83\u7684\u90a3"
                  "\u6279\u67e5\u8be2\u201d\u4e0a\u6d4b\u51fa\u6765\u7684\u6863\u4f4d\u662f"
                  "\u5047\u8bbe\uff0c\u4e0d\u662f\u7ed3\u679c\uff0c\u4f1a\u88ab\u6807\u4e3a"
                  "\u63a2\u7d22\u6027\u3002",
                  "<b>\u914d\u5bf9\u68c0\u9a8c\u3002</b>\u6bcf\u4e00\u6761 A \u5bf9 B "
                  "\u7684\u7ed3\u8bba\u90fd\u5728\u540c\u4e00\u6279\u67e5\u8be2\u4e0a\u914d"
                  "\u5bf9\uff0c\u5e26 bootstrap \u7f6e\u4fe1\u533a\u95f4\u548c\u5bf9\u4e0d"
                  "\u4e00\u81f4\u5bf9\u7684 McNemar \u68c0\u9a8c\u3002\u80dc\u548c\u8d1f"
                  "\u5206\u5f00\u62a5 \u2014\u2014 \u201c0 \u53d8\u5316\u5f97\u5230\u7684"
                  "\u51c0\u96f6\u201d\u548c\u201c40 \u80dc 40 \u8d1f\u5f97\u5230\u7684\u51c0"
                  "\u96f6\u201d\u662f\u4e24\u4ef6\u4e8b\u3002",
                  "<b>\u4e0d\u91cd\u5f00\u3002</b>\u67e5\u8be2\u96c6\u4e00\u65e6\u51bb"
                  "\u7ed3\u3001\u7ed3\u8bba\u4e00\u65e6\u8bb0\u5f55\uff0c\u5c31\u7b97"
                  "\u6570\u3002\u65b0\u95ee\u9898\u8981\u65b0\u67e5\u8be2\u96c6\u3002",
                  "<b>pp</b> \u662f\u767e\u5206\u70b9\u3002<b>CI95</b> \u662f 95% "
                  "bootstrap \u533a\u95f4\u3002"]),
                ("callout", "warn",
                 "\u6700\u5927\u7684\u4e00\u6761\u4fdd\u7559\uff0c\u653e\u5728\u6700\u524d"
                 "\u9762\u8bf4\u4e00\u6b21",
                 "<p>\u8fd9\u4e00\u9875\u4e0a\u6bcf\u4e00\u5957\u67e5\u8be2\u96c6\u90fd"
                 "\u662f\u5de5\u5177\u4f5c\u8005\u81ea\u5df1\u5199\u7684\u3002bootstrap "
                 "\u4fee\u7684\u662f\u62bd\u6837\u566a\u58f0\uff0c\u5bf9\u201c\u4f5c\u8005"
                 "\u77e5\u9053\u5de5\u5177\u64c5\u957f\u4ec0\u4e48\u201d\u8fd9\u4ef6\u4e8b"
                 "\u4e00\u70b9\u529e\u6cd5\u90fd\u6ca1\u6709\u3002\u8fd9\u4e2a\u9879\u76ee"
                 "\u6700\u9700\u8981\u7684\u8d21\u732e\uff0c\u662f\u4e00\u5957\u522b\u4eba"
                 "\u5199\u7684\u67e5\u8be2\u96c6\u3002</p>"),
            ],
        ),
        (
            "w1",
            "W1 \u00b7 \u56db\u9762\u878d\u5408\u8f93\u7ed9\u4e86\u5355\u4e00\u4e2a\u9762",
            [
                ("raw", "<p><span class=\"badge fail\">\u9ed8\u8ba4\u5df2\u64a4</span> "
                        "<span class=\"tiny\">479 \u6761\u67e5\u8be2 \u00b7 \u4e00\u4e2a"
                        "\u771f\u5b9e\u7684 1,700 \u6761\u4e66\u7b7e\u5e93 \u00b7 \u9884"
                        "\u6ce8\u518c</span></p>"),
                ("p",
                 "\u6574\u4e2a\u9879\u76ee\u7684\u524d\u63d0\u5c31\u662f\u300c\u56db\u4e2a"
                 "\u9762\u878d\u5408\u6bd4\u4efb\u4f55\u5355\u4e00\u4e2a\u90fd\u5f3a\u300d"
                 "\u3002\u4e09\u6761\u6807\u51c6\u5728\u8dd1\u4e4b\u524d\u5c31\u5199\u597d"
                 "\u4e86\u3002\u4e09\u6761\u5168\u6ca1\u8fbe\u5230\u3002"),
                ("table",
                 ["\u6863", "\u9762", "Recall@5", "Recall@1", "MRR@10", "p50"],
                 [["<b>A</b>", "\u53ea\u7528\u5185\u5bb9\u5411\u91cf",
                   "<b>0.643</b>", "0.505", "0.564", "<b>148 ms</b>"],
                  ["<b>B</b>", "\uff0b\u4e24\u4e2a\u8bcd\u9762", "0.589", "\u2014",
                   "\u2014", "189 ms"],
                  ["<b>C</b>", "\u56db\u9762\u5168\u4e0a", "0.635", "\u2014", "\u2014",
                   "526 ms"],
                  ["<b>D</b>", "\uff0b\u4e0a\u4e0b\u6587\uff0b\u56fe", "0.639",
                   "\u2014", "\u2014", "523 ms"]],
                 [0]),
                ("p",
                 "\u878d\u5408\u4ed8\u51fa\u4e86 <b>5.4pp</b> \u7684 Recall@5\uff0c\u5e76"
                 "\u4e14\u6162\u4e86 <b>3.5 \u500d</b>\u3002A \u6863\u5206\u7c7b\u578b"
                 "\u770b\uff1a\u5185\u5bb9\u578b <b>0.959</b>\u3001\u6a21\u7cca\u578b "
                 "<b>0.706</b>\u3001\u60c5\u666f\u578b <b>0.279</b>\u3002"),
                ("h3", "\u5b83\u4e3a\u4ec0\u4e48\u8f93"),
                ("p",
                 "\u5e73\u6743\u91cd\u7684 RRF \u6ca1\u6709\u4efb\u4f55\u8868\u8fbe\u300c"
                 "\u6709\u591a\u786e\u5b9a\u300d\u7684\u624b\u6bb5\u3002\u4e24\u4e2a\u5f31"
                 "\u9762\u78b0\u5de7\u4e00\u81f4\uff0c\u5f97 0.0279\uff1b\u4e00\u4e2a\u5f3a"
                 "\u9762\u975e\u5e38\u786e\u5b9a\uff0c\u5f97 0.0164\u3002\u78b0\u5de7\u8d62"
                 "\u4e86\u3002\u8fd9\u4e0d\u662f\u8c03\u53c2\u95ee\u9898\uff0c\u8fd9\u5c31"
                 "\u662f\u516c\u5f0f\u672c\u8eab\u7684\u884c\u4e3a\u3002"),
                ("h3", "\u540c\u4e00\u8f6e\u91cc\u6d3b\u4e0b\u6765\u7684"),
                ("table",
                 ["\u5e78\u5b58\u8005", "\u6548\u679c", "\u80dc / \u8d1f", "p",
                  "\u4ee3\u4ef7"],
                 [["\u56fe\u6269\u5c55\u4f5c\u4e3a<em>\u5355\u72ec\u4e00\u7ec4</em>",
                   "<b>+2.09pp</b> Recall@5", "10 / 0", "0.0019", "9 ms"],
                  ["\u91cd\u6392\uff0c\u5bf9 Recall@1",
                   "<b>+4.80pp</b> CI95 [+1.46, +8.35]", "45 / 22", "0.0067",
                   "\u2014"]]),
                ("p",
                 "\u4e24\u4e2a\u90fd\u53d1\u4e86\u51fa\u53bb\u3002\u6ce8\u610f\u56fe\u6269"
                 "\u5c55\u53ea\u5728\u4f5c\u4e3a<em>\u8865\u5145</em>\u65f6\u6210\u7acb "
                 "\u2014\u2014 \u5355\u72ec\u6210\u7ec4\u8fd4\u56de\uff0c\u4e0d\u5408\u8fdb"
                 "\u6392\u540d\u3002"),
            ],
        ),
        (
            "gate",
            "W2/W3 \u00b7 \u60c5\u666f\u95e8\u5148\u53d1\u4e86\uff0c\u540e\u6765\u8f93\u4e86",
            [
                ("raw", "<p><span class=\"badge fail\">\u53d1\u51fa\u53bb\u4e4b\u540e"
                        "\u56de\u6eda\u4e86\u9ed8\u8ba4</span></p>"),
                ("p",
                 "\u60c5\u666f\u95e8\u8bc6\u522b\u300c\u548c X \u5dee\u4e0d\u591a\u65f6"
                 "\u5019\u5b58\u7684\u90a3\u4e2a\u300d\uff0c\u7136\u540e\u628a\u68c0\u7d22"
                 "\u9650\u5236\u5728\u90a3\u4e2a\u4fdd\u5b58\u7a97\u53e3\u5185\u3002\u5728"
                 "\u5b83\u81ea\u5df1\u7684 616 \u6761 holdout \u4e0a\u5b83\u8d62\u5f97\u5f88"
                 "\u5e72\u51c0\uff0c\u6240\u4ee5\u53d1\u4e86\u51fa\u53bb\u3002"),
                ("table",
                 ["\u67e5\u8be2\u96c6", "\u5bf9\u6bd4", "\u0394Recall@5", "CI95",
                  "\u80dc / \u8d1f", "p"],
                 [["616 \u6761 holdout", "A \u2192 A_gatedctx",
                   "<b class=\"nowrap\">+3.09pp</b>", "[1.79, 4.55]", "19 / 0",
                   "3.8e\u22126"],
                  ["361 \u6761\u7cbe\u5ea6\u63a2\u9488", "A \u2192 A_gatedctx",
                   "<b class=\"nowrap\">\u221218.83pp</b>",
                   "[\u221223.27, \u221214.68]", "3 / 71", "\u2014"]]),
                ("p",
                 "\u7b2c\u4e8c\u884c\u662f\u540c\u4e00\u4e2a\u529f\u80fd\uff0c\u53ea\u662f"
                 "\u6362\u4e86\u4e00\u5957\u4e8b\u540e\u624d\u5efa\u7684\u67e5\u8be2\u96c6"
                 "\u53bb\u95ee\u53e6\u4e00\u4e2a\u95ee\u9898\uff1a\u5b83\u5728\u4e0d\u8be5"
                 "\u89e6\u53d1\u7684\u67e5\u8be2\u4e0a\u89e6\u53d1\u4e86\uff0c\u4f1a\u600e"
                 "\u6837\uff1fRecall@5 \u4ece 0.9058 \u6389\u5230 0.7175\uff0cRecall@1 "
                 "\u4ece 0.801 \u6389\u5230 0.363\u3002"),
                ("h3", "\u5206\u5c42\u4e00\u770b\u5c31\u5168\u660e\u767d\u4e86"),
                ("table",
                 ["\u5206\u5c42", "n", "\u0394Recall@5"],
                 [["\u4fdd\u5b58\u7a97\u53e3\u91cc\u786e\u5b9e\u6709\u76ee\u6807", "57",
                   "<b>+0.00pp</b> \u2014\u2014 \u6070\u597d\u662f\u96f6"],
                  ["\u4fdd\u5b58\u7a97\u53e3\u91cc\u6ca1\u6709\u76ee\u6807", "304",
                   "<b class=\"nowrap\">\u221222.37pp</b>"]]),
                ("p",
                 "\u95e8\u5bf9\u7684\u65f6\u5019\uff0c\u5b83\u4ec0\u4e48\u90fd\u4e0d\u52a0"
                 "\u3002\u95e8\u9519\u7684\u65f6\u5019\uff0c\u5b83\u628a\u7b54\u6848\u6254"
                 "\u4e86\u3002\u7ed3\u8bba "
                 "<code>gate_precision_unqualified</code>\uff0c\u9ed8\u8ba4\u56de\u6eda"
                 "\u5230\u4e0d\u52a0\u95e8\u3002"),
                ("callout", "info",
                 "gate_v2 \u5199\u597d\u4e86\uff0c\u88ab\u6bd9\u4e86",
                 "<p>\u4e00\u4e2a\u66f4\u7a84\u7684\u95e8\u5728\u539f\u6765\u90a3 616 "
                 "\u6761\u4e0a\u62ff\u5230 +1.79pp\uff0c\u5728\u7cbe\u5ea6\u63a2\u9488"
                 "\u4e0a\u662f <b>\u221210.52pp</b>\u3002\u660e\u77e5\u9053\u7b2c\u4e8c"
                 "\u4e2a\u6570\u5b57\u5b58\u5728\u8fd8\u62ff\u7b2c\u4e00\u4e2a\u53d1"
                 "\u8d27\uff0c\u7b49\u4e8e\u6311\u4e86\u4e00\u5957\u80fd\u7ed9\u51fa\u6211"
                 "\u4eec\u60f3\u8981\u7684\u7b54\u6848\u7684\u67e5\u8be2\u96c6\u3002\u6ca1"
                 "\u53d1\u3002</p>"),
            ],
        ),
        (
            "recall",
            "\u95e8\u7684\u53e6\u4e00\u9762 \u00b7 \u65e0\u7ed3\u8bba",
            [
                ("raw", "<p><span class=\"badge warn\">\u4ec5\u63cf\u8ff0 \u00b7 \u4f4e"
                        "\u4e8e\u9884\u6ce8\u518c\u7684\u6837\u672c\u4e0b\u9650</span></p>"),
                ("p",
                 "\u7cbe\u5ea6\u63a2\u9488\u95ee\u7684\u662f\u300c\u5b83\u89e6\u53d1\u4e86"
                 "\u3001\u4f46\u4e0d\u8be5\u89e6\u53d1\u300d\u3002\u8fd9\u4e00\u8f6e\u95ee"
                 "\u53cd\u9762\uff1a\u5b83\u591a\u5c11\u6b21\u8be5\u89e6\u53d1\u5374\u6ca1"
                 "\u89e6\u53d1\uff1f\u534f\u8bae\u5728\u8dd1\u4e4b\u524d\u5c31\u9884\u6ce8"
                 "\u518c\u597d\u4e86\uff0c\u955c\u50cf\u7cbe\u5ea6\u90a3\u4efd\u3002"),
                ("table",
                 ["\u6307\u6807", "\u503c"],
                 [["\u53ef\u7528\u63a2\u9488", "\u51bb\u7ed3\u7684 v3 holdout \u91cc\u7684 "
                   "<b>16</b> \u6761 <code>q_save_action</code>"],
                  ["\u95e8\u89e6\u53d1\u4e86\u51e0\u6b21", "<b>16 \u6761\u91cc 0 \u6761"
                   "</b>"],
                  ["\u6f0f\u68c0\u7387", "<b>100.0%</b>\uff0cWilson CI95 [80.64, 100.00]"],
                  ["\u0394Recall@5\uff08A_gatedctx \u2212 A\uff09",
                   "<b>+0.00pp</b>\uff0cCI95 [0.00, 0.00]"],
                  ["McNemar", "0 \u5f97 0 \u5931\uff0cp = 1.0\uff0c0 \u4e2a\u4e0d\u4e00"
                   "\u81f4\u5bf9"],
                  ["\u534f\u8bae\u81ea\u68c0",
                   "<span class=\"badge pass\">\u901a\u8fc7</span> \u2014\u2014 \u672a"
                   "\u89e6\u53d1\u5b50\u96c6\u5fc5\u987b\u521a\u597d\u52a8 0.00pp\uff0c"
                   "\u5b83\u505a\u5230\u4e86"],
                  ["\u7ed3\u8bba",
                   "<b>\u65e0\u3002</b>16 \u4f4e\u4e8e\u9884\u6ce8\u518c\u7684 25 \u6761"
                   "\u4e0b\u9650"]]),
                ("callout", "warn",
                 "\u90a3\u4e2a\u96f6\u662f\u7ed3\u6784\u6027\u7684\uff0c\u4e0d\u662f"
                 "\u8ba9\u4eba\u5b89\u5fc3\u7684",
                 "<p>\u95e8\u4e00\u6b21\u90fd\u6ca1\u89e6\u53d1\uff0c\u6240\u4ee5\u4e24"
                 "\u8fb9\u8dd1\u7684\u662f\u5b8c\u5168\u76f8\u540c\u7684\u4ee3\u7801\uff0c"
                 "\u9010\u67e5\u8be2\u540d\u6b21\u4e00\u6a21\u4e00\u6837\u3002\u4e00\u4e2a"
                 "\u6070\u597d\u4e3a\u96f6\u3001\u4e14\u4e0d\u4e00\u81f4\u5bf9\u4e5f\u4e3a"
                 "\u96f6\u7684 \u0394\uff0c\u4e0d\u662f\u300c\u95e8\u65e0\u5bb3\u300d\u7684"
                 "\u8bc1\u636e \u2014\u2014 \u5b83\u662f\u300c\u4ec0\u4e48\u90fd\u6ca1\u6d4b"
                 "\u5230\u300d\u7684\u8bc1\u636e\u3002\u53ef\u68c0\u6d4b\u6700\u5c0f\u6548"
                 "\u5e94\u5728\u8fd9\u91cc\u65e0\u5b9a\u4e49\uff0c\u56e0\u4e3a\u516c\u5f0f"
                 "\u8981\u9664\u4ee5\u4e0d\u4e00\u81f4\u5bf9\u7684\u4e2a\u6570\uff0c\u800c"
                 "\u5b83\u662f 0\u3002</p>"),
                ("p",
                 "\u8fd9 16 \u6761\u5168\u90e8\u662f\u5728\u8bf4\u300c\u6211\u6536\u8d77"
                 "\u6765\u7684\u90a3\u4e2a\u300d \u2014\u2014 <em>\u4e4b\u524d\u6536\u8d77"
                 "\u6765\u7684\u90a3\u4e2a</em>\u3001<em>the link I set aside</em>\u3001"
                 "<em>\u6211\u585e\u8fdb\u6e05\u5355\u91cc\u7684\u90a3\u7bc7</em>\u3002"
                 "\u6ca1\u6709\u4e00\u6761\u5305\u542b\u95e8\u7684\u89e6\u53d1\u8bcd\u8868"
                 "\u91cc\u7684\u8bcd \u2014\u2014 \u90a3\u5f20\u8868\u76ee\u524d\u770b\u7684"
                 "\u662f <code>\u4fdd\u5b58</code>\u3001<code>\u6536\u85cf</code>\u3001"
                 "<code>saved</code>\u3001<code>bookmark</code> \u7b49\u5341\u51e0\u4e2a"
                 "\u3002"),
                ("p",
                 "\u90a3\u4e2a\u770b\u4e0a\u53bb\u6700\u81ea\u7136\u7684\u52a8\u4f5c "
                 "\u2014\u2014 \u628a\u8fd9 16 \u6761\u52a0\u8fdb\u8bcd\u8868 \u2014\u2014 "
                 "\u6070\u6070\u662f\u534f\u8bae\u7981\u6b62\u7684\uff0c\u56e0\u4e3a\u7528"
                 "\u8861\u91cf\u5b83\u7684\u63a2\u9488\u53bb\u9009\u8bcd\u8868\u662f\u5faa"
                 "\u73af\u8bba\u8bc1\u3002\u8981\u62ff\u5230\u7ed3\u8bba\uff0c\u5f97\u7528"
                 "\u65b0\u79cd\u5b50\u3001\u5728\u51bb\u7ed3\u53c2\u6570\u4e0b\u65b0\u751f"
                 "\u6210\u81f3\u5c11 25 \u6761\u63a2\u9488\uff0c\u7136\u540e<em>\u540c"
                 "\u65f6</em>\u8fc7\u6f0f\u68c0\u7387\u8fd9\u5173\u548c 361 \u6761\u7cbe"
                 "\u5ea6\u90a3\u5173\u3002\u5728\u90a3\u4e4b\u524d\uff0c\u8bcd\u8868\u4e0d"
                 "\u52a8\u3002"),
            ],
        ),
        (
            "five",
            "\u4e94\u4e2a\u5019\u9009\u4fee\u6cd5\uff0c\u4e94\u4e2a\u7ed3\u8bba",
            [
                ("p",
                 "W1 \u6740\u6389\u878d\u5408\u4e4b\u540e\uff0c\u4e94\u4e2a\u770b\u4e0a"
                 "\u53bb\u5f88\u663e\u7136\u7684\u4fee\u6cd5\uff0c\u9010\u4e2a\u62ff\u53bb"
                 "\u6d4b\u4e86\uff0c\u800c\u4e0d\u662f\u62ff\u53bb\u8fa9\u8bba\u4e86\u3002"),
                ("table",
                 ["\u5019\u9009", "\u6d4b\u5230\u4ec0\u4e48", "\u7ed3\u8bba"],
                 [["\u5e72\u8106\u628a\u8bcd\u9762\u5220\u4e86",
                   "\u5185\u5bb9\u578b\u91cc 80.1%\u3001\u6a21\u7cca\u578b\u91cc 46.3% "
                   "\u6839\u672c\u4e0d\u9700\u8981\u5411\u91cf \u2014\u2014 \u4f46\u6709 "
                   "<b>6.05%</b>\uff08479 \u6761\u91cc 29 \u6761\uff09<em>\u53ea\u6709"
                   "</em>\u8bcd\u9762\u80fd\u627e\u5230\uff0c\u8d85\u8fc7\u9884\u6ce8"
                   "\u518c\u7684 5% \u7ebf\u3002",
                   "<span class=\"badge fail\">\u4fdd\u7559</span>"],
                  ["\u7ed9\u9762\u52a0\u6743\u91cd\u800c\u4e0d\u662f\u5e73\u6743 RRF",
                   "\u4e24\u4e2a\u5f31\u9762\u78b0\u5de7\u4e00\u81f4\u5f97 0.0279\uff1b"
                   "\u4e00\u4e2a\u5f3a\u9762\u786e\u5b9a\u5f97 0.0164\u3002",
                   "<span class=\"badge info\">\u89e3\u91ca\u4e86\u4e3a\u4ec0\u4e48\u8f93"
                   "</span>"],
                  ["\u4fee\u597d\u4e2d\u6587\u4e0a\u7684\u4e09\u5143\u7ec4\u9762",
                   "\u539f\u672c 211 \u6761\u4e2d\u6587\u67e5\u8be2\u53ea\u547d\u4e2d 25 "
                   "\u6761\uff0811.85%\uff09\u3002\u4fee\u540e 202/211\uff0895.73%\uff09"
                   "\u3002\u6574\u4f53 Recall@5\uff1a<b>\u6ca1\u53d8</b>\u3002",
                   "<span class=\"badge warn\">\u4fee\u597d\u4e86\uff0c\u6ca1\u6536\u76ca"
                   "</span>"],
                  ["\u628a boost \u4e0a\u9650\u62ec\u5927",
                   "<code>MAX_BOOST = 1.60</code> \u5728 A \u6863\u80fd\u8de8\u8d8a\u5206"
                   "\u6570\u533a\u95f4\u7684 79.7%\uff0c\u5728 C/D \u53ea\u6709 20.9%"
                   "\u3002\u8981\u6709\u540c\u7b49\u4f4d\u79fb\u80fd\u529b\u5f97 6.03"
                   "\u3002\u800c\u4e14 66.3% \u7684\u5019\u9009\u62ff\u5230\u7684\u5c31"
                   "\u662f 1.0\u3002",
                   "<span class=\"badge info\">\u6d4b\u4e86\uff0c\u6ca1\u53d1</span>"],
                  ["\u628a\u610f\u56fe\u9762\u6253\u5f00",
                   "50 \u6761\u751f\u6210\u610f\u56fe\u91cc\u53ea\u6709 19 \u6761\uff0838%"
                   "\uff09\u7ad9\u5f97\u4f4f\uff0c\u4f4e\u4e8e\u9884\u6ce8\u518c\u7684 50% "
                   "\u7ebf\u3002\u4fe1\u606f\u8bcd\u6839\u672c\u4e0d\u5728\u9875\u9762"
                   "\u4e0a\u7684\u6bd4\u4f8b\u6574\u4f53 34.0%\uff0c\u6b63\u6587\u8d2b"
                   "\u4e4f\u7684\u9875\u9762\u4e0a <b>62.4%</b>\u3002",
                   "<span class=\"badge fail\">\u5173</span>"]]),
                ("p",
                 "\u7b2c\u4e09\u884c\u662f\u6700\u6709\u610f\u601d\u7684\u3002\u4e00\u4e2a"
                 "\u771f\u7684 bug \u88ab\u627e\u5230\u5e76\u4fee\u597d\u4e86 \u2014\u2014 "
                 "\u4e09\u5143\u7ec4\u9762\u4ece\u5728\u4e2d\u6587\u4e0a\u6ca1\u7528\u53d8"
                 "\u6210\u80fd\u7528 \u2014\u2014 \u800c\u7aef\u5230\u7aef\u7684\u53ec"
                 "\u56de\u6ca1\u52a8\u3002\u4e00\u4e2a\u786e\u5b9e\u662f\u4fee\u590d\u3001"
                 "\u4f46\u4e0d\u6539\u53d8\u7ed3\u679c\u7684\u4fee\u590d\uff0c\u662f\u4e00"
                 "\u4e2a\u6b63\u5e38\u7ed3\u679c\uff1b\u628a\u5b83\u62a5\u51fa\u6765\uff0c"
                 "\u662f\u53e6\u5916\u56db\u884c\u8fd8\u80fd\u4fe1\u7684\u552f\u4e00\u7406"
                 "\u7531\u3002"),
            ],
        ),
        (
            "karakeep",
            "karakeep \u5f80\u8fd4 \u00b7 \u4e0d\u5fe0\u5b9e",
            [
                ("raw", "<p><span class=\"badge fail\">roundtrip_unfaithful</span> "
                        "<span class=\"tiny\">2,376 \u6761\u4e66\u7b7e \u00b7 616 \u6761 "
                        "holdout \u67e5\u8be2 \u00b7 \u534f\u8bae\u5148\u51bb\u7ed3"
                        "</span></p>"),
                ("p",
                 "\u95ee\u9898\uff1a\u628a\u4e00\u4e2a\u5e93\u63a8\u8fdb karakeep \u6865"
                 "\u518d\u8bfb\u56de\u6765\uff0c\u5b83\u8fd8\u662f\u540c\u4e00\u4e2a\u5e93"
                 "\u5417\uff1f\u4e09\u6761\u6807\u51c6\u5148\u5199\u597d\u3002"),
                ("table",
                 ["\u6807\u51c6", "\u7ebf", "\u5b9e\u6d4b", "\u5224\u5b9a"],
                 [["\u6307\u6807\u5fe0\u5b9e\u5ea6",
                   "|\u0394Recall@5| \u2264 3pp \u4e14 CI95 \u843d\u5728 \u00b15pp "
                   "\u5185",
                   "<b>\u22120.81pp</b>\uff0cCI95 [\u22122.44, +0.81]",
                   "<span class=\"badge pass\">\u8fc7</span>"],
                  ["\u540d\u6b21\u5fe0\u5b9e\u5ea6",
                   "overlap@5 \u4e2d\u4f4d\u6570 \u2265 4 <b>\u4e14</b> top-1 \u4e00\u81f4"
                   "\u7387 \u2265 80%",
                   "\u4e2d\u4f4d\u6570 4.0\uff0ctop-1 <b>79.06%</b>",
                   "<span class=\"badge fail\">\u5dee 0.94pp \u6ca1\u8fc7</span>"],
                  ["\u8bfb\u8def\u5f84\u7b49\u4ef7",
                   "HTTP \u4e0e\u539f\u751f\u5728 616\u00d72 \u4e0a\u5b8c\u5168\u4e00"
                   "\u81f4",
                   "0 \u5904\u4e0d\u4e00\u81f4",
                   "<span class=\"badge pass\">\u8fc7</span>"]]),
                ("h3", "\u539f\u56e0\u5b8c\u5168\u5f52\u56e0\u6e05\u695a"),
                ("ul",
                 ["\u6b63\u6587\u9010\u5b57\u8282\u76f8\u540c\uff1a1,876 / 1,876\u3002",
                  "\u6458\u8981\u5b58\u6d3b\uff1a2,375 / 2,375\uff0c100%\u3002",
                  "\u4e3b\u9898\u5339\u914d\u7387 <b>0%</b>\uff0c\u5b9e\u4f53 <b>1.18%"
                  "</b> \u2014\u2014 \u56e0\u4e3a karakeep \u7684 tag \u5c31\u662f\u6d4f"
                  "\u89c8\u5668\u7684<em>\u6587\u4ef6\u5939</em>\u540d\uff0c\u4e0d\u662f"
                  "\u4e3b\u9898\u3002",
                  "\u5173\u952e\u8bcd\u4ece <b>19,016 \u4e2a\u4e0d\u540c\u8bcd\u584c\u5230 "
                  "13 \u4e2a</b>\uff1b\u5e73\u5747\u6bcf\u9875\u4ece 10.32 \u8dcc\u5230 "
                  "0.76\uff1b\u6700\u5e38\u89c1\u7684\u6807\u7b7e\u662f "
                  "<code>\u672a\u5206\u7c7b</code>\uff0c\u51fa\u73b0\u5728 1,124 \u9875"
                  "\u4e0a\u3002",
                  "\u5411\u91cf\u7684\u4e2d\u4f4d\u4f59\u5f26\u4f4d\u79fb\u662f 0.9846 "
                  "\u2014\u2014 \u5f88\u5c0f\uff0c\u4f46\u8db3\u591f\u628a\u4e00\u4e2a "
                  "top-5 \u6d17\u4e00\u904d\u3002"]),
                ("p",
                 "\u628a\u6e90\u5bcc\u5316\u690d\u56de\u53bb\u4e4b\u540e\uff0c2,376 / "
                 "2,376 \u7684\u5d4c\u5165\u6587\u672c\u9010\u5b57\u8282\u76f8\u540c\uff0c"
                 "\u6b8b\u5dee\u4e3a\u96f6 \u2014\u2014 \u5f52\u56e0\u95ed\u73af\u3002"
                 "\u91cd\u8dd1\u4e00\u6b21 <code>facetmark index</code> \u5c31\u4fee\u597d"
                 "\u4e86\uff1a0 \u4e2a karakeep \u6b63\u6587\u9700\u8981\u91cd\u6293\uff0c"
                 "2,376 \u884c\u5168\u90e8\u91cd\u65b0\u5bcc\u5316\uff0c\u56fe\u9664\u4e86 "
                 "212 \u6761\u8bed\u4e49\u8fb9\u4e4b\u5916\u5b8c\u5168\u4e00\u81f4"
                 "\uff0826,485 \u5bf9 26,697\uff09\u3002"),
                ("callout", "info", "\u5b9e\u9645\u610f\u4e49",
                 "<p>\u6307\u6807\u5c42\u9762\u7684\u7ed3\u8bba\u80fd\u8fc1\u79fb\u5230\u4e00"
                 "\u4e2a\u7ecf karakeep \u5bcc\u5316\u7684\u5e93\u4e0a\u3002\u540d\u6b21"
                 "\u5c42\u9762\u7684\u4e0d\u80fd\uff0c\u9664\u975e\u4f60\u91cd\u5efa\u7d22"
                 "\u5f15\u3002\u8dd1\u4e86\u6865\uff0c\u5c31\u518d\u8dd1\u4e00\u6b21 "
                 "<code>facetmark index</code>\u3002</p>"),
            ],
        ),
        (
            "decay",
            "\u8870\u51cf\u5c42\u6d4b\u4e86\u4e24\u6b21 \u2014\u2014 \u7b2c\u4e8c\u6b21\u63a8\u7ffb\u4e86\u7b2c\u4e00\u6b21",
            [
                ("p",
                 "\u8870\u51cf\u5c42\u628a\u770b\u8d77\u6765\u9648\u65e7\u7684\u9875\u9762"
                 "\u5f80\u540e\u6392\u3002\u7b2c\u4e00\u8f6e\u6d4b\u5b8c\uff0c\u4ec0\u4e48"
                 "\u4e5f\u6ca1\u6d4b\u5230\uff1a"),
                ("table",
                 ["\u7b2c\u4e00\u8f6e", "\u503c"],
                 [["\u0394Recall@5", "<b>0.0000pp</b>\uff0cCI95 [0.00, 0.00]"],
                  ["\u51b7\u9875\u9762", "2,376 \u4e2d\u7684 8 \u4e2a"],
                  ["230 \u4e2a\u76ee\u6807\u91cc\u7684\u51b7\u9875\u9762", "0"]]),
                ("callout", "bad",
                 "\u7b2c\u4e00\u8f6e\u6d4b\u7684\u662f\u4e00\u4e2a\u6839\u672c\u6ca1\u5f00"
                 "\u7684\u4eea\u5668",
                 "<p><code>health</code> \u8868\u91cc\u662f<b>\u96f6\u884c</b>\uff0c"
                 "2,376 \u9875\u7684 <code>open_count</code> \u5168\u662f 0\u3002\u90a3"
                 "\u4e00\u5c42\u6839\u672c\u65e0\u6cd5\u89e6\u53d1\uff0c\u56e0\u4e3a\u5b83"
                 "\u6ca1\u4e1c\u897f\u53ef\u8bfb\u3002\u4e00\u4e2a\u534f\u8bae\u6267\u884c"
                 "\u5f97\u5f88\u6b63\u786e\u7684\u3001\u5e72\u51c0\u7684\u96f6 \u2014\u2014 "
                 "\u6d4b\u7684\u662f\u865a\u7a7a\u3002</p>"),
                ("p",
                 "\u7b2c\u4e8c\u8f6e\u7528\u540c\u4e00\u4efd\u5b57\u8282\uff0c\u5148\u8dd1"
                 "\u4e86\u4e00\u6b21\u672c\u5730\u5065\u5eb7\u68c0\u67e5\u3002"),
                ("table",
                 ["\u7b2c\u4e8c\u8f6e", "\u51fa\u5382\u503c\uff080.02\uff09",
                  "\u53ef\u8fbe\u503c\uff080.0\uff09"],
                 [["Recall@5", "<b>0.5860</b>", "0.5714"],
                  ["Recall@1", "0.4237", "0.4188"],
                  ["\u6551\u63f4\u9600\u6253\u5f00", "616 \u4e2d\u7684 417",
                   "616 \u4e2d\u7684 0"],
                  ["health \u884c\u6570", "2,376\uff08\u539f\u4e3a 0\uff09", "2,376"],
                  ["\u51b7\u9875\u9762", "73 \u2014\u2014 3.07%\uff08\u539f\u4e3a 8\uff0c"
                   "0.34%\uff09", "73"],
                  ["\u51b7 \u2229 230 \u4e2a\u76ee\u6807", "8\uff0c\u6d89\u53ca 19 \u6761"
                   "\u67e5\u8be2", "8"]]),
                ("p",
                 "\u0394Recall@5 \u4ece\u7b2c\u4e00\u8f6e\u7684 <code>+0.0000pp</code> "
                 "\u53d8\u6210\u7b2c\u4e8c\u8f6e\u7684 <b class=\"nowrap\">"
                 "\u22121.4610pp</b>\uff0cCI95 [\u22122.5974, \u22120.4870]\u3002\u673a"
                 "\u5236\u662f\u53ef\u4ee5\u6570\u51fa\u6765\u7684\uff1a37 \u5904\u540d"
                 "\u6b21\u53d8\u5316\u91cc\uff0c<b>12 \u5904\u76f4\u63a5\u6389\u51fa\u4e86"
                 "\u524d 20</b> \u2014\u2014 \u5176\u4e2d 10 \u4e2a\u539f\u672c\u5728\u524d "
                 "5\uff0c5 \u4e2a\u539f\u672c\u662f\u7b2c 1\u3002\u53e6\u6709 24 \u5904"
                 "\u4e0a\u5347\uff0c21 \u5904\u53ea\u5347\u4e86\u4e00\u540d\uff0c\u6070"
                 "\u597d <b>1</b> \u5904\u8fdb\u4e86\u524d 5\u3002\u51c0 \u221210 + 1 = "
                 "\u22129\uff0c\u800c \u22129/616 = \u22121.4610pp\u3002"),
                ("h3", "\u4e3a\u4ec0\u4e48\u9608\u503c\u81f3\u4eca\u6ca1\u6539"),
                ("p",
                 "\u4e24\u4e2a bug \u5728\u4e92\u76f8\u62b5\u6d88\uff0c\u800c\u4e14\u8fd9"
                 "\u4e2a\u62b5\u6d88\u662f\u627f\u91cd\u7684\u3002"),
                ("ul",
                 ["<b>bug \u4e00\uff1a</b>\u51b7\u5c42\u628a\u300cURL \u6b7b\u4e86\u300d"
                  "\u5f53\u6210\u300c\u5b58\u4e0b\u6765\u7684\u526f\u672c\u6ca1\u7528"
                  "\u4e86\u300d\u3002\u4f46 facetmark \u5b58\u4e86\u6b63\u6587\u3002URL "
                  "\u6b7b\u4e86\u6070\u6070\u662f\u672c\u5730\u5feb\u7167\u6700\u503c"
                  "\u94b1\u7684\u65f6\u5019\uff0c<code>drifted</code> \u66f4\u7cdf \u2014\u2014 \u90a3\u65f6\u5feb\u7167\u662f\u552f\u4e00\u5e78\u5b58\u7684"
                  "\u8bb0\u5f55\u3002",
                  "<b>bug \u4e8c\uff1a</b><code>rrf_k = 60</code> \u4e0b\uff0c\u5355\u4e2a"
                  "\u5355\u4f4d\u6743\u91cd\u7684\u9762\u5c01\u9876\u662f "
                  "<code>1/61 = 0.016393</code>\uff0c\u4f4e\u4e8e\u6551\u63f4\u9608\u503c "
                  "<code>0.02</code>\u3002\u6240\u4ee5\u5728\u51fa\u5382\u7684\u5355\u9762 "
                  "profile \u4e0b\uff0c\u6551\u63f4\u9600<em>\u603b\u662f</em>\u5f00"
                  "\u7740\uff0c\u90a3\u4e2a\u964d\u6743\u4ece\u6765\u6ca1\u6709\u771f\u6b63"
                  "\u6267\u884c\u8fc7\u3002",
                  "\u5355\u62c6\u6389\u4efb\u4e00\u4e2a\uff0c\u7ed3\u679c\u90fd\u4f1a\u5b9e"
                  "\u6d4b\u53d8\u5dee\u3002\u4e24\u8005\u90fd\u88ab "
                  "<code>tests/test_decay_reach.py</code> \u9489\u4f4f\uff0c\u9632\u6b62"
                  "\u88ab\u5f53\u6210\u300c\u987a\u624b\u6e05\u7406\u4e00\u4e0b\u300d"
                  "\u5220\u6389\u3002"]),
                ("p",
                 "\u771f\u6b63\u6539\u7684\u662f\u4eea\u8868\u76d8\u3002"
                 "<code>cold_census()</code> \u73b0\u5728\u5206\u5f00\u62a5\u4e09\u4e2a"
                 "\u6761\u4ef6\uff0c<code>facetmark stats</code> \u548c "
                 "<code>facetmark health --check</code> \u4f1a\u628a "
                 "<code>never_opened_selects_everything</code> \u548c "
                 "<code>health_never_checked</code> \u76f4\u63a5\u53eb\u51fa\u6765\u3002"),
                ("p",
                 "\u8fd8\u6709\u4e00\u4e2a\u503c\u5f97\u7559\u7740\u7684\u7ec6\u8282\uff1a"
                 "8 \u4e2a\u53d7\u635f\u76ee\u6807\u91cc\u6709 4 \u4e2a "
                 "<code>char_count = 0</code>\uff0c\u5374\u4ecd\u7136\u88ab\u6b63\u786e"
                 "\u68c0\u7d22\u51fa\u6765\uff0c\u9760\u7684\u662f\u6807\u9898\u548c\u8bcd"
                 "\u9762\u3002\u6b63\u6587\u4e22\u4e86\u4e0d\u7b49\u4e8e\u68c0\u7d22\u4e22"
                 "\u4e86\u3002"),
            ],
        ),
        (
            "real",
            "\u4e00\u4e2a\u771f\u5b9e\u5e93\uff0c\u4ece\u5934\u5230\u5c3e",
            [
                ("p",
                 "\u5408\u6210\u8bed\u6599\u4f1a\u63a9\u76d6\u96c6\u6210\u5c42\u9762\u7684"
                 "\u5931\u8d25\u3002\u8fd9\u662f\u4e00\u4efd\u771f\u5b9e\u7684\u6d4f\u89c8"
                 "\u5668\u5bfc\u51fa\uff0c\u7528\u51fa\u5382\u4ee3\u7801\u8def\u5f84\u5bfc"
                 "\u5165\u5e76\u5efa\u7d22\u5f15\u3002"),
                ("table",
                 ["\u9636\u6bb5", "\u7ed3\u679c"],
                 [["\u6587\u4ef6",
                   "<code>favorites_2026_8_4.html</code>\uff0c1.7 MB\uff0c96 \u4e2a\u6587"
                   "\u4ef6\u5939\uff0c\u56db\u5c42\u5d4c\u5957"],
                  ["\u5bfc\u5165",
                   "\u89e3\u6790 1,710 \u2192 \u5199\u5165 1,701\uff0c\u5408\u5e76 9 "
                   "\u6761\u91cd\u590d\uff0c1 \u6761\u4e0d\u53ef\u7d22\u5f15"],
                  ["\u5efa\u7d22\u5f15\uff08\u4e0d\u6293\u9875\u9762\uff09",
                   "322 \u4e2a\u4fdd\u5b58\u4f1a\u8bdd\u30019,132 \u6761\u8fb9\u30011,386 "
                   "\u4e2a\u57df\u540d\u30011,775 \u4e2a\u5411\u91cf"],
                  ["\u67e5\u8be2\u5ef6\u8fdf\u4e2d\u4f4d\u6570", "2,265 ms"]]),
                ("p",
                 "\u5ef6\u8fdf\u90a3\u4e2a\u6570\u5b57\u8bda\u5b9e\u800c\u4e0d\u597d\u770b"
                 "\uff1a\u5b83\u662f\u4e00\u4e2a\u672a\u6293\u53d6\u3001\u51b7\u542f\u7684"
                 "\u7d22\u5f15\u5728\u7b14\u8bb0\u672c\u4e0a\u7684\u6570\u5b57\uff0c\u4e5f"
                 "\u6b63\u662f\u53d1\u5e03\u535a\u6587\u91cc\u4f1a\u88ab\u60a8\u9ed8\u9ed8"
                 "\u7565\u6389\u7684\u90a3\u4e00\u4e2a\u3002"),
            ],
        ),
        (
            "gaps",
            "\u8fd9\u4e9b\u90fd\u6ca1\u6d4b\u5230\u4ec0\u4e48",
            [
                ("ul",
                 ["<b>\u522b\u4eba\u7684\u67e5\u8be2\u662f\u4e0d\u662f\u957f\u8fd9\u6837"
                  "\u3002</b>\u6bcf\u4e00\u5957\u67e5\u8be2\u96c6\u90fd\u662f\u5de5\u5177"
                  "\u4f5c\u8005\u5199\u7684\u3002\u8fd9\u662f\u8fd9\u4e00\u9875\u4e0a\u6bcf"
                  "\u4e2a\u6570\u5b57\u6700\u5927\u7684\u5a01\u80c1\uff0c\u800c\u4e14 bootstrap \u4e00\u70b9\u90fd\u78b0\u4e0d\u5230\u5b83\u3002",
                  "<b>\u8870\u51cf\u5c42\u5230\u5e95\u6709\u6ca1\u6709\u7528</b>\uff0c"
                  "\u56e0\u4e3a\u5728\u51fa\u5382 profile \u4e0b\u5b83\u6839\u672c\u89e6"
                  "\u53d1\u4e0d\u4e86\u3002",
                  "<b>\u610f\u56fe\u9762\u5728\u522b\u7684\u5e93\u4e0a\u4f1a\u4e0d\u4f1a"
                  "\u6709\u7528\u3002</b>\u5b83\u53ea\u5728\u8fd9\u4e2a\u5e93\u4e0a\u3001"
                  "\u7528\u4e00\u4e2a\u6a21\u578b\u751f\u6210\u3001\u7136\u540e\u8f93"
                  "\u4e86\u3002",
                  "<b>karakeep \u6865\u5bf9\u771f\u5b9e\u5b9e\u4f8b\u80fd\u4e0d\u80fd"
                  "\u8dd1\u3002</b>\u534f\u8bae\u9489\u4f4f\u4e86\u3001\u56de\u653e\u4e86"
                  "\uff1b\u4e00\u4e2a\u771f\u5728\u8dd1\u7684\u5b9e\u4f8b\u4ece\u6765\u6ca1"
                  "\u6d4b\u8fc7\u3002",
                  "<b>\u771f\u7684 cross-encoder \u91cd\u6392\u6709\u6ca1\u6709\u7528\u3002"
                  "</b>\u79bb\u7ebf\u53d1\u51fa\u53bb\u7684\u662f\u8bcd\u91cd\u53e0\u3002"
                  "\u5728\u90a3\u4e2a\u91cd\u6392\u5668\u4e0b\u8dd1\u7684\u6d88\u878d"
                  "\u6d4b\u7684\u662f\u53f0\u67b6\uff0c\u4e0d\u662f\u60f3\u6cd5\uff0c"
                  "\u4e0d\u80fd\u5f15\u7528\u4e3a\u300c\u91cd\u6392\u6709\u7528\u300d"
                  "\u7684\u8bc1\u636e\u3002",
                  "<b>\u957f\u671f\u884c\u4e3a\u3002</b>\u6bcf\u4e00\u6b21\u6d4b\u91cf"
                  "\u90fd\u662f\u5feb\u7167\u3002\u6ca1\u6709\u4eba\u628a\u5b83\u8dd1\u4e00"
                  "\u5e74\uff0c\u770b\u4e00\u4e2a\u4e0d\u65ad\u957f\u5927\u7684\u5e93\u4f1a"
                  "\u628a\u4f1a\u8bdd\u805a\u7c7b\u641e\u6210\u4ec0\u4e48\u6837\u3002"]),
                ("callout", "info", "\u600e\u4e48\u5e2e\u5fd9",
                 "<p>\u5bf9\u7740\u4f60\u81ea\u5df1\u7684\u5e93\u5199 100 \u6761\u67e5"
                 "\u8be2\uff0c\u6bcf\u6761\u5e26\u4e0a\u76ee\u6807 URL\uff0c\u5b58\u6210 "
                 "JSONL\u3002\u8dd1 <code>facetmark eval --no-build --queries "
                 "yours.jsonl --rungs A,C,full</code>\u3002\u628a JSON \u8d34\u51fa"
                 "\u6765\u3002\u8fd9\u4e00\u4ef6\u4e8b\u6bd4\u4efb\u4f55\u529f\u80fd"
                 "\u8bf7\u6c42\u90fd\u6709\u4ef7\u503c\uff0c\u800c\u4e14\u5b83\u6070\u597d"
                 "\u662f\u4f5c\u8005\u5728\u7ed3\u6784\u4e0a\u505a\u4e0d\u4e86\u7684\u90a3"
                 "\u4ef6\u4e8b\u3002</p>"),
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
    "浏览器界面 — facetmark",
    "界面上每一屏是干什么的、一行搜索结果该怎么读、以及它认哪些快捷键。",
)
ZH["meta"]["config"] = (
    "配置 — facetmark",
    "每一项配置用人话讲一遍，八家模型服务商的现成配置块，以及完全不用 API key 怎么跑。",
)
ZH["meta"]["integrations"] = (
    "连起来 — facetmark",
    "浏览器扩展、给 Claude 和 Cursor 用的 MCP 服务、karakeep 插件、全部命令行，以及怎么备份。",
)

ZH["webui"] = {
    "h1": "浏览器里的那个页面",
    "lede": "六屏，其中一屏你大概不会打开第二次。命令行能做的它都能做，"
    "外加两件命令行做不到的事：告诉你一条结果<em>为什么</em>排在这里，"
    "以及让你不用手写配置文件就能把它装起来。",
    "toc_title": "本页目录",
    "sections": [
        (
            "open",
            "打开它",
            [
                ("cb", "一条命令", "facetmark serve"),
                (
                    "p",
                    "它会打印一个网址——默认是 <code>http://127.0.0.1:8765</code>"
                    "——然后一直跑着。打开这个网址。终端别动，关掉终端服务就停了。",
                ),
                (
                    "dashed",
                    "",
                    "为什么它什么都不问你",
                    [
                        (
                            "p",
                            "服务只绑在你自己这台机器上，页面在能证明两头都是本机的时候"
                            "会自己给自己发一个令牌。所以没有登录页，也没有什么账号需要注册。",
                        ),
                        (
                            "p",
                            "如果你用别的名字访问它——局域网地址、内网穿透、反向代理——"
                            "这次握手会被<strong>故意</strong>拒绝，页面会让你手动粘贴令牌。"
                            "用 <code>facetmark token</code> 取。",
                        ),
                    ],
                ),
                (
                    "callout",
                    "warn",
                    "不要把它挂到公网域名上",
                    "<p>只有一个令牌，也没有限流。它是为「你现在坐的这把椅子」设计的。</p>",
                ),
            ],
        ),
        (
            "firstrun",
            "第一次：三步",
            [
                (
                    "p",
                    "库是空的时候，页面开在一个安装屏而不是搜索屏——"
                    "零条书签上面架一个搜索框是条死路。三个带框的步骤，按顺序来，"
                    "全都在浏览器里完成：",
                ),
                (
                    "steps",
                    [
                        "<b>把书签导进来。</b>从浏览器导出（<i>书签 → 管理 → 导出</i>），"
                        "把那个 HTML 文件丢到按钮上。Chrome 的 <code>Bookmarks</code> "
                        "JSON 文件也认；导入器会自己判断你给的是哪种。",
                        "<b>指一个模型，或者不指。</b>粘贴 API key，"
                        "或者把向量后端切成本地、完全不用 key。两种走法页面都会"
                        "先测一遍连通性，再让你依赖它。",
                        "<b>建索引。</b>一个按钮。七个阶段，跑到哪显示到哪，带日志。"
                        "你可以关掉标签页再回来——任务跑在服务里，不在页面里。",
                    ],
                ),
                (
                    "p",
                    "三个框都打上勾之后，这屏会把搜索框递给你然后让开。"
                    "除非库又空了，它不会再出现。",
                ),
            ],
        ),
        (
            "tabs",
            "五个标签，加一个齿轮",
            [
                (
                    "table",
                    ["屏", "干什么用"],
                    [
                        [
                            "<b>搜索</b>",
                            "主角。打字，拿到排好序的页面，并看到四条路里是哪几条找到了它。",
                        ],
                        [
                            "<b>提问</b>",
                            "用一句话问，答案从你自己的页面里来，每句话都能追回它出自哪条书签。"
                            "它引用，不编造。",
                        ],
                        [
                            "<b>库</b>",
                            "索引里到底有什么：多少页有正文、多少页有向量、"
                            "哪些链接已经死了、队列里排着什么、哪些从来没被打开过。",
                        ],
                        [
                            "<b>时段</b>",
                            "同一段时间里存下来的书签，成组显示。"
                            "当你只记得<i>什么时候</i>、别的都不记得时很有用。",
                        ],
                        [
                            "<b>系统</b>",
                            "版本、数据库路径、模型服务、运行时长。提 bug 时截这一屏。",
                        ],
                        [
                            "<b>⚙ 设置</b>",
                            "模型、限流、隐私，以及索引任务。放在齿轮后面而不是标签栏里，"
                            "因为你一年才开两次。",
                        ],
                    ],
                ),
                (
                    "p",
                    "英文界面里那个「Sittings」不是「Settings」写错了。"
                    "一个 sitting 是一段存书签的时间——你晚上十一点一口气归档的那二十个标签页。"
                    "设置在齿轮里。",
                ),
            ],
        ),
        (
            "read",
            "一行结果怎么读",
            [
                (
                    "p",
                    "一行是：名次、标题、来自哪里、一段把你的词标出来的摘要，"
                    "然后是别的书签搜索都不给你看的那部分——找到它的那几条路。",
                ),
                (
                    "tintrow",
                    [
                        (
                            "",
                            "关于",
                            [
                                (
                                    "p",
                                    "正文的向量。它被找到，是因为这个页面<i>就是在讲</i>"
                                    "你问的东西——不管它有没有用你那几个词。",
                                )
                            ],
                        ),
                        (
                            "lex",
                            "词 / 子串",
                            [
                                (
                                    "p",
                                    "全文检索，按词切和按三字符切各一路。"
                                    "它被找到，是因为你打的那串字就在里面。"
                                    "你记得一个专有名词的时候，救你的是这条路。",
                                )
                            ],
                        ),
                        (
                            "intent",
                            "被这样问过",
                            [
                                (
                                    "p",
                                    "从页面生成的问题的向量。它被找到，"
                                    "是因为有人可能拿你这个问题去问<i>这个</i>页面。",
                                )
                            ],
                        ),
                        (
                            "context",
                            "相邻",
                            [
                                (
                                    "p",
                                    "这一路根本不参与排名：图上距离一跳的页面，"
                                    "在结果下面单独成组。包括「存在一起的」和「意思相近的」。",
                                )
                            ],
                        ),
                    ],
                ),
                (
                    "p",
                    "徽章下面那条短横条用的是同一套颜色。那是配比："
                    "这一条融合分里，每条路各出了多少。两行偏金、一行偏紫，"
                    "意思是前两条对上了你的拼写、第三条对上了你的意思——"
                    "而这通常正是你开始看懂自己那句 query 的时刻。",
                ),
                (
                    "ul",
                    [
                        "<b>从未打开</b>——facetmark 没见你打开过这一条。"
                        "浏览器导出里根本不带使用记录，所以第一天所有条目都是这样。",
                        "每行末尾那个 <b>⋯</b> 按钮——不离开结果列表，就地打开这个页面自己的面板："
                        "正文统计、链接、它属于哪个时段。",
                        "<b>更多选项</b>——选四条路里跑几条。默认跑一条；"
                        "最后一档四条全跑还加重排。它更慢，而且在含糊的问题上"
                        "有实测的提升。",
                    ],
                ),
            ],
        ),
        (
            "keys",
            "快捷键，以及按你的习惯读",
            [
                (
                    "table",
                    ["键", "作用"],
                    [
                        ["<kbd>/</kbd>", "从任何地方跳到搜索框"],
                        ["<kbd>↑</kbd> <kbd>↓</kbd>", "在候选里上下走"],
                        ["<kbd>Enter</kbd>", "搜索，或者采用高亮的那条候选"],
                        ["<kbd>Esc</kbd>", "关掉面板，或者清空输入框"],
                        ["<kbd>Tab</kbd>", "按阅读顺序走过每一个控件"],
                    ],
                ),
                (
                    "ul",
                    [
                        "太阳／月亮那个按钮切主题；你没碰过它之前它跟随系统，碰过之后它记住。",
                        "<b>中文 / EN</b> 切语言。切的是界面，不是你的数据。",
                        "所有东西都是正常字号的真文字，所以浏览器缩放有效，选中复制也有效。",
                        "如果你的系统要求减少动效，这个页面就没有动效。"
                        "没有任何数字要等一个动画播完才肯出现。",
                    ],
                ),
            ],
        ),
        (
            "trouble",
            "它不听话的时候",
            [
                (
                    "table",
                    ["你看到的", "是怎么回事"],
                    [
                        [
                            "页面打开了但要令牌",
                            "你用的不是 <code>127.0.0.1</code> 或 "
                            "<code>localhost</code>。运行 "
                            "<code>facetmark token</code> 粘贴进去，或者改用本机地址。",
                        ],
                        [
                            "<code>address already in use</code>",
                            "端口被别的东西占了。<code>facetmark serve --port 8790</code>。",
                        ],
                        [
                            "搜不出东西，库里显示 0 个向量",
                            "索引没建过。齿轮 → 运行，或者 <code>facetmark index</code>。",
                        ],
                        [
                            "每条结果都写着<i>从未打开</i>",
                            "没错，而且是暂时的。等 facetmark 通过它自己看你打开过几个页面之后，"
                            "这个标记才开始有意义。",
                        ],
                        [
                            "索引任务卡在<i>抓取</i>",
                            "有些页面打不开。它会跳过去；死链会出现在「库」里，"
                            "那些页面也仍然会靠标题进索引。",
                        ],
                    ],
                ),
            ],
        ),
    ],
}


# --------------------------------------------------------------------------
# 配置
# --------------------------------------------------------------------------

ZH["config"] = {
    "h1": "配置，用人话讲",
    "lede": "旋钮很多。你需要的是其中四个，而且只有在你确实要用云端模型的时候才需要。"
    "这一页先讲那四个，再讲其余的，最后给你八家服务商各一段可以直接粘贴的配置。",
    "toc_title": "本页目录",
    "sections": [
        (
            "where",
            "一项配置是从哪来的",
            [
                ("p", "三个地方，越靠左的越大："),
                ("cb", "优先级", "环境变量   >   config.toml   >   内置默认值"),
                (
                    "p",
                    "设置屏会告诉你每个值来自这三者中的哪一个；"
                    "如果是环境变量在压着它，那个输入框会变成只读并说明原因，"
                    "而不是放你写一个根本不会生效的值。"
                    "在浏览器里改会写进文件，永远不会去动你的环境变量。",
                ),
                ("cb", "文件在哪", "facetmark config path"),
                (
                    "p",
                    "第一次有东西往里写的时候它才被创建。"
                    "并不要求你必须有这个文件——没有文件、没有环境变量，"
                    "全用默认值跑起来也是完全正常的一次运行。",
                ),
                (
                    "callout",
                    "",
                    "有三项要重启才生效",
                    "<p><code>embed_backend</code>、<code>embed_dim</code> 和 "
                    "<code>local_embed_path</code> 决定向量库的形状。"
                    "这一屏会把它们存下来，然后明确告诉你要下次启动才生效。</p>",
                ),
            ],
        ),
        (
            "model",
            "真正要紧的四项",
            [
                (
                    "table",
                    ["配置项", "人话"],
                    [
                        [
                            "<code>api_key</code>",
                            "你的 key。存在文件里，回显给你看的是掩码，"
                            "而且你保存别的字段时它不会被重新写一遍。",
                        ],
                        [
                            "<code>base_url</code>",
                            "请求发到哪。任何说 OpenAI 那套 API 的都行，"
                            "包括跑在你自己机器上的东西。",
                        ],
                        [
                            "<code>chat_model</code>",
                            "用来读页面，以及在「提问」屏上回答。"
                            "这里便宜快比聪明重要。",
                        ],
                        [
                            "<code>embed_model</code>",
                            "把文字变成向量。决定搜索质量的是这一项。",
                        ],
                    ],
                ),
                (
                    "callout",
                    "warn",
                    "换向量模型就要重建索引",
                    "<p>两个不同模型出来的向量不可比。换了就跑一次重建，"
                    "否则搜索会悄悄变差，而且没有任何报错会告诉你。</p>",
                ),
                (
                    "p",
                    "设置屏上的<b>测试</b>按钮会分别调用对话和向量，并分别报结果，"
                    "因为实际上通常只有其中一个是坏的——"
                    "有对话权限、没有向量权限的账号是非常常见的一种形态。",
                ),
            ],
        ),
        (
            "presets",
            "八家服务商，直接粘贴",
            [
                (
                    "p",
                    "把这些放进 <code>facetmark config path</code> 指出来的那个文件，"
                    "或者把同样的值填到设置屏里。模型名字是会变的；"
                    "如果某个名字被拒了，去查服务商当前的列表，别信这一页。",
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
                    'api_key = "sk-..."\n'
                    'base_url = "https://api.deepseek.com/v1"\n'
                    'chat_model = "deepseek-chat"',
                ),
                (
                    "cb",
                    "月之暗面 Kimi",
                    'api_key = "sk-..."\n'
                    'base_url = "https://api.moonshot.cn/v1"\n'
                    'chat_model = "moonshot-v1-8k"',
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
                    "<p>facetmark 只发两种请求：对话的和向量的。"
                    "很多人对话用最便宜的、向量用最好的。"
                    "把 <code>base_url</code> 指向做向量那家、"
                    "对话模型写全名；或者向量放本地跑，API 只留给对话。</p>",
                ),
            ],
        ),
        (
            "local",
            "完全不用 API",
            [
                ("p", "向量可以在你自己机器上算。不要 key、不联网、什么都不出这台笔记本："),
                (
                    "cb",
                    "本地向量",
                    'embed_backend = "local"\n'
                    'local_embed_path = "BAAI/bge-m3"\n'
                    "embed_dim = 1024",
                ),
                (
                    "p",
                    "建索引更慢，而且模型要先下载一次。搜索质量不错："
                    "在 1024 token 的窗口上，bge-m3 两次跑出来的向量自身余弦是 0.999976，"
                    "而这正是一个「要长期留着而不是天天重建」的索引最需要的性质。",
                ),
                (
                    "dashed",
                    "context",
                    "你放弃了什么",
                    [
                        (
                            "p",
                            "有两条路是建立在「让语言模型读一遍你的页面」上的："
                            "一个页面能回答的那些问题，以及主题标签。"
                            "没有对话模型，这两块就是空的，你搜的是正文和全文检索"
                            "——仍然是最强的两条路，也仍然比你浏览器给你的强。",
                        ),
                        (
                            "p",
                            "你也可以先从这里开始，以后再加 key。"
                            "什么都不用丢掉；索引会把之前建不出来的那部分补上。",
                        ),
                    ],
                ),
            ],
        ),
        (
            "groups",
            "其余的",
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
                            "永远不抓、永远不外发的域名。银行、健康、公司内网。"
                            "书签还在，只有标题进索引。",
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
                    "排除名单要在第一次建索引之前设",
                    "<p>一个页面的正文一旦进了数据库，把它的域名加进名单只会阻止以后再抓，"
                    "不会让它忘掉已经记住的。你在意的话，改完名单跑一次重建。</p>",
                ),
            ],
        ),
        (
            "faq",
            "你真会遇到的报错",
            [
                (
                    "table",
                    ["报错", "怎么办"],
                    [
                        [
                            "<code>401</code> / <code>invalid_api_key</code>",
                            "key 不对，或者这个 <code>base_url</code> 配了另一家的 key。"
                            "在设置屏上测一下——它会告诉你是哪一半挂了。",
                        ],
                        [
                            "模型名报 <code>404</code>",
                            "这个端点上没有这个名字。去查服务商的模型列表。",
                        ],
                        [
                            "<code>429</code>",
                            "被限流。把 <code>enrich_concurrency</code> 调小再跑一次；"
                            "已经完成的阶段不会重做。",
                        ],
                        [
                            "<code>dim mismatch</code>",
                            "<code>embed_dim</code> 和模型不一致。改对，重启，重建。",
                        ],
                        [
                            "对话能用，向量 403",
                            "很常见。这个账号有一种权限没有另一种。"
                            "把 <code>embed_backend</code> 切成本地，或者把向量指到另一家。",
                        ],
                        [
                            "保存时报 <code>unknown setting</code>",
                            "某个键名打错了。写入器会拒绝不认识的键，"
                            "而不是存一个从此被永久忽略的东西。",
                        ],
                    ],
                ),
            ],
        ),
    ],
}


# --------------------------------------------------------------------------
# 连接
# --------------------------------------------------------------------------

ZH["integrations"] = {
    "h1": "把它接到你桌面上的其他东西",
    "lede": "数据库就是一个 SQLite 文件，这一页里的每一样都只是通往它的另一道门："
    "你的浏览器、你的编辑器、你的 agent、你的终端。",
    "toc_title": "本页目录",
    "sections": [
        (
            "extension",
            "浏览器扩展",
            [
                (
                    "p",
                    "从地址栏搜你的书签，以及不离开当前页面就把它存下来。"
                    "扩展连的是网页界面连的同一个本机服务。",
                ),
                (
                    "steps",
                    [
                        "先起服务：<code>facetmark serve</code>。",
                        "从仓库里的 <code>extension/</code> 加载扩展——Chrome："
                        "<i>chrome://extensions</i>，开开发者模式，<i>加载已解压的扩展程序</i>。",
                        "打开它的选项。服务在默认端口上它会自己配对；"
                        "否则把 <code>facetmark token</code> 的输出粘进去。",
                    ],
                ),
                (
                    "callout",
                    "",
                    "它是配对，不是同步",
                    "<p>什么都不上传，也没有账号。服务没跑的时候，扩展什么也不做。</p>",
                ),
            ],
        ),
        (
            "mcp",
            "Claude、Cursor，以及任何说 MCP 的东西",
            [
                (
                    "p",
                    "facetmark 自带一个 MCP 服务，所以助手可以把「搜你的书签」当成一个工具来用，"
                    "而不是你手动往对话框里粘链接。",
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
                    "Cursor 在它自己的 MCP 设置里是同样的形状。"
                    "如果编辑器看到的 PATH 里没有 <code>facetmark</code>，就写绝对路径"
                    "——几乎每一份「工具一直不出现」的反馈都是这个原因。",
                ),
                (
                    "dashed",
                    "intent",
                    "助手能做什么、不能做什么",
                    [
                        (
                            "p",
                            "它能搜索、能读一条书签、能列时段、能在你的库上提问。"
                            "它不能删任何东西，不能写配置，也碰不到数据库以外的地方。",
                        )
                    ],
                ),
            ],
        ),
        (
            "karakeep",
            "karakeep",
            [
                (
                    "p",
                    "如果你的链接都放在 karakeep 里，facetmark 可以从那边建索引，"
                    "而不是从浏览器导出文件。",
                ),
                (
                    "callout",
                    "warn",
                    "有实测，值得在你投入之前先知道",
                    "<p>经 karakeep 自己的关键词抽取绕一圈，代价是 "
                    "<b>Recall@5 掉 0.81 个百分点</b>（CI95 −2.44 到 +0.81），"
                    "并且和直接建索引在第一名上只有 <b>79.06%</b> 一致。"
                    "词表会塌缩：19,016 个不同词项变成 13 个。"
                    "仓库里记下来的结论是 <code>roundtrip_unfaithful</code>"
                    "——能用，但不等价。能直接索引页面就直接索引。</p>",
                ),
            ],
        ),
        (
            "cli",
            "命令行",
            [
                (
                    "p",
                    "页面能做的都在这里，还有几样页面做不到的。"
                    "任何一条后面都能加 <code>--help</code>。",
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
                    "<code>facetmark demo</code> 是判断你到底要不要用这东西最实在的办法："
                    "它用生成的页面搭出一个库，不要 key 不联网，"
                    "让你在导入任何自己的东西之前先把每一屏都点一遍。",
                ),
            ],
        ),
        (
            "backup",
            "备份，以及搬机器",
            [
                (
                    "p",
                    "一个文件。复制它就等于复制了全部——书签、正文、向量、图、历史。",
                ),
                ("cb", "它在哪", "facetmark stats"),
                (
                    "callout",
                    "warn",
                    "先把服务停掉",
                    "<p>数据库跑在 WAL 模式下，所以在有东西正在写的时候拷走，"
                    "可能会漏掉日志的尾巴。停掉 <code>facetmark serve</code>，"
                    "拷完再起。</p>",
                ),
                (
                    "ul",
                    [
                        "搬机器：把文件拷过去，版本不一样就再跑一次 "
                        "<code>facetmark migrate</code>。",
                        "你的书签本来也还在浏览器里。最坏的情况是重新导入重新建索引，"
                        "代价是时间和几次模型调用，不是数据。",
                        "配置文件是单独的，里面有你的 API key。"
                        "要么备份到你会放密码的地方，要么干脆不备份。",
                    ],
                ),
            ],
        ),
    ],
}
