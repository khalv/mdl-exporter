if "bpy" in locals():
    import importlib
    importlib.reload(War3BillboardProperties)
    importlib.reload(War3EventProperties)
    importlib.reload(War3EventTypesContainer)
    importlib.reload(War3LightSettings)
    importlib.reload(War3MaterialLayerProperties)
    importlib.reload(War3ParticleSystemProperties)
    importlib.reload(War3SequenceProperties)
else:
    from . import War3BillboardProperties
    from . import War3EventProperties
    from . import War3EventTypesContainer
    from . import War3LightSettings
    from . import War3MaterialLayerProperties
    from . import War3ParticleSystemProperties
    from . import War3SequenceProperties

import bpy

classes = [
    War3BillboardProperties.War3BillboardProperties,
    War3EventProperties.War3EventProperties,
    War3LightSettings.War3LightSettings,
    War3MaterialLayerProperties.War3MaterialLayerProperties,
    War3ParticleSystemProperties.War3ParticleSystemProperties,
    War3SequenceProperties.War3SequenceProperties,
]