-- Append the R2 final-page block (License chip · journal · year, DOI,
-- ISSN/FORRT/MüCOS lines) to the end of HTML output, matching the
-- published R2 design. Values come from the merged r2.* metadata.
function Pandoc(doc)
  if not FORMAT:match("html") then return doc end

  local function str(v) return v and pandoc.utils.stringify(v) or "" end
  local r2meta = doc.meta.r2
  if not r2meta then return doc end

  local journal = str(r2meta.journal)
  local year    = str(r2meta.year)
  local doi     = str(r2meta.doi)
  local issn    = str(r2meta.issn)
  local licurl  = str(r2meta["license-url"])
  local forrt   = str(r2meta["forrt-url"]);  if forrt == "" then forrt = "https://forrt.org" end
  local mucos   = str(r2meta["mucos-url"]);  if mucos == "" then mucos = "https://www.uni-muenster.de/MueCOS" end
  local home    = str(r2meta.homepage);      if home  == "" then home  = "#" end

  local badge = "../../_extensions/r2/resources/license-cc-by.png"
  local doiline = ""
  if doi ~= "" then
    doiline = string.format('<div class="doi"><a href="https://doi.org/%s">doi.org/%s</a></div>', doi, doi)
  end
  local issntxt = issn ~= "" and string.format(" (ISSN: %s)", issn) or ""

  local html = string.format([[
<div class="r2-final">
  <div class="line1">
    <span>License</span>
    %s<img src="%s" alt="%s" />%s
    <span class="sep">|</span><span>%s</span><span class="sep">|</span><span>%s</span>
  </div>
  %s
  <div class="part"><em>%s%s</em> is part of the<br/>
    Framework for Open and Reproducible Research Training (FORRT; <a href="%s">forrt.org</a>)<br/>
    and the M&#252;nster Center for Open Science (M&#252;COS; <a href="%s">uni-muenster.de/MueCOS</a>)
  </div>
  <div class="orgs">
    <a href="%s">M&#252;COS</a><span class="sep"> | </span><a href="%s">FORRT</a><span class="sep"> | </span><a href="%s">R2</a>
  </div>
  <div class="rule"></div>
</div>]],
    licurl ~= "" and string.format('<a href="%s">', licurl) or "",
    badge,
    str(r2meta.license),
    licurl ~= "" and "</a>" or "",
    journal, year,
    doiline,
    journal, issntxt,
    forrt, mucos,
    mucos, forrt, home)

  table.insert(doc.blocks, pandoc.RawBlock("html", html))
  return doc
end
