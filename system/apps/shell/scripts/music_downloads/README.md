# Music downloads

Enclosure Music includes a Downloads page with spotDL, audio format selection, activity log and cancellation. The page follows the universal shell theme with labeled source and destination cards, persistent download actions, and a selectable activity log. Downloads require a nonempty link field. Successful download jobs refresh the library. The default audio format is OGG. Lyrics are looked up separately and do not depend on the download format. The default destination is ~/Music; add another destination using Add folder in the library.

spotDL uses the media package group or ~/.local/share/venvs/spotdl/bin/spotdl. The compatible environment can be created with requirements-spotdl.txt. Format conversion cannot improve source quality. Check the activity log for skipped tracks even after a successful exit.

The legacy Music Installer launcher is hidden; use Music for playback and downloads. Closing Music hides it, preserving playback and running downloads.

Music uses the universal shell background surface. Transparent styles reveal the desktop through the window and follow the global compositor blur settings; opaque styles stay solid. Adjust background style and blur in the shared Appearance settings.
