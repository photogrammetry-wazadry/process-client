import Metashape
import os

doc = Metashape.app.document
# doc.open("template.psx")

# chunk = doc.chunk
chunk = Metashape.app.document.addChunk()

images = []
for image_name in os.listdir("metashape_api/render/"):
    if image_name.split(".")[-1] == "png":
        images.append(os.path.join("metashape_api/render/", image_name))

print(images)
chunk.addPhotos(images)

chunk.matchPhotos(downscale=1, generic_preselection=False, reference_preselection=False)
chunk.alignCameras()

chunk.buildDepthMaps(downscale=4, filter_mode=Metashape.AggressiveFiltering)
chunk.buildDenseCloud()
chunk.buildModel(surface_type=Metashape.Arbitrary, interpolation=Metashape.EnabledInterpolation)

# doc.save()

output_dir = "output"
for file_name in glob(os.path.join(output_dir, "*")):
    os.remove(file_name)

chunk.exportModel(path="./output/export.obj", save_texture=False, format=Metashape.ModelFormatOBJ)
chunk.exportModel(path="./output/export.gltf", save_texture=False, format=Metashape.ModelFormatGLTF)
chunk.exportModel(path="./output/export.stl", save_texture=False, format=Metashape.ModelFormatSTL)

doc.save(path = "./output/project.psx", chunks=[doc.chunk])

# chunk.buildUV(mapping_mode=Metashape.GenericMapping)
# chunk.buildTexture(blending_mode=Metashape.MosaicBlending, texture_size=4096)
