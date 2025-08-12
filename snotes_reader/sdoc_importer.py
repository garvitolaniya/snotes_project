# File: sdoc_importer.py
# Location: snotes_project/snotes_reader/sdoc_importer.py
# This is the final, definitive version with accurate parsing logic.

import zipfile
import struct
import gzip
import zlib
from .model import SdocDocument, SdocPage, SdocStroke, SdocPoint

class SdocImporter:
    """
    Imports an .sdocx file and parses its contents, accurately handling the
    proprietary S-Pen SDK binary format.
    """
    def import_sdoc(self, path: str) -> SdocDocument:
        """Imports the document from the given path."""
        doc = SdocDocument()
        try:
            with zipfile.ZipFile(path, 'r') as sdoc_zip:
                for file_info in sdoc_zip.infolist():
                    if file_info.filename.endswith('.page'):
                        page_content = sdoc_zip.read(file_info)
                        page = self._parse_page(page_content)
                        if page:
                            doc.pages.append(page)
        except (zipfile.BadZipFile, FileNotFoundError):
            raise IOError("Failed to open or read the sdocx file.")
        return doc

    def _parse_page(self, content: bytes) -> SdocPage:
        """Parses the binary content of a single page."""
        page = SdocPage()
        try:
            content = gzip.decompress(content)
        except (gzip.BadGzipFile, EOFError, zlib.error):
            pass  # If not GZIP, use the raw content

        offset = 16  # Skip the 16-byte file header
        while offset < len(content):
            try:
                chunk_type, chunk_length = struct.unpack_from('<II', content, offset)
                offset += 8
                chunk_data_offset = offset

                if chunk_length == 0 and chunk_type == 0: break

                # Chunk type '2' is the container for page objects (strokes, images, etc.)
                if chunk_type == 2:
                    sub_offset = chunk_data_offset
                    while sub_offset < chunk_data_offset + chunk_length:
                        if sub_offset + 16 > len(content): break
                        sub_chunk_header = content[sub_offset : sub_offset + 16]
                        object_size = struct.unpack_from('<I', sub_chunk_header, 4)[0]
                        
                        if object_size == 0: break

                        # Identify stroke objects by their magic bytes (0x93A0)
                        if sub_chunk_header[0] == 0x93 and sub_chunk_header[1] == 0xA0:
                            stroke_content = content[sub_offset : sub_offset + object_size]
                            stroke = self._parse_stroke(stroke_content)
                            if stroke:
                                page.strokes.append(stroke)
                        
                        sub_offset += object_size
                
                offset = chunk_data_offset + chunk_length
            except (struct.error, IndexError):
                break
        return page

    def _parse_stroke(self, content: bytes) -> SdocStroke:
        """Parses a single stroke object's binary data with accurate logic."""
        stroke = SdocStroke()
        try:
            # Unpack number of points and a flag indicating point properties
            _, num_points, props_flag = struct.unpack_from('<III', content, 4)
        except struct.error:
            return None  # Not a valid stroke chunk

        point_data_offset = 0x30  # 48 bytes - a common starting offset for point data
        
        # Determine the size of each point's data based on the properties flag
        if props_flag in [0x1d0301, 0x1d0311]: # Formats with 5 floats per point
            bytes_per_point = 20
            format_string = '<fffff'
        elif props_flag in [0x1f0301, 0x1f0311]: # Formats with 6 floats per point
            bytes_per_point = 24
            format_string = '<ffffff'
        else:  # Default to the most common format: x, y, pressure (3 floats)
            bytes_per_point = 12
            format_string = '<fff'
        
        offset = point_data_offset
        for i in range(num_points):
            if offset + bytes_per_point > len(content):
                break
            try:
                point_data = struct.unpack_from(format_string, content, offset)
                x, y, p = point_data[0], point_data[1], point_data[2]
                
                # Assign timestamp if available, otherwise use a sequence index
                t = point_data[3] if bytes_per_point >= 20 else i

                stroke.points.append(SdocPoint(x, y, p, t))
                offset += bytes_per_point
            except struct.error:
                break
        return stroke