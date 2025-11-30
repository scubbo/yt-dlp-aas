This package puts [yt-dlp](https://github.com/yt-dlp/yt-dlp) behind an HTTP-callable server, with a simple web UI at `/`.

**Motivation:** I had a little snippet of bash that I could run on one of my [`*arr` Pods](https://wiki.servarr.com/) to install the `yt-dlp` CLI tool and then use it to download the audio of a video at a given URL. That _worked_, but was awkward - especially having to reinstall the tool any time a Pod was reinitialized. With this setup, I can deploy a light image alongside the Arr Pods that can be invoked over HTTP to download whatever URL I'm interested in, without having to do a `kubectl exec` to shell into the existing pods.

There are _tons_ of improvements that could be made to this, such as:
* not hard-coding the audio format (I've picked the one that appears to work best for my [Jellyfin](https://en.wikipedia.org/wiki/Jellyfin) setup), or indeed allowing the passthrough of oher customizations.
* running this process as a Kubernetes job, or some other separated long-running job mechanism
  * exposing logs more-easily
* using a more secure and robust server implementation than `http.server`
* filename customization (using the `--output` flag)
* Testing :P

# Customization

Environment variables:
* `DOWNLOAD_DIR` sets the directory into-which to download files (defaults to `.`)
* `PORT` sets the port to listen on (default to `8000`)

Request payload:
* `url` (required) - video URL to download
* `filename` (optional) - desired output filename (e.g. `song.m4a`); defaults to yt-dlp's inferred name

The API only accepts YouTube URLs over http(s) (`youtube.com`, `www.youtube.com`, or `youtu.be`).
