# 逐日 / Chasing the Sun

A 66-second animated short: a great white pelican rides a vintage bicycle along a coastal road at sunrise, launches off the end of the road and flies across the sun.

Everything is procedural. `pel/` builds the pelican, bicycle, landscape, sea and sky in Blender (Cycles) from Python; `film.py` animates the nine shots; `score.py` renders the orchestral score from a GM soundfont.

Rendering is fanned out over GitHub Actions: editing `render.json` and pushing starts one job per still or per frame chunk, and each job publishes its result to an `out/<tag>/<id>` branch.
