# Orbiter

![orbiter-thumb](https://github.com/user-attachments/assets/fec90ce2-9aa3-47eb-80b1-bce4a8bf853e)

**Author:** The French Monkey (TFMSTYLE)  
**Version:** 1.1.0  

---

## Overview

**Orbiter** allows you to automatically orbit around a selected object in the Blender 3D Viewport.  
It smoothly rotates the camera view in real-time, creating an animated rotation effect for presentations, turntables, and inspection workflows.

The add-on includes adjustable orbit speed, reverse direction, recentering controls, and fullscreen toggling for immersive viewport focus.

---

## Parameters

### General Settings

- **Speed:**  
  Controls the rotation speed of the orbit motion.  
  *(Default: 0.2, Range: 0.0–1.0)*

- **Recenter Distance:**  
  Sets the distance from which the viewport centers around the object when starting the orbit or when manually centering.  
  *(Default: 5.0, Range: 0.1–100.0)*

- **Reverse:**  
  Inverts the orbit direction (clockwise / counterclockwise).

- **Is Running:**  
  Internal flag showing whether the orbiter is currently active.

- **Is Fullscreen:**  
  Indicates whether the viewport is in fullscreen mode.

---

## Operators

### Start Orbiter
**Operator:** `view3d.orbiter`  
Starts the orbiting process around the active object.  
The camera will continuously rotate around the object’s origin based on the defined speed and direction.

- Automatically recenters the view on the active object.  
- Updates in real-time using a modal timer.  
- Stops when pressing **Esc** or when toggled off.

---

### Center Object
**Operator:** `view3d.center_object`  
Recenters the camera view around the currently selected object at the specified `Recenter Distance`.

---

### Toggle Full Screen
**Operator:** `view3d.toggle_fullscreen`  
Toggles between standard and fullscreen viewport display modes.  
Saves the current layout before entering fullscreen and restores it upon exit.

---

## Internal Behavior

- Uses Blender’s **modal operator system** to continuously update rotation via a **timer event**.  
- Rotation is handled by applying a **Quaternion** around the Z-axis to the viewport’s `view_rotation`.  
- View location and distance are automatically aligned to the active object when orbiting begins.  
- Automatically cancels if:
  - No object is selected  
  - The 3D Viewport area is not found  
  - The user presses `Esc`
