# Silk Preview
<div align="center">
<img width="960" height="480" alt="banner" src="https://raw.githubusercontent.com/VRArt1/Silk-Preview/refs/heads/main/banner.png" />

**A Theme Previewer for CocoonFE**

[![Platform](https://img.shields.io/badge/platform-windows-green.svg)](https://www.microsoft.com/en-us/windows)
[![Platform](https://img.shields.io/badge/platform-linux-green.svg)](https://www.linux.org/)
![Discord](https://img.shields.io/discord/1480567765659029564?label=Discord&logo=discord)

*A work-in-progress vibe coded theme previewer for Cocoon FE.*

The intent of this project is to be an accurate theme previewer for the use of general browsing of themes and for aiding in the development of new themes by allowing for more rapid development at your computer without the need to send files to your device. Simply load in your theme folder just as you would on hardware and it'll display as it would natively. As this software is still a work-in-progress not all features have been replicated but a good chunk of them are already in. If you find any bugs please report them through the issues page. If this project is successful of supporting all aspects of Cocoon themes I hope to expand it to include theme editing and creation features.

[Features](#features) • [Setup](#setup) • [Support](#support)
</div>

## Features
### Software Specific

- **Bezel Edit Mode** Allows for setup of custom bezels using a built in editor. Completed bezels can be shared by sharing the folder containing the images and device.json file.
- **Screenshots** Allows for screenshots of the device for sharing or use in theme display. Ctrl click for transparent cropped variant.
- **Remember Last Theme** For ease of development the software can remember and reload into the last opened theme folder.
- **Drag and Drop** Drag in theme folders to load them more easily.  

### Cocoon Supported

- **Theme.json + Preview** All fields and images populate within the preview panel following the order shown within the wiki. Colors include preview circles and is collapsible .
- **Wallpapers** Supports both screens both animated and static. Support for wallpaper aliases and asigning based on theme.json. Video currently only supports first frame.
- **Smart Folders + Smart Folders/By Platform**  Support for hero, icon, and logo. Properly displayed when selected like on native. (Logo sizing currently inaccurate).
- **Icon Overlays** Support for mask and overlay. Populated with random image from "assets/games"; insert images there to be randomly chosen. Matching names to console will be chosen first for consoles, allows for multiple options using underscores. I.E. gba.gif & gba_blue.png will be matched to gba icon overlay if exists.
- **Apps Dock** Similar to game images for icon overlays there is an apps folder for populating image that'll be randomly chosen from to fill your app dock. Images will automatically be masked into circles.
- **Default Folder Colors** Right click on the default folder to change its color.
- **Logo Size** Supports logo sizing as per Cocoon range.
- **Zoom** Functional zoom to display more slots.
- **Select** Allows for either clicking or keyboard based movement to select different grid slots to preview item select and relevant heroes/logos on the top screen. Allows for complete grid navigation beyond initial page.
- **Single Screen Mode**  Beyond dual screen devices like the AYN Thor you are also able to preview Cocoon themes on single screen devices like the Odin3 or RP6! Allows for both dual and single screen modes on single screen devices!
- **Toggles** Supports multiple display element toggles: dock background, apps, empty apps, empty slots, corner hints.

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
| Esc | Settings Menu |

Right click on default folder to change colors.

## Setup
### How To Run

Download the [latest release](https://github.com/VRArt1/Silk-Preview) and run Silk Preview.py. It will ask if you'd like to install the necessary dependencies before launching if you do not have them installed yet.
Alternatively install the requirements and run app.py.

### Dependencies

- **Pillow**  
- **av + ffmpeg**
- **tkinterdnd2**  

## Support

For bug reports and feature requests please use [GitHub Issues](https://github.com/VRArt1/Silk-Preview/issues) or [join our Discord](https://discord.gg/6XSzUBCEz8).  
If you found this software at all useful consider supporting its further development and sending me a tip on [Ko-fi](https://ko-fi.com/vrart1) or [Patreon](https://www.patreon.com/c/VRArt1).

## Credits
CocoonFE by Moth  
Carticon Icon Overlays by Víctor Redondo / V de Vaporeta

