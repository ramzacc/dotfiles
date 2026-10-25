vim.g.mapleader = " "
vim.g.loaded_netrw = 1
vim.g.loaded_netrwPlugin = 1

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

vim.opt.undofile = true
vim.opt.clipboard = "unnamedplus,unnamed"

vim.cmd.colorscheme("retrobox")

vim.api.nvim_create_autocmd({ "FocusGained", "BufEnter", "CursorHold" }, {
  command = "checktime",
})

vim.keymap.set("n", "<leader>w", vim.cmd.write)
vim.keymap.set("n", "<leader>q", vim.cmd.quit)

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
require("diffview").setup({
  use_icons = false,
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
