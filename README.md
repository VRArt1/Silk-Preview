# Silk Preview
<div align="center">
<img width="960" height="480" alt="banner" src="https://raw.githubusercontent.com/VRArt1/Silk-Preview/refs/heads/main/banner.png" />

**A Theme Previewer for CocoonFE**

*A work-in-progress vibe coded theme previewer for Cocoon FE.*

The intent of this project is to be an accurate theme previewer for the use of general browsing of themes and for aiding in the development of new themes by allowing for more rapid development at your computer without the need to send files to your device. Simply load in your theme folder just as you would on hardware and it'll display as it would natively. As this software is still a work-in-progress not all features have been replicated but a good chunk of them are already in. If you find any bugs please report them through the issues page. If this project is successful of supporting all aspects of Cocoon themes I hope to expand it to include theme editing and creation features.

[Features](#features) • [Setup](#setup) • [Support](#support)
</div>

## Features
### Software Specific

- **Device Colors** Allows for the choosing of all four Ayn Thor device colors with a bonus slot premade for custom designs.
- **Screenshots** Allows for screenshots of the device and without background cropped for sharing or use in theme display. Ctrl click for transparent cropped.
- **Empty Slots** Toggle for displaying empty slots.
- **Remember Theme** For ease of development the software can remember and reload into the last opened theme folder.
- **Functional Zoom** Replicates native zoom functionality to display more slots.
- **Functional Select** Allows for either clicking or keyboard based movement to select different grid slots to preview item select and relevant heroes/logos on the top screen.
- **Drag and Drop** Drag in theme folders to load them.

### Cocoon Supported

- **Theme.json + Preview** All fields and images populate within the preview panel. Colors include preview circles and is collapsible .
- **Wallpapers** Supports both screens both animated and static. Support for wallpaper aliases and asigning based on theme.json. Video currently only supports first frame.
- **Smart Folders + Smart Folders/By Platform**  Support for hero, icon, and logo. Properly displayed when selected like on native. (Logo sizing currently inaccurate).
- **Icon Overlays** Support for mask and overlay. Populated with random image from "assets/games"; insert images there to be randomly chosen. Matching names to console will be chosen first for consoles, allows for multiple options using underscores. I.E. gba.gif & gba_blue.png will be matched to gba icon overlay if exists.
- **Default Folder Colors** Right click on the default folder to change its color.
- **Single Screen Mode**  Beyond the Ayn Thor you are also able to preview Cocoon themes on an Odin3! Allows for both dual and single screen modes.

### Cocoon Not Supported

- **SFX/BGM**  
- **Animated MP4/WEBM** (First frame preview supported)  
- **Theme.json Colors**   
- **Hero Masking**  
- **Hero/Logo Animation**  
- **Icons On Folders**  
- **Append Apply Mode**  
- **Screen Swapping**

### Controls

| Key | Control |
| --- | --- |
| Tab | Frame Cycle |
| Shift Tab | Reverse Frame Cycle |
| L | Load Theme |
| R | Refresh |
| S | Screenshot |
| Ctrl S | Screenshot Device Only |
| + | Zoom In |
| - | Zoom Out |

Right click on default folder to change colors.

## Setup
### How To Run

Download the entire repository and run Silk Preview.py. It will install the necessary dependencies before launching.
Alternatively install the requirements and run app.py.

### Dependencies

- **Pillow**  
- **av + ffmpeg**
- **tkinterdnd2**  

## Support

For bug reports and feature requests please use [GitHub Issues](https://github.com/VRArt1/Silk-Preview/issues).  
If you found this software at all useful consider supporting its further development and sending me a tip on [Ko-fi](https://ko-fi.com/vrart1) or [Patreon](https://www.patreon.com/c/VRArt1).

## Credits
CocoonFE by Moth  
Carticon Icon Overlays by Víctor Redondo / V de Vaporeta

