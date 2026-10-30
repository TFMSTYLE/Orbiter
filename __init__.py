bl_info = {
    "name": "Orbiter",
    "author": "The French Monkey",
    "version": (1, 1, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > Orbiter",
    "description": "Orbit around objects in the viewport",
    "category": "3D View",
    "license": "GPL-3.0-or-later",
}

import bpy
import math
import time
from mathutils import Quaternion, Vector
from bpy.types import PropertyGroup
from bpy.props import FloatProperty, BoolProperty, StringProperty, CollectionProperty
from bpy.app.handlers import persistent

# ------------------------------------------------------------------------
# Constants
# ------------------------------------------------------------------------

RECENTER_FACTOR = 1.0 / 10.0
LOCATION_EPSILON = 0.1
MAX_SPEED = 1

# ------------------------------------------------------------------------
# Property Groups
# ------------------------------------------------------------------------

class AreaInfo(PropertyGroup):
    type: StringProperty(default="")
    ui_type: StringProperty(default="")

class OrbiterSettings(PropertyGroup):
    speed: FloatProperty(
        name="Speed",
        default=0.2,
        min=0.0,
        max=1.0,
        precision=2
    )
    recenter_distance: FloatProperty(
        name="Recenter Distance",
        default=5.0,
        min=0.1,
        max=100.0,
        precision=1
    )
    is_running: BoolProperty(default=False)
    reverse: BoolProperty(default=False)
    is_fullscreen: BoolProperty(default=False)
    original_areas: CollectionProperty(type=AreaInfo)
    original_screen: StringProperty(default="")

# ------------------------------------------------------------------------
# Utility Functions
# ------------------------------------------------------------------------

def get_view3d_context(context):
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces.active
            if space and space.type == 'VIEW_3D' and space.region_3d:
                return area, space.region_3d
    return None, None

def safe_frame_object(context, obj, distance: float):
    if not obj:
        return False
    area, r3d = get_view3d_context(context)
    if not (area and r3d):
        return False
    try:
        region = area.regions[-1] if area.regions else None
        if region:
            with context.temp_override(area=area, region=region):
                bpy.ops.view3d.view_selected(use_all_regions=False)
            r3d.view_distance = distance
            return True
    except Exception as e:
        print(f"Orbiter: Failed to frame object - {e}")
    return False

# ------------------------------------------------------------------------
# Modal Operator
# ------------------------------------------------------------------------

class VIEW3D_OT_orbiter(bpy.types.Operator):
    bl_idname = "view3d.orbiter"
    bl_label = "Start Orbiter"
    bl_options = {"REGISTER", "UNDO"}

    _timer = _target_obj = _current_loc = _cached_area = _cached_region_3d = None

    def modal(self, context, event):
        s = context.scene.orbiter_settings
        a, r3d = self._cached_area, self._cached_region_3d

        if not (a and r3d):
            self.report({'INFO'}, "No 3D Viewport")
            return self.cancel(context)

        o = context.active_object
        if not o:
            self.report({'INFO'}, "No object selected")
            return self.cancel(context)

        if not s.is_running or event.type == 'ESC':
            return self.cancel(context)

        if event.type in {'MOUSEWHEELUP', 'MOUSEWHEELDOWN'}:
            return {'PASS_THROUGH'}

        if o != self._target_obj:
            self._target_obj = o
            if (r3d.view_location - o.location).length > 0.01:
                if safe_frame_object(context, o, s.recenter_distance):
                    r3d.view_distance = s.recenter_distance
            r3d.view_location = o.location.copy()
            self._current_loc = r3d.view_location.copy()

        if event.type == 'TIMER' and self._target_obj and s.speed > 0.0:
            now = time.perf_counter()
            delta = now - getattr(self, "_last_time", now)
            self._last_time = now

            delta = max(0.001, min(delta, 0.05))

            d = -1 if s.reverse else 1
            ang = math.radians(s.speed * MAX_SPEED * d * delta * 60.0)

            r3d.view_rotation = Quaternion((0, 0, 1), ang) @ r3d.view_rotation

            if a:
                for region in a.regions:
                    if region.type == 'WINDOW':
                        region.tag_redraw()

        return {'PASS_THROUGH'}

    def execute(self, context):
        s = context.scene.orbiter_settings
        o = context.active_object
        if not o:
            self.report({'WARNING'}, "No active object")
            return {'CANCELLED'}

        a, r3d = get_view3d_context(context)
        if not (a and r3d):
            self.report({'WARNING'}, "No 3D Viewport")
            return {'CANCELLED'}

        self._cached_area, self._cached_region_3d = a, r3d
        self._target_obj, self._current_loc = o, r3d.view_location.copy()
        s.is_running = True

        safe_frame_object(context, o, s.recenter_distance)
        r3d.view_distance = s.recenter_distance
        r3d.view_location = o.location.copy()

        wm = context.window_manager
        self._timer = wm.event_timer_add(1.0 / 30.0, window=context.window)
        wm.modal_handler_add(self)
        self._last_time = time.perf_counter()

        return {'RUNNING_MODAL'}

    def cancel(self, context):
        s = context.scene.orbiter_settings
        s.is_running = False
        wm = context.window_manager

        if self._timer:
            wm.event_timer_remove(self._timer)
        self._timer = None

        self._target_obj = None
        self._current_loc = None
        self._cached_area = None
        self._cached_region_3d = None

        return {'CANCELLED'}

# ------------------------------------------------------------------------
# Center Operator
# ------------------------------------------------------------------------

class VIEW3D_OT_center_object(bpy.types.Operator):
    bl_idname = "view3d.center_object"
    bl_label = "Center"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        o = context.active_object
        if not o:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}
        s = context.scene.orbiter_settings
        if safe_frame_object(context, o, s.recenter_distance):
            return {'FINISHED'}
        self.report({'WARNING'}, "Failed to center on object")
        return {'CANCELLED'}

# ------------------------------------------------------------------------
# Toggle Fullscreen Operator
# ------------------------------------------------------------------------

class VIEW3D_OT_toggle_fullscreen(bpy.types.Operator):
    bl_idname = "view3d.toggle_fullscreen"
    bl_label = "Toggle Full Screen"
    bl_options = {"REGISTER"}

    def execute(self, context):
        s = context.scene.orbiter_settings
        sc = context.screen
        return self._enter_fullscreen(context, s, sc) if not s.is_fullscreen else self._exit_fullscreen(context, s)

    def _enter_fullscreen(self, context, s, sc):
        s.original_areas.clear()
        for a in sc.areas:
            ai = s.original_areas.add()
            ai.type, ai.ui_type = a.type, a.ui_type
        s.original_screen = sc.name
        a, _ = get_view3d_context(context)
        if not a:
            self.report({'WARNING'}, "No 3D Viewport found")
            return {'CANCELLED'}
        try:
            r = a.regions[-1] if a.regions else None
            if r:
                with context.temp_override(area=a, region=r):
                    bpy.ops.screen.screen_full_area(use_hide_panels=False)
                s.is_fullscreen = True
                return {'FINISHED'}
        except Exception as e:
            self.report({'WARNING'}, f"Failed to maximize viewport: {e}")
        return {'CANCELLED'}

    def _exit_fullscreen(self, context, s):
        try:
            bpy.ops.screen.back_to_previous()
            s.is_fullscreen = False
            return {'FINISHED'}
        except Exception as e:
            self.report({'WARNING'}, f"Failed to restore layout: {e}")
            s.is_fullscreen = False
            return {'CANCELLED'}
        
# ------------------------------------------------------------------------
# UI
# ------------------------------------------------------------------------

class VIEW3D_PT_orbiter(bpy.types.Panel):
    bl_label = "Orbiter"
    bl_idname = "VIEW3D_PT_orbiter"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Orbiter"

    def draw(self, context):
        layout = self.layout
        s = context.scene.orbiter_settings
        o = context.active_object

        row = layout.row(align=True)
        if not s.is_running:
            row.operator("view3d.orbiter", text=" Play", icon="PLAY")
        else:
            row.prop(s, "is_running", text=" Stop", toggle=True, icon="PAUSE")

        row.prop(s, "reverse", text="Reverse", toggle=True, icon="ARROW_LEFTRIGHT")
        row.operator("view3d.center_object", text=" Center", icon="PIVOT_BOUNDBOX")

        layout.separator(factor=0.5)

        col = layout.column(align=True)
        col.prop(s, "speed", slider=True)
        col.prop(s, "recenter_distance", slider=True)

        layout.separator(factor=0.5)

        label = "Exit Full Screen" if s.is_fullscreen else "Toggle Full Screen"
        layout.operator("view3d.toggle_fullscreen", text=label, icon="FULLSCREEN_ENTER")

        layout.separator(factor=0.5)

        if s.is_running and o:
            layout.label(text=f"Orbiting: {o.name}", icon="OBJECT_DATA")
        elif o:
            layout.label(text=f"Selected: {o.name}", icon="OBJECT_DATA")
        else:
            layout.label(text="No object selected", icon="INFO")

# ------------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------------

classes = (
    AreaInfo,
    OrbiterSettings,
    VIEW3D_OT_orbiter,
    VIEW3D_OT_center_object,
    VIEW3D_OT_toggle_fullscreen,
    VIEW3D_PT_orbiter,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.orbiter_settings = bpy.props.PointerProperty(type=OrbiterSettings)

def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    if hasattr(bpy.types.Scene, 'orbiter_settings'):
        del bpy.types.Scene.orbiter_settings

if __name__ == "__main__":
    register()
