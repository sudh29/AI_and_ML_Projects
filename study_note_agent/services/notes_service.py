import subprocess
import markdown
import logging


class NotesService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def save_to_apple_notes(self, title: str, markdown_content: str) -> bool:
        """Saves generated notes to Apple Notes using AppleScript."""

        # Apple Notes prefers HTML for formatting
        html_content = markdown.markdown(markdown_content)

        # AppleScript that accepts arguments via standard input to avoid quote-escaping hell
        applescript = """
        on run argv
            set noteName to item 1 of argv
            set noteBody to item 2 of argv
            
            tell application "Notes"
                tell default account
                    make new note at folder "Notes" with properties {name:noteName, body:noteBody}
                end tell
            end tell
        end run
        """

        try:
            subprocess.run(
                ["osascript", "-", title, html_content],
                input=applescript.encode("utf-8"),
                check=True,
                capture_output=True,
            )
            self.logger.info(f"Successfully saved '{title}' to Apple Notes.")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to save to Apple Notes: {e.stderr.decode()}")
            return False
