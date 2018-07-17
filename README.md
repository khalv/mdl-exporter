# mdl-exporter
Warcraft MDL exporter for Blender
By Kalle Halvarsson

## Installation
* Add mdl-exporter folder to a zip or rar file
* In Blender, go to User Preferences (CTRL+ALT+U) and select "Install Add-on From File". Select your zipped folder.
* The option to export to .mdl will now appear in the export menu (you may need to restart Blender first).

## Instructions
This plugin tries to approximate the functionality of the Wc3 Art Tools exporter for 3ds Max. Due to inherent differences between the Blender and WC3 render pipelines, and my lack of knowledge in creating custom Blender GUI, some features are implemented in whatever ways would most closely match their Blender equivalent. The ambition has been to support multiple ways of achieving the same result, so that users can set up their scene in whatever way feels most intuitive. There are, however, some implementation details you might need to know before using this plugin.

### Materials
Blender uses different systems for material creation depending on which render engine is used. The intention is for this plugin to support both Cycles and Blender Internal (Blender Render) materials, with and without nodes. Since Cycles provides the most intuitive interface, it would seem favorable, but it corresponds poorly to how realtime rendered materials are constructed - for this reason, certain rules are applied for how these are translated into WC3 materials which you will find listed below. The goal is to hopefully be able to make it so that the Blender material setup required to represent a certain WC3 material would look at least approximately similar if rendered.

#### Cycles Materials (Nodes)
When exporting a material, the node tree is traversed looking for branches ending with an Image Texture node. Using Mix nodes to include two or more textuers will generate as many material layers. Mixing in certain other shaders in the same branch as the texture node can alter the properties of its material layer - for instance, mixing in a Transparent shader will set the layer filter mode to "Transparent". Using an Emissive shader instead of a Diffuse shader will make the layer unshaded. Two Transparent shaders added together might represent Additive blending (yet to be decided). Adding a Mapping node to the UV slot of a texture node and animating it corresponds to a TextureAnim. Meshes with no material will be given a default one using the texture "Textures\white.blp".

#### BI Materials
Blender Internal materials are based on textures being layered on top of each other using different blend modes, similar to how WC3 materials work. Adding texture slots and changing their blend modes should provide a similar effect in the exported file. In general, the process of exorting materials is currently poorly supported and you may need to use Magos Model Editor in order to finalize the exported model.

### Geosets
MDL files split up meshes into "geosets" based on material, where each geoset corresponds to geometry sharing the same material. As such, assigning multiple materials onto the same object will cause it to be split into as many geosets. Each geoset must be associated with at least one bone - if the mesh is not parented to a bone, one will be created for it. It is possible to skin an armature to a mesh - however, having vertices not assigned to a bone group may cause issues. Any object which isn't a mesh and whose name starts with "Bone_" can be treated as a bone. 

### Animations
It is possible to animate the position, scale and rotation of bones or meshes, but rotations currently do not export correctly. Support for axis correciton is currently experimental and does not affect animations. You can also animate an object's visibility by keyframing the "render visibility" property (you can do this by holding your mouse over the render icon in the outliner and pressing I) - optionally, you can create a custom property called "visibility" and animate that. Using the Color field of an object, you can animate vertex color (whether this works or not is yet to be confirmed). Linear, DontInterp, and Bezier interpolation modes are currently supported for scaling and translation, Wc3 rotations use Hermite instead of Bezier interpolation - this is currently has some approximate and temporary support which might not produce exactly the same result as you'd get from Wc3 Art Tools. Quaternion interpolation is very abstract and i'll fix this one i've wrapped my head around it. 

#### Sequences
To mark sequences, create timeline markers (using the M key while hovering over the timeline) and rename them (using CTRL+M) to the name of your animation. Each sequence requires both a start and an end key with the same name. This approach was chosen over using acitons because it was deemed to be more intuitive and similar to how the process works in Wc3 Art Tools. If no sequence exists, a default one will be added.

#### Global Sequences
Adding a "Cycles" modifier to an f-curve will create a global sequence around it. Global sequences always start from frame 0. Only the first channel (X for scale/rotation/translation, R for RGB color) is checked for a modifier. 

### Attachment Points
To create an attachment point, simply create an empty object and give it a name which ends with the word "Ref". For example, "Overhead Ref" will produce an attachment point called "Overhead". 

### Event Objects
Similar to attachments, event objects are created by giving an empty object a name which starts with an event type ("UBR" for UberSplat, "SND" for Sound, "FTP" for FootPrint, "SPL" for BloodSplat). The type is followed by a number ID (can be 'x'), and ends with the event identifier (you can find these in Magos Model Editor). An example of an event object is "SND1DHLB", which would produce a "Human Building Death (large)" sound. To animate the event, create a custom property called "eventtrack" and animate its value - the positions of the keyframes are used to trigger the event. 

### Cameras
Cameras are exported as-is.

### Lights
Switch to Blender Render to get more alternatives for changing the properties of your lights. Lights which are not Point or Directional will be considered Ambient. Attenuation always starts at 0 and ends with the max range of the light. Future versions will support animating range and energy values.


## To-do list
* Proper material export (supporting all workflows)
* Particle systems
* Omitting trailing zeroes for floating point numbers



