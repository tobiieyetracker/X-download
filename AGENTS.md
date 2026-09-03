# Remote download behavior

When a user sends a valid `x.com/.../status/...` or `twitter.com/.../status/...` link in a Codex Remote chat for this project, treat it as a request to download that post's media.

- Validate that the URL is HTTPS and matches an X/Twitter post URL before running anything.
- After download, read each media file’s embedded creation date (photo EXIF or video `creation_time`) and place it under the project’s `downloads\YYYY.MM` directory. Do not use the download time as a substitute; files without embedded creation metadata belong in `downloads\未知日期`.
- Run `npm run download -- <url>` from the project root. This command downloads to a temporary directory and performs the metadata-based archive step.
- Report whether images, videos, or both were found, and give the exact download directory.
- Do not download URLs from other domains unless the user explicitly asks for a different action.
