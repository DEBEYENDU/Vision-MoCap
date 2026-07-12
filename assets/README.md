# Assets

Static resources bundled with the application or used during development.

## Directory Structure

| Directory     | Purpose                                                  |
|---------------|----------------------------------------------------------|
| `icons/`      | Application icons (`.ico`, `.png`, `.svg`)               |
| `logos/`      | Brand logos for the project                              |
| `models/`     | 3D models, rigs, or Blender assets used in demos         |
| `fonts/`      | Custom font files (`.ttf`, `.otf`)                       |
| `shaders/`    | GLSL / shader files for rendering                        |
| `textures/`   | Image textures (`.png`, `.jpg`) used in scenes           |

## Naming Conventions

- Icons: `icon_<name>_<size>.<ext>` (e.g. `icon_app_64.png`)
- Logos: `logo_<variant>.<ext>` (e.g. `logo_dark.svg`)
- Models: `<character_or_rig_name>.<ext>` (e.g. `mixamo_rig.fbx`)
- Fonts: `<font_family>_<weight>.<ext>` (e.g. `Inter_Regular.ttf`)
