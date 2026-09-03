# Download workflow notes

This file is documentation only. It is not an execution policy and does not grant permission to run downloads automatically.

The project provides a Windows Electron client and command-line scripts for downloading media from HTTPS X/Twitter post URLs. The desktop client validates the URL before starting the downloader.

The `npm run download -- <url>` command runs the local downloader from the project root. The temporary task files are archived under the project’s `downloads` directory according to embedded media dates: `downloads\YYYY.MM`, or `downloads\未知日期` when no creation metadata is present.

The downloader reads photo EXIF or video `creation_time` locally for this archive step. Before sharing a working copy, remove the `downloads`, `.electron-profile`, and other local runtime artifacts.
