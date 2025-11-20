#!/bin/sh

SCRIPT_DIR="$(dirname "$(realpath "$0")")"
PROJECTS_DIR="~/Projects"
PROJECTS=(
    "yt-dlp"
    "bandcamp-dl"
    "ws4kp"
    "ffxi/server"
    "ffxi/xiloader"
)

update_repo() {
    repo="$1"

    repo=$(eval echo "$repo")  # expand ~
    if [ ! -d "$repo/.git" ]; then
        echo "Skipping $repo — not a git repository."
        return
    fi

    cd "$repo" || return 1

    # Determine branches
    current_branch=$(git rev-parse --abbrev-ref HEAD)

    default_branch=$(
        git remote show origin 2>/dev/null |
        awk '/HEAD branch/ {print $NF}'
    )

    if [ -z "$default_branch" ]; then
        echo "ERROR: Could not determine default branch for $repo"
        return 1
    fi

    echo "Repo: $repo"
    echo "Current branch: $current_branch"
    echo "Default branch: $default_branch"

    # Update current branch
    echo "→ Updating current branch: $current_branch"
    git fetch --all --prune
    git pull --ff-only || echo "WARNING: Could not fast-forward $current_branch"

    # If current branch IS the default, we're done
    if [ "$current_branch" = "$default_branch" ]; then
        echo "✓ Already on default branch; update complete."
        return 0
    fi

    # Switch to remote default branch
    echo "→ Switching to default branch: $default_branch"
    git checkout "$default_branch" || return 1
    git pull --ff-only || echo "WARNING: Could not fast-forward $default_branch"

    # Switch back to working branch
    echo "→ Returning to working branch: $current_branch"
    git checkout "$current_branch" || return 1

    echo "✓ Repo updated on both $current_branch and $default_branch"
}


echo "/usr/bin/apt update"
sudo /usr/bin/apt update

echo "/usr/bin/apt upgrade"
sudo /usr/bin/apt upgrade -y

echo "/usr/bin/apt autoremove"
sudo /usr/bin/apt autoremove -y

for repo in "${PROJECTS[@]}"; do
    update_rep "$PROJECTS_DIR/$repo"
done

echo "Discord updater"
"$SCRIPT_DIR/discord-updater.sh"
