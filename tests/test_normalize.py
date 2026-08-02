"""URL normalisation -- one test class per numbered step, plus the guarantee that
unknown parameters are never touched.
"""

from __future__ import annotations

from facetmark.normalize import (
    body_hash,
    body_normalize_for_hash,
    normalize_url,
    registrable_domain,
)


class TestStep1Scheme:
    def test_http_is_unified_to_https_for_identity(self):
        a = normalize_url("http://example.com/x")
        b = normalize_url("https://example.com/x")
        assert a.hash == b.hash

    def test_original_is_preserved_for_navigation(self):
        n = normalize_url("http://example.com/x")
        assert n.original == "http://example.com/x"
        assert n.scheme == "http"

    def test_force_https_can_be_disabled(self):
        n = normalize_url("http://example.com/x", force_https=False)
        assert n.normalized.startswith("http://")


class TestStep2Host:
    def test_host_is_lowercased(self):
        assert normalize_url("https://EXAMPLE.com/x").normalized == "https://example.com/x"

    def test_leading_www_is_stripped(self):
        assert normalize_url("https://www.example.com/x").host == "example.com"

    def test_www_is_kept_when_it_is_the_whole_second_level(self):
        # "www.com" has only one dot; stripping would produce an empty host.
        assert normalize_url("https://www.com/x").host == "www.com"


class TestStep3Port:
    def test_default_port_is_dropped(self):
        assert normalize_url("https://example.com:443/x").normalized == "https://example.com/x"
        assert normalize_url("http://example.com:80/x").normalized == "https://example.com/x"

    def test_non_default_port_is_kept(self):
        assert normalize_url("https://example.com:8443/x").normalized == (
            "https://example.com:8443/x"
        )


class TestStep4TrackingParams:
    def test_utm_family_is_stripped(self):
        n = normalize_url("https://e.com/p?utm_source=a&utm_medium=b&utm_campaign=c")
        assert n.normalized == "https://e.com/p"

    def test_click_ids_are_stripped(self):
        for p in ("fbclid", "gclid", "msclkid", "igshid", "spm", "ref", "ref_src", "mkt_tok"):
            assert normalize_url(f"https://e.com/p?{p}=x").normalized == "https://e.com/p"

    def test_prefix_families_are_stripped(self):
        n = normalize_url("https://e.com/p?pk_campaign=x&matomo_kwd=y")
        assert n.normalized == "https://e.com/p"


class TestStep5UnknownParamsArePreserved:
    """The single most important rule: prefer under-merging to mis-merging."""

    def test_unknown_param_is_kept(self):
        n = normalize_url("https://e.com/p?id=42")
        assert "id=42" in n.normalized

    def test_pagination_and_query_params_survive(self):
        for p in ("page=2", "q=rust", "v=dQw4w9WgXcQ", "tab=readme", "lang=zh"):
            assert p in normalize_url(f"https://e.com/p?{p}").normalized

    def test_two_pages_differing_only_by_unknown_param_stay_distinct(self):
        a = normalize_url("https://e.com/list?page=1")
        b = normalize_url("https://e.com/list?page=2")
        assert a.hash != b.hash


class TestStep6QuerySorting:
    def test_param_order_does_not_affect_identity(self):
        a = normalize_url("https://e.com/p?b=2&a=1")
        b = normalize_url("https://e.com/p?a=1&b=2")
        assert a.hash == b.hash
        assert a.normalized == "https://e.com/p?a=1&b=2"

    def test_blank_values_are_kept(self):
        assert "flag=" in normalize_url("https://e.com/p?flag=").normalized


class TestStep7TrailingSlash:
    def test_trailing_slash_is_dropped(self):
        a = normalize_url("https://e.com/path/")
        b = normalize_url("https://e.com/path")
        assert a.hash == b.hash

    def test_root_path_keeps_its_slash(self):
        assert normalize_url("https://e.com/").normalized == "https://e.com/"
        assert normalize_url("https://e.com").normalized == "https://e.com/"

    def test_duplicate_slashes_are_collapsed(self):
        assert normalize_url("https://e.com/a//b///c").normalized == "https://e.com/a/b/c"


class TestStep8Fragments:
    def test_ordinary_fragment_is_dropped_and_recorded(self):
        n = normalize_url("https://blog.example/post#comments")
        assert "#" not in n.normalized
        assert n.dropped_fragment == "comments"
        assert n.kept_fragment == ""

    def test_anchor_meaningful_host_keeps_its_fragment(self):
        n = normalize_url("https://github.com/o/r#readme")
        assert n.kept_fragment == "readme"
        assert n.normalized.endswith("#readme")

    def test_anchor_siblings_stay_distinct_on_meaningful_hosts(self):
        a = normalize_url("https://github.com/o/r#readme")
        b = normalize_url("https://github.com/o/r#license")
        assert a.hash != b.hash

    def test_hash_routes_are_always_kept(self):
        # Dropping these would collapse an entire SPA into one row.
        for u in ("https://app.example/#!/dashboard", "https://app.example/#/settings"):
            assert normalize_url(u).kept_fragment != ""

    def test_ordinary_host_merges_fragment_variants(self):
        a = normalize_url("https://blog.example/post#a")
        b = normalize_url("https://blog.example/post#b")
        assert a.hash == b.hash


class TestNonIndexableSchemes:
    def test_data_url_is_marked_non_indexable(self):
        n = normalize_url("data:text/html,hello")
        assert n.indexable is False
        assert n.host == ""

    def test_javascript_bookmarklet_is_non_indexable(self):
        assert normalize_url("javascript:void(0)").indexable is False

    def test_http_and_https_are_indexable(self):
        assert normalize_url("https://e.com").indexable is True
        assert normalize_url("http://e.com").indexable is True


class TestRegistrableDomain:
    def test_plain_two_label_host(self):
        assert registrable_domain("example.com") == "example.com"

    def test_subdomain_is_collapsed(self):
        assert registrable_domain("a.b.example.com") == "example.com"

    def test_two_level_suffix(self):
        assert registrable_domain("shop.example.co.uk") == "example.co.uk"
        assert registrable_domain("www.example.com.cn") == "example.com.cn"

    def test_ip_literal_is_returned_as_is(self):
        assert registrable_domain("127.0.0.1") == "127.0.0.1"


class TestBodyHashing:
    def test_whitespace_changes_do_not_change_the_hash(self):
        assert body_hash("hello   world") == body_hash("hello world\n\n")

    def test_timestamps_are_stripped(self):
        a = "Published 2024-01-01 10:30 by Alice. The content of the article."
        b = "Published 2025-06-15 22:07 by Alice. The content of the article."
        assert body_hash(a) == body_hash(b)

    def test_relative_times_are_stripped_in_both_languages(self):
        assert body_hash("Posted 3 hours ago. Body.") == body_hash("Posted 9 days ago. Body.")
        assert body_hash("发布于 3 小时前。正文内容。") == body_hash("发布于 9 天前。正文内容。")

    def test_real_content_change_does_change_the_hash(self):
        assert body_hash("the original claim") != body_hash("a materially different claim")

    def test_short_navigational_lines_are_dropped(self):
        assert body_normalize_for_hash("A\nB\nreal sentence here") == "real sentence here"

    def test_empty_input(self):
        assert body_normalize_for_hash("") == ""
        assert body_hash("") == body_hash("")
