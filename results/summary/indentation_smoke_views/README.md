# Indentation smoke view index

Each case directory contains nine MAPDL PNG files generated in this fixed order:

| Suffix | View |
|---:|---|
| `000` | Geometry colored by material ID |
| `001` | Probe-eyelid contact pressure, top |
| `002` | Probe-eyelid contact pressure, front |
| `003` | Eyelid Von Mises stress, front |
| `004` | Cornea Von Mises stress, front |
| `005` | Probe Von Mises stress, front |
| `006` | Undeformed central stress section |
| `007` | Actual-scale deformed central stress section |
| `008` | Probe-eyelid numerical contact penetration, top |

The source run is recorded in `../indentation_smoke_metadata.json`. These images
are review artifacts; machine-readable acceptance values are in
`../indentation_smoke.csv` and `../indentation_smoke_qc.json`.
