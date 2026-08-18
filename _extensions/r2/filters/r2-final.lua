-- Append the R2 final-page block (Open Science Badges summary, License
-- chip · journal · year, DOI, ISSN/FORRT/MüCOS lines) to the end of HTML
-- output, matching the published R2 design. Values come from the merged
-- r2.* metadata. Also computes r2.badge-groups (Meta, runs for every
-- format) so template.tex can render the same badge summary for PDF.

local BADGE_FILES = {
  ["preregistered"]  = { file = "preregestered",  svg = "preregestered.png", label = "Preregistered" },
  ["open-materials"] = { file = "openmaterial",   svg = "openmaterial.png", label = "Open Materials" },
  ["open-data"]      = { file = "opendata",       svg = "opendata.png",     label = "Open Data" },
  ["open-code"]      = { file = "opencode",       svg = "opencode.png",     label = "Open Code" },
  ["codecheck"]      = { file = "codecheck",      svg = "codecheck.svg",   label = "CODECHECK" },
  ["openreview"]     = { file = "openreview",     svg = "openreview.svg",  label = "Open Peer Review" },
}

local function str(v) return v and pandoc.utils.stringify(v) or "" end

-- Ordered, active badge list: Prereg, Materials, Data, Code, Codecheck,
-- Reprocert (one of three variants depending on which of AI/Human are
-- true), Open Review. `ext` picks the icon file extension used in each
-- item's `file` field: "svg" (with extension, HTML) or "png" (bare
-- basename, extension added by the caller - LaTeX already appends .png).
local function activeBadges(r2meta, ext)
  local badges = r2meta.badges or {}
  local links  = r2meta["badge-links"] or {}
  local items = {}
  local function add(key)
    if badges[key] then
      local def = BADGE_FILES[key]
      local file = (ext == "svg") and def.svg or (def.file .. ".png")
      table.insert(items, { label = def.label, file = file, link = str(links[key]) })
    end
  end
  add("preregistered")
  add("open-materials")
  add("open-data")
  add("open-code")
  add("codecheck")
  local ai = badges["reprocert-ai"] == true
  local human = badges["reprocert-human"] == true
  if ai or human then
    local link = str(links["reprocert"])
    local file, label
    if ai and human then
      file, label = "reprocert_hai", "Reproducibility Certified (Human & AI)"
    elseif ai then
      file, label = "reprocert_ai", "Reproducibility Certified (AI)"
    else
      file, label = "reprocert_human", "Reproducibility Certified (Human)"
    end
    table.insert(items, { label = label, file = (ext == "svg") and (file .. ".svg") or (file .. ".png"), link = link })
  end
  add("openreview")
  return items
end

-- Groups adjacent badges sharing the same non-empty link into one row.
local function groupBadges(items)
  local groups = {}
  for _, it in ipairs(items) do
    local last = groups[#groups]
    if it.link ~= "" and last and last.link == it.link then
      table.insert(last.members, it)
    else
      table.insert(groups, { link = it.link, members = { it } })
    end
  end
  return groups
end

local function joinNames(names)
  local n = #names
  if n == 1 then return names[1] end
  if n == 2 then return names[1] .. " and " .. names[2] end
  local head = {}
  for i = 1, n - 1 do table.insert(head, names[i]) end
  return table.concat(head, ", ") .. ", and " .. names[n]
end

local function computeGroups(r2meta, ext)
  local groups = groupBadges(activeBadges(r2meta, ext))
  local result = {}
  for _, g in ipairs(groups) do
    local names, files = {}, {}
    for _, it in ipairs(g.members) do
      table.insert(names, it.label)
      table.insert(files, it.file)
    end
    table.insert(result, { label = joinNames(names), link = g.link, files = files })
  end
  return result
end

-- Populate r2.badge-groups (PNG filenames) so template.tex can render the
-- same "Open Science Badges" summary via $for(r2.badge-groups)$.
function Meta(meta)
  local r2meta = meta.r2
  if not r2meta then return meta end
  local groups = computeGroups(r2meta, "png")
  local metaGroups = {}
  for _, g in ipairs(groups) do
    local files = {}
    for _, f in ipairs(g.files) do
      table.insert(files, pandoc.MetaMap({ file = pandoc.MetaString(f) }))
    end
    table.insert(metaGroups, pandoc.MetaMap({
      label = pandoc.MetaString(g.label),
      link  = pandoc.MetaString(g.link),
      files = pandoc.MetaList(files),
    }))
  end
  r2meta["badge-groups"] = pandoc.MetaList(metaGroups)
  meta.r2 = r2meta
  return meta
end

function Pandoc(doc)
  if not FORMAT:match("html") then return doc end

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

  -- Open Science Badges summary (left-aligned, one row per link-group);
  -- omitted entirely if no badges are checked.
  local osBadges = ""
  local groups = computeGroups(r2meta, "svg")
  if #groups > 0 then
    local rows = {}
    for _, g in ipairs(groups) do
      local icons = {}
      for _, f in ipairs(g.files) do
        table.insert(icons, string.format('<img src="../../_extensions/r2/resources/badges/%s" alt="%s">', f, g.label))
      end
      local link = g.link ~= "" and string.format(' <a href="%s">%s</a>', g.link, g.link) or ""
      table.insert(rows, string.format(
        '<div class="os-badge-row"><div class="os-badge-icons">%s</div><div class="os-badge-label"><b>%s:</b>%s</div></div>',
        table.concat(icons), g.label, link))
    end
    osBadges = string.format(
      '<div class="r2-osbadges"><h3>Open Science Badges</h3><p class="lead">This work has received the following badges:</p>%s</div>',
      table.concat(rows))
  end

  local badge = "../../_extensions/r2/resources/license-cc-by.png"
  local doiline = ""
  if doi ~= "" then
    doiline = string.format('<div class="doi"><a href="https://doi.org/%s">doi.org/%s</a></div>', doi, doi)
  end
  local issntxt = issn ~= "" and string.format(" (ISSN: %s)", issn) or ""

  local html = string.format([[
<div class="r2-final">
  %s
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
    osBadges,
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
