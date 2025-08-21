# Git Cheatsheet

## Keep your branch up to date

before pushing, make sure your branch is up to date:

```bash
git fetch origin
git rebase origin/main

git add <files> # if needed
git rebase --continue
```

## Pushing your changes

once up to date:

```bash
git push
```

if git rejects with a non-fast-forward issue:

- run the **fetch + rebase** commands above, and push again.
- if you know you want to overwrite change history:

```bash
git push --force
```

## Pulling updates

by default:

```bash
git pull --rebase
```

- pulls new commits from `origin/main` and rebases your local commits on top.
- keeps history linear

## Undo mistakes


```bash
# undo last commit (keep changes staged)
git reset --soft HEAD~1 

# undo last commit (throw away changes)
git reset --hard HEAD~1

# unstage a file
git restore --staged <file>
```

## Inspecting


```bash
# show branch + status
git status

# show commit log
git log --oneline --graph --decorate
```
