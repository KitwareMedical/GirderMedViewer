from girder.plugin import GirderPlugin
from girder.models.file import File
from girder.constants import AccessType


class MedViewerPlugin(GirderPlugin):

    DISPLAY_NAME = "GirderMedViewer Plugin"

    def load(self, info):
        File().exposeFields(level=AccessType.READ, fields="path")
