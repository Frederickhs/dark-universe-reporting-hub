import os
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from config_loader import get_report_config, load_config
from folder_manager import (
    get_input_folders,
    get_output_folders,
    open_folder,
)
from log_manager import (
    configure_logging,
    log_error,
    log_folder_opened,
    log_report_result,
    log_report_start,
)
from report_runner import ReportResult, run_report


APP_WIDTH = 760
APP_HEIGHT = 650

COLOR_BACKGROUND = "#F3F3F3"
COLOR_CARD = "#FFFFFF"
COLOR_PRIMARY = "#0078D4"
COLOR_PRIMARY_ACTIVE = "#005A9E"
COLOR_RUN_ALL = "#107C10"
COLOR_RUN_ALL_ACTIVE = "#0B6413"
COLOR_TEXT = "#1F1F1F"
COLOR_SECONDARY_TEXT = "#5C5C5C"
COLOR_SUCCESS = "#107C10"
COLOR_WARNING = "#986F0B"
COLOR_FAILED = "#C42B1C"
COLOR_READY = "#555555"

HUB_ROOT = Path(__file__).resolve().parent.parent


class ReportingHubApp:
    """Main desktop interface for the Dark Universe Reporting Hub."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.config = load_config()

        log_folder = self.config["hub"].get("log_folder", "Logs")
        self.logger, self.log_file = configure_logging(log_folder)

        self.is_running = False
        self.report_buttons: list[tk.Button] = []
        self.control_buttons: list[tk.Button] = []

        self.root.title(self.config["hub"]["name"])
        self.root.geometry(f"{APP_WIDTH}x{APP_HEIGHT}")
        self.root.resizable(False, False)
        self.root.configure(bg=COLOR_BACKGROUND)
        self.root.protocol("WM_DELETE_WINDOW", self.close_application)

        self.configure_styles()
        self.build_interface()

        self.logger.info("Reporting Hub application opened.")

    def configure_styles(self) -> None:
        """Configure the progress bar appearance."""

        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Hub.Horizontal.TProgressbar",
            troughcolor="#D9D9D9",
            background=COLOR_PRIMARY,
            bordercolor="#D9D9D9",
            lightcolor=COLOR_PRIMARY,
            darkcolor=COLOR_PRIMARY,
        )

    def build_interface(self) -> None:
        """Build the main application window."""

        title_label = tk.Label(
            self.root,
            text="Dark Universe Reporting Hub",
            font=("Segoe UI", 23, "bold"),
            bg=COLOR_BACKGROUND,
            fg=COLOR_TEXT,
        )
        title_label.pack(pady=(24, 4))

        subtitle_label = tk.Label(
            self.root,
            text="Run reports and access report folders from one location.",
            font=("Segoe UI", 11),
            bg=COLOR_BACKGROUND,
            fg=COLOR_SECONDARY_TEXT,
        )
        subtitle_label.pack(pady=(0, 16))

        report_card = tk.Frame(
            self.root,
            bg=COLOR_CARD,
            highlightbackground="#D0D0D0",
            highlightthickness=1,
        )
        report_card.pack(fill="x", padx=42, pady=(0, 12))

        report_title = tk.Label(
            report_card,
            text="Reports",
            font=("Segoe UI", 14, "bold"),
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
        )
        report_title.pack(pady=(16, 10))

        for report_key in self.config["run_order"]:
            report = get_report_config(self.config, report_key)

            button = self.create_primary_button(
                report_card,
                text=f"Run {report['display_name']}",
                command=lambda key=report_key: self.start_report_run([key]),
            )
            button.pack(pady=5)

            self.report_buttons.append(button)

        run_all_button = self.create_primary_button(
            report_card,
            text="Run All Reports",
            command=lambda: self.start_report_run(
                self.config["run_order"]
            ),
            background=COLOR_RUN_ALL,
            active_background=COLOR_RUN_ALL_ACTIVE,
        )
        run_all_button.pack(pady=(10, 18))

        self.report_buttons.append(run_all_button)

        folder_card = tk.Frame(
            self.root,
            bg=COLOR_CARD,
            highlightbackground="#D0D0D0",
            highlightthickness=1,
        )
        folder_card.pack(fill="x", padx=42, pady=(0, 12))

        folder_title = tk.Label(
            folder_card,
            text="Folders and Logs",
            font=("Segoe UI", 14, "bold"),
            bg=COLOR_CARD,
            fg=COLOR_TEXT,
        )
        folder_title.pack(pady=(14, 10))

        folder_button_frame = tk.Frame(
            folder_card,
            bg=COLOR_CARD,
        )
        folder_button_frame.pack(pady=(0, 14))

        input_button = self.create_secondary_button(
            folder_button_frame,
            text="Input Folders",
            command=self.show_input_folders,
        )
        input_button.grid(row=0, column=0, padx=5, pady=4)

        output_button = self.create_secondary_button(
            folder_button_frame,
            text="Output Folders",
            command=self.show_output_folders,
        )
        output_button.grid(row=0, column=1, padx=5, pady=4)

        log_button = self.create_secondary_button(
            folder_button_frame,
            text="Reporting Hub Logs",
            command=self.open_hub_logs,
        )
        log_button.grid(row=0, column=2, padx=5, pady=4)

        self.control_buttons.extend(
            [input_button, output_button, log_button]
        )

        status_card = tk.Frame(
            self.root,
            bg=COLOR_BACKGROUND,
        )
        status_card.pack(fill="x", padx=42, pady=(2, 0))

        self.status_label = tk.Label(
            status_card,
            text="Ready",
            font=("Segoe UI", 11, "bold"),
            bg=COLOR_BACKGROUND,
            fg=COLOR_READY,
        )
        self.status_label.pack(pady=(4, 8))

        self.progress_bar = ttk.Progressbar(
            status_card,
            style="Hub.Horizontal.TProgressbar",
            mode="determinate",
            maximum=100,
            length=670,
        )
        self.progress_bar.pack()

        self.summary_label = tk.Label(
            status_card,
            text="No reports have been run during this session.",
            font=("Segoe UI", 9),
            bg=COLOR_BACKGROUND,
            fg=COLOR_SECONDARY_TEXT,
            wraplength=670,
            justify="center",
        )
        self.summary_label.pack(pady=(8, 8))

        exit_button = tk.Button(
            self.root,
            text="Exit",
            command=self.close_application,
            font=("Segoe UI", 10),
            width=14,
            relief="groove",
            cursor="hand2",
        )
        exit_button.pack(pady=(2, 12))

        self.control_buttons.append(exit_button)

    def create_primary_button(
        self,
        parent: tk.Widget,
        text: str,
        command,
        background: str = COLOR_PRIMARY,
        active_background: str = COLOR_PRIMARY_ACTIVE,
    ) -> tk.Button:
        """Create a standard report button."""

        return tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", 11, "bold"),
            width=48,
            height=2,
            bg=background,
            fg="white",
            activebackground=active_background,
            activeforeground="white",
            relief="flat",
            cursor="hand2",
        )

    def create_secondary_button(
        self,
        parent: tk.Widget,
        text: str,
        command,
    ) -> tk.Button:
        """Create a standard folder button."""

        return tk.Button(
            parent,
            text=text,
            command=command,
            font=("Segoe UI", 10),
            width=18,
            height=2,
            bg="#E8E8E8",
            fg=COLOR_TEXT,
            activebackground="#D0D0D0",
            relief="groove",
            cursor="hand2",
        )

    def show_input_folders(self) -> None:
        """Open the Input Folders selection window."""

        input_folders = get_input_folders(self.config)

        self.show_folder_window(
            window_title="Input Folders",
            folders=input_folders,
            use_button_name=True,
        )

    def show_output_folders(self) -> None:
        """Open the Output Folders selection window."""

        output_folders = get_output_folders(self.config)

        self.show_folder_window(
            window_title="Output Folders",
            folders=output_folders,
            use_button_name=False,
        )

    def show_folder_window(
        self,
        window_title: str,
        folders: list[dict[str, str]],
        use_button_name: bool,
    ) -> None:
        """Create a secondary window containing folder shortcuts."""

        folder_window = tk.Toplevel(self.root)
        folder_window.title(window_title)
        folder_window.geometry("620x650")
        folder_window.resizable(False, True)
        folder_window.configure(bg=COLOR_BACKGROUND)
        folder_window.transient(self.root)

        title_label = tk.Label(
            folder_window,
            text=window_title,
            font=("Segoe UI", 20, "bold"),
            bg=COLOR_BACKGROUND,
            fg=COLOR_TEXT,
        )
        title_label.pack(pady=(20, 5))

        instruction_label = tk.Label(
            folder_window,
            text="Select a folder to open it in File Explorer.",
            font=("Segoe UI", 10),
            bg=COLOR_BACKGROUND,
            fg=COLOR_SECONDARY_TEXT,
        )
        instruction_label.pack(pady=(0, 14))

        current_report_name = None

        for folder_info in folders:
            report_name = folder_info["report_name"]

            if report_name != current_report_name:
                current_report_name = report_name

                section_label = tk.Label(
                    folder_window,
                    text=report_name,
                    font=("Segoe UI", 11, "bold"),
                    bg=COLOR_BACKGROUND,
                    fg=COLOR_TEXT,
                )
                section_label.pack(pady=(12, 5))

            if use_button_name:
                button_name = folder_info["button_name"]
            else:
                button_name = report_name

            folder_path = folder_info["folder_path"]

            button = tk.Button(
                folder_window,
                text=button_name,
                command=lambda name=button_name, path=folder_path: (
                    self.open_configured_folder(name, path)
                ),
                font=("Segoe UI", 10),
                width=42,
                height=2,
                bg=COLOR_CARD,
                fg=COLOR_TEXT,
                activebackground="#E1E1E1",
                relief="groove",
                cursor="hand2",
            )
            button.pack(pady=3)

        close_button = tk.Button(
            folder_window,
            text="Close",
            command=folder_window.destroy,
            font=("Segoe UI", 10),
            width=16,
        )
        close_button.pack(pady=20)

    def open_configured_folder(
        self,
        button_name: str,
        folder_path: str,
    ) -> None:
        """Open a configured folder and handle errors."""

        try:
            open_folder(folder_path)
            log_folder_opened(
                self.logger,
                button_name,
                folder_path,
            )
        except (FileNotFoundError, NotADirectoryError, OSError) as error:
            log_error(
                self.logger,
                f"Could not open folder | {button_name} | {error}",
            )

            messagebox.showerror(
                "Folder Could Not Be Opened",
                str(error),
                parent=self.root,
            )

    def open_hub_logs(self) -> None:
        """Open the Reporting Hub Logs folder."""

        log_folder = self.config["hub"].get(
            "log_folder",
            "Logs",
        )

        log_path = Path(log_folder)

        if not log_path.is_absolute():
            log_path = HUB_ROOT / log_path

        self.open_configured_folder(
            "Reporting Hub Logs",
            str(log_path),
        )

    def start_report_run(
        self,
        report_keys: list[str],
    ) -> None:
        """Start selected reports in a background thread."""

        if self.is_running:
            messagebox.showwarning(
                "Reports Already Running",
                "Please wait for the current report run to finish.",
                parent=self.root,
            )
            return

        report_names = [
            get_report_config(
                self.config,
                report_key,
            )["display_name"]
            for report_key in report_keys
        ]

        if len(report_names) == 1:
            run_description = report_names[0]
        else:
            run_description = "all configured reports"

        confirmed = messagebox.askyesno(
            "Run Reports",
            f"Run {run_description}?\n\n"
            "Make sure all report input and output Excel files are closed.",
            parent=self.root,
        )

        if not confirmed:
            return

        self.is_running = True
        self.set_controls_enabled(False)
        self.progress_bar["value"] = 0

        self.status_label.config(
            text="Starting report run...",
            fg=COLOR_PRIMARY,
        )
        self.summary_label.config(
            text="The Reporting Hub is preparing the selected report run."
        )

        worker = threading.Thread(
            target=self.execute_reports,
            args=(report_keys,),
            daemon=True,
        )
        worker.start()

    def execute_reports(
        self,
        report_keys: list[str],
    ) -> None:
        """Run reports sequentially outside the interface thread."""

        results: list[ReportResult] = []
        total_reports = len(report_keys)

        for index, report_key in enumerate(report_keys, start=1):
            report = get_report_config(
                self.config,
                report_key,
            )
            report_name = report["display_name"]

            self.root.after(
                0,
                self.update_running_status,
                report_name,
                index,
                total_reports,
            )

            log_report_start(
                self.logger,
                report_name,
            )

            result = run_report(
                self.config,
                report_key,
            )
            results.append(result)

            log_report_result(
                self.logger,
                result.report_name,
                result.status,
                result.duration_seconds,
                result.details,
            )

            progress_value = int(
                index / total_reports * 100
            )

            self.root.after(
                0,
                self.update_progress,
                progress_value,
            )

            continue_after_failure = self.config["hub"].get(
                "continue_after_failure",
                True,
            )

            if (
                result.status == "FAILED"
                and not continue_after_failure
            ):
                break

        self.root.after(
            0,
            self.finish_report_run,
            results,
        )

    def update_running_status(
        self,
        report_name: str,
        current_number: int,
        total_reports: int,
    ) -> None:
        """Update the visible active-report status."""

        self.status_label.config(
            text=(
                f"Running {current_number} of {total_reports}: "
                f"{report_name}"
            ),
            fg=COLOR_PRIMARY,
        )

        self.summary_label.config(
            text="Please wait. Do not open report workbooks during processing."
        )

    def update_progress(self, progress_value: int) -> None:
        """Update the progress bar."""

        self.progress_bar["value"] = progress_value

    def finish_report_run(
        self,
        results: list[ReportResult],
    ) -> None:
        """Display the final result of the selected report run."""

        self.is_running = False
        self.set_controls_enabled(True)

        successful = sum(
            result.status == "SUCCESS"
            for result in results
        )
        failed = sum(
            result.status == "FAILED"
            for result in results
        )
        warnings = sum(
            result.status == "WARNING"
            for result in results
        )

        if failed:
            final_status = "Completed with failures"
            final_color = COLOR_FAILED
        elif warnings:
            final_status = "Completed with warnings"
            final_color = COLOR_WARNING
        else:
            final_status = "Completed successfully"
            final_color = COLOR_SUCCESS

        self.status_label.config(
            text=final_status,
            fg=final_color,
        )

        summary_text = (
            f"Success: {successful}  |  "
            f"Warnings: {warnings}  |  "
            f"Failed: {failed}"
        )

        self.summary_label.config(text=summary_text)

        result_lines = []

        for result in results:
            result_lines.append(
                f"{result.report_name}\n"
                f"Status: {result.status}\n"
                f"Time: {result.duration_seconds:.1f} seconds\n"
                f"Details: {result.details}"
            )

        messagebox.showinfo(
            "Report Run Summary",
            "\n\n".join(result_lines),
            parent=self.root,
        )

    def set_controls_enabled(self, enabled: bool) -> None:
        """Enable or disable controls during report processing."""

        state = tk.NORMAL if enabled else tk.DISABLED

        for button in self.report_buttons:
            button.config(state=state)

        for button in self.control_buttons:
            button.config(state=state)

    def close_application(self) -> None:
        """Close the application when no report is running."""

        if self.is_running:
            messagebox.showwarning(
                "Reports Are Running",
                "The Reporting Hub cannot close while reports are running.",
                parent=self.root,
            )
            return

        self.logger.info("Reporting Hub application closed.")
        self.root.destroy()


def main() -> None:
    """Start the Dark Universe Reporting Hub."""

    root = tk.Tk()

    try:
        ReportingHubApp(root)
        root.mainloop()
    except (
        FileNotFoundError,
        ValueError,
        KeyError,
        OSError,
    ) as error:
        root.withdraw()

        messagebox.showerror(
            "Reporting Hub Startup Error",
            str(error),
        )

        root.destroy()
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()