# SDK Sharing Workflow

This repository includes `sdk_share.py` to prepare a Yocto workspace for Git upload and to restore it after cloning.

## Build Target

Build the image with:

```bash
bitbake -v fsl-image-network-full-cmdline
```

## Prepare The Tree For Upload

Run this from the repository root:

```bash
./sdk_share.py prepare
```

What it does:

- Removes disposable Yocto build output such as `tmp`, `cache`, `sstate-cache`, and `deploy` while keeping `build-frdm/conf` intact.
- Finds every file larger than 50 MB and writes the list to `bigFileIndex.txt`.
- Creates a tar archive for each large file, splits it into 50 MB parts, stores the parts next to the original file, and removes the original file.
- Updates the root `.gitignore` so the original large files stay out of Git while the split archive parts can be committed.

Use `--dry-run` first if you want to inspect the actions:

```bash
./sdk_share.py prepare --dry-run
```

## Restore After Cloning

Run this from the repository root after cloning:

```bash
./sdk_share.py unpack
```

This recreates the original large files in their original directories from the split archive parts tracked in Git.

Use `--force` if a file already exists and you want to replace it:

```bash
./sdk_share.py unpack --force
```

## Transfer To Another GitHub Repository

Run:

```bash
./sdk_share.py transfer
```

If you want the upload split into multiple push sessions, run:

```bash
./sdk_share.py transfer-batched
```

What it does:

- Creates a clean staging copy under `/tmp`.
- Prompts for the target GitHub repository URL and a GitHub token if they were not passed on the command line.
- Stores that information outside the repo in `~/.config/sdk-share/config.json` with user-only permissions so it is not uploaded with Git.
- Copies the repo into the temporary staging directory.
- Optionally removes regenerable build artifacts such as `build-frdm/tmp/` from the live workspace before the staged copy is created.
- Optionally removes top-level build directories such as `build-frdm/` from the staged copy before packaging and upload.
- Runs the same cleanup and large-file packaging workflow on the staged copy.
- Pushes the staged copy to the target repository.

`transfer-batched` does the same thing, but it initializes a fresh Git repository in the staged copy and pushes it in multiple commits. The default batch target is 500 MB per push session.

Useful options:

```bash
./sdk_share.py transfer --dry-run
./sdk_share.py transfer --target-repo https://github.com/openhd-bsp/linux-imx8mp-sc
./sdk_share.py transfer --target-repo https://github.com/openhd-bsp/linux-imx8mp-sc --remove-source-build-artifacts
./sdk_share.py transfer --target-repo https://github.com/openhd-bsp/linux-imx8mp-sc --remove-build-dirs
./sdk_share.py transfer-batched --target-repo https://github.com/openhd-bsp/linux-imx8mp-sc --push-batch-mb 500
./sdk_share.py transfer-batched --target-repo https://github.com/openhd-bsp/linux-imx8mp-sc --push-batch-mb 500 --remove-source-build-artifacts
```
