# File: sdoc_importer.py
# Location: snotes_project/snotes_reader/sdoc_importer.py
# This is the corrected version that accurately parses stroke data.

import zipfile
import struct
import gzip
import zlib
from .model import SdocDocument, SdocPage, SdocStroke, SdocPoint

class SdocImporter:
    """
    Imports an .sdocx file and parses its contents into a structured document.
    """
    def import_sdoc(self, path: str) -> SdocDocument:
        """Imports the document from the given path."""
        doc = SdocDocument()
        with zipfile.ZipFile(path, 'r') as sdoc_zip:
            for file_info in sdoc_zip.infolist():
                # The main content is in files with a .page extension
                if file_info.filename.endswith('.page'):
                    page_content = sdoc_zip.read(file_info)
                    page = self._parse_page(page_content)
                    if page:
                        doc.pages.append(page)
        return doc

    def _parse_page(self, content: bytes) -> SdocPage:
        """Parses the binary content of a single page."""
        page = SdocPage()
        # The content might be GZIP compressed, so we try to decompress it
        try:
            content = gzip.decompress(content)
        except (gzip.BadGzipFile, EOFError, zlib.error):
            # If not GZIP, use the raw content
            pass
        
        offset = 16  # Skip the 16-byte file header
        while offset < len(content):
            try:
                # Read chunk header: 4-byte type and 4-byte length
                chunk_type, chunk_length = struct.unpack_from('<II', content, offset)
                offset += 8
                chunk_data_offset = offset

                # Prevent infinite loops from malformed chunks
                if chunk_length == 0:
                    break

                # Chunk type '2' is the container for page objects (strokes, images, etc.)
                if chunk_type == 2:
                    sub_offset = chunk_data_offset
                    while sub_offset < chunk_data_offset + chunk_length:
                        # Each object inside has its own header
                        sub_chunk_header = content[sub_offset : sub_offset + 16]
                        object_size = struct.unpack_from('<I', sub_chunk_header, 4)[0]
                        
                        # Identify stroke objects by their magic bytes (0x93A0)
                        if sub_chunk_header[0] == 0x93 and sub_chunk_header[1] == 0xA0:
                            stroke_content = content[sub_offset : sub_offset + object_size]
                            stroke = self._parse_stroke(stroke_content)
                            if stroke:
                                page.strokes.append(stroke)
                        
                        if object_size == 0:
                            break # Avoid infinite loop
                        sub_offset += object_size

                offset = chunk_data_offset + chunk_length
            except (struct.error, IndexError):
                break
        return page

    def _parse_stroke(self, content: bytes) -> SdocStroke:
        """Parses a single stroke object's binary data."""
        stroke = SdocStroke()
        # The stroke header contains metadata about the points
        try:
            # Unpack number of points and a flag indicating point properties
            _, num_points, props_flag = struct.unpack_from('<III', content, 4)
        except struct.error:
            return None # Not a valid stroke chunk

        # The actual point data often starts at a fixed offset
        point_data_offset = 0x30 # 48 bytes
        
        # Determine the size of each point's data based on the properties flag
        # This is a simplified lookup; the full format is more complex.
        if props_flag == 0x1d0301:
            bytes_per_point = 20 # x, y, p, timestamp, extra
            format_string = '<fffff'
        elif props_flag == 0x1f0301:
            bytes_per_point = 24 # x, y, p, timestamp, extra, extra
            format_string = '<ffffff'
        else: # Default to the most common format: x, y, pressure
            bytes_per_point = 12
            format_string = '<fff'

        try:
            offset = point_data_offset
            for i in range(num_points):
                if offset + bytes_per_point > len(content):
                    break
                
                try:
                    # Unpack the point data based on the format
                    values = struct.unpack_from(format_string, content, offset)
                    
                    # Create a point with the unpacked values
                    # We always use at least the first 3 values (x, y, pressure)
                    point = SdocPoint(
                        x=values[0],
                        y=values[1],
                        pressure=values[2],
                        timestamp=values[3] if len(values) > 3 else 0.0
                    )
                    stroke.points.append(point)
                except struct.error:
                    break  # Stop if we can't unpack the data
                
                offset += bytes_per_point
        except Exception:
            pass  # Return stroke even if we couldn't parse all points
        
        return stroke
"""                break
            try:
                point_data = struct.unpack_from(format_string, content, offset)
                x, y, p = point_data[0], point_data[1], point_data[2]
                
                # Check for timestamp if the format supports it
                t = point_data[3] if bytes_per_point >= 20 else i

                stroke.points.append(SdocPoint(x, y, p, t))
                offset += bytes_per_point
            except struct.error:
                break
        return stroke"""