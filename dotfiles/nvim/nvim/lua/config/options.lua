-- Options are automatically loaded before lazy.nvim startup
-- Default options that are always set: https://github.com/LazyVim/LazyVim/blob/main/lua/lazyvim/config/options.lua
-- Add any additional options here

-- Window transparency (requires kitty/terminal transparency)
vim.opt.winblend = 10
vim.opt.pumblend = 15

-- Line numbers
vim.opt.number = true
vim.opt.relativenumber = true

-- Better UI
vim.opt.termguicolors = true
vim.opt.cursorline = true
vim.opt.cursorlineopt = "number"

-- Smooth scrolling
vim.opt.scrolloff = 8
vim.opt.sidescrolloff = 8

-- Better completion
vim.opt.completeopt = { "menu", "menuone", "noselect" }
vim.opt.pumheight = 10
vim.opt.pumwidth = 25

-- Disable unused providers
vim.g.loaded_node_provider = 0
vim.g.loaded_perl_provider = 0
vim.g.loaded_python3_provider = 0
vim.g.loaded_ruby_provider = 0

-- Faster UI
vim.opt.timeoutlen = 300
vim.opt.updatetime = 200
vim.opt.redrawtime = 100

-- Force LazyVim to use telescope (prevents snacks picker errors)
vim.g.lazyvim_picker = "telescope"
