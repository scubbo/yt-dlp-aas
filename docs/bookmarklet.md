# Bookmarklet Implementation Guide

## Overview

This document contains detailed implementation information about the yt-dlp-aas bookmarklet feature.

## Bookmarklet Code

### Final Minified Version

```javascript
javascript:(async()=>{try{await fetch('https://yt-dlp-aas.scubbo.org/download',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:location.href,cookies:document.cookie})});alert('Download started')}catch(e){alert('Download failed')}})()
```

### Unminified Version (for development/debugging)

```javascript
javascript:(async () => {
    try {
        await fetch('https://yt-dlp-aas.scubbo.org/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: location.href,
                cookies: document.cookie
            })
        });
        alert('Download started');
    } catch (e) {
        alert('Download failed');
    }
})()
```

## Installation

1. Copy the minified bookmarklet code above
2. Right-click your browser's bookmarks bar
3. Select "Add Page" or "Add Bookmark"
4. Name it something like "yt-dlp Download"
5. Paste the JavaScript code in the URL/location field
6. Save

## Usage

1. Navigate to any YouTube video while logged into your Google account
2. Click the bookmarklet
3. Wait for "Download started" confirmation
4. Download will be processed asynchronously on the server
5. Retrieve downloaded files via your normal server access method

## Technical Details

### Data Flow

```
YouTube Page (user logged in)
    ↓ (bookmarklet click)
Extract: location.href + document.cookie
    ↓
POST to: https://yt-dlp-aas.scubbo.org/download
    ↓
Server: async download with cookies
    ↓
Response: HTTP 202 Accepted
    ↓
Browser: "Download started" alert
```

### Payload Format

```json
{
    "url": "https://www.youtube.com/watch?v=VIDEO_ID",
    "cookies": "cookie_name1=value1; cookie_name2=value2; ..."
}
```

### Error Handling

- **Network failures**: Caught by try/catch, shows "Download failed"
- **Server errors**: Returned as HTTP error status, caught by try/catch
- **Invalid URLs**: Validated by server, returned as 400 error
- **Missing cookies**: Server will attempt download without auth (likely fails at YouTube)

### Browser Compatibility

- **Chrome**: Full support for fetch API in bookmarklets
- **Firefox**: Full support for fetch API in bookmarklets
- **Safari**: Should work, but less tested
- **Mobile browsers**: May have bookmarklet length/compatibility limitations

### Security Considerations

- **CORS**: Server only accepts requests from https://www.youtube.com
- **No persistent storage**: Cookies sent fresh with each request
- **HTTPS**: Recommended for production deployments
- **Single-user design**: No authentication mechanism required

## Debugging

### Common Issues

1. **"Download failed" immediately**
   - Check server connectivity
   - Verify CORS headers are properly set
   - Check browser console for detailed error messages

2. **Download accepted but video fails to download**
   - Verify user is logged into YouTube
   - Check server logs for yt-dlp specific errors
   - Ensure YouTube isn't blocking the download

3. **Bookmarklet not working on certain YouTube pages**
   - Ensure you're on a standard video watch page (/watch?v=)
   - Current implementation only handles standard video URLs

### Server-Side Debugging

Check logs for:
- CORS preflight failures (OPTIONS requests)
- yt-dlp authentication errors
- Network connectivity issues to YouTube

### Client-Side Debugging

Open browser developer console and look for:
- Network request failures
- CORS errors
- JavaScript syntax errors in bookmarklet

## Limitations

- Only works on standard YouTube video pages (/watch?v=)
- Requires manual server access for file retrieval
- No real-time download progress feedback
- No support for playlists or YouTube Shorts
- Firefox-specific implementation (tested primarily on Firefox)