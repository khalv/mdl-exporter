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
Blender uses different systems for material creation depending on which render engine is used. The intention is for this plugin to support both Cycles and BI materials, with and without nodes. Since Cycles provides the most intuitive interface, it would seem favorable, but it corresponds poorly to how realtime rendered materials are constructed - for this reason, certain rules are applied for how there are translated into WC3 materials. The rules for the different ways of material creation are listed below.

#### Cycles Materials (Nodes)
When exporting a material, the node tree is traversed looking for branches ending with an Image Texture node. Using a Mix node between such nodes will generate two separate material layers. Mixing in certain other shaders in the same branch as the texture node can alter its properties - for instance, mixing in a Transparent shader will set the layer filter mode to "Transparent". Using an Emissive shader instead of a Diffuse shader will make the layer unshaded. A translucent shader might later on be used to represent additive blending. Adding a Mapping node to the UV slot of a texture node and animating it corresponts to a TextureAnim. At the moment, Cycles materials must have the "Use Nodes" flag checked in order to properly export. Meshes with no material will be given a default one using the texture "Textures\white.blp".

#### BI Materials
Blender Internal materials are based on textures being layered on top of each other using different blend modes, similar to how WC3 materials work. Adding texture slots and changing their blend modes should provide a similar effect in the exported file. In general, the process of exorting materials is currently poorly supported and you may need to use Magos Model Editor in order to finalize the exported model.

### Geosets
MDL files split up meshes into "geosets" based on material, where each geoset corresponds to geometry sharing the same material. As such, assigning multiple materials onto the same object will cause it to be split into as many geosets. Each geoset must be associated with at least one bone, so of the mesh is not parented to a bone, one will be created for it. It is possible to skin an armature to a mesh - however, having vertices not assigned to a bone group may cause issues. Any object which isn't a mesh and whose name starts with "Bone_" can be treated as a bone. 

### Animations
It is possible to animate the position, scale and rotation of models, but rotations currently do not occur on the wrong axes. Support for axis correciton will come in a later version. You can also animate an objects visibility by keyframing the "render visibility" property (you can do this by holding your mouse over the render icon in the outliner and pressing I). It is also possible to create a custom property called "visibility" and animate that, or animate the viewport visibility - though the latter is not recommended for various reasons. Using the Color field of an object, you can also animate vertex color (whether this works or not is yet to be confirmed). Also note that Bezier controllers are currently unsupported, and so are Euler rotations, so make sure to set fcurves to use Linear interpolation (interpolation mode can be changed in the MDL file manually).

To mark sequences, create timeline markers (using the M key while hovering over the timeline) and rename them (using CTRL+M) to the name of your animation. Each sequence requires both a start and an end key. This approach was chosen over using different acitons because it was deemed to be more intuitive and similar to how the process looks in WC3 Art Tools. If no sequence exists, a default one will be added. 

### Attachment Points
To create an attachment point, simply create an empty object and give it a name which ends with the word "Ref". For example, "Overhead Ref" will produce an attachment point called "Overhead". 

### Event Objects
Similar to attachments, event objects are created by giving an empty object a name which starts with an event type ("UBR" for UberSplat, "SND" for Sound, "FTP" for FootPrint, "SPL" for BloodSplat). The type is followed by a number ID (can be 'x'), and ends with the event identifier (you can find these in Magos Model Editor). An example of an event object is "SND1DHLB", which would produce a "Human Building Death (large)" sound. To animate the event, create a custom property called "eventtrack" and animate its value - the positions of the keyframes are used to trigger the event. 

### Cameras
Cameras are exported as-is. 

### Lights
Switch to Blender Render to get more alternatives for changing the properties of your lights. Lights which are not Point or Directional will be considered Ambient. Attenuation always starts at 0 and ends with the max range of the light. 


## To-do list
* Axis conversion
* Proper animation support (Bezier controllers, global sequences)
* Proper material export (supporting all workflows)
* Particle systems
* Fix rounding errors causing duplicate vertices



