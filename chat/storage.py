from cloudinary_storage.storage import RawMediaCloudinaryStorage


class AttachmentStorage(RawMediaCloudinaryStorage):
    """
    Storage for chat message attachments (PDFs, DOCX, images, etc).
    Uses Cloudinary's 'raw' resource type so file extensions and
    non-image documents are preserved and served correctly,
    unlike the default MediaCloudinaryStorage which assumes
    everything is an image.
    """
    pass