# Music downloads

Enclosure Music includes a Downloads page with spotDL, audio format selection, activity log and cancellation. The page follows the universal shell theme with labeled source and destination cards, persistent download actions, and a selectable activity log. Downloads require a nonempty link field. Successful download jobs refresh the library. The default audio format is OGG. Lyrics are looked up separately and do not depend on the download format. The default destination is ~/Music; add another destination using Add folder in the library.

spotDL uses the media package group or ~/.local/share/venvs/spotdl/bin/spotdl. The compatible environment can be created with requirements-spotdl.txt. Format conversion cannot improve source quality. Check the activity log for skipped tracks even after a successful exit.

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
for direct preview through the running Spotify desktop player. Preview in Spotify
starts the first listed track; clicking an undownloaded row plays that track.
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
