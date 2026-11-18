# Music downloads

Enclosure Music includes a Downloads page with spotDL, audio format selection, activity log and cancellation. The page follows the universal shell theme with labeled source and destination cards, persistent download actions, and a selectable activity log. Downloads require a nonempty link field. Successful download jobs refresh the library. The default audio format is OGG. Lyrics are looked up separately and do not depend on the download format. The default destination is ~/Music; add another destination using Add folder in the library.

spotDL uses the media package group or ~/.local/share/venvs/spotdl/bin/spotdl. The compatible environment can be created with requirements-spotdl.txt. Format conversion cannot improve source quality. Check the activity log for skipped tracks even after a successful exit.

The download service preloads spotDL when Music opens and reuses those imports
across jobs. Each job runs in its own process group, retaining bounded cancellation.
Downloads use two threads. Public track metadata is cached for six hours under
$XDG_CACHE_HOME/enclosure/music/tracks (default ~/.cache); playlist contents are
always resolved again. No Spotify sign-in or official API credentials are added.
Custom executable wrappers remain supported without preloading. The warm runtime
starts on the next normal Music service launch; active playback is not restarted.

The legacy Music Installer launcher is hidden; use Music for playback and downloads. Closing Music hides it, preserving playback and running downloads.

Music uses the universal shell background surface. Transparent styles reveal the desktop through the window and follow the global compositor blur settings; opaque styles stay solid. Adjust background style and blur in the shared Appearance settings.

## Daily Mix snapshots

The Daily Mixes page receives track-list metadata from the existing Spicetify
Lyrics Plus adapter. Keep Spotify and Music open and visit Spotify's Made for You
page once per Spotify session so visible Daily Mix cards can be discovered.
Discovered mixes refresh every hour; complete results are delivered locally
on port 19838. Failed refreshes retain the last good version. Save current keeps
an immutable, dated local snapshot, deduplicated by playlist and track-list version.
View tracks opens individual songs in Spotify. Snapshots contain metadata, not
local audio downloads. No Spotify credentials are sent to Music.

Run `python3 scripts/setup_lyrics_plus.py` from the shell source and then
`spicetify apply -n` to prepare the adapter. An already running Spotify client
loads the updated extension on its next normal launch; setup does not restart it.
The desktop API is internal and can change; an empty page remains in the waiting
state until the integration delivers mixes. Saved snapshots remain available offline.

Use **Update Spotify playlists** on the Daily Mixes page to request an immediate
refresh from Spotify. This updates Music’s current mixes. Requests bypass the hourly
schedule, show progress, and time out after 90 seconds if Spotify is unavailable.


Each current mix and saved snapshot has a **Download** action. It prepares the
Downloads page with a single Spotify playlist link. spotDL resolves the playlist's
current contents, including when downloading from an older saved snapshot. Choose the audio format and press Start download; existing
files are skipped and the activity log reports failures. Downloads are stored in
versioned folders under the XDG Music directory's Daily Mixes folder, using Spotify
track IDs as filenames to identify local audio reliably. Library scanning runs on
completion, including cancellation or partial failure, so available tracks can play.

The mix preview shows downloaded availability and a scrollable track list. Use
Play downloaded or select an available track to play in mix order through Music's
shared player (pause, seek, previous/next and queue). Missing tracks are enabled
for direct preview through the running Spotify desktop player. Each mix card has a **Preview random** button, available before opening its track
list. Every press picks a random song from that mix and avoids immediately repeating
the last preview when another song is available. Clicking an undownloaded row in
the track list still previews that specific track.
No spotDL job, audio-file download or library write is performed. Open Spotify
and sign in before previewing; unavailable playback is reported without silently
starting a download. Local playback pauses only after Spotify accepts the request.
Spotify controls subsequent streaming playback and account/region restrictions
apply. Spotify may manage its own normal streaming buffer/cache.

Cancel stops the current download's process group. If the downloader or a child
ignores termination, the service forces that group to stop after a two-second
grace period. The UI shows Cancelled after completion and permits another job;
existing downloaded files remain available. Closing the service also cancels its job.


Music navigation is a wrapping top bar rather than a sidebar. Tabs divide the
full available width evenly, with balanced rows and a full-width final row on
narrower windows. Daily Mixes uses
Current/Saved category tabs and a responsive card browser. Wide windows show the
selected track preview alongside the browser; narrower windows give the preview
full width with a Mixes back action. The header stays compact and only cards and
tracks scroll, so preview controls remain reachable. Track title and artist use
separate themed lines; download and Spotify-preview behavior are unchanged.

Downloaded Daily Mix folders appear in the separate **Downloaded Mixes** section,
including existing downloads. Names use the two most frequent artists, with the
original Daily Mix label and song count beneath each card. Similar names gain a
readable mix/version label. Folder hashes remain internal; files are not moved.
Ordinary playlists stay in Playlists; Daily Mixes remains the discovery section.

Click anywhere on a library song row to play or pause it. The favorite and queue
buttons retain their separate actions.

## YouTube cookie files

Downloads accepts an optional **YouTube cookie file** path, with Browse and Clear
controls. Sign into YouTube in your browser and complete any requested age
verification first. Export that session as a Netscape-format `cookies.txt` using
[yt-dlp's cookie guidance](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp).
Select the file before starting a download. Music validates the path and format
and passes it to spotDL with `--cookie-file`, including Daily Mix downloads.
A blank field preserves unauthenticated downloading. The selection lasts while
Music is open; no cookies are imported into Music's settings or shipped payload.
Keep cookie files private (for example, `chmod 600 /path/to/cookies.txt`), outside
the checkout. They grant access to your signed-in session. Refresh the export
if the session expires. Cookies do not remove YouTube account/age restrictions
or guarantee that a particular video can be downloaded.

Playlist suggestions: open a downloaded playlist to request recommended tracks from its original Spotify playlist through the desktop integration. Spotify must be open and signed in. Suggestions show the album cover when Spotify provides one. Play streams through Spotify without downloading. Add downloads the track using spotDL into that playlist's folder (or links an existing local copy); additions survive rescans. Existing playlist songs and duplicate artist/title pairs are excluded. If the source is unavailable, load its Spotify playlist link in Spotify playlists first. The updated Lyrics Plus adapter must be prepared and applied; an already running Spotify client loads the extension on its next launch. No Spotify credentials cross the local bridge.

The cookie-file field remembers its selected path in local music download settings. Browse or edit the path to update it; Clear forgets the selection. The original cookies.txt stays in place and its contents are not copied into settings. Download-time validation reports missing or invalid files.

## Sync a downloaded Spotify playlist

Open a downloaded playlist and choose **Sync Spotify playlist**, then **Sync playlist** on Downloads. The saved Spotify source is resolved again; new tracks download and local playlist membership mirrors the latest result, in Spotify order. Songs removed from Spotify stay on disk and in Songs, but no longer appear in that playlist, including after rescans. An empty source leaves an empty playlist. Failed or cancelled jobs retain the previous membership. This is a manual, one-way update from Spotify; it does not change Spotify itself. Playlists need one saved Spotify source (downloads made from a single Spotify playlist link record it).

## Replace Spotify with Music

On a downloaded playlist with one linked Spotify source, **Replace Spotify with Music** replaces the remote playlist contents with the local playlist's tracks in their current order, including clearing an empty playlist. This changes Spotify immediately when the signed-in desktop integration receives the command; audio files remain untouched. Every track must have a known Spotify identity; unknown or ambiguous local songs block the whole request before any write. Spotify must grant edit permission: Spotify-owned Daily Mixes and other read-only playlists cannot be replaced.

The bridge uses Spotify's desktop playlist editor and reads the resulting playlist back before reporting success. It keeps existing rows that are already in the requested relative order. Permission/network errors are displayed; failure during a later batch may leave partial remote contents. Check Spotify before retrying an unconfirmed operation. Acknowledgement retries do not repeat writes within the same Spotify session. No automatic background or two-way sync runs. Prepare/apply the updated Lyrics Plus extension; an already running Spotify client loads it on its next normal launch.
