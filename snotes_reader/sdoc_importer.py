# File: sdoc_importer.py
# Location: snotes_project/snotes_reader/sdoc_importer.py
# This is the final, working version using the correct stroke identifier.

import zipfile
import struct
import gzip
import zlib
from .model import SdocDocument, SdocPage, SdocStroke, SdocPoint

class SdocImporter:
    def import_sdoc(self, path: str) -> SdocDocument:
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
        page = SdocPage()
        try:
            content = gzip.decompress(content)
        except (gzip.BadGzipFile, EOFError, zlib.error):
            pass

        offset = 16
        while offset < len(content):
            try:
                # This is a brute-force search for the header pattern we found.
                # It's less structured but more robust than assuming chunk types.
                
                # We are looking for the header pattern 0x00010000930A...
                # The key identifier seems to be b'\x93\x0A' at offset 4 in the header.
                header_id_offset = content.find(b'\x93\x0A', offset)
                if header_id_offset == -1 or header_id_offset < 4:
                    break # No more strokes found
                
                # The actual header starts 4 bytes before the identifier
                header_start = header_id_offset - 4
                
                # Now we read the full header from this position
                sub_chunk_header = content[header_start : header_start + 16]
                object_size = struct.unpack_from('<I', sub_chunk_header, 4)[0]
                
                stroke_content = content[header_start : header_start + object_size]
                stroke = self._parse_stroke(stroke_content)
                if stroke:
                    page.strokes.append(stroke)
                
                offset = header_start + object_size
                
            except (struct.error, IndexError):
                break
        return page

    def _parse_stroke(self, content: bytes) -> SdocStroke:
        stroke = SdocStroke()
        try:
            # We know the number of points is at offset 8 of the header
            num_points = struct.unpack_from('<I', content, 8)[0]
        except struct.error:
            return None

        point_data_offset = 0x30  # 48 bytes
        bytes_per_point = 12      # Assume 12 bytes (x, y, p) as the most common format
        format_string = '<fff'
        
        offset = point_data_offset
        for i in range(num_points):
            if offset + bytes_per_point > len(content):
                break
            try:
                point_data = struct.unpack_from(format_string, content, offset)
                x, y, p = point_data
                stroke.points.append(SdocPoint(x, y, p, i)) # Use index as timestamp
                offset += bytes_per_point
            except struct.error:
                break
        return stroke