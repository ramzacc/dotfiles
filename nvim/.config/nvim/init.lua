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

vim.keymap.set("n", "<leader>w", vim.cmd.write)
vim.keymap.set("n", "<leader>q", vim.cmd.quit)

vim.cmd.colorscheme("retrobox")

vim.api.nvim_create_autocmd({ "FocusGained", "BufEnter", "CursorHold" }, {
  command = "checktime",
})

vim.cmd.packadd("nvim.difftool")

-- Fuzzy finding
vim.pack.add({ "https://github.com/ibhagwan/fzf-lua" })
local fzf = require("fzf-lua")
fzf.setup({
  winopts = {
    height = 1.0,
    width = 1.0,
    row = 0,
    col = 0,
  },
})

vim.keymap.set("n", "<leader>ff", fzf.files)
vim.keymap.set("n", "<leader>fg", fzf.live_grep)
vim.keymap.set("n", "<leader>fb", fzf.buffers)
