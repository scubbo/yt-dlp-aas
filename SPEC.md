# Cookie Authentication Feature Specification

## Problem

YouTube now requires authentication to download videos, returning "Sign in to confirm you're not a bot" errors. The yt-dlp tool can use browser cookies to authenticate, but these cookies need to be provided to the containerized yt-dlp-aas service.

## Goal

Allow users to easily provide their YouTube cookies to yt-dlp-aas without leaving the YouTube website or manually exporting cookie files.

## Current Architecture

- Python HTTP server (`http.server.SimpleHTTPRequestHandler`)
- Single endpoint: `POST /download` accepts `{url, filename?}`
- Static UI at `/` with a simple form
- Downloads run asynchronously via `multiprocessing.Pool`
- yt-dlp is invoked via its Python API (`YoutubeDL` class)
- Runs in a Docker container on Kubernetes

## Proposed Approaches

### Approach 1: Bookmarklet

A JavaScript bookmarklet that the user runs while on youtube.com. The bookmarklet extracts YouTube cookies from the current page context and POSTs them to the yt-dlp-aas server.

#### How it works

1. User adds a bookmarklet to their browser's bookmarks bar
2. User navigates to any youtube.com page (while logged in)
3. User clicks the bookmarklet
4. JavaScript runs in YouTube's context, reads `document.cookie`
5. Bookmarklet POSTs cookies to `https://<yt-dlp-aas-host>/cookies`
6. Server stores cookies and uses them for subsequent downloads

#### Implementation requirements

**Server-side:**
- New endpoint: `POST /cookies` - accepts cookies and stores them
- New endpoint: `GET /cookies/status` - returns whether valid cookies are stored
- Cookie storage mechanism (file on disk, in-memory, or environment variable)
- Modify `download()` function to pass `cookiefile` or `cookiesfrombrowser` option to `YoutubeDL`
- CORS headers to allow cross-origin POST from youtube.com

**Client-side (bookmarklet):**
- JavaScript that reads `document.cookie`
- POSTs to configured yt-dlp-aas endpoint
- Visual feedback (alert or injected DOM element) confirming success/failure
- The bookmarklet URL must be configurable (user's yt-dlp-aas instance)

**UI updates:**
- Display bookmarklet installation instructions on the main page
- Show current cookie status (valid/expired/missing)
- Provide a "generate bookmarklet" feature where user enters their yt-dlp-aas URL

#### Pros
- No browser extension installation required
- Works on any browser that supports bookmarklets
- User stays on YouTube - very low friction
- Simple implementation

#### Cons
- Bookmarklet URL is visible and contains the server address
- User must manually click bookmarklet to refresh cookies
- Some browsers restrict bookmarklet functionality
- CORS configuration required

#### Cookie format considerations

`document.cookie` returns cookies as a semicolon-separated string: `name1=value1; name2=value2`. This needs to be converted to Netscape cookie format for yt-dlp:
```
# Netscape HTTP Cookie File
.youtube.com	TRUE	/	TRUE	0	cookie_name	cookie_value
```

Alternatively, pass cookies directly to yt-dlp via the Python API using the `http_headers` option or by writing to a temp file.

---

### Approach 2: Browser Extension

A browser extension that monitors YouTube cookies and automatically syncs them to the yt-dlp-aas server.

#### How it works

1. User installs the browser extension
2. User configures the extension with their yt-dlp-aas server URL
3. Extension monitors cookies for youtube.com domain
4. When cookies change (login, refresh), extension POSTs them to the server
5. Optional: extension adds a "Download with yt-dlp-aas" button to YouTube pages

#### Implementation requirements

**Server-side:**
- Same as bookmarklet approach: `POST /cookies`, `GET /cookies/status`
- Cookie storage mechanism
- Modify `download()` to use stored cookies
- CORS headers for extension requests

**Extension (Chrome/Firefox):**
- Manifest v3 (Chrome) / Manifest v2 (Firefox) configuration
- Permissions: `cookies` for youtube.com, `storage` for settings
- Options page to configure server URL
- Background script to monitor cookie changes via `chrome.cookies.onChanged`
- Content script (optional) to inject download button on YouTube pages
- Popup UI showing connection status

**UI updates (yt-dlp-aas):**
- Link to extension installation (Chrome Web Store / Firefox Add-ons, or direct .crx/.xpi)
- Display cookie status

#### Pros
- Automatic cookie sync - user doesn't need to remember to refresh
- Can add YouTube integration (download button on video pages)
- More polished user experience
- Can handle cookie rotation automatically

#### Cons
- Requires extension installation (higher friction)
- Must maintain extension for Chrome and Firefox separately
- Extension store submission process (or self-hosted installation)
- More complex implementation
- Users may be wary of installing extensions that access cookies

---

## Server-Side Changes (Common to Both)

### New endpoints

```
POST /cookies
Content-Type: application/json
Body: { "cookies": "cookie_string_here" }
Response: 200 OK / 400 Bad Request

GET /cookies/status
Response: { "valid": true/false, "expires": "ISO timestamp or null" }
```

### Cookie storage

Options (in order of simplicity):
1. **File on disk** - Write to `/tmp/youtube_cookies.txt` in Netscape format. Simple, persists across requests, but lost on container restart.
2. **Persistent volume** - Mount a PVC for cookie storage. Survives restarts.
3. **In-memory with TTL** - Store in a global variable. Lost on restart but no disk I/O.

### yt-dlp integration

Modify the `download()` function:
```python
ydl_opts = {
    # ... existing options ...
    'cookiefile': '/path/to/cookies.txt',  # if using file storage
    # OR
    'http_headers': {'Cookie': cookie_string},  # if passing directly
}
```

### CORS

Add CORS headers for `/cookies` endpoint to allow requests from `https://www.youtube.com`:
```python
self.send_header("Access-Control-Allow-Origin", "https://www.youtube.com")
self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
self.send_header("Access-Control-Allow-Headers", "Content-Type")
```

---

## Final Implementation: Bookmarklet Approach

After detailed analysis, we're implementing the **bookmarklet approach** with the following design decisions:

### Core Design Principles

- **Fire-and-forget**: User clicks bookmarklet, gets minimal feedback ("Download started" or "Download failed")
- **No cookie storage**: Fresh cookies sent with every request from active YouTube session
- **Simple server integration**: Extend existing `/download` endpoint, don't create new endpoints
- **Minimal validation**: Only user calling it, so no rate limiting or complex validation needed
- **Browser extension can be added later**: Current approach keeps door open for future enhancement

### Technical Implementation Details

#### Bookmarklet JavaScript (Minified)

```javascript
javascript:(async()=>{try{await fetch('https://yt-dlp-aas.scubbo.org/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:location.href,cookies:document.cookie})});alert('Download started')}catch(e){alert('Download failed')}})()
```

**Design decisions:**
- IIFE wrapper for proper async/await and error handling
- No client-side validation - server handles URL validation
- Simple browser alerts for success/failure
- Raw cookie string transmission (no parsing on client)
- Target URL hardcoded (user-specific instance)

#### Server-Side Changes

**Modified `download()` function signature:**
```python
def download(url, filename=None, cookies=None):
```

**Cookie integration in `ydl_opts`:**
```python
if cookies:
    ydl_opts['http_headers'] = {'Cookie': cookies}
```

**Updated POST handling:**
- Extract `cookies = body.get('cookies')` from JSON
- Pass cookies to async pool: `self.pool.apply_async(download, (url,), {'filename': filename, 'cookies': cookies})`

#### CORS Implementation

**New `do_OPTIONS()` method:**
```python
def do_OPTIONS(self):
    self.send_response(HTTPStatus.OK)
    self.send_header("Access-Control-Allow-Origin", "https://www.youtube.com")
    self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
    self.send_header("Access-Control-Allow-Headers", "Content-Type")
    self.send_header('Content-Length', 0)
    self.end_headers()
```

**CORS headers added to all responses:**
```python
self.send_header("Access-Control-Allow-Origin", "https://www.youtube.com")
self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
self.send_header("Access-Control-Allow-Headers", "Content-Type")
```

#### API Extension

**Enhanced `/download` endpoint:**
```json
{
  "url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "filename": "optional custom filename",
  "cookies": "name1=value1; name2=value2"
}
```

- `cookies` field is optional for backward compatibility
- Existing UI continues to work unchanged
- Bookmarklet sends all three fields

### User Experience Flow

1. User navigates to any YouTube video page while logged in
2. User clicks bookmarklet from bookmarks bar
3. JavaScript extracts current URL (`location.href`) and cookies (`document.cookie`)
4. POST request sent to `/download` endpoint with cookies
5. Server returns `HTTPStatus.ACCEPTED` and starts async download
6. User sees "Download started" alert
7. Download runs asynchronously on server
8. User retrieves file via manual server access (SSH/file system)

### File Organization

- **Implementation details**: `docs/bookmarklet.md`
- **Future improvements**: `docs/TODO.md`
- **Main specification**: `SPEC.md` (this file)

## Security Considerations

- **Restrictive CORS**: Only allow requests from `https://www.youtube.com`
- **No authentication needed**: Single-user deployment, trusted bookmarklet
- **HTTPS recommended**: For production use (HTTP acceptable for trusted environments)
- **No cookie logging**: Cookies passed directly to yt-dlp, not stored or logged
- **Minimal validation**: Single-user scenario reduces attack surface
