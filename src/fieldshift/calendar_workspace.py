"""Streamlit view for locations without a validated regional rotation catalogue."""
from calendar import month_abbr, monthrange
from datetime import date

import pandas as pd
import streamlit as st

from .global_calendar import Calendar, SOURCE, at_point, month_name, sequences


def _month_day(month: int, last: bool = False) -> int:
    day = monthrange(2001, month)[1] if last else 1
    return date(2001, month, day).timetuple().tm_yday


def _slot(day: int) -> str:
    return f"{month_name(day)} · year {(day - 1) // 365 + 1}"


def render(page: str) -> str | None:
    farm = st.session_state.farm
    location = (farm["latitude"], farm["longitude"])
    settings = st.session_state.setdefault("calendar_preferences", {}).setdefault(location, {})
    custom = st.session_state.setdefault("farmer_calendars", {}).setdefault(location, {})
    observed = {c.name: c for c in at_point(*location)}
    titles = {"Rotation Recommendations":"Crop calendars", "Comparison View":"Compare crop sequences",
              "Farmer Priorities":"Choose your calendar preferences"}
    st.title(titles[page])
    st.caption(f"Selected field · {location[0]:.4f}°, {location[1]:.4f}°")
    st.write("Explore when crops typically occupy the field. These drafts check timing only. "
             "Local soil, water supply, pests and crop compatibility still need review.")
    dataset = st.session_state.get("power_dataset")
    if dataset:
        series = dataset.data["PRECTOTCORR"].dropna()
        st.caption(f"NASA POWER · {dataset.provenance.start_date} to {dataset.provenance.end_date} · "
                   f"{series.sum():.0f} mm across {len(series)} days with rainfall data." if len(series)
                   else "Rainfall is missing for the selected historical period.")
    if st.button("View climate history", icon=":material/partly_cloudy_day:"):
        return "Climate Insights"

    if not observed:
        st.info("This grid cell has no published calendar in the atlas. For a farm here, add crops and months from your own records below.")
    with st.expander("Add a crop from my own records", expanded=not observed and not custom):
        st.caption("Your months apply only to this location. The comparison reserves the entire planting and harvest months.")
        with st.form("local_calendar_form", clear_on_submit=True):
            name = st.text_input("Crop name", max_chars=60).strip()
            a, b = st.columns(2)
            start = a.selectbox("Planting month", range(1, 13), format_func=month_abbr.__getitem__, index=None)
            end = b.selectbox("Harvest month", range(1, 13), format_func=month_abbr.__getitem__, index=None)
            if st.form_submit_button("Save crop calendar"):
                if not name or not start or not end:
                    st.error("Enter a crop name and both months.")
                else:
                    existing = next((k for k in (*observed, *custom) if k.casefold() == name.casefold()), name)
                    crop = observed[existing].crop if existing in observed else existing
                    custom[existing] = Calendar(existing, crop, _month_day(start), _month_day(end, last=True))
        if custom and st.button("Clear my calendar entries for this field"):
            custom.clear()
            st.rerun()
    calendars = {**observed, **custom}
    if not calendars:
        return None
    with st.expander("Planting and harvest months", expanded=page == "Rotation Recommendations"):
        st.dataframe(pd.DataFrame([{"Crop":c.name, "Typical planting":month_name(c.plant),
            "Typical harvest":month_name(c.harvest), "Source":"Your entry" if c.name in custom else "Sacks et al. (2010)"}
            for c in calendars.values()]), hide_index=True, width="stretch")
    st.caption(f"Historical regional calendars at 0.5° resolution. A record in a grid cell does not establish that the crop grows on this field today. [Dataset and methods]({SOURCE})")
    st.subheader("Build a calendar comparison")
    chosen = st.multiselect("Crops to consider", list(calendars),
                            default=[c for c in settings.get("crops", calendars) if c in calendars])
    a, b = st.columns(2)
    start = a.selectbox("Earliest planting month", range(1, 13), index=settings.get("month", 1)-1,
                        format_func=month_abbr.__getitem__)
    count = b.radio("Crops in sequence", (2, 3), index=settings.get("count", 2)-2, horizontal=True)
    settings.update(month=start, count=count, crops=chosen)
    options = sequences(tuple(calendars[k] for k in chosen), start, count)
    if not options:
        st.info(f"Select at least {count} distinct crops to compare sequences.")
        return None
    st.caption("Each next crop waits for its next recorded planting date after harvest. "
               "Year 1 starts in January. Options are ordered by earliest finish on a repeating calendar.")
    st.dataframe(pd.DataFrame([{
        "Sequence":" → ".join(s[0] for s in option),
        **{f"Crop {i}":f"{_slot(p)} – {_slot(h)}" for i, (_, p, h) in enumerate(option, 1)},
        "Days from first planting to last harvest":option[-1][2]-option[0][1]+1,
    } for option in options[:12]]), hide_index=True, width="stretch")
    st.caption(f"Showing {min(12, len(options))} of {len(options)} calendar combinations. Changing the crops or starting month recalculates the table.")
    return None
