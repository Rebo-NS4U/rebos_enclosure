#!/usr/bin/env python3
"""Graphical front end for the verified Enclosure development commands."""
import os
from pathlib import Path
import shlex
import subprocess
import sys
import threading

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GLib, Gtk
import develop

PRIMARY = [
    ('check', 'Check', 'Check the project for problems. This does not change your desktop.'),
    ('deploy', 'Apply local changes', 'Install the changes in this checkout. Preview first; keep your preferences.'),
    ('update', 'Update', 'Get desktop updates from GitHub. Preview first; keep your preferences.'),
]

SECTIONS = {
    'Overview': [
        ('status', 'Repository status', 'See your branch, changed files and recent commits.'),
        ('diff', 'Review changes', 'Read changes before staging or installing them.'),
        ('hardware', 'Hardware information', 'Detect this machine and preview its setup plan.'),
        ('configs', 'Personal settings', 'Open your personal configuration folder.')],
    'Desktop': [
        ('update-preview', 'Preview update', 'See what an update from GitHub would change.'),
        ('preview', 'Preview local installation', 'See what the files in this checkout would install.'),
        ('organize-preview', 'Preview file organization', 'See how existing files would be grouped.'),
        ('organize', 'Organize files', 'Group installed settings and source using a recovery journal.')],
    'Development': [
        ('stage', 'Stage files', 'Choose explicit repository paths for the next commit.'),
        ('hashes', 'Refresh checksums', 'Update the payload inventory after reviewing source changes.'),
        ('commit', 'Commit staged changes', 'Test the staged source and create a local commit.'),
        ('pull', 'Pull source updates', 'Update a clean checkout from its upstream branch.'),
        ('push', 'Push commits to GitHub', 'Publish local commits to the configured upstream branch.')],
}
CONFIRM = {
    'update': 'Download and install the desktop update?',
    'deploy': 'Install this checkout’s files on your desktop?',
    'organize': 'Move installed files into the managed layout?',
    'pull': 'Pull source updates into this checkout?',
    'push': 'Publish this branch’s local commits to GitHub?',
    'hashes': 'Rewrite payload checksums from the reviewed source files?',
    'commit': 'Test and commit the currently staged files?',
}
PREVIEWS = {'update': 'update-preview', 'deploy': 'preview', 'organize': 'organize-preview',
            'push': 'status', 'commit': 'diff', 'pull': 'status'}


class DevelopmentWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title='Enclosure Development')
        self.set_default_size(780, 650)
        self.busy = False
        self.connect('close-request', self.close_requested)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for edge in ('top', 'bottom', 'start', 'end'):
            getattr(outer, 'set_margin_' + edge)(18)
        self.set_child(outer)
        title = Gtk.Label(label='Enclosure Development', xalign=0)
        title.add_css_class('title-1')
        outer.append(title)
        outer.append(Gtk.Label(label='Check your work, apply local changes, or get updates.', xalign=0))
        branch = develop.verify_checkout()
        location = Gtk.Label(label=f'{branch}  ·  {develop.ROOT}', xalign=0, selectable=True)
        location.add_css_class('dim-label')
        outer.append(location)
        self.controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        outer.append(self.controls)
        for name, label, description in PRIMARY:
            self.controls.append(self.action_row(name, label, description))
        advanced = Gtk.Expander(label='Advanced — Git, files and maintenance')
        self.controls.append(advanced)
        advanced_scroll = Gtk.ScrolledWindow(min_content_height=240)
        advanced.set_child(advanced_scroll)
        advanced_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        advanced_scroll.set_child(advanced_box)
        stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        switcher = Gtk.StackSwitcher(stack=stack, halign=Gtk.Align.START)
        advanced_box.append(switcher)
        advanced_box.append(stack)
        for section, actions in SECTIONS.items():
            page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            for name, label, description in actions:
                page.append(self.action_row(name, label, description))
            stack.add_titled(page, section.lower(), section)
        inputs = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.paths = Gtk.Entry(placeholder_text='Repository paths to stage, e.g. README.md "path with spaces"', hexpand=True)
        self.message = Gtk.Entry(placeholder_text='Commit message', hexpand=True)
        inputs.append(self.paths)
        inputs.append(self.message)
        page.append(inputs)
        self.status = Gtk.Label(label='Ready. Start with Check if you are unsure.', xalign=0)
        outer.append(self.status)
        scroll = Gtk.ScrolledWindow(vexpand=True, min_content_height=180)
        self.output = Gtk.TextView(editable=False, monospace=True, cursor_visible=False)
        self.output.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scroll.set_child(self.output)
        self.details = Gtk.Expander(label='Technical details', vexpand=True)
        self.details.set_child(scroll)
        outer.append(self.details)

    def action_row(self, name, label, description):
        row = Gtk.Box(spacing=16)
        button = Gtk.Button(label=label, width_request=200)
        button.connect('clicked', lambda _button: self.choose(name))
        row.append(button)
        row.append(Gtk.Label(label=description, xalign=0, wrap=True, hexpand=True))
        return row

    def action_label(self, name):
        actions = PRIMARY + [action for section in SECTIONS.values() for action in section]
        return next((label for action, label, _ in actions if action == name), name)

    def close_requested(self, *_):
        if self.busy:
            self.status.set_text('An action is running. Keep this window open until it finishes.')
        return self.busy

    def append(self, text):
        buffer = self.output.get_buffer()
        buffer.insert(buffer.get_end_iter(), text)
        self.output.scroll_to_iter(buffer.get_end_iter(), 0, False, 0, 0)
        return False

    def choose(self, name):
        if self.busy:
            return
        extra = []
        if name == 'stage':
            try:
                paths = shlex.split(self.paths.get_text())
                if not paths:
                    raise ValueError('Enter the repository paths to stage first.')
                extra = ['--', *paths]
            except ValueError as error:
                self.status.set_text(str(error))
                return
        if name == 'commit':
            message = self.message.get_text().strip()
            if not message:
                self.status.set_text('Enter a commit message first.')
                return
            extra = ['-m', message]
        if name in CONFIRM:
            def confirm(success=True):
                if not success:
                    return
                self.details.set_expanded(True)
                dialog = Gtk.MessageDialog(transient_for=self, modal=True,
                    message_type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.OK_CANCEL,
                    text=CONFIRM[name], secondary_text='Review the output below before continuing.')
                def response(widget, answer):
                    widget.destroy()
                    if answer == Gtk.ResponseType.OK:
                        self.execute(name, extra)
                dialog.connect('response', response)
                dialog.present()
            if name in PREVIEWS:
                self.execute(PREVIEWS[name], [], confirm)
            else:
                confirm()
        else:
            self.execute(name, extra)

    def execute(self, name, extra, callback=None):
        self.busy = True
        self.controls.set_sensitive(False)
        label = self.action_label(name)
        self.status.set_text(label + ' — working…')
        self.append('\n── ' + name + ' ──\n')
        def worker():
            success = False
            try:
                command = [sys.executable, '-u', str(Path(__file__).with_name('develop.py')), name, *extra]
                with subprocess.Popen(command, cwd=develop.ROOT, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, text=True, errors='replace',
                                      env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1',
                                           'GIT_TERMINAL_PROMPT': '0', 'GIT_PAGER': 'cat'},
                                      stdin=subprocess.DEVNULL) as process:
                    for line in process.stdout:
                        GLib.idle_add(self.append, line)
                    success = process.wait() == 0
            except OSError as error:
                GLib.idle_add(self.append, str(error) + '\n')
            GLib.idle_add(finished, success)
        def finished(success):
            self.busy = False
            self.controls.set_sensitive(True)
            self.status.set_text((label + ' — finished.') if success else
                                 (label + ' could not finish. See Technical details for the reason.'))
            if not success:
                self.details.set_expanded(True)
            if callback:
                callback(success)
            return False
        threading.Thread(target=worker, daemon=True).start()


def main():
    app = Gtk.Application(application_id='org.enclosure.Development')
    def activate(application):
        window = application.get_active_window() or DevelopmentWindow(application)
        window.present()
    app.connect('activate', activate)
    return app.run([])


if __name__ == '__main__':
    sys.exit(main())
