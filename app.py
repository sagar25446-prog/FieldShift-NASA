"""Streamlit entry point for the FieldShift foundation."""

from pathlib import Path
import sys

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
SOURCE_DIRECTORY = PROJECT_ROOT / "src"
if str(SOURCE_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIRECTORY))

from fieldshift.ui import render_application  # noqa: E402


def main() -> None:
    """Render the guided FieldShift planning workflow."""
    st.set_page_config(page_title="FieldShift", page_icon="🌾", layout="wide", initial_sidebar_state="expanded")
    render_application()


if __name__ == "__main__":
    main()
