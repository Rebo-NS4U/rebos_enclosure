# Music downloads

Enclosure Music includes a Downloads page with spotDL and Zotify, audio format selection, browser sign-in, activity log and cancellation. Completed jobs refresh the library. The default destination is ~/Music; add another destination using Add folder in the library.

spotDL uses the media package group or ~/.local/share/venvs/spotdl/bin/spotdl. The compatible environment can be created with requirements-spotdl.txt. Zotify is optional and requires ~/.local/share/venvs/zotify/bin/python with Zotify installed. Existing browser authentication files under ~/.config/zotify-gui and Zotify credentials are reused; no credentials are shipped. Web API configuration remains in ~/.config/zotify-gui/spotify-client.json. Format conversion cannot improve source quality. Check the activity log for skipped tracks even after a successful exit.

The legacy Music Installer launcher is hidden; use Music for playback and downloads. Closing Music hides it, preserving playback and running downloads.
