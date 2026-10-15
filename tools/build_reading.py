"""Builds a self-contained static HTML reading edition from lesson Markdown.

Run `python tools/build_reading.py` from the project root after installing
`tools/requirements.txt`. The generated site is written to `_site/`.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import html
import mimetypes
import os
import re
import shutil
import string
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit, urlunsplit

import bleach
from bleach.css_sanitizer import CSSSanitizer
from markdown_it import MarkdownIt


ROOT = Path(__file__).resolve().parents[1]
LESSON_ROOT = ROOT / "01_每日学习"
TEMPLATE_ROOT = ROOT / "tools" / "reading" / "templates"
ASSET_ROOT = ROOT / "tools" / "reading" / "assets"
OUTPUT_ROOT = ROOT / "_site"
OUTPUT_MARKER = ".openharmony-reading-site"

ALLOWED_TAGS = set(bleach.sanitizer.ALLOWED_TAGS) | {
    "article",
    "aside",
    "caption",
    "details",
    "figure",
    "figcaption",
    "h1",
    "h2",
    "h3",
    "h4",
    "header",
    "img",
    "main",
    "nav",
    "pre",
    "section",
    "summary",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "u",
    "span",
}
def allow_html_attribute(tag: str, name: str, value: str) -> bool:
    """Allows only safe attributes, including generated raster image data URIs."""
    if tag == "a" and name in {"href", "title"}:
        return name == "title" or urlsplit(value).scheme in {"", "http", "https", "mailto"}
    if tag in {"h1", "h2", "h3", "h4"} and name == "id":
        return True
    if tag == "img" and name in {"alt", "title"}:
        return True
    if tag == "img" and name == "src":
        parsed = urlsplit(value)
        if parsed.scheme in {"http", "https"}:
            return False
        if parsed.scheme == "data":
            return value.startswith((
                "data:image/png;base64,",
                "data:image/jpeg;base64,",
                "data:image/gif;base64,",
                "data:image/webp;base64,",
                "data:image/avif;base64,",
            ))
        return not parsed.scheme
    if tag == "span" and name == "style":
        return True
    if tag in {"td", "th"} and name == "align":
        return value in {"left", "center", "right"}
    return False


HTML_CLEANER = bleach.Cleaner(
    tags=ALLOWED_TAGS,
    attributes=allow_html_attribute,
    protocols={"http", "https", "mailto", "data"},
    strip=True,
    css_sanitizer=CSSSanitizer(allowed_css_properties=["color"]),
)


@dataclass(frozen=True)
class Lesson:
    """Represents one discovered Markdown lesson and its generated page."""

    source: Path
    number: int
    title: str
    output: Path


def make_markdown_parser() -> MarkdownIt:
    """Creates the Markdown parser with the constructs used by course files."""
    return MarkdownIt("commonmark", {"html": True}).enable(["table", "strikethrough"])


def plain_inline_text(token) -> str:
    """Returns readable text from an inline token for titles and headings."""
    if token.children is None:
        return token.content
    pieces = []
    for child in token.children:
        if child.type in {"text", "code_inline", "html_inline", "image"}:
            pieces.append(child.content if child.type != "image" else child.attrGet("alt") or "")
        elif child.type in {"softbreak", "hardbreak"}:
            pieces.append(" ")
    return re.sub(r"\s+", " ", "".join(pieces)).strip()


def slugify_heading(text: str) -> str:
    """Creates a stable, Unicode-friendly fragment identifier."""
    normalized = unicodedata.normalize("NFKC", text).strip().lower()
    characters = []
    separator = False
    for character in normalized:
        if character.isalnum():
            if separator and characters:
                characters.append("-")
            characters.append(character)
            separator = False
        else:
            separator = True
    return "".join(characters).strip("-") or "section"


def add_heading_ids(tokens) -> list[tuple[int, str]]:
    """Adds unique fragment IDs and returns the in-page navigation entries."""
    entries = []
    used = {}
    for index, token in enumerate(tokens):
        if token.type != "heading_open" or index + 1 >= len(tokens):
            continue
        inline = tokens[index + 1]
        title = plain_inline_text(inline)
        base = slugify_heading(title)
        used[base] = used.get(base, 0) + 1
        identifier = base if used[base] == 1 else f"{base}-{used[base]}"
        token.attrSet("id", identifier)
        level = int(token.tag[1:])
        if level in {2, 3, 4}:
            entries.append((level, title, identifier))
    return entries


def discover_lessons(lesson_root: Path, output_root: Path) -> list[Lesson]:
    """Finds existing Day lessons and maps them to stable numbered pages."""
    lessons = []
    numbers = set()
    for source in sorted(lesson_root.rglob("Day[0-9][0-9][0-9]_*.md")):
        number = int(source.stem[3:6])
        if number in numbers:
            raise ValueError(f"Duplicate Day number {number:03}: {source}")
        numbers.add(number)
        lessons.append(
            Lesson(
                source=source.resolve(),
                number=number,
                title="",
                output=output_root / "lessons" / f"Day{number:03}.html",
            )
        )
    return lessons


def assign_lesson_titles(lessons: list[Lesson], parser: MarkdownIt) -> list[Lesson]:
    """Reads the first Markdown H1 title for every discovered lesson."""
    titled = []
    for lesson in lessons:
        tokens = parser.parse(lesson.source.read_text(encoding="utf-8"))
        title = next(
            (
                plain_inline_text(tokens[index + 1])
                for index, token in enumerate(tokens[:-1])
                if token.type == "heading_open" and token.tag == "h1"
            ),
            lesson.source.stem,
        )
        titled.append(Lesson(lesson.source, lesson.number, title, lesson.output))
    return titled


def rewrite_local_markdown_links(
    tokens,
    lesson: Lesson,
    lessons_by_source: dict[Path, Lesson],
    project_root: Path,
    diagnostics: list[str],
    share: bool = False,
    asset_root: Path | None = None,
) -> None:
    """Maps local links and embeds or copies local raster images."""
    output_parent = lesson.output.parent
    for block in tokens:
        children = block.children or []
        index = 0
        while index < len(children):
            token = children[index]
            if token.type == "image":
                rewrite_image_source(token, lesson, project_root, output_parent, diagnostics, share, asset_root)
                index += 1
                continue
            if token.type != "link_open":
                index += 1
                continue

            destination = token.attrGet("href")
            if not destination:
                index += 1
                continue
            parsed = urlsplit(destination)
            if parsed.scheme or parsed.netloc or not parsed.path:
                index += 1
                continue

            target = (lesson.source.parent / unquote(parsed.path)).resolve()
            target_lesson = lessons_by_source.get(target) if target.suffix.lower() == ".md" else None
            if target_lesson:
                if share:
                    remove_link_markup(children, index)
                    diagnostics.append(
                        f"INFO: Share page rendered cross-lesson link as text in {lesson.source}: {destination}"
                    )
                    continue
                mapped = os.path.relpath(target_lesson.output, output_parent).replace(os.sep, "/")
                token.attrSet("href", urlunsplit(("", "", mapped, parsed.query, parsed.fragment)))
                index += 1
                continue

            if target.is_file() and target.is_relative_to(project_root):
                if share:
                    remove_link_markup(children, index)
                    diagnostics.append(
                        f"INFO: Share page retained local reference text without a site link in {lesson.source}: {destination}"
                    )
                    continue
                mapped = os.path.relpath(target, output_parent).replace(os.sep, "/")
                token.attrSet("href", urlunsplit(("", "", mapped, parsed.query, parsed.fragment)))
                index += 1
                continue

            if share:
                remove_link_markup(children, index)
                diagnostics.append(
                    f"WARNING: Share page rendered unresolved local reference as text in {lesson.source}: {destination}"
                )
                continue
            diagnostics.append(f"WARNING: Unresolved Markdown link in {lesson.source}: {destination}")
            index += 1


def remove_link_markup(tokens: list, start: int) -> None:
    """Removes link delimiters while retaining the linked label tokens."""
    depth = 0
    closing_index = None
    for index in range(start, len(tokens)):
        if tokens[index].type == "link_open":
            depth += 1
        elif tokens[index].type == "link_close":
            depth -= 1
            if depth == 0:
                closing_index = index
                break
    if closing_index is not None:
        del tokens[closing_index]
        del tokens[start]


def replace_image_with_notice(token, alt: str) -> None:
    """Replaces an unavailable image with visible alternative text."""
    token.type = "text"
    token.tag = ""
    token.nesting = 0
    token.attrs = None
    token.content = f"[图片未能内嵌：{alt or '无替代文字'}]"
    token.children = None


def rewrite_image_source(
    token,
    lesson: Lesson,
    project_root: Path,
    output_parent: Path,
    diagnostics: list[str],
    share: bool,
    asset_root: Path | None,
) -> None:
    """Embeds local raster images for sharing and copies them for the site."""
    source = token.attrGet("src") or ""
    parsed = urlsplit(source)
    alt = token.attrGet("alt") or ""
    if parsed.scheme or parsed.netloc:
        diagnostics.append(f"WARNING: Remote image not fetched for offline output in {lesson.source}: {source}")
        replace_image_with_notice(token, alt)
        return

    target = (lesson.source.parent / unquote(parsed.path)).resolve()
    if not target.is_file() or not target.is_relative_to(project_root):
        diagnostics.append(f"WARNING: Unresolved local image in {lesson.source}: {source}")
        replace_image_with_notice(token, alt)
        return

    media_type = mimetypes.guess_type(target.name)[0]
    allowed_types = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/avif"}
    if media_type not in allowed_types:
        diagnostics.append(f"WARNING: Unsupported image type for offline output in {lesson.source}: {source}")
        replace_image_with_notice(token, alt)
        return

    data = target.read_bytes()
    if len(data) > 5 * 1024 * 1024:
        diagnostics.append(f"WARNING: Image exceeds the 5 MiB inline limit in {lesson.source}: {source}")
        replace_image_with_notice(token, alt)
        return

    if share:
        encoded = base64.b64encode(data).decode("ascii")
        token.attrSet("src", f"data:{media_type};base64,{encoded}")
        return

    if asset_root is None:
        raise ValueError("An asset directory is required to copy site images.")
    digest = hashlib.sha256(data).hexdigest()[:16]
    filename = f"{digest}{target.suffix.lower()}"
    asset_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(target, asset_root / filename)
    token.attrSet("src", f"../assets/content/{filename}")


def build_toc(entries: list[tuple[int, str, str]]) -> str:
    """Builds nested HTML navigation from actual Markdown headings."""
    items = []
    for level, title, identifier in entries:
        escaped_title = html.escape(title)
        escaped_id = html.escape(identifier, quote=True)
        items.append(
            f'<li class="toc-level-{level}"><a href="#{escaped_id}">{escaped_title}</a></li>'
        )
    if not items:
        return '<p class="toc-empty">本课没有可生成的页内目录。</p>'
    return '<ul class="toc-list">' + "".join(items) + "</ul>"


def render_markdown(
    source: Path,
    lesson: Lesson,
    lessons_by_source: dict[Path, Lesson],
    output_root: Path,
    project_root: Path,
    diagnostics: list[str],
    share: bool = False,
    asset_root: Path | None = None,
) -> tuple[str, list[tuple[int, str, str]]]:
    """Renders and sanitizes one course without executing source HTML."""
    parser = make_markdown_parser()
    tokens = parser.parse(source.read_text(encoding="utf-8"))
    toc_entries = add_heading_ids(tokens)
    for index, token in enumerate(tokens):
        if token.type == "heading_open" and token.tag == "h1":
            del tokens[index : index + 3]
            break
    rewrite_local_markdown_links(
        tokens,
        lesson,
        lessons_by_source,
        project_root,
        diagnostics,
        share=share,
        asset_root=asset_root,
    )
    rendered = parser.renderer.render(tokens, parser.options, {})
    return HTML_CLEANER.clean(rendered), toc_entries


def load_template(name: str) -> string.Template:
    """Loads a UTF-8 HTML template from the tool-owned template directory."""
    return string.Template((TEMPLATE_ROOT / name).read_text(encoding="utf-8"))


def render_base(main_content: str, page_title: str, asset_prefix: str, home_href: str) -> str:
    """Wraps page content in the shared accessible offline HTML shell."""
    return load_template("base.html").substitute(
        page_title=html.escape(page_title),
        asset_prefix=asset_prefix,
        home_href=home_href,
        main_content=main_content,
    )


def render_lesson_page(
    lesson: Lesson,
    body: str,
    toc_entries: list[tuple[int, str, str]],
    previous: Lesson | None,
    following: Lesson | None,
    share_output: Path,
) -> str:
    """Creates one lesson page and links only to existing neighboring lessons."""
    home_href = "../index.html"
    toc_html = build_toc(toc_entries)
    pager_items = []
    if previous:
        href = Path(os.path.relpath(previous.output, lesson.output.parent)).as_posix()
        pager_items.append(
            f'<a class="pager-link previous" href="{html.escape(href, quote=True)}">'
            f'<span>上一课</span><strong>{html.escape(previous.title)}</strong></a>'
        )
    else:
        pager_items.append('<span class="pager-placeholder" aria-hidden="true"></span>')
    if following:
        href = Path(os.path.relpath(following.output, lesson.output.parent)).as_posix()
        pager_items.append(
            f'<a class="pager-link next" href="{html.escape(href, quote=True)}">'
            f'<span>下一课</span><strong>{html.escape(following.title)}</strong></a>'
        )
    else:
        pager_items.append(
            f'<a class="pager-link next" href="{home_href}">'
            '<span>课程</span><strong>返回阅读首页</strong></a>'
        )

    content = load_template("lesson.html").substitute(
        home_href=home_href,
        lesson_number=f"Day{lesson.number:03}",
        title=html.escape(lesson.title),
        share_href=Path(os.path.relpath(share_output, lesson.output.parent)).as_posix(),
        toc_html=toc_html,
        article_html=body,
        pager_html="".join(pager_items),
    )
    return render_base(content, lesson.title, "../assets", home_href)


def render_share_page(
    lesson: Lesson,
    body: str,
    toc_entries: list[tuple[int, str, str]],
    resource_warnings: list[str],
) -> str:
    """Creates a page that carries its complete reading resources inline."""
    warning_html = ""
    if resource_warnings:
        message = "分享版有未能内嵌的资源，以下位置已用文字提示代替：" + "；".join(resource_warnings)
        warning_html = f'<aside class="share-resource-warning">{html.escape(message)}</aside>'
    content = load_template("share.html").substitute(
        lesson_number=f"Day{lesson.number:03}",
        title=html.escape(lesson.title),
        toc_html=build_toc(toc_entries),
        article_html=body,
        resource_notice=warning_html,
    )
    style_inline = "<style>\n" + (ASSET_ROOT / "reading.css").read_text(encoding="utf-8") + "\n</style>"
    script_inline = "<script>\n" + (ASSET_ROOT / "reading.js").read_text(encoding="utf-8") + "\n</script>"
    return load_template("share_base.html").substitute(
        page_title=html.escape(lesson.title),
        style_inline=style_inline,
        script_inline=script_inline,
        main_content=content,
    )


def render_home_page(
    lessons: list[Lesson], output_root: Path = OUTPUT_ROOT, share_root: Path | None = None
) -> str:
    """Creates a home page listing only courses present in the source tree."""
    if lessons:
        share_root = share_root or (output_root / "share")
        cards = []
        for lesson in lessons:
            href = Path(os.path.relpath(lesson.output, output_root)).as_posix()
            share_href = Path(os.path.relpath(
                share_root / f"{lesson.source.stem}_分享.html", output_root
            )).as_posix()
            display_title = re.sub(r"^Day\d{3}[：:]?\s*", "", lesson.title)
            cards.append(
                '<li class="lesson-card">'
                '<div class="lesson-card-links">'
                f'<a class="course-entry" href="{html.escape(href, quote=True)}">'
                f'<span class="lesson-number">Day{lesson.number:03}</span>'
                f'<span class="lesson-title">{html.escape(display_title)}</span></a>'
                f'<a class="share-download" download href="{html.escape(share_href, quote=True)}">'
                "下载独立分享版</a></div></li>"
            )
        listing = '<ol class="lesson-list">' + "".join(cards) + "</ol>"
    else:
        listing = '<p class="empty-state">目前没有可生成的课程，请先在 Markdown 源目录中添加课程。</p>'

    content = load_template("home.html").substitute(lesson_list=listing)
    return render_base(content, "阅读首页", "assets", "index.html")


def prepare_output_directory(output_root: Path) -> Path:
    """Creates a fresh staging directory without deleting unrelated files."""
    if output_root.is_symlink():
        raise FileExistsError(f"Refusing to replace a symlink: {output_root}")
    if output_root.exists() and not (output_root / OUTPUT_MARKER).is_file():
        raise FileExistsError(
            f"Refusing to replace unmarked output directory: {output_root}"
        )
    return Path(tempfile.mkdtemp(prefix="_site-build-", dir=output_root.parent))


def build_site(
    project_root: Path = ROOT,
    output_root: Path = OUTPUT_ROOT,
) -> list[str]:
    """Builds the offline site and returns non-fatal link diagnostics."""
    project_root = project_root.resolve()
    lesson_root = project_root / "01_每日学习"
    lessons = discover_lessons(lesson_root, output_root)
    parser = make_markdown_parser()
    lessons = assign_lesson_titles(lessons, parser)
    lesson_map = {lesson.source: lesson for lesson in lessons}
    diagnostics = []
    staging = prepare_output_directory(output_root)

    try:
        (staging / "lessons").mkdir(parents=True)
        (staging / "share").mkdir()
        (staging / "assets").mkdir()
        shutil.copy2(ASSET_ROOT / "reading.css", staging / "assets" / "reading.css")
        shutil.copy2(ASSET_ROOT / "reading.js", staging / "assets" / "reading.js")

        for index, lesson in enumerate(lessons):
            share_diagnostics = []
            body, toc_entries = render_markdown(
                lesson.source,
                lesson,
                lesson_map,
                output_root,
                project_root,
                diagnostics,
                asset_root=staging / "assets" / "content",
            )
            previous = lessons[index - 1] if index else None
            following = lessons[index + 1] if index + 1 < len(lessons) else None
            share_output = output_root / "share" / f"{lesson.source.stem}_分享.html"
            page = render_lesson_page(lesson, body, toc_entries, previous, following, share_output)
            (staging / "lessons" / lesson.output.name).write_text(page, encoding="utf-8")

            share_body, share_toc = render_markdown(
                lesson.source,
                lesson,
                lesson_map,
                output_root,
                project_root,
                share_diagnostics,
                share=True,
            )
            resource_warnings = [
                message.removeprefix("WARNING: ")
                for message in share_diagnostics
                if message.startswith("WARNING: ")
            ]
            diagnostics.extend(share_diagnostics)
            share_page = render_share_page(lesson, share_body, share_toc, resource_warnings)
            (staging / "share" / f"{lesson.source.stem}_分享.html").write_text(
                share_page, encoding="utf-8"
            )

        home = render_home_page(lessons, output_root, output_root / "share")
        (staging / "index.html").write_text(home, encoding="utf-8")
        (staging / OUTPUT_MARKER).write_text(
            "Generated by tools/build_reading.py. Do not edit by hand.\n",
            encoding="utf-8",
        )

        if output_root.exists():
            shutil.rmtree(output_root)
        staging.rename(output_root)
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return diagnostics


def main() -> int:
    """Builds the site and reports unresolved repository Markdown links."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        diagnostics = build_site()
    except (FileExistsError, OSError, ValueError) as error:
        print(f"Build failed: {error}", file=sys.stderr)
        return 1

    lesson_count = len(discover_lessons(LESSON_ROOT, OUTPUT_ROOT))
    print(
        f"Built {lesson_count} lesson page(s), {lesson_count} share file(s), "
        f"and {OUTPUT_ROOT / 'index.html'}"
    )
    for diagnostic in diagnostics:
        stream = sys.stderr if diagnostic.startswith("WARNING: ") else sys.stdout
        print(diagnostic, file=stream)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
