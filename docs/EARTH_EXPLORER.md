# Earth explorer

The homepage takes inspiration from the globe-first exploration in NASA Eyes on the Earth. FieldShift uses its own geographic illustration and farmer workflow; the globe does not display satellite imagery, current weather, or crop suitability layers.

Design: ocean navy `#081b2d`, marine blue `#245f7c`, land sage `#669b8d`, selection amber `#ffdb9a`, and pale field green `#e6eee9`. Bricolage Grotesque provides the display hierarchy; Manrope is used for controls and readable farm inputs. The globe is the primary visual, with a location report beside it on desktop and beneath it on mobile. Motion only responds to selection. Reduced-motion preferences disable the selection animation.

The globe uses orthographic projection with hemisphere clipping. Drag to rotate, use the buttons or mouse wheel to zoom, centre on a selected location, or switch to an equirectangular flat map. Zoom keeps the chosen projection. Click coordinates are calculated by inverting the active projection. Clicks outside the globe are ignored. Dragging does not select a point. Arrow keys refine a cursor and Enter selects it. The region selector provides a keyboard and mobile route to every pilot, including markers on the hidden hemisphere.

The location report provides a monthly precipitation and temperature summary from the NASA POWER daily series, a CSV download, exact coordinate entry and shortcuts to the climate and planning pages. The chart shows derived monthly summaries, while the CSV preserves the retrieved daily parameter columns. Missing observations remain missing and their coverage is shown.

Geography comes from the existing bundled Natural Earth land outlines. Rendering uses pinned, bundled d3-geo 3.1.1 and its dependency d3-array 3.2.4. Their ISC licenses are in `assets/vendor/`. These libraries provide spherical clipping and coordinate inversion; they do not calculate climate or agronomic values. No CDN is contacted at runtime.

NASA POWER retrieval and the regional rotation engine retain their existing Python modules. Global calendar comparisons remain timing-only drafts. A location selection does not establish that land is farmable.

Reference: https://eyes.nasa.gov/apps/earth/
Projection documentation: https://d3js.org/d3-geo
