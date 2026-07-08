-- Pandoc Lua filter for figure and table cross-references
-- Supports: {#fig-xxx}, {#tbl-xxx} IDs and @fig-xxx, @tbl-xxx references
-- Works with Pandoc 3.x

local fig_counter = 0
local tbl_counter = 0
local fig_ids = {}
local tbl_ids = {}

function Image(el)
  if el.identifier and el.identifier:match("^fig%-") then
    fig_counter = fig_counter + 1
    fig_ids[el.identifier] = fig_counter
    local prefix = pandoc.List({pandoc.Str("图 " .. fig_counter .. " ")})
    if #el.caption > 0 then
      el.caption = prefix .. el.caption
    else
      el.caption = prefix
    end
    return el
  end
  return el
end

function Table(el)
  if el.identifier and el.identifier:match("^tbl%-") then
    tbl_counter = tbl_counter + 1
    tbl_ids[el.identifier] = tbl_counter
    local prefix_block = pandoc.Plain({pandoc.Str("表 " .. tbl_counter .. " ")})
    -- In Pandoc 3.x, caption is a Caption object with a 'long' field (Blocks)
    if el.caption then
      if el.caption.long then
        -- Pandoc 3.x Caption
        el.caption.long:insert(1, prefix_block)
      elseif type(el.caption) == "table" then
        -- Older Pandoc: caption is a plain list
        table.insert(el.caption, 1, prefix_block)
      end
    end
  end
  return el
end

-- Extract @fig-xxx or @tbl-xxx from a string, handling trailing punctuation
local function extract_ref(text)
  local id = text:match("^@(fig%-[%w-]+)$")
  if id then return "fig", id, "" end
  id = text:match("^@(tbl%-[%w-]+)$")
  if id then return "tbl", id, "" end
  -- With trailing punctuation
  local tag, punc = text:match("^@(fig%-[%w-]+)(%p)$")
  if tag then return "fig", tag, punc end
  tag, punc = text:match("^@(tbl%-[%w-]+)(%p)$")
  if tag then return "tbl", tag, punc end
  return nil
end

function Str(el)
  local result = extract_ref(el.text)
  if not result then return el end
  local kind, tag, suffix = result[1], result[2], result[3] or ""
  if kind == "fig" and fig_ids[tag] then
    return pandoc.Str("图 " .. fig_ids[tag] .. suffix)
  elseif kind == "tbl" and tbl_ids[tag] then
    return pandoc.Str("表 " .. tbl_ids[tag] .. suffix)
  end
  return el
end
