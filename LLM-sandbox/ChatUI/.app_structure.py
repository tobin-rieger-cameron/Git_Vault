# imports


_log = logging.getLogger(__name__)
_COMMANDS = [ "/draft", "/done", "/tags", "/wikilinks", "/folder", "/review", "/ingest", "/web", "/model", "/explorer", "/palette", ]
_FILE_TREE_POLL_SECONDS = 2.0
CSS = ( """ Screen { background: %(bg)s; color: %(text)s; } Header { background: %(surface)s; color: %(text)s; } HeaderTitle { content-align: left middle; } #statusbar { height: %(border_row)s; background: %(surface)s; color: %(muted)s; padding: %(padding_tight)s; } #statusbar .value { color: %(accent)s; text-style: bold; } #sidebar { width: %(sidebar_width)s; border-right: solid %(border)s; background: %(bg)s; } #sidebar.collapsed { width: 0; border-right: none; display: none; } #file-search { height: %(sidebar_head_height)s; background: %(surface)s; color: %(text)s; border: none; padding: 0 1; } #file-search:focus { background-tint: transparent; } FilePicker { height: 1fr; scrollbar-size: 0 0; background: %(bg)s; color: %(text)s; } FilePicker > .tree--cursor { background: %(accent)s; color: %(accent_dark)s; text-style: bold; } FilePicker > .tree--highlight { color: %(accent)s; } #middle { width: 1fr; border-right: solid %(border)s; background: %(bg)s; } #preview-scroll { scrollbar-size: 0 0; background: %(bg)s; } #preview-body { padding: %(padding_comfortable)s; background: %(bg)s; color: %(text)s; } #chat { width: %(chat_width)s; background: %(bg)s; } #log { height: 1fr; scrollbar-size: 0 0; background: %(bg)s; color: %(text)s; } SuggestionChecklist, SuggestionChecklist:focus { height: auto; max-height: %(checklist_max_height)s; background: %(bg)s; color: %(text)s; border: none; padding: 0; scrollbar-size: 0 0; background-tint: transparent; } SuggestionChecklist > .option-list--option-highlighted { background: %(accent)s; color: %(accent_dark)s; } SuggestionChecklist > .option-list--separator { color: %(bg)s; background: %(bg)s; } #inputbar { height: %(input_bar_height)s; padding: 0 0 %(breathing_row)s 0; background: %(surface)s; } #caret { width: %(caret_width)s; color: %(accent)s; text-style: bold; } #cmd { background: %(surface)s; color: %(text)s; border: none; padding: 0; } #cmd:focus { background-tint: transparent; } """ % { "bg": theme.BG, "surface": theme.SURFACE, "border": theme.BORDER, "muted": theme.MUTED, "text": theme.TEXT, "accent": theme.ACCENT, "accent_dark": theme.ACCENT_DARK, "sidebar_width": theme.SIDEBAR_WIDTH, "chat_width": theme.CHAT_WIDTH, "caret_width": theme.CARET_WIDTH, "checklist_max_height": theme.CHECKLIST_MAX_HEIGHT, "border_row": theme.BORDER_ROW, "breathing_row": theme.BREATHING_ROW, "sidebar_head_height": theme.SIDEBAR_HEAD_HEIGHT, "input_bar_height": theme.INPUT_BAR_HEIGHT, "padding_tight": theme.PADDING_TIGHT, "padding_comfortable": theme.PADDING_COMFORTABLE, })
BINDINGS = [
    Binding("f2", "toggle_sidebar", "Toggle explorer"),
    Binding("ctrl+f", "focus_search", "Find file"),
    Binding("tab", "accept_suggestion_or_focus_next", "Accept suggestion", priority=True, show=False),
]

# ---- top level, local functions
def _diff_highlight(old: str, new: str) -> Text:
    """Highlight the parts of `new` added since `old`."""
def _truncate(text: str, limit: int) -> str:
def _match_suggestion_kind(text: str) -> str | None:
    """Return which suggestion kind, if any, the text refers to."""
def _write_hint(app: "ChatApp", text: str) -> None:
    """Write a muted informational hint line to the chat log and transcript."""
def _write_prompt(app: "ChatApp", text: str) -> None:
    """Echo the user's submitted input as a chat log line."""
def _write_answer(app: "ChatApp", text: str) -> None:
    """Write the model's answer as a bright chat log line."""
def _write_log(app: "ChatApp", text: str) -> None:
    """Write a status line, styled as label:detail if the text contains a colon."""
def _format_tool_args(args: dict) -> str:
    """Render tool-call kwargs as a truncated, comma-joined string for status display."""


class ChatApp(App):
    """Textual application shell."""

    def __init__(self, vault : Vault, retriever : Retriever, model : ModelClient, settings : Settings, transcript : TranscriptWriter) -> None:
        super().__init__()
        self.vault          = vault
        self.retriever      = retriever
        self.model          = model
        self.settings       = settings
        self.transcript     = transcript
        self.tools          = build_registry(vault, retriever, model, settings)
        self._review_index  = 0
        self._drafting      = False
        self._web_enabled   = False

        self._active_file               : File | None                           = None
        self._selected_folder           : Path | None                           = None
        self._folder_tag_plan           : list[tuple[Path, FolderTagChange]]    = []
        self._history                   : list[tuple[str, str]]                 = []
        self._classification            : ClassificationSuggestion | None       = None
        self._checklist                 : SuggestionChecklist | None            = None
        self._checklist_kind            : str | None                            = None
        self._checklist_wikilink_kind   : dict[str, str]                        = {}
        self._review_queue              : list[ReviewQuestion]                  = []

    # ---- public ----
    def compose(self) -> ComposeResult:
        """Build the sidebar, preview, chat, and status bar layout."""
    def on_mount(self) -> None:
        """Wire up initial focus and links, then kick off ingest and file-tree polling."""
    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        """Yield the built-in system commands, minus the theme switcher."""
    def action_toggle_sidebar(self) -> None:
    def action_focus_search(self) -> None:
    def action_accept_suggestion_or_focus_next(self) -> None:
        """Accept the command input's inline suggestion, or move focus to the next widget."""
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Preview the selected file, or mark a selected folder for /tags."""
    @on(Input.Changed, "#file-search")
    def on_search_changed(self, event: Input.Changed) -> None:
    @on(Input.Submitted, "#file-search")
    def on_search_submitted(self, event: Input.Submitted) -> None:
        """Apply the search filter, then preview the best match and reset the search box."""
    def on_suggestion_checklist_toggled(self, _event: SuggestionChecklist.Toggled) -> None:

    # ---- private ----
    def _update_statusbar(self) -> None:
    def _poll_file_tree(self) -> None:
    def _open_wikilink_target(self, target: str) -> None:
        """Navigate to the vault file a clicked committed [[wikilink]] points to, if it exists."""
    def _preview_file(self, path: Path) -> None:
    def _set_active_file(self, file: File) -> None:
        """Switch the active file, resetting drafting, classification, review, and checklist state."""
    def _refresh_preview(self) -> None:
    def _preview_content(self) -> tuple[str, list[tuple[str, int, int]]]:
        """Return the active file's body, overlaid with pending checklist edits if one is open."""
    @staticmethod
    def _folder_tag_change_text(change: FolderTagChange) -> Text:
    def _write_statusbar(self, text: str) -> None:
        """Flash an ephemeral message to the status bar only, without touching the chat log or transcript."""
    def _ask_review_question(self) -> None:
    def _resolve_review(self, answer: str) -> None:
        """Handle a review answer: show a hint, stop early, advance, or mark the file reviewed."""
    def _handle_model_command(self, text: str) -> None:
        """Report the active model, or switch to the one named in `/model <name>`."""

    # ---- public (async) ----
    async def on_key(self, event: events.Key) -> None:
        """Clear and unfocus the file search, or cancel an open checklist, on escape."""
    @on(Input.Submitted, "#cmd")
    async def on_cmd_submitted(self, event: Input.Submitted) -> None:
        """Route submitted input to the open checklist, an in-progress review, a command, or ask."""

    # ---- private (async) ----
    async def _ask(self, question: str) -> None:
        """Stream an answer to `question` through the tool registry, then append it to history."""
        def on_status(text: str) -> None:
        def on_tool_call(name: str, args: dict) -> None:
        def on_token(token: str) -> None:
    async def _start_or_continue_draft(self, subject: str | None) -> None:
        """Start a new draft on `subject`, or continue drafting the active file."""
    async def _revise_active_draft(self, instruction: str) -> None:
        """Rewrite the active draft's body wholesale per an instruction."""
    async def _finish_draft(self) -> None:
        """Save the active draft to the vault and reindex it."""
    async def _ensure_classification(self) -> ClassificationSuggestion | None:
        """Return the cached classification suggestion for the active file, computing it if stale."""
    async def _show_suggestion_checklist(self, kind: str) -> None:
    async def _start_wikilink_walkthrough(self) -> None:
        """Suggest new inline and see-also wikilinks for the active file and open a checklist for them."""
    async def _show_folder_tag_checklist(self) -> None:
        """Open a checklist of tag changes needed to match the selected folder's files to its structure."""
    async def _open_checklist( self, kind: str, items: list[str], initial_checked: set[int] | None = None, columns: list[tuple[str, Text]] | None = None,) -> None:
        """Mount a checklist of `items`, replacing any that's already open."""
    async def _close_checklist(self) -> None:
    async def _dismiss_checklist(self, reason: str) -> None:
    async def _apply_checklist(self) -> None:
        """Apply the checked items for the open checklist's kind, then reindex and refresh."""
    async def _start_review(self) -> None:
        """List files due for review if none is active, else generate and begin its review questions."""
    async def _handle_ingest(self) -> None:
