-- Core plugin configs — Gruvbox Material god-tier rice
return {
  -- Take down unstable extras that cause errors
  { import = "lazyvim.plugins.extras.editor.snacks_picker", enabled = false },
  { "goolord/alpha-nvim", enabled = false },

  -- Set the colorscheme to gruvbox
  {
    "LazyVim/LazyVim",
    opts = {
      colorscheme = "gruvbox-material",
    },
  },

  -- Gruvbox Material — warm, rich, iconic
  {
    "sainnhe/gruvbox-material",
    lazy = false,
    priority = 1000,
    init = function()
      vim.g.gruvbox_material_enable_bold = 1
      vim.g.gruvbox_material_enable_italic = 1
      vim.g.gruvbox_material_transparent_background = 1
      vim.g.gruvbox_material_background = "hard"       -- hard/medium/soft
      vim.g.gruvbox_material_foreground = "material"    -- mix/material/original
      vim.g.gruvbox_material_better_performance = 1
      vim.g.gruvbox_material_diagnostic_text_highlight = 1
      vim.g.gruvbox_material_current_word = "grey background" -- bold/italic/grey background/none

      -- Set colorscheme immediately
      vim.cmd.colorscheme("gruvbox-material")
    end,
  },

  -- Neo-tree: file explorer (replaces netrw/nvim-tree)
  {
    "nvim-neo-tree/neo-tree.nvim",
    branch = "v3.x",
    dependencies = {
      "nvim-lua/plenary.nvim",
      "nvim-tree/nvim-web-devicons",
      "MunifTanjim/nui.nvim",
    },
    cmd = "Neotree",
    keys = {
      { "<leader>e", ":Neotree toggle<CR>", desc = "Toggle file tree" },
      { "<leader>E", ":Neotree focus<CR>", desc = "Focus file tree" },
    },
    opts = {
      filesystem = {
        filtered_items = {
          visible = false,
          hide_dotfiles = false,
          hide_gitignored = true,
        },
        use_libuv_file_watcher = true,
        follow_current_file = { enabled = true },
      },
      window = {
        position = "left",
        width = 30,
        popup = {
          size = { height = "75%", width = "60%" },
        },
      },
    },
  },

  -- Lualine: clean statusline with gruvbox
  {
    "nvim-lualine/lualine.nvim",
    event = "VeryLazy",
    opts = function(_, opts)
      opts.options.component_separators = { left = "", right = "" }
      opts.options.section_separators = { left = "", right = "" }
      opts.options.theme = "gruvbox-material"
    end,
  },

  -- Smear cursor — smooth animation
  {
    "sphamba/smear-cursor.nvim",
    opts = {
      smear_between_neighbor_lines = true,
      smear_between_buffers = true,
      smear_after_key = true,
      cursor_color = "#d65d0e", -- gruvbox orange
      stiffness = 0.6,
    },
  },

  -- Better icons
  {
    "nvim-tree/nvim-web-devicons",
    opts = { default = true },
  },
}
