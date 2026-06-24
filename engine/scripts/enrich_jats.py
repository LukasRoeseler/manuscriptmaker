"""Inject R2-specific front matter into Pandoc-generated JATS.

Pandoc's `jats_publishing` writer emits a solid <article-meta> (title,
contributors, abstract, keywords, references) but does not expose the
journal's DOI, article categories, lay summary, funding, or license. This
step adds them in place so the JATS galley is a faithful archival record.

Idempotent: re-running on an already-enriched file is a no-op for each
element (it checks before inserting).

Usage:
    python engine/scripts/enrich_jats.py manuscripts/R2.2025.001/article.xml manuscripts/R2.2025.001
"""
from __future__ import annotations

import sys
from pathlib import Path
from xml.dom import minidom

import r2meta

JATS_NS = None  # Pandoc JATS is in the null namespace


def _text_el(doc, tag, text, **attrs):
    el = doc.createElement(tag)
    for k, v in attrs.items():
        el.setAttribute(k, str(v))
    if text is not None:
        el.appendChild(doc.createTextNode(str(text)))
    return el


def _first(parent, tag):
    nodes = parent.getElementsByTagName(tag)
    return nodes[0] if nodes else None


def enrich(xml_path: Path, manuscript_dir: Path) -> None:
    meta = r2meta.load(manuscript_dir)
    r2 = meta.get("r2", {})
    doc = minidom.parse(str(xml_path))

    article = _first(doc, "article")
    if article is None:
        raise SystemExit("No <article> element found — not a JATS file?")

    # article-type attribute on <article> (override Pandoc's default "other")
    if r2.get("article-type"):
        article.setAttribute("article-type", str(r2["article-type"]).lower())

    front = _first(doc, "front")
    article_meta = _first(doc, "article-meta")
    journal_meta = _first(doc, "journal-meta")

    # --- journal-meta: journal title, publisher, issn -----------------
    if journal_meta is not None:
        if r2.get("journal") and not journal_meta.getElementsByTagName("journal-title"):
            grp = doc.createElement("journal-title-group")
            grp.appendChild(_text_el(doc, "journal-title", r2["journal"]))
            journal_meta.insertBefore(grp, journal_meta.firstChild)
        if r2.get("issn") and not journal_meta.getElementsByTagName("issn"):
            journal_meta.appendChild(_text_el(doc, "issn", r2["issn"]))
        if r2.get("publisher") and not journal_meta.getElementsByTagName("publisher"):
            pub = doc.createElement("publisher")
            pub.appendChild(_text_el(doc, "publisher-name", r2["publisher"]))
            journal_meta.appendChild(pub)

    if article_meta is None:
        doc.writexml(open(xml_path, "w", encoding="utf-8"))
        return

    # --- DOI as <article-id pub-id-type="doi"> ------------------------
    if r2.get("doi"):
        has_doi = any(n.getAttribute("pub-id-type") == "doi"
                      for n in article_meta.getElementsByTagName("article-id"))
        if not has_doi:
            article_meta.insertBefore(
                _text_el(doc, "article-id", r2["doi"], **{"pub-id-type": "doi"}),
                article_meta.firstChild)

    # --- article categories: article-type + discipline ----------------
    if not article_meta.getElementsByTagName("article-categories"):
        cats = doc.createElement("article-categories")
        for kind, val in (("heading", r2.get("article-type")),
                          ("subject", r2.get("discipline"))):
            if val:
                grp = doc.createElement("subj-group")
                grp.setAttribute("subj-group-type", kind)
                grp.appendChild(_text_el(doc, "subject", val))
                cats.appendChild(grp)
        if cats.hasChildNodes():
            # article-categories must precede title-group
            tg = _first(article_meta, "title-group")
            article_meta.insertBefore(cats, tg if tg else article_meta.firstChild)

    # --- volume / elocation -------------------------------------------
    if r2.get("volume") and not article_meta.getElementsByTagName("volume"):
        article_meta.appendChild(_text_el(doc, "volume", r2["volume"]))
    if r2.get("article-id") and not article_meta.getElementsByTagName("elocation-id"):
        article_meta.appendChild(_text_el(doc, "elocation-id", r2["article-id"]))

    # --- permissions / license ----------------------------------------
    if r2.get("license") and not article_meta.getElementsByTagName("permissions"):
        perm = doc.createElement("permissions")
        lic = doc.createElement("license")
        if r2.get("license-url"):
            lic.setAttribute("xlink:href", r2["license-url"])
        lic.appendChild(_text_el(doc, "license-p",
                                 f"Published under the {r2['license']} license."))
        perm.appendChild(lic)
        article_meta.appendChild(perm)

    # --- lay summary as a second <abstract abstract-type="..."> -------
    if r2.get("lay-summary"):
        already = any(a.getAttribute("abstract-type") == "summary"
                      for a in article_meta.getElementsByTagName("abstract"))
        if not already:
            lay = doc.createElement("abstract")
            lay.setAttribute("abstract-type", "summary")
            lay.appendChild(_text_el(doc, "title", "Lay Summary"))
            lay.appendChild(_text_el(doc, "p", str(r2["lay-summary"]).strip()))
            kw = _first(article_meta, "kwd-group")
            article_meta.insertBefore(lay, kw) if kw else article_meta.appendChild(lay)

    # --- custom-meta-group: badges + recommended citation -------------
    cmg = doc.createElement("custom-meta-group")

    def _cmeta(name, value):
        cm = doc.createElement("custom-meta")
        cm.appendChild(_text_el(doc, "meta-name", name))
        cm.appendChild(_text_el(doc, "meta-value", value))
        cmg.appendChild(cm)

    badges = r2.get("badges", {}) or {}
    earned = [k for k, v in badges.items() if v]
    if earned:
        _cmeta("open-science-badges", ", ".join(earned))
    if r2.get("recommended-citation"):
        _cmeta("recommended-citation", str(r2["recommended-citation"]).strip())
    if cmg.hasChildNodes():
        article_meta.appendChild(cmg)

    with open(xml_path, "w", encoding="utf-8") as fh:
        doc.writexml(fh)
    print(f"Enriched JATS: {xml_path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: enrich_jats.py <article.xml> [manuscript-dir]", file=sys.stderr)
        sys.exit(2)
    xml = Path(sys.argv[1])
    mdir = Path(sys.argv[2]) if len(sys.argv) > 2 else xml.parent
    enrich(xml, mdir)
