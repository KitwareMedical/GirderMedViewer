from girder.constants import AccessType
from girder.models.file import File
from girder.plugin import GirderPlugin


class MedViewerPlugin(GirderPlugin):
    DISPLAY_NAME = "GirderMedViewer Plugin"

    def load(self, _info):
        File().exposeFields(level=AccessType.READ, fields="path")
