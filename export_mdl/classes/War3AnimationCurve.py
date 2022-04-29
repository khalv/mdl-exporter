import bpy

import math
from mathutils import Quaternion, Matrix, Euler, Vector

from ..utils import *

class War3AnimationCurve:
    def __init__(self):
        self.interpolation = 'Linear'
        self.global_sequence = -1
        self.type = 'Default'
        self.keyframes = {}
        self.handles_right = {}
        self.handles_left = {}
    
    @staticmethod
    def from_fcurve(fcurves, data_path, sequences, scale=1):
        curve = War3AnimationCurve()

        frames = set()

        if 'rotation' in data_path:
            curve.type = 'Rotation'
        elif 'location' in data_path:
            curve.type = 'Translation'
        elif 'scale' in data_path:
            curve.type = 'Scaling'
        elif 'color' in data_path or 'default_value' in data_path:
            curve.type = 'Color'
        elif 'event' in data_path.lower():
            curve.type = 'EventTrack'
        elif 'visibility' in data_path.lower() or 'hide_render' in data_path.lower():
            curve.type = 'Boolean'

        f2ms = 1000 / bpy.context.scene.render.fps
        
        for fcurve in fcurves.values():
            if len(fcurve.keyframe_points):
                if fcurve.keyframe_points[0].interpolation == 'BEZIER' and curve.type != 'Rotation': # Nonlinear interpolation for rotations is disabled for now
                    curve.interpolation = 'Bezier'
                elif fcurve.keyframe_points[0].interpolation == 'CONSTANT':
                    curve.interpolation = 'DontInterp'
                    
            for mod in fcurve.modifiers:
                if mod.type == 'CYCLES':
                    curve.global_sequence = max(curve.global_sequence, int(fcurve.range()[1] * f2ms))
                    
            for keyframe in fcurve.keyframe_points:
                frame = keyframe.co[0] * f2ms
                for sequence in sequences:
                    if (frame >= sequence.start and frame <= sequence.end) or curve.global_sequence > 0:
                        frames.add(keyframe.co[0])
                        break
         
        # We want start and end keyframes for each sequence. Make sure not to do this for events and global sequences, though!
        if curve.global_sequence < 0 and curve.type in {'Rotation', 'Translation', 'Scaling'}:
            for sequence in sequences:
                frames.add(round(sequence.start / f2ms))
                frames.add(round(sequence.end / f2ms))
            
        if curve.type == 'Boolean' or curve.type == 'EventTrack':
            curve.interpolation = 'DontInterp'
         
        curve.curves = []
        
        for frame in frames:
            values = []
            handle_left = []
            handle_right = []
            
            keys = fcurves.keys()
            keys = sorted(keys, key=lambda x: x[1])
            for key in keys:
                curve.curves.append(fcurves[key])
                value = fcurves[key].evaluate(frame)
                values.append(value * scale)
                
                if 'color' in data_path:
                    values = values[::-1] # Colors are stored in reverse
                    
                if 'hide_render' in data_path:
                    values = [1 - v for v in values] # Hide_Render is the opposite of visibility!
                
                if curve.interpolation == 'Bezier':
                    hl = fcurves[key].evaluate(frame-1)
                    hr = fcurves[key].evaluate(frame+1)
                    handle_left.append(hl)
                    handle_right.append(hr)
            
            if 'rotation' in data_path and 'quaternion' not in data_path: # Warcraft 3 only uses quaternions!
                curve.keyframes[frame] = tuple(Euler(values).to_quaternion())
            else:
                curve.keyframes[frame] = tuple(values)
                
            if curve.interpolation == 'Bezier':
                if 'rotation' in data_path and 'quaternion' not in data_path:
                    curve.handles_left[frame] = tuple(Euler(math.radians(x) for x in handle_left).to_quaternion())
                    curve.handles_right[frame] = tuple(Euler(math.radians(x) for x in handle_right).to_quaternion())
                else:
                    curve.handles_right[frame] = tuple(handle_right)
                    curve.handles_left[frame] = tuple(handle_right)

        return curve

    @staticmethod # This was used just for debug/validation purposes, to be removed
    def bezier_curve(p0, p0_out, p1_in, p1, t):
        nt = (1 - t)
        return nt*nt*nt*p0 + 3 * t * nt*nt * p0_out + 3*t*t*nt * p1_in + t*t*t*p1

    def to_fcurves(self, target, anim_data_obj, data_path, full_data_path, matrix=None):
        num_channels = 1
        for keyframe in self.keyframes:
            frame = int(round(keyframe * bpy.context.scene.render.fps / 1000))
            value = self.keyframes[keyframe]

            num_channels = len(value)

            if 'color' in data_path:
                value = tuple(reversed(value))
            if 'hide_render' in data_path:
                # Invert from 'visibility' to 'hidden'
                value = [not v for v in value]

            if matrix is not None:
                value = matrix @ Vector(value)

            if len(value) == 1:
                value = value[0]

            setattr(target, data_path, value)
            target.keyframe_insert(data_path, frame=frame)

        for channel in range(num_channels):
            curve = anim_data_obj.animation_data.action.fcurves.find(full_data_path, index=channel)

            if curve is None:
                print("Missing curve for object %s, data path %s, channel %d" % (anim_data_obj.name, data_path, channel))
                continue
            if self.global_sequence != -1:
                curve.modifiers.new('CYCLES')
            i = 0
            for frame in self.keyframes:
                frame_num = frame * bpy.context.scene.render.fps / 1000.0
                # Sometimes blender fails to create another frame (for instance, millisecond rounding error might cause two frames to overlap).
                # Because of this, we have to search for the right frame.
                while abs(curve.keyframe_points[i].co[0] - frame_num) > 0.001 and i < len(curve.keyframe_points)-1:
                    i +=1
                curve_frame = curve.keyframe_points[i]
                curve_frame.interpolation = {
                    'DontInterp':'CONSTANT',
                    'Bezier':'BEZIER',
                    'Hermite':'LINEAR',
                    'Linear':'LINEAR'
                }[self.interpolation]

                if self.interpolation in {'Bezier', 'Hermite'}:
                    hl = self.handles_left[frame]
                    hr = self.handles_right[frame]

                    if matrix is not None and self.type != 'Rotation':
                        hl = matrix @ Vector(hl)
                        hr = matrix @ Vector(hr)

                    if self.interpolation == 'Hermite':
                        continue # Not supported yet, should convert to bezier handles

                    def lerp(a, b, t):
                        return a + (b - a) * t

                    if i == 0:
                        curve_frame.handle_left = (curve_frame.co[0] - 20, hl[channel]) 
                    else:
                        hl_frame = lerp(curve.keyframe_points[i-1].co[0], curve_frame.co[0], 0.5)
                        curve_frame.handle_left = (hl_frame, hl[channel])

                    if i+1 < len(curve.keyframe_points):
                        hr_frame = lerp(curve_frame.co[0], curve.keyframe_points[i+1].co[0], 0.5)
                        curve_frame.handle_right = (hr_frame, hr[channel])
                    else:
                        curve_frame.handle_right = (curve_frame.co[0] + 20, hr[channel])

    def split_segment(self, start, end, tolerance):
        n = float(end[0] - start[0])
        error = -1
        frame = 0
        # print('Start: %d, End: %d, Range: %f' % (start[0], end[0], n))
        
        for i in (i for i in range(start[0], end[0]) if i in self.keyframes.keys()):
            middle = self.keyframes[i]
            distance = 0
            t = max(0, min(1, float(i - start[0]) / n)) # Interpolation factor
            if self.type == 'Translation' or self.type == 'Scaling':
                a = Vector(start[1])
                b = Vector(middle)
                c = Vector(end[1])
                delta = b - a.lerp(c, t)
                distance = delta.magnitude # Just the linear distance, for now
            elif self.type == 'Rotation':
                distance = 1 - Quaternion(middle).dot(Quaternion(start[1]).slerp(Quaternion(end[1]), t)) # Spherical distance in the range of 0-2
                
            if distance > error:
                error = distance
                frame = i
                
        if error > 0 and error > tolerance:
            middle = (frame, self.keyframes[frame])
            result = [middle]
            if frame != start[0] and frame != end[0]: # Prevents infinite recursion
                result += self.split_segment(start, middle, tolerance)
                result += self.split_segment(middle, end, tolerance)
                return result
                
        return []
    
    def optimize(self, tolerance, sequences):
        
        f2ms = 1000 / bpy.context.scene.render.fps
        
        if self.interpolation == 'Bezier':
            self.interpolation = 'Linear' # This feature doesn't support bezier as of right now
           
        print('Before: %d' % len(self.keyframes))
        
        newKeys = []
        for sequence in sequences:
            start = int(round(sequence.start / f2ms))
            end = int(round(sequence.end / f2ms))
            newKeys += [(start, self.keyframes[start]), (end, self.keyframes[end])]
            newKeys += self.split_segment((start, self.keyframes[start]) , (end, self.keyframes[end]), tolerance)
        
        self.keyframes.clear()
        self.keyframes.update(newKeys)
        print('After: %d' % len(self.keyframes))

    def transform_rot(self, matrix):
        for frame in self.keyframes.keys():
            axis, angle = Quaternion(self.keyframes[frame]).to_axis_angle()
            
            axis.rotate(matrix)
            quat = Quaternion(axis, angle)
            quat.normalize()
            
            self.keyframes[frame] = tuple(quat)
            
    def transform_vec(self, matrix):
        for frame in self.keyframes.keys():
            self.keyframes[frame] = tuple(matrix @ Vector(self.keyframes[frame]))
            if self.interpolation == 'Bezier':
                self.handles_right[frame] = tuple(matrix @ Vector(self.handles_right[frame]))
                self.handles_left[frame] = tuple(matrix @ Vector(self.handles_left[frame]))
            
        
    def write_mdl(self, name, writer, model):
    
        f2ms = 1000 / bpy.context.scene.render.fps
    
        writer.begin_scope(name, "%d" % len(self.keyframes))
        if self.type != 'EventTrack':
            writer.write(self.interpolation)
        if self.global_sequence > 0:
            writer.write("GlobalSeqId %d" % model.global_seqs.index(self.global_sequence))
            
        for frame in sorted(self.keyframes.keys()):
            n = len(self.keyframes[frame])
            line = "%s"
            if n > 1:
                line = "{ %s" % ('%s, ' * (n-1))
                line += "%s }"
            
            if self.type == 'EventTrack':
                writer.write("%d" % (frame * f2ms))
            else:
                keyframe = self.keyframes[frame]
                
                if self.type == 'Rotation':
                    keyframe = keyframe[1:] + keyframe[:1] # MDL quaternions must be on the form XYZW
                
                value = line % tuple(f2s(rnd(x)) for x in keyframe)
                writer.write("%d: %s" % (frame * f2ms, value))

                    
                if self.interpolation == 'Bezier':
                    hl = self.handles_left[frame]
                    hr = self.handles_right[frame]
                    
                    if self.type == 'Rotation':
                        hl = hl[1:]+hl[:1]
                        hr = hr[1:]+hr[:1]
                
                    writer.write("\tInTan %s" % (line % tuple(f2s(rnd(x)) for x in hl)))
                    writer.write("\tOutTan %s" % (line % tuple(f2s(rnd(x)) for x in hr)))
           
        writer.end_scope()
        
    def write_mdx(self, model, writer):
        pass
        
    def __eq__(self, other):
        if isinstance(self, other.__class__):
            if self.interpolation != other.interpolation:
                return False
            if self.global_sequence != other.global_sequence:
                return False
            if len(self.keyframes) != len(other.keyframes):
                return False
                
            return self.keyframes == other.keyframes and self.handles_left == other.handles_left and self.handles_right == other.handles_right
            
        return NotImplemented
    
    def __ne__(self, other):
        return not self.__eq__(other)
        
    def __hash__(self):
        values = [self.interpolation, self.global_sequence, self.type]
        values.append(tuple(sorted(self.keyframes.items())))
        values.append(tuple(sorted(self.handles_left.items())))
        values.append(tuple(sorted(self.handles_right.items())))
        return hash(tuple(values))
                
    @staticmethod
    def get(anim_data, data_path, num_indices, sequences, scale=1):
        curves = {}
   
        if anim_data and anim_data.action:
            for index in range(num_indices):
                curve = anim_data.action.fcurves.find(data_path, index=index)
                if curve is not None:
                    curves[(data_path.split('.')[-1], index)] = curve # For now, i'm just interested in the type, not the whole data path. Hence, the split returns the name after the last dot. 
            
        if len(curves):
            return War3AnimationCurve.from_fcurve(curves, data_path, sequences, scale)
        return None