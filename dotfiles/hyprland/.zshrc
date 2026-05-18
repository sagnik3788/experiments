# If you come from bash you might have to change your $PATH.
# export PATH=$HOME/bin:/usr/local/bin:$PATH

export ZSH="$HOME/.oh-my-zsh"

ZSH_THEME="agnosterzak"

plugins=( 
    git
    dnf
    zsh-autosuggestions
    zsh-syntax-highlighting
)

source $ZSH/oh-my-zsh.sh

# check the dnf plugins commands here
# https://github.com/ohmyzsh/ohmyzsh/tree/master/plugins/dnf


# Fastfetch runs below (once per session) — this line was a duplicate
#pokemon-colorscripts --no-title -s -r | fastfetch -c $HOME/.config/fastfetch/config-pokemon.jsonc --logo-type file-raw --logo-height 10 --logo-width 5 --logo -

# Set-up FZF key bindings (CTRL R for fuzzy history finder)
source <(fzf --zsh)

HISTFILE=~/.zsh_history
HISTSIZE=10000
SAVEHIST=10000
setopt appendhistory

# Set-up icons for files/directories in terminal using lsd
alias ls='lsd'
alias l='ls -l'
alias la='ls -a'
alias lla='ls -la'
alias lt='ls --tree'
export PATH=$HOME/.npm-global/bin:$PATH

. "$HOME/.local/bin/env"
export PATH="$HOME/.tfenv/bin:$PATH"
export PATH=$PATH:/usr/local/go/bin
export GOPATH=$HOME/go
export PATH=$PATH:$GOPATH/bin

# opencode
export PATH=/home/sagnik/.opencode/bin:$PATH

# Android SDK
export ANDROID_HOME=$HOME/Android/Sdk
export PATH=$PATH:$ANDROID_HOME/emulator
export PATH=$PATH:$ANDROID_HOME/platform-tools
export PATH=$PATH:$ANDROID_HOME/cmdline-tools/latest/bin 
export PATH=$PATH:$HOME/android-studio/bin

# Entire CLI shell completion
autoload -Uz compinit && compinit && source <(entire completion zsh)
export GEMINI_API_KEY=AIzaSyCsZvio9Z2UIm9gSdc75GtyUdZMNVNWAMU
export PATH=$PATH:/usr/local/cuda-13.1/bin
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/usr/local/cuda-13.1/lib64

# Starship prompt
export VIMRUNTIME=/usr/share/nvim/runtime   # fix nvim runtime path
eval "$(/home/sagnik/.local/bin/starship init zsh)"

# Fastfetch on new terminal (once per session)
if [ -z "$FASTFETCH_RAN" ]; then
    export FASTFETCH_RAN=1
    fastfetch -c ~/.config/fastfetch/config.jsonc
fi
export GROQ_API_KEY=""
