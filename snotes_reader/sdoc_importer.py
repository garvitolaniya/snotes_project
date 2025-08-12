# File: sdoc_importer.py
# Location: snotes_project/snotes_reader/sdoc_importer.py
# This is the definitive version, using the correct data format for your specific notes.

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

        offset = 0
        while offset < len(content):
            # We will now directly search for the unique header signature we found
            header_signature = b'\x00\x01\x00\x00\x93\x0A'
            header_start = content.find(header_signature, offset)
            
            if header_start == -1:
                break # No more strokes found
            
            try:
                header_data = content[header_start : header_start + 48] # Read enough for a full header
                object_size = struct.unpack_from('<I', header_data, 4)[0]
                
                stroke_content = content[header_start : header_start + object_size]
                stroke = self._parse_stroke(stroke_content)
                if stroke and stroke.points:
                    page.strokes.append(stroke)
                
                offset = header_start + object_size
            except (struct.error, IndexError):
                offset = header_start + 1 # Move past this point to avoid infinite loop
                
        return page

    def _parse_stroke(self, content: bytes) -> SdocStroke:
        stroke = SdocStroke()
        try:
            # Unpack the full header to get the properties flag
            # size_val, num_points, props_flag
            _, _, props_flag = struct.unpack_from('<III', content, 4)
        except struct.error:
            return None

        point_data_offset = 0x30  # 48 bytes
        
        # --- THIS IS THE CRITICAL FIX ---
        # We now check for the specific flag (0x690000) from your file
        # The value is 6881280 in decimal.
        if props_flag == 6881280:
            # This format uses 6 floats (24 bytes) per point: x, y, p, tiltX, tiltY, timestamp
            bytes_per_point = 24
            format_string = '<ffffff'
        else:
            # Fallback to the most common format
            bytes_per_point = 12
            format_string = '<fff'
        
        num_points = struct.unpack_from('<I', content, 8)[0]
        offset = point_data_offset
        
        for i in range(num_points):
            if offset + bytes_per_point > len(content):
                break
            try:
                point_data = struct.unpack_from(format_string, content, offset)
                x, y, p = point_data[0], point_data[1], point_data[2]
                
                # Use the real timestamp if available, otherwise use index
                t = point_data[5] if bytes_per_point == 24 else i

                stroke.points.append(SdocPoint(x, y, p, t))
                offset += bytes_per_point
            except (struct.error, IndexError):
                break
        return stroke