"""Рендер выбранных кадров из сохранённой сцены: python render_frames.py scene.blend out_dir кадры(через запятую|a-b) процент сэмплы"""
import sys

import bpy

blend, out, frames, pct, spp = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
sc.render.resolution_percentage, sc.cycles.samples = pct, spp
fl = list(range(*map(int, (frames.split("-")[0], int(frames.split("-")[1]) + 1)))) if "-" in frames else [int(x) for x in frames.split(",")]
for i in fl:
    sc.frame_set(i)
    sc.render.filepath = f"{out}/{i:04d}.exr"
    bpy.ops.render.render(write_still=True)
    print("рендер", i, flush=True)
