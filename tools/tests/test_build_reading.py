"""Tests critical parsing, link mapping, and offline-content safety behavior."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build_reading import (  # noqa: E402
    Lesson,
    add_heading_ids,
    assign_lesson_titles,
    build_toc,
    build_site,
    discover_lessons,
    make_markdown_parser,
    render_home_page,
    render_markdown,
    rewrite_local_markdown_links,
)


class BuildReadingTest(unittest.TestCase):
    def test_discovery_uses_only_existing_numbered_lessons(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            lessons_root = root / "source"
            lessons_root.mkdir()
            (lessons_root / "Day002_second.md").write_text(
                "# Day002: Second\n", encoding="utf-8"
            )
            (lessons_root / "Day001_first.md").write_text(
                "# Day001: First\n", encoding="utf-8"
            )
            (lessons_root / "Day006_planned.md.txt").write_text(
                "not a lesson\n", encoding="utf-8"
            )

            lessons = discover_lessons(lessons_root, root / "_site")
            lessons = assign_lesson_titles(lessons, make_markdown_parser())

            self.assertEqual([lesson.number for lesson in lessons], [1, 2])
            self.assertEqual([lesson.title for lesson in lessons], ["Day001: First", "Day002: Second"])
            self.assertEqual([lesson.output.name for lesson in lessons], ["Day001.html", "Day002.html"])

    def test_duplicate_heading_ids_are_unique_and_listed(self):
        parser = make_markdown_parser()
        tokens = parser.parse("# Title\n\n## Repeated\n\n## Repeated\n")

        entries = add_heading_ids(tokens)
        heading_ids = [
            token.attrGet("id")
            for token in tokens
            if token.type == "heading_open"
        ]
        toc = build_toc(entries)

        self.assertEqual(heading_ids, ["title", "repeated", "repeated-2"])
        self.assertIn('href="#repeated-2"', toc)

    def test_safe_inline_emphasis_survives_and_unsafe_html_is_removed(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "Day001_test.md"
            source.write_text(
                '# Day001: Test\n\n## 摘要\n\n摘要。\n\n## 正文\n\n'
                '<u>下划线</u> '
                '<span style="color: #b00020" onclick="alert(1)">标红</span> '
                '<script>alert(2)</script> '
                '[不安全链接](javascript:alert(3))\n\n第二段。\n',
                encoding="utf-8",
            )
            lesson = Lesson(source, 1, "Day001: Test", root / "_site" / "lessons" / "Day001.html")
            diagnostics = []

            rendered, _ = render_markdown(
                source,
                lesson,
                {source.resolve(): lesson},
                root / "_site",
                root,
                diagnostics,
            )

            self.assertIn("<u>下划线</u>", rendered)
            self.assertIn("<p>摘要。</p>", rendered)
            self.assertIn("<p>第二段。</p>", rendered)
            self.assertIn("style=\"color: #b00020;\"", rendered)
            self.assertIn('id="摘要"', rendered)
            self.assertNotIn("onclick", rendered)
            self.assertNotIn("<script", rendered)
            self.assertNotIn("href=\"javascript:", rendered)

    def test_tables_and_text_diagrams_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "Day001_test.md"
            source.write_text(
                "# Day001: Test\n\n## 摘要\n\n摘要。\n\n## 正文\n\n"
                "| 层 | 职责 |\n| --- | --- |\n| 内核 | 管理资源 |\n\n"
                "```text\n应用 → 内核 → 资源\n```\n",
                encoding="utf-8",
            )
            lesson = Lesson(source, 1, "Day001: Test", root / "_site" / "lessons" / "Day001.html")
            rendered, _ = render_markdown(
                source,
                lesson,
                {source.resolve(): lesson},
                root / "_site",
                root,
                [],
            )

            self.assertIn("<table>", rendered)
            self.assertIn("<pre><code>", rendered)
            self.assertIn("应用 → 内核 → 资源", rendered)

    def test_local_lesson_links_map_to_generated_pages(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_root = root / "lessons"
            source_root.mkdir()
            current_source = source_root / "Day001_current.md"
            next_source = source_root / "Day002_next.md"
            current_source.write_text("# Current\n", encoding="utf-8")
            next_source.write_text("# Next\n", encoding="utf-8")
            output_root = root / "_site"
            current = Lesson(current_source, 1, "Current", output_root / "lessons" / "Day001.html")
            following = Lesson(next_source, 2, "Next", output_root / "lessons" / "Day002.html")
            parser = make_markdown_parser()
            tokens = parser.parse("[Next](Day002_next.md#intro)\n")
            diagnostics = []

            rewrite_local_markdown_links(
                tokens,
                current,
                {current_source.resolve(): current, next_source.resolve(): following},
                root,
                diagnostics,
            )
            link = next(
                token
                for block in tokens
                for token in (block.children or [])
                if token.type == "link_open"
            )

            self.assertEqual(link.attrGet("href"), "Day002.html#intro")
            self.assertEqual(diagnostics, [])

    def test_empty_course_list_has_a_readable_home_state(self):
        page = render_home_page([], Path("_site"))

        self.assertIn("目前没有可生成的课程", page)
        self.assertNotIn("Day006.html", page)

    def test_build_is_repeatable_and_generates_only_present_lessons(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            lesson_root = root / "01_每日学习" / "00_先导课"
            lesson_root.mkdir(parents=True)
            first = lesson_root / "Day001_first.md"
            second = lesson_root / "Day002_second.md"
            first.write_text(
                "# Day001：第一课\n\n## 摘要\n\n摘要。\n\n## 正文\n\n"
                "### 内容\n\n旧内容。\n\n![像素](pixel.png)\n\n[下一课](Day002_second.md)\n",
                encoding="utf-8",
            )
            second.write_text(
                "# Day002：第二课\n\n## 摘要\n\n摘要。\n\n## 正文\n\n正文。\n",
                encoding="utf-8",
            )
            (lesson_root / "pixel.png").write_bytes(b"local image bytes")
            output = root / "_site"

            build_site(root, output)
            first_page = (output / "lessons" / "Day001.html").read_text(encoding="utf-8")
            last_page = (output / "lessons" / "Day002.html").read_text(encoding="utf-8")
            share_page = (output / "share" / "Day001_first_分享.html").read_text(encoding="utf-8")
            self.assertEqual(first_page.count("<h1>"), 1)
            self.assertIn('href="Day002.html"', first_page)
            self.assertIn('href="../index.html"', last_page)
            self.assertNotIn("Day006.html", last_page)
            self.assertIn("下一课", share_page)
            self.assertIn("<style>", share_page)
            self.assertIn("<script>", share_page)
            self.assertNotIn("<link rel=\"stylesheet\"", share_page)
            self.assertNotIn('href="../index.html"', share_page)
            self.assertNotIn('href="Day002.html"', share_page)
            self.assertNotIn('href="../../', share_page)
            self.assertNotIn('src="../', share_page)
            self.assertNotIn("../assets/", share_page)
            self.assertNotIn("fetch(", share_page)
            self.assertIn("data:image/png;base64,", share_page)
            self.assertIn("../assets/content/", first_page)
            self.assertEqual(len(list((output / "assets" / "content").glob("*.png"))), 1)

            detached_directory = root / "detached"
            detached_directory.mkdir()
            detached_copy = detached_directory / "independent.html"
            detached_copy.write_text(share_page, encoding="utf-8")
            self.assertIn("旧内容", detached_copy.read_text(encoding="utf-8"))

            first.write_text(
                first.read_text(encoding="utf-8").replace("旧内容", "新内容"),
                encoding="utf-8",
            )
            build_site(root, output)
            rebuilt_page = (output / "lessons" / "Day001.html").read_text(encoding="utf-8")
            rebuilt_share = (output / "share" / "Day001_first_分享.html").read_text(
                encoding="utf-8"
            )
            self.assertIn("新内容", rebuilt_page)
            self.assertIn("新内容", rebuilt_share)


if __name__ == "__main__":
    unittest.main()
