# SO101 Bucket Viewer

GitHub Pages viewer for an SO101 bucket with explicit rear servo attachment
geometry.

## Model

The generated STL is `assets/so101-bucket-servo-mount.stl`.

Key dimensions:

- Bucket envelope: 80 mm wide, 77 mm bucket depth, 40 mm bucket height.
- Servo-mount envelope: 80 x 96 x 48 mm overall.
- Two servo horn axes: x = -22 mm and x = 22 mm, y = -45.5 mm, z = 28 mm.
- Horn center clearance: 6.4 mm diameter.
- Screw clearance tubes: 2.7 mm diameter, four per servo station.

The attachment is modeled as two yoke plates, horn rings, through-standoff
tubes, bridge/spine members, and diagonal gussets connected back to the bucket
rear wall. The grey servo bodies in the viewer are visual alignment references;
the yellow STL is the printable bucket/mount geometry.

## Regenerate

```bash
python3 scripts/generate_viewer.py
```

This rewrites both the STL asset and the embedded STL in `index.html`.
