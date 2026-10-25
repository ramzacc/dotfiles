vim.g.mapleader = " "
vim.g.netrw_banner = 0
vim.g.netrw_liststyle = 3
vim.g.netrw_list_hide = [[^\.git/$]]

vim.opt.tabstop = 2
vim.opt.shiftwidth = 2
vim.opt.expandtab = true

vim.opt.number = true
vim.opt.relativenumber = true
vim.opt.scrolloff = 8

vim.opt.ignorecase = true
vim.opt.smartcase = true

vim.opt.linebreak = true
vim.opt.breakindent = true

vim.opt.mouse = ""
vim.opt.showtabline = 0
vim.opt.laststatus = 3
vim.opt.fillchars = { diff = " ", fold = " ", eob = " " }
vim.opt.foldtext = ""

vim.opt.undofile = true
vim.opt.clipboard = "unnamedplus,unnamed"

vim.cmd.colorscheme("retrobox")
vim.api.nvim_set_hl(0, "netrwTreeBar", { link = "Comment" })
vim.api.nvim_set_hl(0, "netrwClassify", { link = "Comment" })

vim.api.nvim_create_autocmd({ "FocusGained", "BufEnter", "CursorHold" }, {
  command = "checktime",
})

vim.keymap.set("n", "<leader>w", vim.cmd.write)
vim.keymap.set("n", "<leader>q", vim.cmd.quit)
vim.keymap.set("n", "<leader>ft", "<cmd>Explore .<cr>")

vim.pack.add({
  "https://github.com/ibhagwan/fzf-lua",
  "https://github.com/sindrets/diffview.nvim",
})

-- Fuzzy finding
local fzf = require("fzf-lua")
fzf.setup({ winopts = { fullscreen = true } })

vim.keymap.set("n", "<leader>ff", fzf.files)
vim.keymap.set("n", "<leader>fg", fzf.live_grep)
vim.keymap.set("n", "<leader>fb", fzf.buffers)

-- Diffs
vim.api.nvim_set_hl(0, "DiffOldSide", { bg = "#3b1f22" })
vim.api.nvim_set_hl(0, "DiffNewSide", { bg = "#1f3626" })

local function setup_diff_window(_, window, context)
  local color = context.symbol == "a" and "DiffOldSide" or "DiffNewSide"

  vim.wo[window].foldcolumn = "0"
  vim.wo[window].statusline = "%t %m%=%l,%c  %P"
  vim.wo[window].winhl = table.concat({
    "DiffAdd:" .. color,
    "DiffChange:" .. color,
    "DiffText:" .. color,
    "DiffTextAdd:" .. color,
    "DiffDelete:Normal",
  }, ",")
end

local close_diff = { "n", "<leader>q", "<cmd>DiffviewClose<cr>" }

require("diffview").setup({
  use_icons = false,
  show_help_hints = false,
  signs = { fold_open = "▾ ", fold_closed = "▸ " },
  hooks = { diff_buf_win_enter = setup_diff_window },
  keymaps = { view = { close_diff }, file_panel = { close_diff } },
})

local function branch_name(picker_line)
  return picker_line:match("^[*+]?%s*(%S+)")
end

vim.keymap.set("n", "<leader>gd", function()
  fzf.git_branches({
    fzf_opts = { ["--no-multi"] = false, ["--multi"] = true },
    actions = {
      enter = function(selected)
        local branches = vim.tbl_map(branch_name, selected)
        vim.cmd.DiffviewOpen(table.concat(branches, ".."))
      end,
    },
  })
end)
